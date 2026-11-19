import socket
import threading
import time
from collections.abc import Callable, Iterator
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from server.core import Server
from shared.base_packet import BasePacket
from shared.connection import Connection
from shared.device_protocol import DeviceConnection

type DeviceFactory = Callable[[str], Connection]


def wait_for[T](condition: Callable[[], T], timeout: float = 3.0) -> T:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = condition()
        if result:
            return result
        time.sleep(0.01)
    return condition()


def connect_packet(uuid: str) -> DeviceConnection:
    return DeviceConnection(
        type="connect_device",
        request_id=str(uuid4()),
        name="Test device",
        capabilities={},
        uuid=uuid,
    )


@pytest.fixture
def server() -> Iterator[Server]:
    srv = Server(port=0, accept_timeout=0.05)
    thread = threading.Thread(target=srv.start, args=("127.0.0.1",), daemon=True)
    thread.start()
    wait_for(lambda: srv.running)

    yield srv

    srv.close()
    thread.join(timeout=3)


@pytest.fixture
def connect_device(server: Server) -> Iterator[DeviceFactory]:
    connections: list[Connection] = []

    def connect(uuid: str) -> Connection:
        sock = socket.create_connection(("127.0.0.1", server.port))
        con = Connection(sock, TypeAdapter(BasePacket), lambda: None)
        con.start()
        con.send(connect_packet(uuid))
        connections.append(con)
        return con

    yield connect

    for con in connections:
        con.close()
        con.join(timeout=3)


def test_new_device_gets_device_id(server: Server, connect_device: DeviceFactory) -> None:
    uuid = str(uuid4())
    connect_device(uuid)

    assert wait_for(lambda: server.device_id_for(uuid)) == 1


def test_different_devices_get_different_ids(server: Server, connect_device: DeviceFactory) -> None:
    uuid_a = str(uuid4())
    uuid_b = str(uuid4())
    connect_device(uuid_a)
    connect_device(uuid_b)

    id_a = wait_for(lambda: server.device_id_for(uuid_a))
    id_b = wait_for(lambda: server.device_id_for(uuid_b))

    assert id_a is not None
    assert id_b is not None
    assert id_a != id_b


def test_reconnecting_device_keeps_its_id(server: Server, connect_device: DeviceFactory) -> None:
    uuid = str(uuid4())
    first = connect_device(uuid)
    original_id = wait_for(lambda: server.device_id_for(uuid))

    first.close()
    first.join(timeout=3)
    wait_for(lambda: server.client_count() == 0)

    other_uuid = str(uuid4())
    connect_device(other_uuid)
    wait_for(lambda: server.device_id_for(other_uuid))
    connect_device(uuid)
    wait_for(lambda: server.client_count() == 2)

    assert server.device_id_for(uuid) == original_id


def test_unknown_uuid_has_no_device_id(server: Server) -> None:
    assert server.device_id_for(str(uuid4())) is None


@pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")
def test_client_that_never_registers_can_disconnect(server: Server) -> None:
    sock = socket.create_connection(("127.0.0.1", server.port))
    wait_for(lambda: server.client_count() == 1)

    sock.close()

    assert wait_for(lambda: server.client_count() == 0)


def test_many_devices_registering_at_once_get_unique_ids(
    server: Server, connect_device: DeviceFactory
) -> None:
    uuids = [str(uuid4()) for _ in range(20)]
    for uuid in uuids:
        connect_device(uuid)

    ids = [wait_for(lambda uuid=uuid: server.device_id_for(uuid)) for uuid in uuids]

    assert None not in ids
    assert len(set(ids)) == len(uuids)
