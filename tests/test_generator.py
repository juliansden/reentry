from reentry.ccsds import constants as c
from reentry.ccsds.packet import PrimaryHeader
from reentry.generator.boundary import generate_all


def test_generate_all_covers_every_category():
    cases = generate_all()
    categories = {c.category for c in cases}
    assert categories == {
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
