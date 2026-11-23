"""Tests for simulated actuators."""

from typing import cast

import pytest
from device.actuator import BinaryActuator, NumericActuator
from shared.base_packet import SensorValue

# BinaryActuator tests


def test_binary_actuator_starts_off() -> None:
    """Test that a binary actuator starts with False."""
    actuator = BinaryActuator("Lamp")

    assert actuator.get_value() is False


def test_binary_actuator_custom_initial_value() -> None:
    """Test that a binary actuator can start with True."""
    actuator = BinaryActuator("Lamp", initial_value=True)

    assert actuator.get_value() is True


def test_binary_actuator_can_be_turned_on() -> None:
    """Test that a binary actuator can be turned on."""
    actuator = BinaryActuator("Lamp")

    actuator.set_value(True)

    assert actuator.get_value() is True


def test_binary_actuator_can_be_turned_off() -> None:
    """Test that a binary actuator can be turned off."""
    actuator = BinaryActuator("Lamp", initial_value=True)

    actuator.set_value(False)

    assert actuator.get_value() is False


def test_binary_actuator_can_change_value_multiple_times() -> None:
    """Test that a binary actuator can change repeatedly."""
    actuator = BinaryActuator("Lamp")

    actuator.set_value(True)
    assert actuator.get_value() is True

    actuator.set_value(False)
    assert actuator.get_value() is False

    actuator.set_value(True)
    assert actuator.get_value() is True


def test_binary_actuator_rejects_invalid_initial_value() -> None:
    """Test that invalid initial values are rejected."""
    with pytest.raises(TypeError):
        BinaryActuator("Lamp", initial_value=cast(bool, 123))


def test_binary_actuator_rejects_invalid_set_value() -> None:
    """Test that invalid values are rejected."""
    actuator = BinaryActuator("Lamp")

    with pytest.raises(TypeError):
        actuator.set_value(cast(SensorValue, "on"))

    assert actuator.get_value() is False


# NumericActuator tests


def test_numeric_actuator_starts_at_zero() -> None:
    """Test that a numeric actuator starts at zero."""
    actuator = NumericActuator("Dimmer")

    assert actuator.get_value() == 0


def test_numeric_actuator_custom_initial_value() -> None:
    """Test that a numeric actuator accepts a starting value."""
    actuator = NumericActuator("Dimmer", initial_value=50)

    assert actuator.get_value() == 50


def test_numeric_actuator_can_change_value() -> None:
    """Test that a numeric actuator can update its value."""
    actuator = NumericActuator("Dimmer")

    actuator.set_value(75)

    assert actuator.get_value() == 75


def test_numeric_actuator_can_change_value_multiple_times() -> None:
    """Test that a numeric actuator can change repeatedly."""
    actuator = NumericActuator("Dimmer")

    actuator.set_value(25)
    assert actuator.get_value() == 25

    actuator.set_value(80)
    assert actuator.get_value() == 80


def test_numeric_actuator_rejects_invalid_initial_value() -> None:
    """Test that invalid initial values are rejected."""
    with pytest.raises(TypeError):
        NumericActuator("Dimmer", initial_value=cast(int, "on"))


@pytest.mark.parametrize("invalid_value", [True, 1.5, "75"])
def test_numeric_actuator_rejects_invalid_set_value(
    invalid_value: object,
) -> None:
    """Test that a numeric actuator only accepts integers."""
    actuator = NumericActuator("Dimmer")

    with pytest.raises(TypeError):
        actuator.set_value(cast(SensorValue, invalid_value))

    assert actuator.get_value() == 0
