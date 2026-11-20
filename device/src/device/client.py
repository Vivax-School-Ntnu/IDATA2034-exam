"""TCP client for simulated devices."""

import logging
import socket

from pydantic import TypeAdapter
from shared.base_packet import DisconnectPacket, ErrorPacket, GenericPacket
from shared.connection import Connection
from shared.device_protocol import DeviceConnection, SensorUpdate

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

    def connect(self) -> None:
        """Establish a TCP connection and start receiving messages."""
        if self._connection is not None:
            raise RuntimeError("Client is already connected")

        sock = socket.create_connection((self.host, self.port), timeout=5.0)
        sock.settimeout(None)

        connection = Connection(sock, TypeAdapter(GenericPacket), self._on_disconnect,)
        connection.register(ErrorPacket, self._handle_error)
        connection.register(DisconnectPacket, self._handle_disconnect)

        self._connection = connection
        connection.start()

    def send_connect_device(self, device: Device, name: str):
        """Register the device with the server."""
        if self._connection is None:
            raise RuntimeError("Client is not connected")

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
            sensors=device.get_sensor_values(),
        )

        self._connection.send(packet)

    def _handle_error(self, packet: ErrorPacket) -> None:
        """Log errors received from the server."""
        logger.error(f"Server error for request {packet.request_id}: {packet.msg}")

    def _handle_disconnect(self, _packet: DisconnectPacket) -> None:
        """Close the connection when the server request it."""
        self.close()

    def _on_disconnect(self) -> None:
        """Reset the connection when the read loop terminates."""
        self._connection = None

    def close(self) -> None:
        """Close the connection and stop its reader thread."""
        connection = self._connection

        if connection is not None:
            self._connection = None
            connection.close()
            connection.join(timeout=3.0)

