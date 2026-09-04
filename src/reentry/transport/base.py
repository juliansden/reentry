"""Transport abstraction: delivers raw packet bytes to a target under test."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TransportError:
    """Structured evidence for a failed transport operation."""

    operation: str
    error_type: str
    message: str
    errno: int | None = None
    packet_length: int | None = None
    destination: tuple[str, int] | None = None


class Transport(ABC):
    """Abstract delivery mechanism for sending packet bytes to a target."""

    last_error: TransportError | None = None

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Send raw bytes to the target. Must not raise on the target rejecting them."""

    @abstractmethod
    def receive(self, timeout: float) -> bytes | None:
        """Wait up to timeout for a reply; return its raw bytes, or None on timeout."""

    def probe(self, timeout: float) -> bool:
        """Convenience liveness check: True if any reply arrives within timeout."""
        return self.receive(timeout) is not None

    def drain_stale_replies(self) -> None:
        """Discard replies already queued before a new request."""

    @abstractmethod
    def close(self) -> None:
        """Release any underlying resources (sockets, handles)."""

    def __enter__(self) -> "Transport":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
