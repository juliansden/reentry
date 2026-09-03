import json

from docker.cfs_ci_lab.resolve_ids import find_resolved_defines
from docker.cfs_ci_lab.enable_to_lab import build_add_packet, build_enable_packet


def test_find_resolved_defines_reads_build_artifact(tmp_path):
    artifact = tmp_path / "default_cpu1" / "ci_lab_ids.json"
    artifact.parent.mkdir()
    artifact.write_text(
        json.dumps(
            {
                "CI_LAB_CMD_MID": 0x1884,
                "CI_LAB_SEND_HK_MID": 0x1885,
                "CI_LAB_CMD_UDP_PORT": 1234,
            }
        )
    )

    assert find_resolved_defines(tmp_path) == {
        "CI_LAB_CMD_MID": 0x1884,
        "CI_LAB_SEND_HK_MID": 0x1885,
        "CI_LAB_CMD_UDP_PORT": 1234,
    }


def test_find_resolved_defines_returns_empty_without_artifact(tmp_path):
    assert find_resolved_defines(tmp_path) == {}


def test_build_enable_packet_has_valid_checksum_and_payload():
    packet = build_enable_packet(0x1880, "127.0.0.1")
    assert packet[:6] == bytes.fromhex("1880c0000011")
    assert packet[6] == 6
    assert packet[8:17] == b"127.0.0.1"
    assert len(packet) == 24
    checksum = 0xFF
    for value in packet:
        checksum ^= value
    assert checksum == 0


def test_build_add_packet_has_valid_checksum_and_stream():
    packet = build_add_packet(0x1880, 0x0884)
    assert packet[6] == 2
    assert packet[8:12] == bytes.fromhex("84080000")
    assert packet[12:15] == bytes((0, 0, 1))
    checksum = 0xFF
    for value in packet:
        checksum ^= value
    assert checksum == 0