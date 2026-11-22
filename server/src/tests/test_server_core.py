import socket
import threading
import time
from collections.abc import Callable, Iterator

import pytest
from pydantic import TypeAdapter
from server.core import Server
from shared.base_packet import BasePacket
from shared.connection import Connection


def wait_for(condition: Callable[[], bool], timeout: float = 3.0) -> bool:
    """Poll `condition` until it is true or `timeout` seconds have passed."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


@pytest.fixture
def server() -> Iterator[Server]:
    srv = Server(port=0, accept_timeout=0.05)
    thread = threading.Thread(target=srv.start, args=("127.0.0.1",), daemon=True)
    thread.start()

    time.sleep(1)
    yield srv

    srv.close()
    thread.join(timeout=3)


@pytest.fixture
def client(server: Server) -> Iterator[Connection]:
    sock = socket.socket()
    sock.connect(("127.0.0.1", server.port))
    con = Connection(sock, TypeAdapter(BasePacket), lambda: None)
    con.start()

    yield con

    con.close()
    con.join(timeout=3)


@pytest.mark.usefixtures("client")
def test_client_connects(server: Server) -> None:
    assert wait_for(lambda: server.client_count() == 1)


def test_disconnect_removes_client(server: Server, client: Connection) -> None:
    client.close()
    assert wait_for(lambda: server.client_count() == 0)


def test_close_stops_serve_loop() -> None:
    srv = Server(port=0, accept_timeout=0.05)
    thread = threading.Thread(target=srv.start, args=("127.0.0.1",), daemon=True)
    thread.start()
    time.sleep(1)

    srv.close()
    thread.join(timeout=3)
    assert not thread.is_alive()
