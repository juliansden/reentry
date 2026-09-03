"""Default oracle: liveness/timeout only, no target-specific telemetry knowledge."""

from __future__ import annotations

from reentry.generator.cases import PacketCase
from reentry.oracle.base import Oracle, Verdict
from reentry.transport.base import Transport


class LivenessOracle(Oracle):
    """Judges CRASH/HANG from a post-send liveness probe; can't see accept/reject.

    Without application-specific telemetry, a response to the probe only proves the
    target is still alive — it cannot distinguish a clean reject from an unexpected
    accept, so anything that isn't CRASH/HANG is reported INCONCLUSIVE.
    """

    def __init__(self, probe_timeout: float = 2.0) -> None:
        self._probe_timeout = probe_timeout

    def judge(self, case: PacketCase, transport: Transport) -> tuple[Verdict, str]:
        transport.send(case.packet_bytes)
        if transport.probe(self._probe_timeout):
            return Verdict.INCONCLUSIVE, "target responded to liveness probe after the case"
        return Verdict.HANG, "no response to liveness probe within timeout (possible hang/crash)"
