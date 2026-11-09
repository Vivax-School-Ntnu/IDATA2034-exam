"""Map incoming packet types to the functions that handle them."""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from server.connection import Connection
    from server.core import Server

logger = logging.getLogger(__name__)

type HandlerFunc = Callable[["Connection", dict[str, object]], None]


class Handler:
    """Validate incoming packets and route them to the function registered for their type."""

    def __init__(self, server: "Server") -> None:
        """Create the handler and register all packet types."""
        self.server = server
        self._commands: dict[str, HandlerFunc] = {}
        self.register("connect_device", self.connect_device)

    def register(self, packet_type: str, func: HandlerFunc) -> None:
        """Register `func` to handle packets whose `type` is `packet_type`."""
        self._commands[packet_type] = func

    def dispatch(self, connection: "Connection", packet: object) -> None:
        """Check a packet and pass it to the handler for its type.

        Malformed packets, unknown types and handler crashes are answered with an error packet
        instead of closing the connection. Connection errors are re-raised so the connection's
        read loop can clean up.
        """
        if not isinstance(packet, dict):
            connection.send_error("Packet must be a JSON object")
            return

        packet_dict = cast("dict[str, object]", packet)
        request_id = packet_dict.get("request_id")
        if not isinstance(request_id, str):
            request_id = None

        packet_type = packet_dict.get("type")
        if not isinstance(packet_type, str):
            connection.send_error("Packet is missing a string 'type' field", request_id)
            return

        func = self._commands.get(packet_type)
        if func is None:
            connection.send_error(f"Unknown packet type '{packet_type}'", request_id)
            return

        try:
            func(connection, packet_dict)
        except ConnectionError:
            raise
        except Exception:
            logger.exception("Handler for %r crashed", packet_type)
            connection.send_error(f"Server failed to handle '{packet_type}'", request_id)

    def connect_device(self, connection: "Connection", packet: dict[str, object]) -> None:
        """Log a connect_device packet (placeholder until registration is implemented)."""
        print(f"Client {connection.client_id} sent connect_device: {packet}")
