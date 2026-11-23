"""Tests for simulated devices."""

import pytest
from device.actuator import BinaryActuator, NumericActuator
from device.device import Device
from device.sensor import BinarySensor, NumericSensor

TEST_UUID = "8F3c92a1-6b47-4d20-pe15-c8a72f0b6349"


@pytest.fixture
def device() -> Device:
    """Create a new device with a UUID for each test."""
    return Device(TEST_UUID)


def test_device_id(device: Device) -> None:
    """Test that a device stores its UUID."""
    assert device.uuid == TEST_UUID


def test_device_starts_empty(device: Device) -> None:
    """Test that a new device has no sensors."""
    assert device.get_sensor_values() == {}


def test_add_sensor(device: Device) -> None:
    """Test that a sensor can be added."""
    sensor = NumericSensor("temperature")

    device.add_sensor("temp1", sensor)

    assert device.sensors["temp1"] is sensor


def test_multiple_sensors(device: Device) -> None:
    """Test that a device supports multiple sensors."""
    device.add_sensor("temp1", NumericSensor("temperature"))
    device.add_sensor("motion1", BinarySensor("motion"))

    values = device.get_sensor_values()

    assert len(values) == 2
    assert type(values["temp1"]) is int
    assert type(values["motion1"]) is bool


def test_duplicate_sensor_id(device: Device) -> None:
    """Test that duplicate sensor IDs are rejected."""
    device.add_sensor("temp1", NumericSensor("temperature"))

    with pytest.raises(ValueError):
        device.add_sensor("temp1", NumericSensor("temperature"))


def test_invalid_sensor_id(device: Device) -> None:
    """Test that sensor IDs cannot contain dots."""
    with pytest.raises(ValueError):
        device.add_sensor("temp.1", NumericSensor("temperature"))


def test_empty_capabilities(device: Device) -> None:
    """Test that a device without sensors has no capabilities."""
    assert device.get_capabilities() == {}


def test_get_capabilities(device: Device) -> None:
    """Test that capabilities contain correct sensor information."""
    device.add_sensor("temp1", NumericSensor("temperature"))
    device.add_sensor("motion1", BinarySensor("motion"))

    capabilities = {
        sensor_id: config.model_dump() for sensor_id, config in device.get_capabilities().items()
    }

    assert capabilities == {
        "temp1": {
            "type": "sensor",
            "name": "temperature",
            "sensor_type": "numeric",
        },
        "motion1": {
            "type": "sensor",
            "name": "motion",
            "sensor_type": "binary",
        },
    }


def test_device_add_actuator() -> None:
    """Test that an actuator can be added to a device."""
    device = Device("test-uuid")
    actuator = BinaryActuator("Lamp")

    device.add_actuator("lamp", actuator)

    assert device.get_actuator_values() == {"lamp": False}


def test_device_set_actuator_value() -> None:
    """Test that a device can update an actuator value."""
    device = Device("test-uuid")
    device.add_actuator("lamp", BinaryActuator("Lamp"))

    device.set_actuator_value("lamp", True)

    assert device.get_actuator_values() == {"lamp": True}


def test_device_set_unknown_actuator() -> None:
    """Test that updating an unknown actuator raises an error."""
    device = Device("test-uuid")

    with pytest.raises(ValueError):
        device.set_actuator_value("lamp", True)


def test_device_rejects_duplicate_actuator_id() -> None:
    """Test that two actuators cannot have the same ID."""
    device = Device("test-uuid")
    device.add_actuator("lamp", BinaryActuator("Lamp"))

    with pytest.raises(ValueError):
        device.add_actuator("lamp", BinaryActuator("Another lamp"))


@pytest.mark.parametrize("actuator_id", ["", "living.room"])
def test_device_rejects_invalid_actuator_id(actuator_id: str) -> None:
    """Test that invalid actuator IDs are rejected."""
    device = Device("test-uuid")

    with pytest.raises(ValueError):
        device.add_actuator(actuator_id, BinaryActuator("Lamp"))


def test_device_rejects_actuator_with_sensor_id() -> None:
    """Test that an actuator cannot reuse a sensor ID."""
    device = Device("test-uuid")
    device.add_sensor("temperature", NumericSensor("Temperature"))

    with pytest.raises(ValueError):
        device.add_actuator("temperature", BinaryActuator("Lamp"))


def test_device_rejects_sensor_with_actuator_id() -> None:
    """Test that a sensor cannot reuse an actuator ID."""
    device = Device("test-uuid")
    device.add_actuator("lamp", BinaryActuator("Lamp"))

    with pytest.raises(ValueError):
        device.add_sensor("lamp", NumericSensor("Temperature"))


def test_device_numeric_actuator() -> None:
    """Test that a device supports numeric actuators."""
    device = Device("test-uuid")
    device.add_actuator("dimmer", NumericActuator("Dimmer"))

    device.set_actuator_value("dimmer", 75)

    assert device.get_actuator_values() == {"dimmer": 75}


def test_get_actuator_capabilities() -> None:
    """Test that capabilities include binary and numeric actuators."""
    device = Device("test-uuid")
    device.add_actuator("lamp", BinaryActuator("Living room light"))
    device.add_actuator("dimmer", NumericActuator("Dimmer"))

    capabilities = {
        actuator_id: config.model_dump()
        for actuator_id, config in device.get_capabilities().items()
    }

    assert capabilities == {
        "lamp": {
            "type": "actuator",
            "name": "Living room light",
            "actuator_type": "binary",
        },
        "dimmer": {
            "type": "actuator",
            "name": "Dimmer",
            "actuator_type": "numeric",
        },
    }


def test_get_mixed_capabilities() -> None:
    """Test that capabilities include both sensors and actuators."""
    device = Device("test-uuid")

    device.add_sensor("temperature", NumericSensor("Temperature"))
    device.add_actuator("lamp", BinaryActuator("Living room light"))

    capabilities = {
        capability_id: config.model_dump()
        for capability_id, config in device.get_capabilities().items()
    }

    assert capabilities == {
        "temperature": {
            "type": "sensor",
            "name": "Temperature",
            "sensor_type": "numeric",
        },
        "lamp": {
            "type": "actuator",
            "name": "Living room light",
            "actuator_type": "binary",
        },
    }
