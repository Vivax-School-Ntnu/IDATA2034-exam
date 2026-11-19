"""Accepts clients and keeps track of them."""

import logging
import socket
import threading

from pydantic import TypeAdapter
from shared.base_packet import ErrorPacket
from shared.connection import Connection

from shared import PORT, ToServerPacket

logger = logging.getLogger(__name__)


class Server:
    """Central server that devices and controllers connect to."""

    def __init__(self, port: int = PORT, accept_timeout: float = 1.0) -> None:
        """Create the server.

        `accept_timeout` is how often the accept loop wakes up to check whether it should stop.
        """
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._clients: dict[int, Connection] = {}
        self._clients_lock = threading.Lock()
        self._next_id: int = 1
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
            connection.register(ErrorPacket, lambda packet: self._handle_error(client_id, packet))

            self._clients[client_id] = connection
        return connection

    def _remove_client(self, client_id: int) -> None:
        """Remove a client from the registry."""
        with self._clients_lock:
            del self._clients[client_id]
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

    def client_count(self) -> int:
        """Return the amount of currently connected clients."""
        return len(self._clients)

    def close(self) -> None:
        """Stop accepting clients and close the listening socket."""
        self.running = False
        self._sock.close()
        logger.info("Server closed")
