import contextlib
import queue
import socket
import threading
import time
from collections.abc import Callable, Iterator
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from server.core import Server
from shared.base_packet import (
    ActuatorConfiguration,
    BasePacket,
    Capability,
    DisconnectPacket,
    ErrorPacket,
    SensorConfiguration,
    SensorValue,
)
from shared.controller_protocol import (
    ConnectionConfirmation,
    ControllerConnection,
    DeviceAdded,
    DeviceRemoved,
    SensorReading,
    ServerToControllerPacket,
    SetActuator,
    Subscribe,
)
from shared.device_protocol import (
    DeviceConnected,
    DeviceConnection,
    SensorUpdate,
    ServerToDevicePacket,
    UpdateActuator,
)

from shared import read_frame, write_frame

TIMEOUT = 3.0
QUIET = 0.3

CAPABILITIES: dict[str, Capability] = {
    "temperature": SensorConfiguration(name="Temperature", sensor_type="numeric"),
    "light": ActuatorConfiguration(name="Ceiling light", actuator_type="binary"),
    "target": ActuatorConfiguration(name="Target temperature", actuator_type="numeric"),
}


class ProbeClient:
    """A raw TCP client that records every packet the server sends it."""

    def __init__(self, port: int, adapter: TypeAdapter[BasePacket]) -> None:
        self._sock = socket.create_connection(("127.0.0.1", port))
        self._writer = self._sock.makefile("wb")
        self._reader = self._sock.makefile("rb")
        self._adapter = adapter
        self._inbox: queue.Queue[BasePacket] = queue.Queue()
        self._skipped: list[BasePacket] = []
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        try:
            while True:
                frame = read_frame(self._reader)
                self._inbox.put(self._adapter.validate_python(frame.model_dump()))
        except (EOFError, OSError, ValueError):
            return

    def send(self, packet: BasePacket) -> None:
        write_frame(self._writer, packet)
        self._writer.flush()

    def expect[T: BasePacket](self, packet_type: type[T], timeout: float = TIMEOUT) -> T:
        """Return the first unread packet of `packet_type`, waiting for it if needed."""
        for packet in self._skipped:
            if isinstance(packet, packet_type):
                self._skipped.remove(packet)
                return packet
        deadline = time.monotonic() + timeout
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                packet = self._inbox.get(timeout=remaining)
            except queue.Empty:
                break
            if isinstance(packet, packet_type):
                return packet
            self._skipped.append(packet)
        raise AssertionError(f"No {packet_type.__name__} within {timeout}s, got {self._skipped}")

    def expect_none(self, packet_type: type[BasePacket], wait: float = QUIET) -> None:
        """Fail if a packet of `packet_type` arrives within `wait` seconds."""
        time.sleep(wait)
        while not self._inbox.empty():
            self._skipped.append(self._inbox.get())
        unexpected = [p for p in self._skipped if isinstance(p, packet_type)]
        assert not unexpected, f"Did not expect {unexpected}"

    def close(self) -> None:
        """Close the socket. Shutdown first so the blocked reader thread wakes up."""
        with contextlib.suppress(OSError):
            self._sock.shutdown(socket.SHUT_RDWR)
        self._thread.join(timeout=TIMEOUT)
        for closeable in (self._writer, self._reader, self._sock):
            with contextlib.suppress(OSError):
                closeable.close()


def connect_device_packet(uuid: str) -> DeviceConnection:
    return DeviceConnection(
        type="connect_device",
        request_id=str(uuid4()),
        uuid=uuid,
        name="Test device",
        capabilities=CAPABILITIES,
    )


def sensor_update(**values: SensorValue) -> SensorUpdate:
    return SensorUpdate(type="sensor_update", request_id=None, sensors=values)


def set_actuator(address: str, value: SensorValue) -> SetActuator:
    return SetActuator(type="set_actuator", request_id=str(uuid4()), address=address, value=value)


def subscribe(*addresses: str) -> Subscribe:
    return Subscribe(type="subscribe", request_id=str(uuid4()), addresses=list(addresses))


type ClientFactory = Callable[[TypeAdapter[BasePacket]], ProbeClient]


