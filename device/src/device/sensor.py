from abc import ABC, abstractmethod
import random

class Sensor(ABC):
    """Abstract base class for all sensors."""

    def __init__(self, name: str, sensor_type: str):
        self.name = name
        self.sensor_type = sensor_type

    @abstractmethod
    def get_value(self) -> int | bool:
        """Return the current sensor value."""
        pass

class NumericSensor(Sensor):
    """Sensor that generates random integer values."""

    def __init__(self, name: str):
        super().__init__(name, "numeric")

    def get_value(self) -> int:
        return random.randint(0, 100)

class BinarySensor(Sensor):
    """Sensor that generates random boolean values."""

    def __init__(self, name: str):
        super().__init__(name, "binary")

    def get_value(self) -> bool:
        return random.choice([True, False])