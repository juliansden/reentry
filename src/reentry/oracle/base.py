"""Oracle abstraction: judges whether a target handled a test case safely."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from reentry.generator.cases import PacketCase
from reentry.transport.base import Transport, TransportError


class Verdict(str, Enum):
    CLEAN_ACCEPT = "clean_accept"
    CLEAN_REJECT = "clean_reject"
    SAFE_DROP = "safe_drop"
    CRASH = "crash"
    HANG = "hang"
    UNEXPECTED_ACCEPT = "unexpected_accept"
    INCONCLUSIVE = "inconclusive"

    @property
    def is_unsafe(self) -> bool:
        return self in (Verdict.CRASH, Verdict.HANG, Verdict.UNEXPECTED_ACCEPT)


@dataclass(frozen=True)
class OracleResult:
    verdict: Verdict
    detail: str
    evidence: dict = field(default_factory=dict)
    transport_error: TransportError | None = None


class Oracle(ABC):
    """Judges the outcome of sending one `TestCase` to a target via `Transport`."""

    @abstractmethod
    def judge(self, case: PacketCase, transport: Transport) -> OracleResult:
        """Send/observe as needed and return a structured result."""
