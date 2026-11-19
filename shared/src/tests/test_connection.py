import socket
import time
from collections.abc import Iterator
from concurrent.futures import Future
from typing import Annotated, Literal

import pytest
from pydantic import Field, TypeAdapter
from shared.base_packet import BasePacket, ErrorPacket, GenericPacket
from shared.connection import Connection


class EchoPacket(BasePacket, frozen=True):
    type: Literal["echo"] = "echo"
    msg: str


class EchoReply(BasePacket, frozen=True):
    type: Literal["echo_reply"] = "echo_reply"
    msg: str


EchoPackets = Annotated[GenericPacket | EchoPacket | EchoReply, Field(discriminator="type")]


@pytest.fixture
def sockets() -> Iterator[tuple[socket.socket, socket.socket]]:
    con_socket, client_socket = socket.socketpair()
    yield con_socket, client_socket
    con_socket.close()
    client_socket.close()


@pytest.fixture
def connection1(sockets: tuple[socket.socket, socket.socket]) -> Iterator[Connection]:
    con = Connection(sockets[0], TypeAdapter(EchoPackets), lambda: None)
    con.start()

    yield con

    con.close()
    con.join(timeout=3)


@pytest.fixture
def connection2(sockets: tuple[socket.socket, socket.socket]) -> Iterator[Connection]:
    con = Connection(sockets[1], TypeAdapter(EchoPackets), lambda: None)
    con.start()

    yield con

    con.close()
    con.join(timeout=3)


def test_registered_handler_receives_packet(
    connection1: Connection, connection2: Connection
) -> None:
    def echo(packet: EchoPacket) -> None:
        connection1.send(EchoReply(request_id=packet.request_id, msg=packet.msg))

    reply_future: Future[EchoReply] = Future()

    def echo_reply(packet: EchoReply) -> None:
        reply_future.set_result(packet)

    connection1.register(EchoPacket, echo)
    connection2.register(EchoReply, echo_reply)

    connection2.send(EchoPacket(request_id="r1", msg="Hello World"))
    reply = reply_future.result(2)
    assert reply.request_id == "r1"
    assert reply.msg == "Hello World"


@pytest.mark.usefixtures("connection2")
def test_unknown_type_gives_error_with_request_id(connection1: Connection) -> None:

    error_future: Future[ErrorPacket] = Future()

    def error_handler(packet: ErrorPacket) -> None:
        error_future.set_result(packet)

    connection1.register(ErrorPacket, error_handler)
    connection1.send(BasePacket(type="not_real", request_id="r2"))

    reply = error_future.result(2)
    assert reply.request_id == "r2"


def test_crashing_handler_gives_error_and_connection_survives(
    connection1: Connection, connection2: Connection
) -> None:
    def crash(_packet: EchoPacket) -> None:
        raise ValueError("Oh NO!")

    error_future1: Future[ErrorPacket] = Future()
    error_future2: Future[ErrorPacket] = Future()

    def error_handler(packet: ErrorPacket) -> None:
        if error_future1.done():
            error_future2.set_result(packet)
        else:
            error_future1.set_result(packet)

    connection1.register(EchoPacket, crash)
    connection2.register(ErrorPacket, error_handler)

    connection2.send(EchoPacket(request_id="c1", msg="please dont crash?"))
    error = error_future1.result(2)
    assert error.request_id == "c1"

    connection2.send(EchoPacket(request_id="c2", msg="please dont crash?"))
    error = error_future2.result(2)
    assert error.request_id == "c2"


def test_send_doesnt_error_for_disconnected_client(
    connection1: Connection, connection2: Connection
) -> None:
    connection1.close()
    # Just testing that send doesnt fail from a closed connection.
    connection2.send(BasePacket(type="hello", request_id="world"))


def test_close_stops_read_loop(connection1: Connection, connection2: Connection) -> None:
    echo_future: Future[EchoPacket] = Future()

    def echo(packet: EchoPacket) -> None:
        echo_future.set_result(packet)

    connection1.register(EchoPacket, echo)
    connection1.close()

    # Check that after the connection is closed that its handlers are *not* called again.
    time.sleep(2)
    connection2.send(EchoPacket(request_id="test", msg="hello"))
    time.sleep(2)

    assert not echo_future.done()
