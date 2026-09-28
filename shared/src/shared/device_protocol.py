"""The protocol types for the server <-> device protocol."""

from typing import Literal, TypedDict

from shared import SensorConfiguration, SensorValue


class DeviceConnection(TypedDict):
    """Connection request from a device to the server containing its configuration."""

    type: Literal["connect_device"]
    request_id: str
    name: str
    capabilities: dict[str, SensorConfiguration]


class SensorUpdate(TypedDict):
    """A update to the values of the sensors on a device."""

    type: Literal["sensor_update"]
    sensors: dict[str, SensorValue]
