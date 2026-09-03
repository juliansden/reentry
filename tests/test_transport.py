import socket
import threading
import time

import pytest

from reentry.transport.udp import UDPTransport
from tests.fixtures.mock_target import MockTarget


@pytest.fixture
def mock_target():
    target = MockTarget("127.0.0.1", 0)
    port = target._sock.getsockname()[1]
    thread = threading.Thread(target=target.serve_forever, daemon=True)
    thread.start()
    yield port


def test_udp_transport_send_and_probe(mock_target):
    transport = UDPTransport("127.0.0.1", mock_target, probe_payload=b"HK?")
    try:
        assert transport.probe(timeout=2.0) is True
    finally:
        transport.close()


def test_udp_transport_probe_times_out_with_no_listener():
    transport = UDPTransport("127.0.0.1", 1, probe_payload=b"HK?")
    try:
        assert transport.probe(timeout=0.2) is False
    finally:
        transport.close()


def test_udp_transport_receive_returns_raw_bytes(mock_target):
    transport = UDPTransport("127.0.0.1", mock_target)
    try:
        transport.send(b"HK?")
        reply = transport.receive(timeout=2.0)
        assert reply is not None
        assert len(reply) == 8  # 6-byte dummy header + 2 counter bytes
    finally:
        transport.close()


def test_udp_transport_ignores_replies_from_unexpected_host():
    receiver = UDPTransport("127.0.0.1", 1, listen_port=0, allowed_reply_host="127.0.0.2")
    port = receiver._recv_sock.getsockname()[1]
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sender.sendto(b"unexpected", ("127.0.0.1", port))
        assert receiver.receive(timeout=0.1) is None
    finally:
        sender.close()
        receiver.close()
