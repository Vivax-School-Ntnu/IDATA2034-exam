"""A single client connection to the server."""

import socket
import threading
from typing import TYPE_CHECKING

from shared import ErrorPacket, read_frame, write_frame

if TYPE_CHECKING:
    from server.core import Server


class Connection:
    """Wrap a client's socket."""

    def __init__(
        self,
        sock: socket.socket,
        address: tuple[str, int],
        server: "Server",
        client_id: int,
    ) -> None:
        """Create a connection object."""
        self.server = server
        self.client_id = client_id
        self.sock = sock
        self.address = address
        self.writer = sock.makefile("wb")
        self.write_lock = threading.Lock()

    def send(self, packet: object) -> None:
        """Send a packet to this client.

        Raises `ConnectionError` if the client is gone. Use this when replying to the client
        whose packet is being handled, so a dead socket ends that client's own connection.
        """
        with self.write_lock:
            write_frame(self.writer, packet)
            self.writer.flush()

    def send_safe(self, packet: object) -> bool:
        """Send a packet to this client, returning False instead of raising if it is gone.

        Use this when sending to a different client than the one being handled, so a dead
        recipient does not disconnect the sender.
        """
        try:
            self.send(packet)
        except (OSError, ValueError):
            return False
        return True

    def send_error(self, msg: str, request_id: str | None = None) -> None:
        """Send an error packet to this client."""
        error: ErrorPacket = {"type": "error", "request_id": request_id, "msg": msg}
        self.send(error)

    def run(self) -> None:
        """Read packets from the client and dispatch them until it disconnects."""
        reader = self.sock.makefile("rb")
        try:
            while True:
                try:
                    packet = read_frame(reader)
                except ValueError:
                    self.send_error("Packet is not valid JSON")
                    continue
                self.server.handler.dispatch(self, packet)
        except (EOFError, ConnectionError):
            print(f"Connection {self.address} disconnected")
        finally:
            self.server.remove_client(self)
            reader.close()
            self.writer.close()
            self.sock.close()
