"""The protocol types for the server <-> device protocol."""

from typing import Annotated, Literal

from pydantic import Field

from shared.base_packet import (
    ActuatorConfiguration,
    BasePacket,
    GenericPacket,
    SensorConfiguration,
    SensorValue,
)


class DeviceConnection(BasePacket, frozen=True):
    """Connection request from a device to the server containing its configuration. Must contain a semi random uuid."""

    type: Literal["connect_device"]
    name: str
    capabilities: dict[str, SensorConfiguration]
    actuators: dict[str, ActuatorConfiguration] = Field(default_factory=dict)
    uuid: str


class SensorUpdate(BasePacket, frozen=True):
    """A update to the values of the sensors on a device.

    Devices also report the current state of their actuators here, keyed by actuator id.
    """

    type: Literal["sensor_update"]
    sensors: dict[str, SensorValue]


DeviceToServerPacket = DeviceConnection | SensorUpdate


class DeviceConnected(BasePacket, frozen=True):
    """Acknowledgement of a `connect_device`, sent once the server has registered the device.

    Carries the `request_id` of the `connect_device` it answers. Devices should wait for it
    before sending sensor updates.
    """

    type: Literal["device_connected"] = "device_connected"
    device_id: int


class UpdateActuator(BasePacket, frozen=True):
    """Command from the server telling a device to set one of its actuators.

    `actuator` is the device-local actuator id. The device reports the resulting state back
    in a `sensor_update`.
    """

    type: Literal["update_actuator"] = "update_actuator"
    actuator: str
    value: SensorValue


ServerToDevicePacket = Annotated[
    GenericPacket | DeviceConnected | UpdateActuator, Field(discriminator="type")
]
