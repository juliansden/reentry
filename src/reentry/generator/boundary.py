"""Deterministic boundary-value packet builders exercising CCSDS Space Packet edge cases.

Each `build_*` function returns a list of `TestCase`. `generate_all()` aggregates them.
All cases are constructed to be unambiguously invalid or degenerate, so a
spec-conformant target is expected to reject every one of them cleanly.
"""

from __future__ import annotations

from reentry.ccsds import constants as c
from reentry.ccsds.packet import PrimaryHeader, SpacePacket
from reentry.generator.cases import PacketCase


def _valid_header(**overrides: int) -> PrimaryHeader:
    header = PrimaryHeader(apid=42, seq_flags=c.SEQ_FLAGS_UNSEGMENTED, seq_count=1)
    for key, value in overrides.items():
        setattr(header, key, value)
    return header


def _with_command_checksum(packet: bytes) -> bytes:
    data = bytearray(packet)
    data[7] = 0
    checksum = 0xFF
    for value in data:
        checksum ^= value
    data[7] = checksum
    return bytes(data)


def build_known_good_noop_case(apid: int = 42) -> list[PacketCase]:
    """Build a valid cFE command with CI_LAB's NOOP function code (zero)."""
    header = _valid_header(packet_type=1, sec_hdr_flag=1, apid=apid)
    packet = SpacePacket(header=header, secondary_header=b"\x00\x00")
    return [
        PacketCase(
            name="ci_lab_noop",
            category="known_good",
            packet_bytes=_with_command_checksum(packet.to_bytes()),
            expect_safe_reject=False,
            expect_accept=True,
        )
    ]


def build_command_malformed_cases() -> list[PacketCase]:
    """Build CI_LAB commands with one controlled command-level defect each."""
    valid = build_known_good_noop_case()[0].packet_bytes
    cases = []

    bad_checksum = bytearray(valid)
    bad_checksum[7] ^= 0x01
    cases.append(
        PacketCase(
            name="command_bad_checksum",
            category="command_malformed",
            packet_bytes=bytes(bad_checksum),
            expect_safe_reject=True,
            checksum_valid=False,
        )
    )

    invalid_function = bytearray(valid)
    invalid_function[6] = 0xFF
    cases.append(
        PacketCase(
            name="command_invalid_function",
            category="command_malformed",
            packet_bytes=_with_command_checksum(bytes(invalid_function)),
            expect_safe_reject=True,
        )
    )

    wrong_length = bytearray(valid)
    wrong_length[4:6] = (2).to_bytes(2, "big")
    cases.append(
        PacketCase(
            name="command_wrong_length",
            category="command_malformed",
            packet_bytes=_with_command_checksum(bytes(wrong_length)),
            expect_safe_reject=True,
        )
    )
    return cases


def build_version_cases() -> list[PacketCase]:
    cases = []
    for version in range(1, c.VERSION_MAX + 1):
        header = _valid_header(version=version)
        packet = SpacePacket(header=header, user_data=b"\x00\x01\x02\x03")
        cases.append(
            PacketCase(
                name=f"version_{version}",
                category="version",
                packet_bytes=packet.to_bytes(),
                expect_safe_reject=True,
            )
        )
    return cases


