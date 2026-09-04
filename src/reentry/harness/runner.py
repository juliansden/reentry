"""Orchestrates: generate cases -> deliver via transport -> judge via oracle -> findings."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from reentry.ccsds.packet import PrimaryHeader
from reentry.generator.boundary import generate_all
from reentry.generator.cases import PacketCase
from reentry.harness.config import RunConfig
from reentry.harness.profiles import categories_for_profile
from reentry.oracle.base import Oracle, Verdict
from reentry.transport.base import Transport
from reentry.transport.udp import UDPTransport


@dataclass(frozen=True)
class Finding:
    case: PacketCase
    verdict: Verdict
    detail: str
    evidence: dict = field(default_factory=dict)


def _with_command_checksum(packet: bytes) -> bytes:
    if len(packet) < 8:
        return packet
    data = bytearray(packet)
    data[7] = 0
    checksum = 0xFF
    for value in data:
        checksum ^= value
    data[7] = checksum
    return bytes(data)


def _load_oracle(config: RunConfig) -> Oracle:
    module_path, _, class_name = config.oracle.plugin.rpartition(".")
    oracle_cls = getattr(importlib.import_module(module_path), class_name)
    args = dict(config.oracle.args)
    if config.oracle.plugin in {
        "reentry.oracle.liveness.LivenessOracle",
        "reentry.oracle.ci_lab.CiLabOracle",
    }:
        args.setdefault("probe_timeout", config.timeout)
    return oracle_cls(**args)


def _build_transport(config: RunConfig) -> Transport:
    t = config.transport
    if t.kind != "udp":
        raise ValueError(f"unsupported transport kind: {t.kind!r}")
    return UDPTransport(
        host=t.host,
        port=t.port,
        probe_payload=t.probe_payload,
        listen_port=t.listen_port,
        allowed_reply_host=t.allowed_reply_host,
        allowed_reply_apid=t.allowed_reply_apid,
    )


def _select_cases(config: RunConfig) -> list[PacketCase]:
    cases = generate_all()
    if config.transport.target_apid is not None:
        targeted = []
        for case in cases:
            if case.category == "apid" or len(case.packet_bytes) < 6:
                targeted.append(case)
                continue
            header = PrimaryHeader.unpack(case.packet_bytes)
            header.apid = config.transport.target_apid
            header.packet_type = 1
            if case.category != "secondary_header":
                header.sec_hdr_flag = 1
            packet = header.pack() + case.packet_bytes[6:]
            if case.category != "secondary_header":
                packet = _with_command_checksum(packet)
                if not case.checksum_valid and len(packet) >= 8:
                    damaged = bytearray(packet)
                    damaged[7] ^= 0x01
                    packet = bytes(damaged)
            targeted.append(
                PacketCase(
                    name=case.name,
                    category=case.category,
                    packet_bytes=packet,
                    expect_safe_reject=case.expect_safe_reject,
                    expect_accept=case.expect_accept,
                    checksum_valid=case.checksum_valid,
                )
            )
        cases = targeted
    include_categories = config.include_categories
    if config.profile is not None:
        include_categories = categories_for_profile(config.profile)
    if include_categories is not None:
        cases = [c for c in cases if c.category in include_categories]
    if config.exclude_categories:
        cases = [c for c in cases if c.category not in config.exclude_categories]
    return cases


class Runner:
    def __init__(self, config: RunConfig) -> None:
        self._config = config

    def run(self) -> list[Finding]:
        cases = _select_cases(self._config)
        oracle = _load_oracle(self._config)
        findings: list[Finding] = []
        with _build_transport(self._config) as transport:
            for case in cases:
                verdict, detail = oracle.judge(case, transport)
                findings.append(
                    Finding(
                        case=case,
                        verdict=verdict,
                        detail=detail,
                        evidence=getattr(oracle, "last_evidence", {}),
                    )
                )
        return findings
