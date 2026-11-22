from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError
from shared.controller_protocol import (
    ControllerConnection,
    DeviceAdded,
    DeviceInfo,
    DeviceRemoved,
    SensorReading,
    ServerToControllerPacket,
    SetActuator,
    Subscribe,
)
from shared.device_protocol import DeviceConnected, ServerToDevicePacket, UpdateActuator

from shared import ToServerPacket

to_server = TypeAdapter(ToServerPacket)
to_controller = TypeAdapter(ServerToControllerPacket)
to_device = TypeAdapter(ServerToDevicePacket)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"type": "connect_controller", "request_id": "1", "role": "user"}, ControllerConnection),
        ({"type": "subscribe", "request_id": "2", "addresses": ["3.temp"]}, Subscribe),
        (
            {"type": "set_actuator", "request_id": "3", "address": "3.fan", "value": True},
            SetActuator,
        ),
    ],
)
def test_server_accepts_controller_packets(data: dict[str, Any], expected: type) -> None:
    assert isinstance(to_server.validate_python(data), expected)


def test_unknown_role_is_rejected() -> None:
    with pytest.raises(ValidationError):
        to_server.validate_python(
            {"type": "connect_controller", "request_id": "1", "role": "admin"}
        )


@pytest.mark.parametrize(
    "packet",
    [
        DeviceAdded(
            request_id=None,
            device=DeviceInfo(device_id=3, name="AC", capabilities={}, values={"temp": 21}),
        ),
        DeviceRemoved(request_id=None, device_id=3),
        SensorReading(request_id=None, address="3.temp", value=22),
    ],
)
def test_controller_packets_round_trip(packet: object) -> None:
    assert isinstance(packet, DeviceAdded | DeviceRemoved | SensorReading)
    assert to_controller.validate_json(packet.model_dump_json()) == packet


@pytest.mark.parametrize(
    "packet",
    [
        DeviceConnected(request_id="1", device_id=3),
        UpdateActuator(request_id="2", actuator="fan", value=True),
    ],
)
def test_device_packets_round_trip(packet: DeviceConnected | UpdateActuator) -> None:
    assert to_device.validate_json(packet.model_dump_json()) == packet