def build_apid_cases() -> list[PacketCase]:
    edge_apids = {0, c.APID_IDLE, c.APID_MAX // 2}
    cases = []
    for apid in sorted(edge_apids):
        header = _valid_header(apid=apid)
        packet = SpacePacket(header=header, user_data=b"\x00\x01\x02\x03")
        cases.append(
            PacketCase(
                name=f"apid_{apid}",
                category="apid",
                packet_bytes=packet.to_bytes(),
                # Idle APID is spec-valid but should never be treated as a command;
                # the mid-range APID here is likely unassigned on the target.
                expect_safe_reject=True,
            )
        )
    return cases


def build_seq_flags_cases() -> list[PacketCase]:
    cases = []
    for flags in (
        c.SEQ_FLAGS_CONTINUATION,
        c.SEQ_FLAGS_FIRST,
        c.SEQ_FLAGS_LAST,
        c.SEQ_FLAGS_UNSEGMENTED,
    ):
        header = _valid_header(seq_flags=flags)
        packet = SpacePacket(header=header, user_data=b"\x00\x01\x02\x03")
        cases.append(
            PacketCase(
                name=f"seq_flags_{flags:02b}",
                category="seq_flags",
                packet_bytes=packet.to_bytes(),
                # Only unsegmented (11) is valid for a single-packet command; the rest
                # imply segmentation this harness's target does not support.
                expect_safe_reject=(flags != c.SEQ_FLAGS_UNSEGMENTED),
            )
        )
    return cases


def build_packet_length_cases() -> list[PacketCase]:
    payload = b"\x00\x01\x02\x03"
    scenarios = {
        "length_zero": 0,
        "length_max": c.PACKET_DATA_LENGTH_MAX,
        "length_claims_more_than_sent": len(payload) + 100 - 1,
        "length_claims_less_than_sent": max(len(payload) - 100 - 1, 0),
    }
    cases = []
    for name, declared in scenarios.items():
        header = _valid_header()
        packet = SpacePacket(header=header, user_data=payload, declared_data_length=declared)
        cases.append(
            PacketCase(
                name=name,
                category="packet_length",
                packet_bytes=packet.to_bytes(),
                expect_safe_reject=True,
            )
        )
    return cases


def build_secondary_header_flag_cases() -> list[PacketCase]:
    cases = []
    # Flag set but no secondary header bytes actually present.
    header = _valid_header(sec_hdr_flag=1)
    packet = SpacePacket(header=header, user_data=b"\x00\x01\x02\x03")
    cases.append(
        PacketCase(
            name="sec_hdr_flag_set_but_absent",
            category="secondary_header",
            packet_bytes=packet.to_bytes(),
            expect_safe_reject=True,
        )
    )
    # Flag clear but data laid out as if a secondary header were present: this is
    # framing-valid (indistinguishable from plain user data without app knowledge),
    # so no reject is expected — only crash/hang on it would be a real finding.
    header = _valid_header(sec_hdr_flag=0)
    packet = SpacePacket(header=header, secondary_header=b"\xff\xff", user_data=b"\x00\x01")
    cases.append(
        PacketCase(
            name="sec_hdr_flag_clear_but_present",
            category="secondary_header",
            packet_bytes=packet.to_bytes(),
            expect_safe_reject=False,
        )
    )
    return cases


def build_truncation_cases() -> list[PacketCase]:
    cases = []
    for size in range(0, c.PRIMARY_HEADER_SIZE):
        header = _valid_header()
        full = header.pack()
        cases.append(
            PacketCase(
                name=f"truncated_{size}_bytes",
                category="truncation",
                packet_bytes=full[:size],
                expect_safe_reject=True,
            )
        )
    return cases


def build_oversized_cases() -> list[PacketCase]:
    cases = []
    header = _valid_header()
    reachable_packet_size = 4 * 1024
    reachable_payload = b"\x00" * (reachable_packet_size - c.PRIMARY_HEADER_SIZE)
    packet = SpacePacket(
        header=header,
        user_data=reachable_payload,
        declared_data_length=len(reachable_payload) - 1,
    )
    cases.append(
        PacketCase(
            name="oversized_reachable",
            category="oversized",
            packet_bytes=packet.to_bytes(),
            expect_safe_reject=True,
        )
    )
    max_payload = c.MAX_PACKET_DATA_LENGTH
    packet = SpacePacket(
        header=header,
        user_data=b"\x00" * max_payload,
        declared_data_length=max_payload - 1,
    )
    cases.append(
        PacketCase(
            name="oversized_max_spec_size",
            category="oversized",
            packet_bytes=packet.to_bytes(),
            expect_safe_reject=True,
        )
    )
    # One octet beyond the largest length the field can represent.
    over_max_payload = b"\x00" * (max_payload + 1)
    packet = SpacePacket(
        header=header,
        user_data=over_max_payload,
        declared_data_length=c.PACKET_DATA_LENGTH_MAX,
    )
    cases.append(
        PacketCase(
            name="oversized_beyond_field_range",
            category="oversized",
            packet_bytes=packet.to_bytes(),
            expect_safe_reject=True,
        )
    )
    return cases


def build_degenerate_payload_cases() -> list[PacketCase]:
    cases = []
    header = _valid_header()
    # all_zero/all_ff are framing-valid (no structural violation, just odd content);
    # only the length-field lie below is a genuine spec violation.
    for name, payload, expect_safe_reject in (
        ("all_zero", b"\x00" * 16, False),
        ("all_ff", b"\xff" * 16, False),
        ("empty_but_length_nonzero", b"", True),
    ):
        declared = 15 if expect_safe_reject else None  # claim 16 octets while sending none
        packet = SpacePacket(header=header, user_data=payload, declared_data_length=declared)
        cases.append(
            PacketCase(
                name=f"degenerate_{name}",
                category="degenerate_payload",
                packet_bytes=packet.to_bytes(),
                expect_safe_reject=expect_safe_reject,
            )
        )
    return cases


def generate_all() -> list[PacketCase]:
    builders = (
        build_known_good_noop_case,
        build_command_malformed_cases,
        build_version_cases,
        build_apid_cases,
        build_seq_flags_cases,
        build_packet_length_cases,
        build_secondary_header_flag_cases,
        build_truncation_cases,
        build_oversized_cases,
        build_degenerate_payload_cases,
    )
    cases: list[PacketCase] = []
    for builder in builders:
        cases.extend(builder())
    return cases
