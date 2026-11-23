"""Manage sensors and actuators belonging to a simulated device."""

from shared.base_packet import ActuatorConfiguration, Capability, SensorConfiguration, SensorValue

from device.actuator import Actuator
from device.sensor import Sensor


class Device:
    """Represent a simulated device containing sensors and actuators."""

    def __init__(self, uuid: str):
        """Initialize a device with a persistent UUID and no sensors."""
        self.uuid = uuid
        self.sensors: dict[str, Sensor] = {}
        self.actuators: dict[str, Actuator] = {}

    def add_sensor(self, sensor_id: str, sensor: Sensor) -> None:
        """Add a sensor with a unique local ID."""
        if not sensor_id or "." in sensor_id:
            raise ValueError("Invalid sensor ID")

        if sensor_id in self.sensors or sensor_id in self.actuators:
            raise ValueError(f"Sensor with ID '{sensor_id}' already exists")

        self.sensors[sensor_id] = sensor

    def add_actuator(self, actuator_id: str, actuator: Actuator) -> None:
        """Add an actuator with a unique local ID."""
        if not actuator_id or "." in actuator_id:
            raise ValueError("Invalid actuator ID")

        if actuator_id in self.actuators or actuator_id in self.sensors:
            raise ValueError(f"Actuator with ID '{actuator_id}' already exists")

        self.actuators[actuator_id] = actuator

    def get_sensor_values(self) -> dict[str, SensorValue]:
        """Return the current values of all sensors."""
        return {sensor_id: sensor.get_value() for sensor_id, sensor in self.sensors.items()}

    def get_actuator_values(self) -> dict[str, SensorValue]:
        """Return the current values of all actuators."""
        return {
            actuator_id: actuator.get_value() for actuator_id, actuator in self.actuators.items()
        }

    def set_actuator_value(self, actuator_id: str, value: SensorValue) -> None:
        """Update the value of an actuator."""
        if actuator_id not in self.actuators:
            raise ValueError(f"Actuator with ID '{actuator_id}' does not exist")

        self.actuators[actuator_id].set_value(value)

    def get_capabilities(self) -> dict[str, Capability]:
        """Return the configuration of all sensors and actuators."""
        capabilities: dict[str, Capability] = {
            sensor_id: SensorConfiguration(
                type="sensor",
                name=sensor.name,
                sensor_type=sensor.sensor_type,
            )
            for sensor_id, sensor in self.sensors.items()
        }

        for actuator_id, actuator in self.actuators.items():
            capabilities[actuator_id] = ActuatorConfiguration(
                type="actuator",
                name=actuator.name,
                actuator_type=actuator.actuator_type,
            )

        return capabilities
