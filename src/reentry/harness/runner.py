"""Orchestrates: generate cases -> deliver via transport -> judge via oracle -> findings."""

from __future__ import annotations

import importlib
from dataclasses import asdict
from dataclasses import dataclass, field

from reentry.ccsds.packet import PrimaryHeader
from reentry.generator.boundary import generate_all
from reentry.generator.cases import PacketCase
from reentry.harness.config import RunConfig
from reentry.harness.health import ExternalHealthCheck
from reentry.harness.profiles import categories_for_profile
from reentry.oracle.base import Oracle, OracleResult, Verdict
from reentry.transport.base import Transport
from reentry.transport.udp import UDPTransport


@dataclass(frozen=True)
class Finding:
    case: PacketCase
    verdict: Verdict
    detail: str
    evidence: dict = field(default_factory=dict)
    transport_error: dict | None = None


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
    if config.health_command is not None:
        args.setdefault("health_check", ExternalHealthCheck(config.health_command, config.timeout))
    if config.oracle.plugin in {
        "reentry.oracle.liveness.LivenessOracle",
        "reentry.oracle.ci_lab.CiLabOracle",
    }:
        args.setdefault("probe_timeout", config.timeout)
    oracle = oracle_cls(**args)
    profile = config.profile
    contract = getattr(oracle, "adapter_contract", None)
    if profile is not None:
        if contract is None:
            raise ValueError(
                f"oracle plugin {config.oracle.plugin!r} does not declare adapter_contract "
                f"required for profile {profile.value!r}"
            )
        contract.validate_profile(profile.value)
    return oracle


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
                result: OracleResult = oracle.judge(case, transport)
                findings.append(
                    Finding(
                        case=case,
                        verdict=result.verdict,
                        detail=result.detail,
                        evidence=result.evidence,
                        transport_error=(
                            asdict(result.transport_error)
                            if result.transport_error is not None
                            else None
                        ),
                    )
                )
        return findings
