import json
import socket
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError
from server.core import Server
from shared.base_packet import BasePacket
from shared.connection import Connection
from shared.device_protocol import DeviceConnection


def wait_for[T](condition: Callable[[], T], timeout: float = 3.0) -> T:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = condition()
        if result:
            return result
        time.sleep(0.01)
    return condition()


@contextmanager
def running_server(id_file: Path) -> Generator[Server]:
    srv = Server(port=0, accept_timeout=0.05, id_file=id_file)
    thread = threading.Thread(target=srv.start, args=("127.0.0.1",), daemon=True)
    thread.start()
    wait_for(lambda: srv.running)
    try:
        yield srv
    finally:
        srv.close()
        thread.join(timeout=3)


def register(server: Server, uuid: str) -> int | None:
    sock = socket.create_connection(("127.0.0.1", server.port))
    con = Connection(sock, TypeAdapter(BasePacket), lambda: None)
    con.start()
    con.send(
        DeviceConnection(
            type="connect_device",
            request_id=str(uuid4()),
            name="Test device",
            capabilities={},
            uuid=uuid,
        )
    )
    device_id = wait_for(lambda: server.device_id_for(uuid))
    con.close()
    con.join(timeout=3)
    return device_id


@pytest.fixture
def id_file(tmp_path: Path) -> Path:
    return tmp_path / "device_ids.json"


def test_device_id_survives_restart(id_file: Path) -> None:
    uuid = str(uuid4())
    with running_server(id_file) as server:
        register(server, str(uuid4()))
        original_id = register(server, uuid)

    with running_server(id_file) as server:
        assert register(server, uuid) == original_id


def test_new_device_after_restart_gets_unused_id(id_file: Path) -> None:
    with running_server(id_file) as server:
        first = register(server, str(uuid4()))
        second = register(server, str(uuid4()))

    with running_server(id_file) as server:
        third = register(server, str(uuid4()))

    assert len({first, second, third}) == 3


def test_mapping_is_written_to_file(id_file: Path) -> None:
    uuid = str(uuid4())
    with running_server(id_file) as server:
        device_id = register(server, uuid)

    assert json.loads(id_file.read_text(encoding="utf-8")) == {uuid: device_id}
    assert list(id_file.parent.iterdir()) == [id_file]


def test_missing_file_starts_empty(id_file: Path) -> None:
    with running_server(id_file) as server:
        assert server.device_id_for(str(uuid4())) is None
        assert register(server, str(uuid4())) == 1

    assert id_file.exists()


def test_reconnect_does_not_rewrite_file(id_file: Path) -> None:
    uuid = str(uuid4())
    with running_server(id_file) as server:
        register(server, uuid)
        written_at = id_file.stat().st_mtime_ns
        register(server, uuid)

    assert id_file.stat().st_mtime_ns == written_at


def test_corrupt_file_refuses_to_start(id_file: Path) -> None:
    id_file.write_text("not json", encoding="utf-8")

    with pytest.raises(ValidationError):
        Server(port=0, id_file=id_file)
