"""Accepts clients and keeps track of them."""

import logging
import socket
import threading
from pathlib import Path

from pydantic import TypeAdapter
from shared.base_packet import ErrorPacket
from shared.connection import Connection
from shared.device_protocol import DeviceConnection

from shared import PORT, ToServerPacket

logger = logging.getLogger(__name__)

type ConnectionId = int
"""Identifies every instance of a connection, new every time, gone on a disconnect."""
type DeviceId = int
"""Handed out by the server, tied to the devices specific HardwareId. Short, used for addressing."""
type HardwareId = str
"""Identity a device generates once and keeps forever. Works like a MAC address."""

_ID_MAP_ADAPTER = TypeAdapter(dict[HardwareId, DeviceId])


class Server:
    """Central server that devices and controllers connect to."""

    def __init__(
        self, port: int = PORT, accept_timeout: float = 1.0, id_file: Path | None = None
    ) -> None:
        """Create the server.

        `accept_timeout` is how often the accept loop wakes up to check whether it should stop.

        `id_file` is where hardware_ids is persisted. None disables persistence.
        """
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._id_file = id_file
        self._hardware_ids: dict[HardwareId, DeviceId] = {}
        if self._id_file is not None and self._id_file.exists():
            self._hardware_ids = _ID_MAP_ADAPTER.validate_json(self._id_file.read_bytes())

        self._clients: dict[int, Connection] = {}
        self._device_ids: dict[ConnectionId, DeviceId] = {}
        self._clients_lock = threading.Lock()
        self._next_id: int = 1
        self._next_device_id: int = max(self._hardware_ids.values(), default=0) + 1
        self.accept_timeout = accept_timeout
        self.running = False

    def _bind(self, host: str) -> None:
        """Bind and listen on the given host.

        If the server was created with port 0, `self.port` is updated to the port the OS picked.
        """
        self._sock.bind((host, self.port))
        self._sock.listen()
        self._sock.settimeout(self.accept_timeout)
        self.port = self._sock.getsockname()[1]
        logger.info(f"Server listening on {host}:{self.port}")

    def _serve(self) -> None:
        """Accept clients until `close` is called.

        Accept uses a short timeout so the loop can notice `close` and Ctrl+C on Windows.
        """
        self.running = True
        while self.running:
            self._accept_client()

    def start(self, host: str) -> None:
        """Bind to the given host and accept clients until stopped."""
        self._bind(host)
        self._serve()

    def _add_client(self, conn: socket.socket, address: tuple[str, int]) -> Connection:
        """Register a new client and return its connection."""
        with self._clients_lock:
            client_id = self._next_id
            self._next_id += 1
            logger.info(f"Got client with id {client_id} from {address}")

            connection = Connection(
                conn, TypeAdapter(ToServerPacket), lambda: self._remove_client(client_id)
            )
            connection.register(
                DeviceConnection, lambda packet: self._handle_device_connection(client_id, packet)
            )
            connection.register(ErrorPacket, lambda packet: self._handle_error(client_id, packet))

            self._clients[client_id] = connection
        return connection

    def _remove_client(self, client_id: int) -> None:
        """Remove a client from the registry."""
        with self._clients_lock:
            del self._clients[client_id]
            self._device_ids.pop(client_id, None)
        print(f"Client {client_id} removed")

    def _accept_client(self) -> None:
        """Wait up to `accept_timeout` for a client, then register it and serve it in a thread."""
        try:
            conn, address = self._sock.accept()
        except TimeoutError:
            return
        except OSError:
            if self.running:
                raise
            return
        conn.settimeout(None)
        connection = self._add_client(conn, address)
        connection.start()

    def _handle_error(self, client_id: int, packet: ErrorPacket) -> None:
        logger.error(f"Error from {client_id}, request {packet.request_id}: {packet.msg}")

    def _handle_device_connection(self, client_id: int, packet: DeviceConnection) -> None:
        """Handle the device connection packet."""
        with self._clients_lock:
            if packet.uuid in self._hardware_ids:
                self._device_ids[client_id] = self._hardware_ids[packet.uuid]
                logger.info(
                    f"Device reconnected. Client id: {client_id}, Device id: {self._device_ids[client_id]}"
                )
            else:
                self._hardware_ids[packet.uuid] = self._next_device_id
                self._device_ids[client_id] = self._next_device_id
                logger.info(
                    f"New device. Client id: {client_id}. Device id: {self._next_device_id}"
                )
                self._next_device_id += 1
                self._save_hardware_ids()

    def _save_hardware_ids(self) -> None:
        """Save hardware IDs to a persistent file. Does nothing if persistence is not enabled.
        
        Caller must call under _clients_lock.
        """
        if self._id_file is None:
            return
        data = _ID_MAP_ADAPTER.dump_json(self._hardware_ids)
        tmp = self._id_file.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(self._id_file)
    
    def client_count(self) -> int:
        """Return the amount of currently connected clients."""
        return len(self._clients)

    def device_id_for(self, uuid: HardwareId) -> DeviceId | None:
        """Return the device id assigned to `uuid`, or `None` if that device has never connected."""
        with self._clients_lock:
            return self._hardware_ids.get(uuid)

    def close(self) -> None:
        """Stop accepting clients and close the listening socket."""
        self.running = False
        self._sock.close()
        logger.info("Server closed")
