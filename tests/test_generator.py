from reentry.ccsds import constants as c
from reentry.ccsds.packet import PrimaryHeader
from reentry.generator.boundary import generate_all


def test_generate_all_covers_every_category():
    cases = generate_all()
    categories = {c.category for c in cases}
    assert categories == {
        "known_good",
        "command_malformed",
        "version",
        "apid",
        "seq_flags",
        "packet_length",
        "secondary_header",
        "truncation",
        "oversized",
        "degenerate_payload",
    }


def test_generate_all_names_are_unique():
    cases = generate_all()
    names = [c.name for c in cases]
    assert len(names) == len(set(names))


def test_generate_all_nonempty_per_category():
    cases = generate_all()
    by_category: dict[str, int] = {}
    for case in cases:
        by_category[case.category] = by_category.get(case.category, 0) + 1
    assert all(count > 0 for count in by_category.values())


def test_oversized_reachable_is_length_consistent_and_4k_total():
    case = next(c for c in generate_all() if c.name == "oversized_reachable")
    header = PrimaryHeader.unpack(case.packet_bytes)
    assert len(case.packet_bytes) == 4 * 1024
    assert header.data_length == len(case.packet_bytes) - c.PRIMARY_HEADER_SIZE


def test_known_good_noop_has_valid_command_shape_and_checksum():
    case = next(c for c in generate_all() if c.name == "ci_lab_noop")
    header = PrimaryHeader.unpack(case.packet_bytes)

    assert case.expect_accept is True
    assert case.expect_safe_reject is False
    assert header.packet_type == 1
    assert header.seq_flags == c.SEQ_FLAGS_UNSEGMENTED
    assert header.sec_hdr_flag == 1
    assert header.data_length == 2
    assert case.packet_bytes[6] == 0

    checksum = 0xFF
    for value in case.packet_bytes:
        checksum ^= value
    assert checksum == 0
