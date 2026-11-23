"""Implementation of Backend against the real server."""

import logging
import socket
from collections.abc import Callable, Sequence
from typing import override
from uuid import uuid4

from pydantic import TypeAdapter
from shared.base_packet import (
    ActuatorConfiguration,
    ErrorPacket,
    SensorConfiguration,
    SensorValue,
)
from shared.connection import Connection
from shared.controller_protocol import (
    ConnectionConfirmation,
    ControllerConnection,
    DeviceAdded,
    DeviceInfo,
    SensorReading,
    ServerToControllerPacket,
    SetActuator,
    Subscribe,
)

from controller.backend import Actuator, Backend, Device, Sensor

logger = logging.getLogger(__name__)


class RealSensor(Sensor):
    """A live updating sensor."""

    def __init__(self, cap: SensorConfiguration, inital_value: SensorValue) -> None:
        """Create a new live updating sensor."""
        self.name = cap.name
        self.type_ = cap.sensor_type
        self._value = inital_value
        self._on_update: Callable[[], None] = lambda: None

    @override
    def get_value(self) -> SensorValue:
        return self._value

    @override
    def register_on_update(self, callback: Callable[[], None]) -> None:
        self._on_update = callback

    def set_value(self, value: SensorValue) -> None:
        """Set the current value of the sensor from the server."""
        self._value = value
        self._on_update()


class RealActuator(Actuator):
    """A live updating actuator that lets you also set its state."""

    def __init__(
        self,
        connection: Connection,
        address: str,
        cap: ActuatorConfiguration,
        inital_value: SensorValue,
    ) -> None:
        """Create a new actuator.

        It will use the given connection and address to issue value updates to its server mirror.
        """
        self._connection = connection
        self._address = address
        self.name = cap.name
        self.type_ = cap.actuator_type
        self._value = inital_value
        self._on_update: Callable[[], None] = lambda: None

    @override
    def get_value(self) -> SensorValue:
        return self._value

    @override
    def register_on_update(self, callback: Callable[[], None]) -> None:
        self._on_update = callback

    def set_value(self, value: SensorValue) -> None:
        """Update the value of this actuator from the server.

        Does *not* send a message to the server, for that use `update_value`
        """
        self._value = value
        self._on_update()

    @override
    def update_value(self, value: SensorValue) -> None:
        self._connection.send(SetActuator(request_id=None, address=self._address, value=value))


class RealDevice(Device):
    """A device holding sensors and actuators and routing updates to them."""

    def __init__(self, connection: Connection, device_info: DeviceInfo) -> None:
        """Create a real device.

        This will subscribe to all sensors and actuators on the device.
        """
        self.sensors: dict[str, RealSensor] = {}
        self.actuators: dict[str, RealActuator] = {}

        base_address = str(device_info.device_id)
        addresses: list[str] = []
        for cap_id, cap in device_info.capabilities.items():
            full_address = f"{base_address}.{cap_id}"
            addresses.append(full_address)
            if cap.type == "sensor":
                self.sensors[cap_id] = RealSensor(cap, device_info.values[cap_id])
            else:
                self.actuators[cap_id] = RealActuator(
                    connection, full_address, cap, device_info.values[cap_id]
                )

        connection.send(Subscribe(addresses=addresses, request_id=None))

        self.name = device_info.name
        self._connection = connection

    def update_value(self, address: str, value: SensorValue) -> None:
        """Update the value of the sensor/actuator at the given local address."""
        if address in self.sensors:
            self.sensors[address].set_value(value)
        elif address in self.actuators:
            self.actuators[address].set_value(value)

    @override
    def get_actuators(self) -> Sequence[Actuator]:
        return tuple(self.actuators.values())

    @override
    def get_sensors(self) -> Sequence[Sensor]:
        return tuple(self.sensors.values())


class RealBackend(Backend):
    """A backend that connects to the real server and provides live updates."""

    def __init__(self, server: tuple[str, int]) -> None:
        """Create a backend that will connect to the given server."""
        self._server = server
        self._on_error: Callable[[str], None] = lambda _msg: None
        self._on_new_device: Callable[[Device], None] = lambda _device: None
        self._devices: dict[int, RealDevice] = {}

    @override
    def register_on_error(self, callback: Callable[[str], None]) -> None:
        self._on_error = callback

    @override
    def register_on_new_device(self, callback: Callable[[Device], None]) -> None:
        self._on_new_device = callback

    @override
    def start(self) -> None:
        logger.info(f"Connecting to server {self._server}")
        sock = socket.socket()
        sock.connect(self._server)

        connection = Connection(sock, TypeAdapter(ServerToControllerPacket), lambda: None)
        connection.register(ErrorPacket, lambda packet: self._on_error(packet.msg))
        connection.register(ConnectionConfirmation, lambda _packet: None)
        connection.register(
            DeviceAdded, lambda packet: self._handle_device_added(connection, packet)
        )
        connection.register(SensorReading, self._handle_sensor_reading)

        connection.send(ControllerConnection(request_id=str(uuid4())))

        connection.run()

    def _handle_device_added(self, connection: Connection, packet: DeviceAdded) -> None:
        device = RealDevice(connection, packet.device)
        self._devices[packet.device.device_id] = device
        self._on_new_device(device)

    def _handle_sensor_reading(self, packet: SensorReading) -> None:
        device_id, sensor_address = packet.address.split(".", 1)
        self._devices[int(device_id)].update_value(sensor_address, packet.value)
