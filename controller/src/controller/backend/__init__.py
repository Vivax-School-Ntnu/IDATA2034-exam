"""Abstraction to allow swapping the real server with a fake one for the controller."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from shared.base_packet import ActuatorType, SensorType, SensorValue


class Sensor(ABC):
    """A sensor from the backend."""

    name: str
    type_: SensorType

    @abstractmethod
    def get_value(self) -> SensorValue:
        """Get the latest value of the sensor."""

    @abstractmethod
    def register_on_update(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when the sensor value changes."""


class Actuator(ABC):
    """A actuator from the backend."""

    name: str
    type_: ActuatorType

    @abstractmethod
    def get_value(self) -> SensorValue:
        """Get the current value of the actuator."""

    @abstractmethod
    def register_on_update(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when the actuator value changes."""

    @abstractmethod
    def update_value(self, value: SensorValue) -> None:
        """Update the value of this actuator."""


class Device(ABC):
    """A device in the backend."""

    name: str

    @abstractmethod
    def get_sensors(self) -> Sequence[Sensor]:
        """Get a sequence of sensors on this device."""

    @abstractmethod
    def get_actuators(self) -> Sequence[Actuator]:
        """Get a sequence of actuators on this device."""


class Backend(ABC):
    """A backend provides data and handles actions from the ui."""

    @abstractmethod
    def start(self) -> None:
        """Start this backend.

        Should be spawned in a background thread.
        """

    @abstractmethod
    def register_on_new_device(self, callback: Callable[[Device], None]) -> None:
        """Register callback for when a device is added."""

    @abstractmethod
    def register_on_device_removed(self, callback: Callable[[Device], None]) -> None:
        """Register callback for when a device is removed."""

    @abstractmethod
    def register_on_error(self, callback: Callable[[str], None]) -> None:
        """Register callback for when a error occurs in the backend."""
