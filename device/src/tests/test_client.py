"""Tests for the Device TCP client."""

import socket
from collections.abc import Iterator

import pytest
from device.client import DeviceClient
from device.device import Device
from device.sensor import NumericSensor
from shared.device_protocol import DeviceConnected

from shared import read_frame

TEST_UUID = "8f3c92a1-6b47-4d20-9e15-c8a72f0b6349"


@pytest.fixture
def connected_client() -> Iterator[tuple[DeviceClient, socket.socket]]:
    """Connect a DeviceClient to a local TCP test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(2.0)

        client = DeviceClient("127.0.0.1", listener.getsockname()[1])
        client.connect()

        server_socket, _ = listener.accept()
        with server_socket:
            server_socket.settimeout(2.0)
            try:
                yield client, server_socket
            finally:
                client.close()


def test_connect_and_close(
    connected_client: tuple[DeviceClient, socket.socket],
) -> None:
    """Test connecting to and closing a TCP connection."""
    client, server_socket = connected_client

    client.close()
    client.close()

    assert server_socket.recv(1) == b""


def test_reject_duplicate_connection(
    connected_client: tuple[DeviceClient, socket.socket],
) -> None:
    """Test that the client rejects a second connection."""
    client, _ = connected_client

    with pytest.raises(RuntimeError, match="already connected"):
        client.connect()


def test_connect_failure() -> None:
    """Test connecting when no server is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unused:
        unused.bind(("127.0.0.1", 0))

        client = DeviceClient("127.0.0.1", unused.getsockname()[1])

        with pytest.raises(OSError):
            client.connect()

        client.close()


def test_send_connect_device(
    connected_client: tuple[DeviceClient, socket.socket],
) -> None:
    """Test sending device registration with UUID and capabilities."""
    client, server_socket = connected_client
    device = Device(TEST_UUID)
    device.add_sensor("temp1", NumericSensor("temperature"))

    client.send_connect_device(device, "Living room")

    with server_socket.makefile("rb") as reader:
        packet = read_frame(reader).model_dump()

    assert packet["type"] == "connect_device"
    assert packet["request_id"] is None
    assert packet["uuid"] == TEST_UUID
    assert packet["name"] == "Living room"
    assert packet["capabilities"] == {
        "temp1": {
            "type": "sensor",
            "name": "temperature",
            "sensor_type": "numeric",
        }
    }


def test_send_sensor_update(
    connected_client: tuple[DeviceClient, socket.socket],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test sending the current sensor values."""
    client, server_socket = connected_client
    device = Device(TEST_UUID)
    sensor = NumericSensor("temperature")
    monkeypatch.setattr(sensor, "get_value", lambda: 23)
    device.add_sensor("temp1", sensor)

    client.send_sensor_update(device)

    with server_socket.makefile("rb") as reader:
        packet = read_frame(reader).model_dump()

    assert packet["type"] == "sensor_update"
    assert packet["request_id"] is None
    assert packet["sensors"] == {"temp1": 23}


def test_cannot_send_without_connection() -> None:
    """Test that messages cannot be sent without a connection."""
    client = DeviceClient("127.0.0.1")
    device = Device(TEST_UUID)

    with pytest.raises(RuntimeError, match="not connected"):
        client.send_connect_device(device, "Living room")

    with pytest.raises(RuntimeError, match="not connected"):
        client.send_sensor_update(device)


def test_device_connected_confirmation() -> None:
    """Test that the client handles device registration confirmation."""
    client = DeviceClient("127.0.0.1")

    assert client.wait_for_registration(timeout=0) is False
    assert client.device_id is None

    packet = DeviceConnected(
        request_id=None,
        device_id=42,
    )

    client._handle_device_connected(packet)  # pyright: ignore[reportPrivateUsage]

    assert client.wait_for_registration(timeout=0) is True
    assert client.device_id == 42
