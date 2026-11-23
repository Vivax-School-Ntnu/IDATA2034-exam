"""Represent simulated actuators."""

from abc import ABC, abstractmethod
from typing import override

from shared.base_packet import ActuatorType, SensorValue


class Actuator(ABC):
    """Abstract base class for all actuators."""

    def __init__(self, name: str, actuator_type: ActuatorType) -> None:
        """Initialize the actuator with its name and type."""
        self.name = name
        self.actuator_type: ActuatorType = actuator_type

    @abstractmethod
    def get_value(self) -> SensorValue:
        """Return the current actuator value."""

    @abstractmethod
    def set_value(self, value: SensorValue) -> None:
        """Update the actuator value."""


class BinaryActuator(Actuator):
    """Actuator with a boolean value."""

    def __init__(self, name: str, initial_value: bool = False) -> None:
        """Initialize the binary actuator."""
        super().__init__(name, "binary")
        self._value: bool = False
        self.set_value(initial_value)

    @override
    def get_value(self) -> bool:
        """Return the current actuator value."""
        return self._value

    @override
    def set_value(self, value: SensorValue) -> None:
        """Update the binary actuator value."""
        if not isinstance(value, bool):
            raise TypeError("Binary actuator value must be a boolean")

        self._value = value


class NumericActuator(Actuator):
    """Actuator with an integer value."""

    def __init__(self, name: str, initial_value: int = 0) -> None:
        """Initialize the numeric actuator."""
        super().__init__(name, "numeric")
        self._value: int = 0
        self.set_value(initial_value)

    @override
    def get_value(self) -> int:
        """Return the current actuator value."""
        return self._value

    @override
    def set_value(self, value: SensorValue) -> None:
        """Update the numeric actuator value."""
        if type(value) is not int:
            raise TypeError("Numeric actuator value must be an integer")

        self._value = value
