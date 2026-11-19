"""Core protcol packets that all clients need to handle."""

from typing import Literal

from pydantic import BaseModel

type SensorType = Literal["numeric", "binary"]
type SensorValue = int | bool


class SensorConfiguration(BaseModel):
    """A description of a sensor."""

    type: Literal["sensor"] = "sensor"
    name: str
    sensor_type: SensorType


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
