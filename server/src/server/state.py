from dataclasses import dataclass, field

from shared.base_packet import Capability
from shared.connection import Connection
from shared.controller_protocol import Role
from shared.device_protocol import SensorValue

type LocalAddress = str
"""An address that points to a Capability thats local to a device like for exmaple "temp"."""

type GlobalAddress = str
"""A global address, meant to point to a Capability from anywhere like for exmaple "3.temp"."""
@dataclass
class DeviceState:
    """Hold the state of a device."""

    connection: Connection
    name: str
    capabilities: dict[LocalAddress, Capability]
    values: dict[LocalAddress, SensorValue] = field(default_factory=dict[LocalAddress, SensorValue])

@dataclass
class ControllerState:
    """Hold the controller state."""

    connection: Connection
    role: Role
    subscriptions: set[GlobalAddress] = field(default_factory=set[GlobalAddress])