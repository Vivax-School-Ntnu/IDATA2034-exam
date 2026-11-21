"""Tests for DeviceRuntime."""

from unittest.mock import patch

import pytest
from device.client import DeviceClient
from device.device import Device
from device.runtime import DeviceRuntime


def test_runtime_rejects_invalid_interval() -> None:
    """Test that the update interval must be positive."""
    device = Device("test-uuid")
    client = DeviceClient("127.0.0.1")

    with pytest.raises(ValueError):
        DeviceRuntime(
            device=device,
            client=client,
            name="Test device",
            update_interval=0,
        )


def test_runtime_connects_and_closes() -> None:
    """Test that runtime connects, registers, and closes."""
    device = Device("test-uuid")
    client = DeviceClient("127.0.0.1")
    runtime = DeviceRuntime(device, client, "Test device")

    runtime.stop()

    with (
        patch.object(client, "connect") as connect,
        patch.object(client, "send_connect_device") as register,
        patch.object(client, "close") as close,
    ):
        runtime.run()

    connect.assert_called_once_with()
    register.assert_called_once_with(device, "Test device")
    close.assert_called_once_with()


def test_runtime_sends_sensor_updates() -> None:
    """Test that runtime sends sensor updates automatically."""
    device = Device("test-uuid")
    client = DeviceClient("127.0.0.1")
    runtime = DeviceRuntime(
        device,
        client,
        "Test device",
        update_interval=0.001,
    )

    def stop_after_update(_device: Device) -> None:
        runtime.stop()

    with (
        patch.object(client, "connect"),
        patch.object(client, "send_connect_device"),
        patch.object(
            client,
            "send_sensor_update",
            side_effect=stop_after_update,
        ) as send_update,
        patch.object(client, "close"),
    ):
        runtime.run()

    send_update.assert_called_once_with(device)


def test_runtime_closes_on_error() -> None:
    """Test that the connection closes when an error occurs."""
    device = Device("test-uuid")
    client = DeviceClient("127.0.0.1")
    runtime = DeviceRuntime(
        device,
        client,
        "Test device",
        update_interval=0.001,
    )

    with (
        patch.object(client, "connect"),
        patch.object(client, "send_connect_device"),
        patch.object(
            client,
            "send_sensor_update",
            side_effect=RuntimeError("Connection lost"),
        ),
        patch.object(client, "close") as close,
        pytest.raises(RuntimeError),
    ):
        runtime.run()

    close.assert_called_once_with()
