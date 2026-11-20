"""The central brooker server, facilitates communication between all other nodes."""

import logging
from pathlib import Path
from server.core import Server


def main() -> None:
    """Start the server."""
    logging.basicConfig(level=logging.DEBUG)
    server = Server(id_file=Path("device_ids.json"))
    try:
        server.start("0.0.0.0")
    finally:
        server.close()
