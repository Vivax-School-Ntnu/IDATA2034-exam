"""The protocol types for the server <-> device protocol."""

from typing import Annotated, Literal

from pydantic import Field

from shared import BasePacket, GenericPacket, SensorConfiguration, SensorValue


class DeviceConnection(BasePacket, frozen=True):
    """Connection request from a device to the server containing its configuration."""

    type: Literal["connect_device"]
    name: str
    capabilities: dict[str, SensorConfiguration]


class SensorUpdate(BasePacket, frozen=True):
    """A update to the values of the sensors on a device."""

    type: Literal["sensor_update"]
    sensors: dict[str, SensorValue]


DeviceToServerPacket = Annotated[
    GenericPacket | DeviceConnection | SensorUpdate, Field(discriminator="type")
]
