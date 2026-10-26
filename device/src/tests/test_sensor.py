from unittest.mock import patch

import pytest
from device.sensor import BinarySensor, NumericSensor, Sensor


def test_sensor_is_abstract():
    """Test that Sensor cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Sensor("temperature", "numeric")

def test_numeric_sensor_name():
    """Tests that the numeric sensor stores its name correctly."""
    sensor = NumericSensor("temperature")
    assert sensor.name == "temperature"

def test_numeric_sensor_type():
    """Test that the numeric sensor has the correct sensor type."""
    sensor = NumericSensor("temperature")
    assert sensor.sensor_type == "numeric"

def test_numeric_sensor_value():
    """Test that the numeric sensor returns an integer between 0 and 100."""
    sensor = NumericSensor("temperature")
    value = sensor.get_value()

    assert type(value) is int
    assert 0 <= value <= 100

def test_binary_sensor_name():
    """Test that the binary sensor stores its name correctly."""
    sensor = BinarySensor("motion")
    assert sensor.name == "motion"

def test_binary_sensor_type():
    """Test that the binary sensor has the correct sensor type."""
    sensor = BinarySensor("motion")
    assert sensor.sensor_type == "binary"

def test_binary_sensor_value():
    """Test that the binary sensor returns a boolean value."""
    sensor = BinarySensor("motion")
    value = sensor.get_value()

    assert isinstance(value, bool)

def test_binary_sensor_both_values():
    """Test that the binary sensor returns both possible values."""
    sensor = BinarySensor("motion")

    with patch("device.sensor.random.choice", return_value=True):
        assert sensor.get_value() is True

    with patch("device.sensor.random.choice", return_value=False):
        assert sensor.get_value() is False