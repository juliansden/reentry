"""CCSDS Space Packet primary header and packet container (CCSDS 133.0-B-2).

Construction is deliberately permissive: callers can build headers/packets with
out-of-spec field values or mismatched lengths so the fuzz generator can exercise
a target with malformed input. Use `validate()` to check spec conformance.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from reentry.ccsds import constants as c


@dataclass
class PrimaryHeader:
    version: int = c.VERSION_CCSDS
    packet_type: int = 0
    sec_hdr_flag: int = 0
    apid: int = 0
    seq_flags: int = c.SEQ_FLAGS_UNSEGMENTED
    seq_count: int = 0
    packet_data_length_field: int = 0  # raw field value: (octets after header) - 1

    def pack(self) -> bytes:
        word0 = (
            ((self.version & 0x7) << 13)
            | ((self.packet_type & 0x1) << 12)
            | ((self.sec_hdr_flag & 0x1) << 11)
            | (self.apid & c.APID_MAX)
        )
        word1 = ((self.seq_flags & 0x3) << 14) | (self.seq_count & c.SEQ_COUNT_MAX)
        word2 = self.packet_data_length_field & c.PACKET_DATA_LENGTH_MAX
        return struct.pack(">HHH", word0, word1, word2)

    @classmethod
    def unpack(cls, data: bytes) -> "PrimaryHeader":
        if len(data) < c.PRIMARY_HEADER_SIZE:
            raise ValueError(
                f"need at least {c.PRIMARY_HEADER_SIZE} bytes for a primary header, got {len(data)}"
            )
        word0, word1, word2 = struct.unpack(">HHH", data[: c.PRIMARY_HEADER_SIZE])
        return cls(
            version=(word0 >> 13) & 0x7,
            packet_type=(word0 >> 12) & 0x1,
            sec_hdr_flag=(word0 >> 11) & 0x1,
            apid=word0 & c.APID_MAX,
            seq_flags=(word1 >> 14) & 0x3,
            seq_count=word1 & c.SEQ_COUNT_MAX,
            packet_data_length_field=word2,
        )

    @property
    def data_length(self) -> int:
        """Actual octet count of (secondary header + user data) implied by the field."""
        return self.packet_data_length_field + 1

    def validate(self) -> list[str]:
        issues = []
        if self.version != c.VERSION_CCSDS:
            issues.append(f"version field is {self.version}, expected {c.VERSION_CCSDS}")
        if self.apid == c.APID_IDLE:
            issues.append("APID is the reserved idle value (0x7FF)")
        return issues


@dataclass
class SpacePacket:
    header: PrimaryHeader
    secondary_header: bytes = b""
    user_data: bytes = b""
    # Overrides the packet-data-length field written on to_bytes(); None = derive from payload.
    declared_data_length: int | None = field(default=None)

    def to_bytes(self) -> bytes:
        payload = self.secondary_header + self.user_data
        header = self.header
        length_field = (
            self.declared_data_length
            if self.declared_data_length is not None
            else max(len(payload) - 1, 0)
        )
        header = PrimaryHeader(
            version=header.version,
            packet_type=header.packet_type,
            sec_hdr_flag=header.sec_hdr_flag,
            apid=header.apid,
            seq_flags=header.seq_flags,
            seq_count=header.seq_count,
            packet_data_length_field=length_field,
        )
        return header.pack() + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "SpacePacket":
        header = PrimaryHeader.unpack(data)
        return cls(header=header, user_data=data[c.PRIMARY_HEADER_SIZE :])

    def validate(self) -> list[str]:
        issues = list(self.header.validate())
        actual_payload_len = len(self.secondary_header) + len(self.user_data)
        if self.header.data_length != actual_payload_len:
            issues.append(
                f"packet-data-length field implies {self.header.data_length} octets, "
                f"actual payload is {actual_payload_len} octets"
            )
        total_size = c.PRIMARY_HEADER_SIZE + actual_payload_len
        if total_size > c.MAX_PACKET_SIZE:
            issues.append(f"total packet size {total_size} exceeds max {c.MAX_PACKET_SIZE}")
        return issues
