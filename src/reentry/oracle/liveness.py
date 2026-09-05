"""Default oracle: liveness/timeout only, no target-specific telemetry knowledge."""

from __future__ import annotations

from reentry.generator.cases import PacketCase
from reentry.harness.adapters import LIVENESS_CONTRACT, AdapterContract
from reentry.harness.health import HealthResult
from reentry.oracle.base import Oracle, OracleResult, Verdict
from reentry.transport.base import Transport


class LivenessOracle(Oracle):
    """Judges CRASH/HANG from a post-send liveness probe; can't see accept/reject.

    Without application-specific telemetry, a response to the probe only proves the
    target is still alive — it cannot distinguish a clean reject from an unexpected
    accept, so anything that isn't CRASH/HANG is reported INCONCLUSIVE.
    """

    adapter_contract: AdapterContract = LIVENESS_CONTRACT

    def __init__(self, probe_timeout: float = 2.0, health_check=None) -> None:
        self._probe_timeout = probe_timeout
        self._health_check = health_check

    def _health_result(self) -> HealthResult | None:
        return self._health_check() if self._health_check is not None else None

    def judge(self, case: PacketCase, transport: Transport) -> OracleResult:
        transport.send(case.packet_bytes)
        if transport.last_error is not None:
            return OracleResult(
                Verdict.INCONCLUSIVE,
                "transport failed while sending the case",
                transport_error=transport.last_error,
            )
        if transport.probe(self._probe_timeout):
            return OracleResult(
                Verdict.INCONCLUSIVE,
                "target responded to liveness probe after the case",
            )
        if transport.last_error is not None:
            return OracleResult(
                Verdict.INCONCLUSIVE,
                "transport failed while probing target liveness",
                transport_error=transport.last_error,
            )
        health = self._health_result()
        if health is not None and not health.alive:
            return OracleResult(
                Verdict.CRASH,
                health.detail,
                evidence={"health": {"alive": health.alive, "detail": health.detail}},
            )
        evidence = {} if health is None else {
            "health": {"alive": health.alive, "detail": health.detail}
        }
        return OracleResult(
            Verdict.HANG,
            "no response to liveness probe within timeout (target still reports alive)"
            if health is not None
            else "no response to liveness probe within timeout (possible hang/crash)",
            evidence=evidence,
        )
