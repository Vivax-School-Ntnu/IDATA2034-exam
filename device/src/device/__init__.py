"""A IoT device on the network providing actuators and sensors."""

from pathlib import Path

from device.actuator import BinaryActuator, NumericActuator
from device.client import DeviceClient
from device.device import Device
from device.identity import load_or_create_uuid
from device.runtime import DeviceRuntime
from device.sensor import BinarySensor, NumericSensor


def main() -> None:
    """Start the device."""
    device_uuid = load_or_create_uuid(Path("data/device_uuid.txt"))
    device = Device(device_uuid)

    device.add_sensor("temperature", NumericSensor("Temperature"))
    device.add_sensor("motion", BinarySensor("Motion"))

    device.add_actuator("lamp", BinaryActuator("Living room light"))
    device.add_actuator("dimmer", NumericActuator("Living room dimmer", initial_value=50))

    client = DeviceClient("127.0.0.1")

    runtime = DeviceRuntime(
        device=device,
        client=client,
        name="Living room",
        update_interval=2.0,
    )

    try:
        runtime.run()
    except KeyboardInterrupt:
        print("Device stopped.")