@pytest.fixture
def server() -> Iterator[Server]:
    srv = Server(port=0, accept_timeout=0.05)
    thread = threading.Thread(target=srv.start, args=("127.0.0.1",), daemon=True)
    thread.start()
    deadline = time.monotonic() + TIMEOUT
    while not srv.running and time.monotonic() < deadline:
        time.sleep(0.01)

    yield srv

    srv.close()
    thread.join(timeout=TIMEOUT)


@pytest.fixture
def new_client(server: Server) -> Iterator[ClientFactory]:
    clients: list[ProbeClient] = []

    def make(adapter: TypeAdapter[BasePacket]) -> ProbeClient:
        client = ProbeClient(server.port, adapter)
        clients.append(client)
        return client

    yield make

    for client in clients:
        client.close()


@pytest.fixture
def connect_device(new_client: ClientFactory) -> Callable[..., tuple[ProbeClient, int]]:
    """Connect a device, wait for its ACK and return it with its device id."""

    def connect(uuid: str | None = None) -> tuple[ProbeClient, int]:
        client = new_client(TypeAdapter(ServerToDevicePacket))
        client.send(connect_device_packet(uuid or str(uuid4())))
        return client, client.expect(DeviceConnected).device_id

    return connect


@pytest.fixture
def connect_controller(new_client: ClientFactory) -> Callable[[], ProbeClient]:
    """Connect a controller and wait for its confirmation."""

    def connect() -> ProbeClient:
        client = new_client(TypeAdapter(ServerToControllerPacket))
        client.send(ControllerConnection(type="connect_controller", request_id=str(uuid4())))
        client.expect(ConnectionConfirmation)
        return client

    return connect


def test_device_gets_ack_with_its_request_id(new_client: ClientFactory) -> None:
    device = new_client(TypeAdapter(ServerToDevicePacket))
    request = connect_device_packet(str(uuid4()))
    device.send(request)

    ack = device.expect(DeviceConnected)

    assert ack.request_id == request.request_id


