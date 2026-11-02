"""accepts clients and keeps track of them."""

import socket
import threading

from server.connection import Connection
from shared import PORT


class Server:
    """Central server that devices and controllers connect to."""

    def __init__(self, port: int = PORT):
        """Create the server."""
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: dict[int, Connection] = {}
        self.clients_lock = threading.Lock()
        self.next_id: int = 1

    def start(self, host: str):
        """Listen on given host and accept clients until stopped."""
        self.sock.bind((host, self.port))
        self.sock.listen()
        print(f"Server listening on {host}:{self.port}")
        while True:
            self.accept_client()

    def add_client(self, connection: Connection) -> int:
        """Add a client and returns its unique id."""
        with self.clients_lock:
            client_id = self.next_id
            self.next_id += 1
            self.clients[client_id] = connection
        return client_id

    def accept_client(self):
        """Wait for a client, register it and start a thread to serve it."""
        conn, address = self.sock.accept()
        connection = Connection(conn, address)
        client_id = self.add_client(connection)
        print(f"Client {client_id} connected from {address}")
        threading.Thread(target=connection.run, daemon=True).start()

    def close(self) -> None:
        """Close the server connection."""
        self.sock.close()
        print("Server closed")
