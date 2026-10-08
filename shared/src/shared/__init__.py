"""Shared library between all 3 nodes for sharing protcol helpers.

As well as sharing shared types and constants.
"""

import json
import struct
from io import Reader, Writer
from typing import Literal, TypedDict

PORT = 3000


def write_frame(target: Writer[bytes], value: object):
    """Write the given value to the stream using the packet format.

    value should be a type suitable for `json.dump`
    """
    raw_json = json.dumps(value)
    length = struct.pack(">Q", len(raw_json))

    target.write(length)
    target.write(raw_json.encode("UTF-8"))


def read_frame(reader: Reader[bytes]) -> object:
    """Read a packet from the given reader.

    returns a json compatible object.
    """
    length: int = struct.unpack(">Q", reader.read(8))[0]
    raw_json = reader.read(length).decode("UTF-8")

    return json.loads(raw_json)


class ErrorPacket(TypedDict):
    """An erorr occured.

    Contains a message, and a optional `request_id` field if the error can be asscoaited with one.
    """

    type: Literal["error"]
    request_id: str | None
    msg: str


type SensorType = Literal["numeric", "binary"]
type SensorValue = int | bool


class SensorConfiguration(TypedDict):
    """A description of a sensor."""

    type: Literal["sensor"]
    name: str
    sensor_type: SensorType