def test_controller_gets_existing_devices_with_latest_values(
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    watcher = connect_controller()
    watcher.send(subscribe(f"{device_id}.temperature"))
    device.send(sensor_update(temperature=21, light=False, target=20))
    watcher.expect(SensorReading)

    controller = connect_controller()

    info = controller.expect(DeviceAdded).device
    assert info.device_id == device_id
    assert info.capabilities == CAPABILITIES
    assert info.values == {"temperature": 21, "light": False, "target": 20}


def test_connected_controller_is_told_about_new_device(
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    controller = connect_controller()

    _, device_id = connect_device()

    assert controller.expect(DeviceAdded).device.device_id == device_id


def test_subscribe_sends_current_value(
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    watcher = connect_controller()
    watcher.send(subscribe(f"{device_id}.temperature"))
    device.send(sensor_update(temperature=19))
    watcher.expect(SensorReading)

    controller = connect_controller()
    controller.send(subscribe(f"{device_id}.temperature"))

    reading = controller.expect(SensorReading)
    assert (reading.address, reading.value) == (f"{device_id}.temperature", 19)


def test_sensor_update_reaches_only_subscribed_controllers(
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    subscribed = connect_controller()
    other = connect_controller()
    subscribed.send(subscribe(f"{device_id}.temperature"))
    time.sleep(QUIET)

    device.send(sensor_update(temperature=25, light=True))

    reading = subscribed.expect(SensorReading)
    assert (reading.address, reading.value) == (f"{device_id}.temperature", 25)
    subscribed.expect_none(SensorReading)
    other.expect_none(SensorReading)


def test_partial_update_keeps_old_values(
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    watcher = connect_controller()
    watcher.send(subscribe(f"{device_id}.temperature"))
    device.send(sensor_update(temperature=20, light=True, target=18))
    watcher.expect(SensorReading)
    device.send(sensor_update(temperature=22))
    watcher.expect(SensorReading)

    controller = connect_controller()

    assert controller.expect(DeviceAdded).device.values == {
        "temperature": 22,
        "light": True,
        "target": 18,
    }


@pytest.mark.parametrize("bad_address", ["9.temperature", "{id}.missing", "temperature", "x.light"])
def test_subscribe_with_unknown_address_is_rejected_whole(
    bad_address: str,
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    controller = connect_controller()
    request = subscribe(f"{device_id}.temperature", bad_address.format(id=device_id))
    controller.send(request)

    error = controller.expect(ErrorPacket)

    assert error.request_id == request.request_id
    device.send(sensor_update(temperature=30))
    controller.expect_none(SensorReading)


def test_set_actuator_is_forwarded_to_device_with_local_id(
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    controller = connect_controller()

    controller.send(set_actuator(f"{device_id}.light", True))

    command = device.expect(UpdateActuator)
    assert (command.actuator, command.value) == ("light", True)


def test_set_actuator_subscribes_sender_to_result(
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    controller = connect_controller()
    controller.send(set_actuator(f"{device_id}.target", 23))
    device.expect(UpdateActuator)

    device.send(sensor_update(target=23))

    reading = controller.expect(SensorReading)
    assert (reading.address, reading.value) == (f"{device_id}.target", 23)


@pytest.mark.parametrize(
    ("local_id", "value"),
    [
        ("temperature", 20),
        ("light", 1),
        ("target", True),
        ("missing", True),
    ],
    ids=["sensor", "binary-given-number", "numeric-given-bool", "unknown-capability"],
)
def test_invalid_set_actuator_is_error_and_not_forwarded(
    local_id: str,
    value: SensorValue,
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    controller = connect_controller()
    request = set_actuator(f"{device_id}.{local_id}", value)

    controller.send(request)

    assert controller.expect(ErrorPacket).request_id == request.request_id
    device.expect_none(UpdateActuator)


def test_set_actuator_on_unknown_device_is_error(
    connect_controller: Callable[[], ProbeClient],
) -> None:
    controller = connect_controller()

    controller.send(set_actuator("42.light", True))

    controller.expect(ErrorPacket)


def test_device_disconnect_notifies_controllers(
    server: Server,
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    controller = connect_controller()

    device.close()

    assert controller.expect(DeviceRemoved).device_id == device_id
    assert server.device_count() == 0


def test_disconnect_packet_is_accepted_before_closing(
    server: Server,
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    device, device_id = connect_device()
    controller = connect_controller()

    device.send(DisconnectPacket(type="disconnect", request_id=None))
    device.expect_none(ErrorPacket)
    device.close()

    assert controller.expect(DeviceRemoved).device_id == device_id
    assert server.device_count() == 0


def test_fast_reconnect_keeps_live_device(
    server: Server,
    connect_device: Callable[..., tuple[ProbeClient, int]],
    connect_controller: Callable[[], ProbeClient],
) -> None:
    uuid = str(uuid4())
    old, device_id = connect_device(uuid)
    controller = connect_controller()

    new, new_id = connect_device(uuid)
    assert new_id == device_id
    controller.expect(DeviceAdded)
    old.close()

    controller.expect_none(DeviceRemoved)
    assert server.device_count() == 1
    controller.send(set_actuator(f"{device_id}.light", True))
    new.expect(UpdateActuator)


def test_device_cannot_send_controller_packets(
    connect_device: Callable[..., tuple[ProbeClient, int]],
) -> None:
    device, device_id = connect_device()
    request = subscribe(f"{device_id}.temperature")

    device.send(request)

    assert device.expect(ErrorPacket).request_id == request.request_id


def test_controller_cannot_send_sensor_updates(
    connect_controller: Callable[[], ProbeClient],
) -> None:
    controller = connect_controller()

    controller.send(sensor_update(temperature=1))

    controller.expect(ErrorPacket)


def test_packets_before_registering_are_rejected(new_client: ClientFactory) -> None:
    client = new_client(TypeAdapter(ServerToControllerPacket))
    request = subscribe("1.temperature")

    client.send(request)

    assert client.expect(ErrorPacket).request_id == request.request_id


def test_second_connect_on_same_connection_is_rejected(
    connect_controller: Callable[[], ProbeClient],
) -> None:
    controller = connect_controller()
    request = connect_device_packet(str(uuid4()))

    controller.send(request)

    assert controller.expect(ErrorPacket).request_id == request.request_id
