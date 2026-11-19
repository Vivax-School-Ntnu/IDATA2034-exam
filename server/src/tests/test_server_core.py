import socket
import threading
import time
from collections.abc import Callable, Iterator
from typing import BinaryIO

import pytest
from server.connection import Connection
from server.core import Server

from shared import read_frame, write_frame


class Client:
    def __init__(self, port: int) -> None:
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        self.writer: BinaryIO = self.sock.makefile("wb")
        self.reader: BinaryIO = self.sock.makefile("rb")

    def send(self, packet: object) -> None:
        write_frame(self.writer, packet)
        self.writer.flush()

    def send_raw(self, payload: bytes) -> None:
        _ = self.writer.write(len(payload).to_bytes(8, "big") + payload)
        self.writer.flush()

    def recv(self) -> object:
        return read_frame(self.reader)

    def close(self) -> None:
        self.writer.close()
        self.reader.close()
        self.sock.close()


def wait_for(condition: Callable[[], bool], timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def server() -> Iterator[Server]:
    srv = Server(port=0, accept_timeout=0.05)
    srv.bind("127.0.0.1")
    thread = threading.Thread(target=srv.serve, daemon=True)
    thread.start()
    yield srv
    srv.close()
    thread.join(timeout=3)


@pytest.fixture
def client(server: Server) -> Iterator[Client]:
    c = Client(server.port)
    assert wait_for(lambda: len(server.clients) == 1)
    yield c
    c.close()


def echo(connection: Connection, packet: dict[str, object]) -> None:
    connection.send({"type": "echo_reply", "request_id": packet.get("request_id")})


@pytest.mark.usefixtures("client")
def test_client_is_registered(server: Server) -> None:
    assert list(server.clients) == [1]


def test_registered_handler_receives_packet(server: Server, client: Client) -> None:
    server.handler.register("echo", echo)
    client.send({"type": "echo", "request_id": "r1"})
    assert client.recv() == {"type": "echo_reply", "request_id": "r1"}


def test_unknown_type_gives_error_with_request_id(client: Client) -> None:
    client.send({"type": "banana", "request_id": "r2"})
    reply = client.recv()
    assert isinstance(reply, dict)
    assert reply["type"] == "error"
    assert reply["request_id"] == "r2"


def test_non_object_packet_gives_error(client: Client) -> None:
    client.send([1, 2, 3])
    assert client.recv() == {
        "type": "error",
        "request_id": None,
        "msg": "Packet must be a JSON object",
    }


def test_missing_type_gives_error(client: Client) -> None:
    client.send({"request_id": "r3"})
    reply = client.recv()
    assert isinstance(reply, dict)
    assert reply["type"] == "error"
    assert reply["request_id"] == "r3"


def test_invalid_json_gives_error_and_connection_survives(server: Server, client: Client) -> None:
    server.handler.register("echo", echo)
    client.send_raw(b"{not json")
    reply = client.recv()
    assert isinstance(reply, dict)
    assert reply["type"] == "error"
    client.send({"type": "echo", "request_id": "r4"})
    assert client.recv() == {"type": "echo_reply", "request_id": "r4"}


def test_crashing_handler_gives_error_and_connection_survives(
    server: Server, client: Client
) -> None:
    def crash(_connection: Connection, _packet: dict[str, object]) -> None:
        raise KeyError("name")

    server.handler.register("crash", crash)
    server.handler.register("echo", echo)
    client.send({"type": "crash", "request_id": "r5"})
    reply = client.recv()
    assert isinstance(reply, dict)
    assert reply["type"] == "error"
    assert reply["request_id"] == "r5"
    client.send({"type": "echo", "request_id": "r6"})
    assert client.recv() == {"type": "echo_reply", "request_id": "r6"}


def test_disconnect_removes_client(server: Server, client: Client) -> None:
    client.close()
    assert wait_for(lambda: len(server.clients) == 0)


def test_send_safe_returns_false_for_disconnected_client(server: Server, client: Client) -> None:
    connection = server.clients[1]
    client.close()
    assert wait_for(lambda: not connection.send_safe({"type": "ping"}))


def test_close_stops_serve_loop() -> None:
    srv = Server(port=0, accept_timeout=0.05)
    srv.bind("127.0.0.1")
    thread = threading.Thread(target=srv.serve, daemon=True)
    thread.start()
    srv.close()
    thread.join(timeout=3)
    assert not thread.is_alive()
