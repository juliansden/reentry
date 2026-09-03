"""Transport abstraction: delivers raw packet bytes to a target under test."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Transport(ABC):
    """Abstract delivery mechanism for sending packet bytes to a target."""

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Send raw bytes to the target. Must not raise on the target rejecting them."""

    @abstractmethod
    def receive(self, timeout: float) -> bytes | None:
        """Wait up to timeout for a reply; return its raw bytes, or None on timeout."""

    def probe(self, timeout: float) -> bool:
        """Convenience liveness check: True if any reply arrives within timeout."""
        return self.receive(timeout) is not None

    @abstractmethod
    def close(self) -> None:
        """Release any underlying resources (sockets, handles)."""

    def __enter__(self) -> "Transport":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
