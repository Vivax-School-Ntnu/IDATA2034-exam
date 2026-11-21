"""The protocol types for the server <-> controller protocol."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from shared.base_packet import (
    BasePacket,
    Capability,
    GenericPacket,
    SensorValue,
)

type Role = Literal["user", "technician"]
"""Access level of a controller."""


class ControllerConnection(BasePacket, frozen=True):
    """Connection request from a controller to the server.

    The controller declares its own `role`, which the server trusts.
    """

    type: Literal["connect_controller"] = "connect_controller"
    role: Role = "user"


class Subscribe(BasePacket, frozen=True):
    """Request to receive pushed `sensor_reading` packets for the given sensor addresses.

    Addresses use the global `{device_id}.{sensor_id}` format. Subscriptions are additive:
    each `subscribe` adds its addresses to the ones the controller is already subscribed to.
    """

    type: Literal["subscribe"] = "subscribe"
    addresses: list[str]


class SetActuator(BasePacket, frozen=True):
    """Request to set the actuator at `address` to `value`.

    Requires a role that is allowed to control actuators.
    """

    type: Literal["set_actuator"] = "set_actuator"
    address: str
    value: SensorValue


ControllerToServerPacket = ControllerConnection | Subscribe | SetActuator


class DeviceInfo(BaseModel, frozen=True):
    """Everything a controller needs to know about one connected device.

    `values` only contains sensors the device has reported so far. Controllers should show a
    default (0 or false) for sensors without a value until the first `sensor_reading` arrives.
    """

    device_id: int
    name: str
    capabilities: dict[str, Capability]
    values: dict[str, SensorValue] = Field(default_factory=dict)


class ConnectionConfirmation(BasePacket, frozen=True):
    """Acknowledgement of a `connect_controller`.

    Followed by one `device_added` for every device that is already connected.
    """

    type: Literal["connection_confirmation"] = "connection_confirmation"


class DeviceAdded(BasePacket, frozen=True):
    """A device is available, either newly connected or already connected when the controller joined."""

    type: Literal["device_added"] = "device_added"
    device: DeviceInfo


class DeviceRemoved(BasePacket, frozen=True):
    """A device disconnected."""

    type: Literal["device_removed"] = "device_removed"
    device_id: int


class SensorReading(BasePacket, frozen=True):
    """A new value for a sensor the controller has subscribed to."""

    type: Literal["sensor_reading"] = "sensor_reading"
    address: str
    value: SensorValue


ServerToControllerPacket = Annotated[
    GenericPacket | ConnectionConfirmation | DeviceAdded | DeviceRemoved | SensorReading,
    Field(discriminator="type"),
]
