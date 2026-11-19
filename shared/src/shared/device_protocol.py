"""The protocol types for the server <-> device protocol."""

from typing import Literal

from shared.base_packet import BasePacket, SensorConfiguration, SensorValue


class DeviceConnection(BasePacket, frozen=True):
    """Connection request from a device to the server containing its configuration."""

    type: Literal["connect_device"]
    name: str
    capabilities: dict[str, SensorConfiguration]


class SensorUpdate(BasePacket, frozen=True):
    """A update to the values of the sensors on a device."""

    type: Literal["sensor_update"]
    sensors: dict[str, SensorValue]


DeviceToServerPacket = DeviceConnection | SensorUpdate
