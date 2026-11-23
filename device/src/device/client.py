"""TCP client for simulated devices."""

import logging
import socket
from threading import Event

from pydantic import TypeAdapter
from shared.base_packet import DisconnectPacket, ErrorPacket
from shared.connection import Connection
from shared.device_protocol import (
    DeviceConnected,
    DeviceConnection,
    SensorUpdate,
    ServerToDevicePacket,
    UpdateActuator,
)

from device.device import Device
from shared import PORT

logger = logging.getLogger(__name__)


class DeviceClient:
    """Manage TCP communication between a device and the server."""

    def __init__(self, host: str, port: int = PORT) -> None:
        """Store the server address without connecting yet."""
        self.host = host
        self.port = port
        self._connection: Connection | None = None
        self._device: Device | None = None

        self._registered = Event()
        self.device_id: int | None = None

    def connect(self) -> None:
        """Establish a TCP connection and start receiving messages."""
        if self._connection is not None:
            raise RuntimeError("Client is already connected")

        self._registered.clear()
        self.device_id = None

        sock = socket.create_connection((self.host, self.port), timeout=5.0)
        sock.settimeout(None)

        connection = Connection(
            sock,
            TypeAdapter(ServerToDevicePacket),
            self._on_disconnect,
        )
        connection.register(ErrorPacket, self._handle_error)
        connection.register(DisconnectPacket, self._handle_disconnect)
        connection.register(DeviceConnected, self._handle_device_connected)
        connection.register(UpdateActuator, self._handle_update_actuator)

        self._connection = connection
        connection.start()

    def send_connect_device(self, device: Device, name: str):
        """Register the device with the server."""
        if self._connection is None:
            raise RuntimeError("Client is not connected")

        self._device = device

        packet = DeviceConnection(
            type="connect_device",
            request_id=None,
            uuid=device.uuid,
            name=name,
            capabilities=device.get_capabilities(),
        )

        self._connection.send(packet)

    def send_sensor_update(self, device: Device) -> None:
        """Send the current sensor values to the server."""
        if self._connection is None:
            raise RuntimeError("Client is not connected")

        packet = SensorUpdate(
            type="sensor_update",
            request_id=None,
            sensors={
                **device.get_sensor_values(),
                **device.get_actuator_values(),
            },
        )

        self._connection.send(packet)

    def _handle_device_connected(self, packet: DeviceConnected) -> None:
        """Handle successful device registration."""
        self.device_id = packet.device_id
        self._registered.set()

    def _handle_update_actuator(self, packet: UpdateActuator):
        """Update an actuator when requested by the server."""
        if self._device is None:
            logger.warning("Received actuator update without a device")
            return

        try:
            self._device.set_actuator_value(packet.actuator, packet.value)
        except (ValueError, TypeError) as error:
            logger.warning("Failed to update actuator: %s", error)

    def wait_for_registration(self, timeout: float = 5.0) -> bool:
        """Wait for the server to confirm device registration."""
        return self._registered.wait(timeout)

    def _handle_error(self, packet: ErrorPacket) -> None:
        """Log errors received from the server."""
        logger.error(f"Server error for request {packet.request_id}: {packet.msg}")

    def _handle_disconnect(self, _packet: DisconnectPacket) -> None:
        """Close the connection when the server request it."""
        self.close()

    def _on_disconnect(self) -> None:
        """Reset the connection when the read loop terminates."""
        self._connection = None
        self._registered.clear()
        self.device_id = None
        self._device = None

    def close(self) -> None:
        """Close the connection and stop its reader thread."""
        connection = self._connection

        self._connection = None
        self._registered.clear()
        self.device_id = None
        self._device = None

        if connection is not None:
            connection.close()
            connection.join(timeout=3.0)
