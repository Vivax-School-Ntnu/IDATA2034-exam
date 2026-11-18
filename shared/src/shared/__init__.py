"""Shared library between all 3 nodes for sharing protcol helpers.

As well as sharing shared types and constants.
"""

import logging
import struct
from io import Reader, Writer
from typing import Literal

from pydantic import BaseModel

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


class BasePacket(BaseModel, frozen=True, extra="allow"):
    """The base packet all packets build from.

    * `type`: indicates the subtype to parse the packet into
    * `request_id`: a request_id for error handling and other needs of associating reponses.
    """

    type: str
    request_id: str | None


class ErrorPacket(BasePacket, frozen=True):
    """An erorr occured.

    Contains a message, and a optional `request_id` field if the error can be asscoaited with one.
    """

    type: Literal["error"] = "error"
    msg: str


class DisconnectPacket(BasePacket, frozen=True):
    """Disconnection request from a node to the server holding its connection."""

    type: Literal["disconnect"]


GenericPacket = ErrorPacket | DisconnectPacket

type SensorType = Literal["numeric", "binary"]
type SensorValue = int | bool


class SensorConfiguration(BaseModel):
    """A description of a sensor."""

    type: Literal["sensor"] = "sensor"
    name: str
    sensor_type: SensorType
