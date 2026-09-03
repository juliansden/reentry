import threading

from reentry.generator.cases import PacketCase
from reentry.harness.config import OracleConfig, RunConfig, TransportConfig
from reentry.harness.runner import Runner, _build_transport, _load_oracle, _select_cases
from reentry.ccsds.packet import PrimaryHeader
from tests.fixtures.mock_target import MockTarget


def _start_target(buggy: bool) -> int:
    target = MockTarget("127.0.0.1", 0, buggy=buggy)
    port = target._sock.getsockname()[1]
    threading.Thread(target=target.serve_forever, daemon=True).start()
    return port


def _config(port: int, include_categories=None) -> RunConfig:
    return RunConfig(
        transport=TransportConfig(host="127.0.0.1", port=port, probe_payload_hex="484b3f"),
        oracle=OracleConfig(
            plugin="reentry.oracle.ci_lab.CiLabOracle",
            args={"hk_request_payload_hex": "484b3f", "probe_timeout": 0.3},
        ),
        include_categories=include_categories,
    )


def test_runner_against_well_behaved_mock_target_has_no_unsafe_findings():
    port = _start_target(buggy=False)
    findings = Runner(_config(port)).run()
    unsafe = [f for f in findings if f.verdict.is_unsafe]
    assert unsafe == []


def test_runner_against_buggy_mock_target_detects_crash():
    # Deliberately over the mock's 2048-byte buggy threshold but still small enough
    # to actually go out over loopback UDP (the generator's spec-max oversized cases
    # exceed what UDP can carry at all, so they never reach the target to trigger this).
    port = _start_target(buggy=True)
    config = _config(port)
    oracle = _load_oracle(config)
    case = PacketCase(
        name="deliverable_oversized",
        category="oversized",
        packet_bytes=b"\x00" * 4096,
        expect_safe_reject=True,
    )
    with _build_transport(config) as transport:
        verdict, _detail = oracle.judge(case, transport)
    # v1 oracles can't distinguish a crashed process from a hung one over bare UDP;
    # both surface as HANG, which is what matters for CI gating (an unsafe finding).
    assert verdict.is_unsafe


def test_select_cases_retargets_to_valid_command_mid():
    target_apid = 0x84
    config = RunConfig(transport=TransportConfig(host="127.0.0.1", port=1234, target_apid=target_apid))
    cases = _select_cases(config)

    for case in cases:
        if case.category == "apid" or len(case.packet_bytes) < 8 or case.category == "secondary_header":
            continue
        header = PrimaryHeader.unpack(case.packet_bytes)
        assert header.apid == target_apid
        assert header.packet_type == 1
        assert header.sec_hdr_flag == 1
        checksum = 0xFF
        for value in case.packet_bytes:
            checksum ^= value
        assert checksum == 0


def test_select_cases_preserves_secondary_header_flag_cases():
    target_apid = 0x84
    config = RunConfig(transport=TransportConfig(host="127.0.0.1", port=1234, target_apid=target_apid))
    cases = {case.name: case for case in _select_cases(config)}

    set_case = PrimaryHeader.unpack(cases["sec_hdr_flag_set_but_absent"].packet_bytes)
    clear_case = PrimaryHeader.unpack(cases["sec_hdr_flag_clear_but_present"].packet_bytes)

    assert set_case.apid == target_apid
    assert clear_case.apid == target_apid
    assert set_case.sec_hdr_flag == 1
    assert clear_case.sec_hdr_flag == 0
