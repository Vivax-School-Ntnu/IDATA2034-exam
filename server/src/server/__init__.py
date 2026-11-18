"""The central brooker server, facilitates communication between all other nodes."""

import logging

from server.core import Server


def main() -> None:
    """Start the server."""
    logging.basicConfig(level=logging.DEBUG)
    server = Server()
    try:
        server.start("0.0.0.0")
    finally:
        server.close()
