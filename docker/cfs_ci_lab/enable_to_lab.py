"""Enable the cFS TO_LAB UDP telemetry output through CI_LAB."""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

from reentry.ccsds.packet import PrimaryHeader, SpacePacket


def _with_checksum(packet: bytes) -> bytes:
    data = bytearray(packet)
    data[7] = 0
    checksum = 0xFF
    for value in data:
        checksum ^= value
    data[7] = checksum
    return bytes(data)


def build_enable_packet(to_lab_cmd_mid: int, destination_ip: str) -> bytes:
    encoded_ip = destination_ip.encode("ascii")
    if len(encoded_ip) >= 16:
        raise ValueError("destination IP must fit in TO_LAB's 16-byte field")
    packet = SpacePacket(
        header=PrimaryHeader(packet_type=1, sec_hdr_flag=1, apid=to_lab_cmd_mid & 0x7FF),
        secondary_header=bytes((6, 0)),
        user_data=encoded_ip + bytes(16 - len(encoded_ip)),
    )
    return _with_checksum(packet.to_bytes())


def build_add_packet(to_lab_cmd_mid: int, stream_mid: int) -> bytes:
    packet = SpacePacket(
        header=PrimaryHeader(packet_type=1, sec_hdr_flag=1, apid=to_lab_cmd_mid & 0x7FF),
        secondary_header=bytes((2, 0)),
        user_data=stream_mid.to_bytes(4, "little") + bytes((0, 0, 1)),
    )
    return _with_checksum(packet.to_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resolved_ids", type=Path)
    parser.add_argument("--destination-ip", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    resolved = json.loads(args.resolved_ids.read_text())
    packets = (
        build_enable_packet(resolved["TO_LAB_CMD_MID"], args.destination_ip),
        build_add_packet(resolved["TO_LAB_CMD_MID"], resolved["CI_LAB_HK_TLM_MID"]),
    )
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for packet in packets:
            sock.sendto(packet, (args.host, resolved["CI_LAB_CMD_UDP_PORT"]))
    print(f"enabled TO_LAB output to {args.destination_ip} and subscribed to ci_lab HK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())