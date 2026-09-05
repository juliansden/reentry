"""Renders a real reentry.toml for the ci_lab sandbox from resolve_ids.py's output.

Builds the actual HK-request packet bytes using reentry's own CCSDS library (not
hand-rolled bytes), so the wire format stays consistent with the rest of the project.

CI_LAB_SEND_HK_MID's numeric value is mapped to an APID via the classic CFE MsgId
encoding (APID = MID & 0x7FF). Command packets use cFE's XOR checksum convention.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reentry.ccsds.packet import PrimaryHeader, SpacePacket

APID_MASK = 0x07FF


def _with_checksum(packet: bytes) -> bytes:
    data = bytearray(packet)
    data[7] = 0
    checksum = 0xFF
    for value in data:
        checksum ^= value
    data[7] = checksum
    return bytes(data)

TOML_TEMPLATE = """\
# Auto-rendered by render_config.py from resolve_ids.py's output — do not hand-edit.
resolved_identifiers = {{ {resolved_identifiers} }}

[transport]
kind = "udp"
host = "{host}"
port = {port}
listen_port = {listen_port}
allowed_reply_host = "{allowed_reply_host}"
allowed_reply_apid = {allowed_reply_apid}
target_apid = {target_apid}
probe_payload_hex = "{payload_hex}"

[oracle]
plugin = "reentry.oracle.ci_lab.CiLabOracle"

[oracle.args]
hk_request_payload_hex = "{payload_hex}"
"""


def build_hk_request_payload(send_hk_mid: int) -> bytes:
    header = PrimaryHeader(
        version=0,
        packet_type=1,  # command
        sec_hdr_flag=1,
        apid=send_hk_mid & APID_MASK,
        seq_flags=0b11,
        seq_count=0,
    )
    # cFE command secondary header: function code + checksum.
    secondary_header = bytes([0x00, 0x00])
    packet = SpacePacket(header=header, secondary_header=secondary_header)
    return _with_checksum(packet.to_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resolved_ids", type=Path, help="Path to resolve_ids.py's resolved_ids.json")
    parser.add_argument("output", type=Path, help="Path to write the rendered reentry.toml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--allowed-reply-host", default="127.0.0.1")
    args = parser.parse_args()

    resolved = json.loads(args.resolved_ids.read_text())
    missing = [
        k
        for k in ("CI_LAB_SEND_HK_MID", "CI_LAB_CMD_UDP_PORT", "TO_LAB_TLM_PORT", "CI_LAB_HK_TLM_MID", "CI_LAB_CMD_MID")
        if k not in resolved
    ]
    if missing:
        print(f"error: resolved_ids.json is missing {missing}", file=sys.stderr)
        return 1

    payload = build_hk_request_payload(resolved["CI_LAB_SEND_HK_MID"])
    resolved_identifiers = ", ".join(
        f"{name} = {value}" for name, value in sorted(resolved.items())
    )
    args.output.write_text(
        TOML_TEMPLATE.format(
            host=args.host,
            port=resolved["CI_LAB_CMD_UDP_PORT"],
            listen_port=resolved["TO_LAB_TLM_PORT"],
            allowed_reply_host=args.allowed_reply_host,
            allowed_reply_apid=resolved["CI_LAB_HK_TLM_MID"] & APID_MASK,
            target_apid=resolved["CI_LAB_CMD_MID"] & APID_MASK,
            payload_hex=payload.hex(),
            resolved_identifiers=resolved_identifiers,
        )
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
