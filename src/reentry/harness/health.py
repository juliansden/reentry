"""External target health checks used to classify liveness failures."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthResult:
    alive: bool
    detail: str


class ExternalHealthCheck:
    """Runs a configured command where exit status 0 means the target is alive."""

    def __init__(self, command: list[str], timeout: float) -> None:
        self._command = tuple(command)
        self._timeout = timeout

    def __call__(self) -> HealthResult:
        try:
            completed = subprocess.run(
                self._command,
                capture_output=True,
                check=False,
                timeout=self._timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return HealthResult(False, f"health check failed: {error}")
        if completed.returncode == 0:
            return HealthResult(True, "health check reported target alive")
        return HealthResult(
            False,
            f"health check exited with status {completed.returncode}",
        )