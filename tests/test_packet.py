from reentry.ccsds import constants as c
from reentry.ccsds.packet import PrimaryHeader, SpacePacket


def test_primary_header_round_trip():
    header = PrimaryHeader(
        version=0, packet_type=1, sec_hdr_flag=0, apid=42, seq_flags=0b11, seq_count=100
    )
    data = header.pack()
    assert len(data) == c.PRIMARY_HEADER_SIZE
    parsed = PrimaryHeader.unpack(data)
    assert parsed == header


def test_primary_header_unpack_too_short_raises():
    try:
        PrimaryHeader.unpack(b"\x00\x00\x00")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_primary_header_validate_flags_bad_version():
    header = PrimaryHeader(version=3)
    assert any("version" in issue for issue in header.validate())


def test_primary_header_validate_flags_idle_apid():
    header = PrimaryHeader(apid=c.APID_IDLE)
    assert any("idle" in issue for issue in header.validate())


def test_space_packet_round_trip_derives_length_field():
    header = PrimaryHeader(apid=7)
    packet = SpacePacket(header=header, user_data=b"\x01\x02\x03\x04")
    data = packet.to_bytes()
    parsed = SpacePacket.from_bytes(data)
    assert parsed.header.data_length == 4
    assert parsed.user_data == b"\x01\x02\x03\x04"
    assert parsed.validate() == []


def test_space_packet_validate_detects_length_mismatch():
    header = PrimaryHeader(apid=7)
    packet = SpacePacket(header=header, user_data=b"\x01\x02", declared_data_length=99)
    issues = packet.validate()
    assert any("packet-data-length" in issue for issue in issues)


def test_space_packet_validate_detects_oversized_packet():
    header = PrimaryHeader(apid=7)
    packet = SpacePacket(
        header=header,
        user_data=b"\x00" * (c.MAX_PACKET_DATA_LENGTH + 1),
        declared_data_length=c.PACKET_DATA_LENGTH_MAX,
    )
    issues = packet.validate()
    assert any("exceeds max" in issue for issue in issues)
