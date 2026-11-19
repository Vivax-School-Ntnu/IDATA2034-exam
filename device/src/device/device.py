"""Manage sensors belonging to a simulated device."""

from shared.base_packet import SensorConfiguration, SensorValue

from device.sensor import Sensor


class Device:
    """Represent a simulated device containing multiple sensors."""

    def __init__(self, device_id: str):
        """Initialize a device with an ID and no sensors."""
        self.device_id = device_id
        self.sensors: dict[str, Sensor] = {}

    def add_sensor(self, sensor_id: str, sensor: Sensor) -> None:
        """Add a sensor with a unique local ID."""
        if "." in sensor_id:
            raise ValueError("Sensor ID cannot contain '.'")

        if sensor_id in self.sensors:
            raise ValueError(f"Sensor with ID '{sensor_id}' already exists")

        self.sensors[sensor_id] = sensor

    def get_sensor_values(self) -> dict[str, SensorValue]:
        """Return the current values of all sensors."""
        return {sensor_id: sensor.get_value() for sensor_id, sensor in self.sensors.items()}

    def get_capabilities(self) -> dict[str, SensorConfiguration]:
        """Return the configuration of all sensors."""
        return {
            sensor_id: SensorConfiguration(
                type="sensor",
                name=sensor.name,
                sensor_type=sensor.sensor_type,
            )
            for sensor_id, sensor in self.sensors.items()
        }
