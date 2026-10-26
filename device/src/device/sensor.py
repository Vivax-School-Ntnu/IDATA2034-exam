"""Define simulated numeric and binary sensors."""

import random
from abc import ABC, abstractmethod


class Sensor(ABC):

    """Abstract base class for all sensors."""

    def __init__(self, name: str, sensor_type: str):
        """Initialize the sensor with its name and type."""
        self.name = name
        self.sensor_type = sensor_type

    @abstractmethod
    def get_value(self) -> int | bool:
        """Return the current sensor value."""

class NumericSensor(Sensor):

    """Sensor that generates random integer values."""

    def __init__(self, name: str):
        """Initialize a numeric sensor with the given name."""
        super().__init__(name, "numeric")

    def get_value(self) -> int:
        """Return a random integer between 0 and 100."""
        return random.randint(0, 100)

class BinarySensor(Sensor):

    """Sensor that generates random boolean values."""

    def __init__(self, name: str):
        """Initialize a binary sensor with the given name."""
        super().__init__(name, "binary")

    def get_value(self) -> bool:
        """Return a random boolean value."""
        return random.choice([True, False])