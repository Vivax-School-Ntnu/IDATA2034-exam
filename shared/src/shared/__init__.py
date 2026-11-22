"""Shared library between all 3 nodes for sharing protcol helpers.

As well as sharing shared types and constants.
"""

import logging
import struct
from io import Reader, Writer
from typing import Annotated

from pydantic import Field

from shared.base_packet import BasePacket, GenericPacket
from shared.controller_protocol import ControllerToServerPacket
from shared.device_protocol import DeviceToServerPacket

PORT = 8043

logger = logging.getLogger(__name__)


def write_frame(target: Writer[bytes], value: "BasePacket"):
    """Write the given packet to the stream using the packet format."""
    logger.debug(f"Writing {value!r} to socket.")
    raw_json = value.model_dump_json().encode("UTF-8")
    length = struct.pack(">Q", len(raw_json))

    target.write(length)
    target.write(raw_json)


def _read_n(reader: Reader[bytes], n: int) -> bytes:
    """Read exactly `n` bytes from the given reader."""
    result = b""
    while len(result) < n:
        data_read = reader.read(n - len(result))
        if len(data_read) == 0:
            raise EOFError(f"Reached EoF, but expected to read {n - len(result)} more bytes.")

        result += data_read

    assert len(result) == n, "Read more than `n` bytes from reader"
    return result


def read_frame(reader: Reader[bytes]) -> "BasePacket":
    """Read one frame from the reader and parse it as a `BasePacket`.

    Raises `EOFError` if the stream ends mid-frame, and `ValidationError` if the frame is not
    a valid packet.
    """
    length: int = struct.unpack(">Q", _read_n(reader, 8))[0]
    raw_json = _read_n(reader, length)

    packet = BasePacket.model_validate_json(raw_json)
    logger.debug(f"Read {packet!r} from socket.")
    return packet


ToServerPacket = Annotated[
    GenericPacket | DeviceToServerPacket | ControllerToServerPacket, Field(discriminator="type")
]
