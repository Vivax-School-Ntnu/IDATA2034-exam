"""The central brooker server, facilitates communication between all other nodes."""

from server.core import Server


def main() -> None:
    """Start the server."""
    server = Server()
    try:
        server.start("0.0.0.0")
    finally:
        server.close()
