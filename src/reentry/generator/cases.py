"""Test case container produced by the boundary-condition generator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PacketCase:
    name: str
    category: str
    packet_bytes: bytes
    # True if a spec-conformant target should reject this input.
    expect_safe_reject: bool
    # True if this is an explicit known-good command expected to be accepted.
    expect_accept: bool = False
    # False when a deliberately malformed checksum must survive APID retargeting.
    checksum_valid: bool = True
