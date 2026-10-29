"""Define simulated numeric and binary sensors."""

import random
from abc import ABC, abstractmethod
from typing import override

from shared import SensorType, SensorValue


class Sensor(ABC):
    """Abstract base class for all sensors."""

    def __init__(self, name: str, sensor_type: SensorType):
        """Initialize the sensor with its name and type."""
        self.name = name
        self.sensor_type = sensor_type

    @abstractmethod
    def get_value(self) -> SensorValue:
        """Return the current sensor value."""


class NumericSensor(Sensor):
    """Sensor that generates random integer values."""

    def __init__(self, name: str):
        """Initialize a numeric sensor with the given name."""
        super().__init__(name, "numeric")

    @override
    def get_value(self) -> int:
        return random.randint(0, 100)


class BinarySensor(Sensor):
    """Sensor that generates random boolean values."""

    def __init__(self, name: str):
        """Initialize a binary sensor with the given name."""
        super().__init__(name, "binary")

    @override
    def get_value(self) -> bool:
        return random.choice([True, False])
