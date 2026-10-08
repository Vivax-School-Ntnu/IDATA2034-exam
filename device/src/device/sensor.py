from abc import ABC, abstractmethod
import random

class Sensor(ABC):
    def __init__(self, name, sensor_type):
        self.name = name
        self.sensor_type = sensor_type

    @abstractmethod
    def get_value(self):
        pass

class NumericSensor(Sensor):
    def __init__(self, name):
        super().__init__(name, "numeric")

    def get_value(self):
        return int(random.uniform(0, 100))

class BinarySensor(Sensor):
    def __init__(self, name):
        super().__init__(name, "binary")

    def get_value(self):
        return random.choice([True, False])