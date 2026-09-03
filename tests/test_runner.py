import threading

from reentry.generator.cases import PacketCase
from reentry.harness.config import OracleConfig, RunConfig, TransportConfig
from reentry.harness.runner import Runner, _build_transport, _load_oracle
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
