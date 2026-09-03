"""UDP transport: the only transport ci_lab (and v1 of this harness) needs to support."""

from __future__ import annotations

import socket
import time

from reentry.ccsds.packet import PrimaryHeader
from reentry.transport.base import Transport


class UDPTransport(Transport):
    """Sends packet bytes to a UDP command port, and probes liveness via a telemetry reply.

    If the target replies on a separate downlink port (as cFS/ci_lab does), pass
    `listen_port`. Otherwise probing listens on the same socket used to send.
    """

    def __init__(
        self,
        host: str,
        port: int,
        probe_payload: bytes = b"",
        listen_host: str = "0.0.0.0",
        listen_port: int | None = None,
        allowed_reply_host: str | None = None,
        allowed_reply_apid: int | None = None,
    ) -> None:
        self._addr = (host, port)
        self._probe_payload = probe_payload
        self._allowed_reply_host = allowed_reply_host
        self._allowed_reply_apid = allowed_reply_apid
        self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if listen_port is not None:
            self._recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._recv_sock.bind((listen_host, listen_port))
        else:
            self._recv_sock = self._send_sock

    def send(self, data: bytes) -> None:
        try:
            self._send_sock.sendto(data, self._addr)
        except OSError:
            # e.g. EMSGSIZE: the datagram exceeds what UDP can carry on the wire at all.
            # That's itself a legitimate (if degenerate) test outcome, not a transport bug.
            pass

    def receive(self, timeout: float) -> bytes | None:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self._recv_sock.settimeout(remaining)
            try:
                data, address = self._recv_sock.recvfrom(65535)
            except (TimeoutError, OSError):
                return None
            if self._allowed_reply_host is not None and address[0] != self._allowed_reply_host:
                continue
            if self._allowed_reply_apid is not None:
                if len(data) < 6 or PrimaryHeader.unpack(data).apid != self._allowed_reply_apid:
                    continue
            return data

    def probe(self, timeout: float) -> bool:
        self._drain_stale_replies()
        self.send(self._probe_payload)
        return self.receive(timeout) is not None

    def _drain_stale_replies(self) -> None:
        self._recv_sock.settimeout(0)
        try:
            while True:
                self._recv_sock.recvfrom(65535)
        except (BlockingIOError, OSError):
            pass

    def close(self) -> None:
        self._send_sock.close()
        if self._recv_sock is not self._send_sock:
            self._recv_sock.close()
