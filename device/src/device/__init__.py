"""A simulated IoT device providing actuators and sensors."""

import argparse
import os
from pathlib import Path

from device.actuator import BinaryActuator, NumericActuator
from device.client import DeviceClient
from device.device import Device
from device.identity import load_or_create_uuid
from device.runtime import DeviceRuntime
from device.sensor import BinarySensor, NumericSensor


def main() -> None:
    """Start a simulated device using the selected configuration."""
    parser = argparse.ArgumentParser(description="Start a simulated IoT device.")
    parser.add_argument(
        "--config",
        choices=["living-room", "bathroom"],
        default="living-room",
        help="Select the device configuration",
    )
    args = parser.parse_args()

    if args.config == "living-room":
        uuid_path = Path("data/device_uuid.txt")
        device_name = "Living room"
    else:
        uuid_path = Path("data/bathroom_uuid.txt")
        device_name = "Bathroom"

    device_uuid = load_or_create_uuid(uuid_path)
    device = Device(device_uuid)

    if args.config == "living-room":
        device.add_sensor("temperature", NumericSensor("Temperature"))
        device.add_sensor("motion", BinarySensor("Motion"))
        device.add_actuator("lamp", BinaryActuator("Living room light"))
        device.add_actuator("dimmer", NumericActuator("Living room dimmer", initial_value=50))
    else:
        device.add_sensor("temperature", NumericSensor("Bathroom temperature"))
        device.add_actuator("lamp", BinaryActuator("Bathroom light"))

    client = DeviceClient(os.environ.get("SERVER_HOST", "127.0.0.1"))

    runtime = DeviceRuntime(
        device=device,
        client=client,
        name=device_name,
        update_interval=3.0,
    )

    try:
        runtime.run()
    except KeyboardInterrupt:
        print("Device stopped.")
