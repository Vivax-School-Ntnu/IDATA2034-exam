"""A fake backend for testing the tui."""

from collections.abc import Sequence
from typing import Callable
import time

from controller.backend import Backend, Device, Sensor
from shared.base_packet import SensorType, SensorValue

import logging

logger = logging.getLogger(__name__)


class MockSensor(Sensor):
    def __init__(self, name: str, type_: SensorType, value: SensorValue) -> None:
        self.name = name
        self.type_ = type_
        self._value = value
        self._on_update: Callable[[], None] = lambda: None

    def get_value(self) -> SensorValue:
        logger.debug("Getting sensor value")
        return self._value

    def register_on_update(self, callback: Callable[[], None]) -> None:
        self._on_update = callback

    def update(self) -> None:
        match self.type_:
            case "numeric":
                self._value += 1
            case "binary":
                self._value = not self._value
        self._on_update()


class MockDevice(Device):
    """A fake device"""

    def __init__(self, name: str, sensors: list[MockSensor]) -> None:
        self.name = name
        self.sensors = sensors

    def get_sensors(self) -> Sequence[Sensor]:
        return self.sensors


class MockBackend(Backend):
    """A backend returning hardcoded fake sensors for testing the controller without the server."""

    def __init__(self, devices: list[MockDevice]) -> None:
        self._devices = devices
        self._on_new_device: Callable[[Device], None] = lambda _device: None
        self._on_error: Callable[[str], None] = lambda _msg: None

    def start(self) -> None:
        logger.debug("Mock backend started")

        for device in self._devices:
            logger.debug("Adding new device")
            self._on_new_device(device)
            time.sleep(1)

        logger.debug("Sending test error to ui")
        self._on_error("Test Error")

        while True:
            time.sleep(1)
            for device in self._devices:
                for sensor in device.sensors:
                    time.sleep(0.5)
                    sensor.update()

    def register_on_new_device(self, callback: Callable[[Device], None]) -> None:
        self._on_new_device = callback

    def register_on_error(self, callback: Callable[[str], None]) -> None:
        self._on_error = callback
