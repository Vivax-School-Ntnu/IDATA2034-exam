"""Abstraction to allow swapping the real server with a fake one for the controller."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Callable

from shared.base_packet import SensorType, SensorValue


class Sensor(ABC):
    """A sensor from the backend."""

    name: str
    type_: SensorType

    @abstractmethod
    def get_value(self) -> SensorValue:
        """"""

    @abstractmethod
    def register_on_update(self, callback: Callable[[], None]) -> None:
        """"""


class Device(ABC):
    """A device in the backend."""

    name: str

    @abstractmethod
    def get_sensors(self) -> Sequence[Sensor]:
        """"""


class Backend(ABC):
    """A backend provides data and handles actions from the ui."""

    @abstractmethod
    def start(self) -> None:
        """"""

    @abstractmethod
    def register_on_new_device(self, callback: Callable[[Device], None]) -> None:
        """"""

    @abstractmethod
    def register_on_error(self, callback: Callable[[str], None]) -> None:
        pass
