"""Map incoming packet types to the functions that handle them."""

import contextlib
import logging
import socket
import threading
from collections.abc import Callable
from typing import Any

from pydantic import TypeAdapter
from pydantic_core import ValidationError

from shared import BasePacket, ErrorPacket, read_frame, write_frame

logger = logging.getLogger(__name__)

type HandlerFunction[T] = Callable[[T], None]


class Connection(threading.Thread):
    """Validate incoming packets and route them to the function registered for their type."""

    def __init__[T: BasePacket](
        self,
        socket: socket.socket,
        pydantic_converter: TypeAdapter[T],
        disconnect_handler: Callable[[], None],
    ) -> None:
        """Create the handler and register all packet types."""
        self._pydantic_converter = pydantic_converter
        self.socket = socket
        self._writer = self.socket.makefile("wb")
        self._reader = self.socket.makefile("rb")
        self._write_lock = threading.Lock()
        self._disconnect_handler = disconnect_handler

        # the typer checker (correctly) will complain that in theory some code might call the wrong handler with the wrong arugment type.
        # we are effectivelly doing a "any-map" here
        self._commands: dict[type[BasePacket], HandlerFunction[Any]] = {}

        super().__init__(daemon=True, name="Connection")

    def send(self, packet: BasePacket) -> None:
        """Send the given packet to the socket.

        This method is thread-safe.
        """
        try:
            with self._write_lock:
                write_frame(self._writer, packet)
                self._writer.flush()
        except (OSError, ValueError):
            logger.exception(f"Could not send {packet!r}")

    def send_error(self, msg: str, request_id: str | None) -> None:
        """Send (and log) the given error message to this client.

        If the error is a issue with a known request also send `request_id` matching that request.
        """
        logger.exception(msg)
        error = ErrorPacket(request_id=request_id, msg=msg)
        self.send(error)

    def register[T: BasePacket](self, packet_type: type[T], func: HandlerFunction[T]) -> None:
        """Register `func` to handle packets whose type is `packet_type`.

        Handlers will be ran in a dedicated thread, as such ensure the handlers are thread safe.
        """
        self._commands[packet_type] = func

    def _dispatch(self, packet: BasePacket) -> None:
        """Check a packet and pass it to the handler for its type."""
        logger.debug(f"Validating {packet!r}")

        try:
            packet = self._pydantic_converter.validate_python(packet.model_dump())
        except ValidationError:
            self.send_error(f"Unknown (or invalid) packet {packet!r}", packet.request_id)
            return

        func = self._commands.get(type(packet))
        if func is None:
            self.send_error(
                f"Unknown packet type '{type(packet)}' for this handler", packet.request_id
            )
            return

        logger.debug(f"Handling {packet!r}.")
        try:
            func(packet)
        except Exception:  # noqa: BLE001 - `self.send_error` calls `logger.exception`
            self.send_error(f"Failed to handle {packet!r}", packet.request_id)

    def run(self) -> None:
        """Start the read loop for this connection.

        This will read frames and hand them to the functions registered with `.register`.
        """
        logger.info("Starting read loop.")
        try:
            while True:
                try:
                    packet = read_frame(self._reader)
                except ValidationError:
                    self.send_error("Failed to read frame.", None)
                else:
                    threading.Thread(
                        target=self._dispatch, args=(packet,), daemon=True, name="Packet Handler"
                    ).start()
        except (EOFError, ValueError, OSError):
            logger.exception("Error in read loop")
        finally:
            logger.info("Disconnecting.")
            self._reader.close()
            with contextlib.suppress(OSError):
                self._writer.close()
            self.socket.close()
            self._disconnect_handler()

    def close(self) -> None:
        """Close this connection, stopping the read-loop thread and closing the socket."""
        logger.debug("Requesting read loop to stop.")
        with contextlib.suppress(OSError):
            self.socket.shutdown(socket.SHUT_RDWR)
