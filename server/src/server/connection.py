"""A single client connection to the server."""

import socket

from shared import read_frame


class Connection:
    """Wrap a clients socket."""

    def __init__(self, sock: socket.socket, address: tuple[str, int]) -> None:
        """Create a connection object."""
        self.sock = sock
        self.address = address

    def run(self) -> None:
        """Read packets from the client until it disconnects."""
        reader = self.sock.makefile("rb")
        try:
            while True:
                packet = read_frame(reader)
                print(f"{packet} : {self.address}")
        except (EOFError, ConnectionError):
            print(f"Connection {self.address} disconnected")
        finally:
            reader.close()
            self.sock.close()
