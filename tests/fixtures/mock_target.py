"""Minimal mock UDP command-ingest target for fast local dev/testing of the harness.

NOT a substitute for validating against the real cFS/ci_lab sandbox (docker/cfs_ci_lab):
this only proves the harness's send/monitor/report pipeline works end to end, since a
hand-written mock is always more lenient and more predictable than a real target.

Speaks a tiny subset of the ci_lab HK protocol: an HK-request payload of b"HK?" gets a
reply packet with a cFS-compatible 16-byte telemetry header followed by the CI_LAB
housekeeping payload, including command and ingest counters.
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys

from reentry.ccsds.constants import PRIMARY_HEADER_SIZE
from reentry.ccsds.packet import PrimaryHeader

HK_REQUEST = b"HK?"


class MockTarget:
    """Accepts only well-formed, unsegmented, version-0 packets; rejects everything else.

    `buggy` mode deliberately mis-handles oversized packets (an unhandled parse
    exception that kills the listener) so tests can prove the harness actually
    detects CRASH, not just report CLEAN_REJECT every time.
    """

    def __init__(self, host: str, port: int, buggy: bool = False) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((host, port))
        self._buggy = buggy
        self._accept_count = 0
        self._error_count = 0

    EXPECTED_APID = 42
    # Mirrors a real target's finite command-buffer size: even a structurally
    # valid packet larger than this is rejected, not just parsed-and-accepted.
    MAX_COMMAND_SIZE = 2048

    def _is_well_formed(self, data: bytes) -> bool:
        if len(data) < PRIMARY_HEADER_SIZE or len(data) > self.MAX_COMMAND_SIZE:
            return False
        header = PrimaryHeader.unpack(data)
        payload_len = len(data) - PRIMARY_HEADER_SIZE
        checksum = 0xFF
        for value in data:
            checksum ^= value
        return (
            header.version == 0
            and header.packet_type == 1
            and header.seq_flags == 0b11
            and header.data_length == payload_len
            and header.apid == self.EXPECTED_APID
            and header.sec_hdr_flag == 1
            and len(data) >= 8
            and data[6] == 0
            and checksum == 0
        )

    def _handle_command(self, data: bytes) -> None:
        if self._buggy and len(data) > self.MAX_COMMAND_SIZE:
            raise RuntimeError("simulated unhandled overflow in buggy mode")
        if self._is_well_formed(data):
            self._accept_count += 1
        else:
            self._error_count += 1

    def serve_forever(self) -> None:
        while True:
            data, addr = self._sock.recvfrom(65535)
            if data == HK_REQUEST:
                reply = bytes(16) + struct.pack(
                    "<BBBBII",
                    self._accept_count & 0xFF,
                    self._error_count & 0xFF,
                    0,
                    1,
                    0,
                    0,
                )
                self._sock.sendto(reply, addr)
                continue
            self._handle_command(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1234)
    parser.add_argument("--buggy", action="store_true")
    args = parser.parse_args()
    MockTarget(args.host, args.port, buggy=args.buggy).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
