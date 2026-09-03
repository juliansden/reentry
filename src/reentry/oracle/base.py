"""Oracle abstraction: judges whether a target handled a test case safely."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from reentry.generator.cases import PacketCase
from reentry.transport.base import Transport


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


class Oracle(ABC):
    """Judges the outcome of sending one `TestCase` to a target via `Transport`."""

    @abstractmethod
    def judge(self, case: PacketCase, transport: Transport) -> tuple[Verdict, str]:
        """Send/observe as needed and return (verdict, human-readable detail)."""
