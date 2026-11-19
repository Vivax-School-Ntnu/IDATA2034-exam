import pytest
from device.device import Device
from device.sensor import BinarySensor, NumericSensor


@pytest.fixture
def device() -> Device:
    """Creates a new device for each test."""
    return Device("device1")


def test_device_id(device: Device):
    """Test that a device stores its ID."""
    assert device.device_id == "device1"


def test_device_starts_empty(device: Device):
    """Test that a new device has no sensors."""
    assert device.get_sensor_values() == {}


def test_add_sensor(device: Device):
    """Tests that a sensor can be added."""
    sensor = NumericSensor("temperature")

    device.add_sensor("temp1", sensor)

    assert device.sensors["temp1"] is sensor


def test_multiple_sensors(device: Device):
    """Test that a device supports multiple sensors."""
    device.add_sensor("temp1", NumericSensor("temperature"))
    device.add_sensor("motion1", BinarySensor("motion"))

    values = device.get_sensor_values()

    assert len(values) == 2
    assert type(values["temp1"]) is int
    assert type(values["motion1"]) is bool


def test_duplicate_sensor_id(device: Device):
    """Tests that duplicate sensor IDs are rejected"""
    device.add_sensor("temp1", NumericSensor("temperature"))

    with pytest.raises(ValueError):
        device.add_sensor("temp1", NumericSensor("temperature"))


def test_invalid_sensor_id(device: Device):
    """Test that sensor IDs cannot contain dots."""
    with pytest.raises(ValueError):
        device.add_sensor("temp.1", NumericSensor("temperature"))


def test_empty_capabilities(device: Device):
    """Test that a device without sensors has no capabilities."""
    assert device.get_capabilities() == {}


def test_get_capabilities(device: Device):
    """Test that capabilities contain correct sensor information."""
    device.add_sensor("temp1", NumericSensor("temperature"))
    device.add_sensor("motion1", BinarySensor("motion"))

    capabilities = {
        sensor_id: config.model_dump() for sensor_id, config in device.get_capabilities().items()
    }

    assert capabilities == {
        "temp1": {"type": "sensor", "name": "temperature", "sensor_type": "numeric"},
        "motion1": {"type": "sensor", "name": "motion", "sensor_type": "binary"},
    }
