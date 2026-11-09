"""Accepts clients and keeps track of them."""

import socket
import threading

from server.connection import Connection
from server.handler import Handler
from shared import PORT


class Server:
    """Central server that devices and controllers connect to."""

    def __init__(self, port: int = PORT, accept_timeout: float = 1.0) -> None:
        """Create the server.

        `accept_timeout` is how often the accept loop wakes up to check whether it should stop.
        """
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: dict[int, Connection] = {}
        self.clients_lock = threading.Lock()
        self.next_id: int = 1
        self.handler = Handler(self)
        self.accept_timeout = accept_timeout
        self.running = False

    def bind(self, host: str) -> None:
        """Bind and listen on the given host.

        If the server was created with port 0, `self.port` is updated to the port the OS picked.
        """
        self.sock.bind((host, self.port))
        self.sock.listen()
        self.sock.settimeout(self.accept_timeout)
        self.port = self.sock.getsockname()[1]
        print(f"Server listening on {host}:{self.port}")

    def serve(self) -> None:
        """Accept clients until `close` is called.

        Accept uses a short timeout so the loop can notice `close` and Ctrl+C on Windows.
        """
        self.running = True
        while self.running:
            self.accept_client()

    def start(self, host: str) -> None:
        """Bind to the given host and accept clients until stopped."""
        self.bind(host)
        self.serve()

    def add_client(self, conn: socket.socket, address: tuple[str, int]) -> Connection:
        """Register a new client and return its connection."""
        with self.clients_lock:
            client_id = self.next_id
            self.next_id += 1
            connection = Connection(conn, address, self, client_id)
            self.clients[client_id] = connection
        return connection

    def remove_client(self, connection: Connection) -> None:
        """Remove a client from the registry."""
        with self.clients_lock:
            _ = self.clients.pop(connection.client_id, None)
        print(f"Client {connection.client_id} removed")

    def accept_client(self) -> None:
        """Wait up to `accept_timeout` for a client, then register it and serve it in a thread."""
        try:
            conn, address = self.sock.accept()
        except TimeoutError:
            return
        except OSError:
            if self.running:
                raise
            return
        conn.settimeout(None)
        connection = self.add_client(conn, address)
        print(f"Client {connection.client_id} connected from {connection.address}")
        threading.Thread(target=connection.run, daemon=True).start()

    def close(self) -> None:
        """Stop accepting clients and close the listening socket."""
        self.running = False
        self.sock.close()
        print("Server closed")
