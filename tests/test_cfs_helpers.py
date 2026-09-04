import json
import struct
import sys

from docker.cfs_ci_lab.resolve_ids import find_resolved_defines, main
from docker.cfs_ci_lab.render_config import main as render_config_main
from docker.cfs_ci_lab.enable_to_lab import build_add_packet, build_enable_packet
from docker.cfs_ci_lab.render_config import build_hk_request_payload
from reentry.oracle.ci_lab import parse_command_counters, parse_hk_counters, parse_ingest_counters
from reentry.oracle.base import Verdict


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


def test_resolve_ids_main_reports_partial_output_on_missing_values(tmp_path, monkeypatch, capsys):
    artifact = tmp_path / "default_cpu1" / "ci_lab_ids.json"
    artifact.parent.mkdir()
    artifact.write_text(json.dumps({"CI_LAB_CMD_MID": 0x1884}))
    output = tmp_path / "resolved_ids.json"

    monkeypatch.setattr(
        sys,
        "argv",
        ["resolve_ids.py", str(tmp_path), str(output)],
    )

    assert main() == 1
    captured = capsys.readouterr()
    assert "wrote partial" in captured.err
    assert "wrote " not in captured.out
    assert json.loads(output.read_text()) == {"CI_LAB_CMD_MID": 0x1884}


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


def test_build_hk_request_has_valid_checksum():
    packet = build_hk_request_payload(0x1885)
    assert packet[:6] == bytes.fromhex("1885c0000001")
    assert packet[6:8] == bytes((0, packet[7]))
    checksum = 0xFF
    for value in packet:
        checksum ^= value
    assert checksum == 0


def test_parse_ci_lab_counters_uses_payload_after_telemetry_header():
    packet = bytes(16) + struct.pack("<BBBBII", 0, 0, 0, 1, 3, 0)
    assert parse_command_counters(packet) == (0, 0)
    assert parse_ingest_counters(packet) == (3, 0)
    assert parse_hk_counters(packet).socket_connected == 1


def test_render_config_main_reports_missing_required_ids(tmp_path, monkeypatch, capsys):
    resolved_ids = tmp_path / "resolved_ids.json"
    resolved_ids.write_text(json.dumps({"CI_LAB_SEND_HK_MID": 0x1885, "CI_LAB_CMD_UDP_PORT": 1234, "TO_LAB_TLM_PORT": 1235}))
    output = tmp_path / "reentry.toml"
    monkeypatch.setattr(sys, "argv", ["render_config.py", str(resolved_ids), str(output)])

    assert render_config_main() == 1
    captured = capsys.readouterr()
    assert "missing" in captured.err
    assert "CI_LAB_HK_TLM_MID" in captured.err
    assert "CI_LAB_CMD_MID" in captured.err


def test_safe_drop_is_not_unsafe():
    assert Verdict.SAFE_DROP.is_unsafe is False


def test_clean_accept_is_not_unsafe():
    assert Verdict.CLEAN_ACCEPT.is_unsafe is False