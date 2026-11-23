"""Controller for the IoT network, connects to the server and provides a GUI."""

import logging
import sys

from controller.backend import Backend
from controller.backend.mock_backend import MockActuator, MockBackend, MockDevice, MockSensor
from controller.backend.real_backend import RealBackend
from controller.tui import SmartHomeApp

logger = logging.getLogger(__name__)


def _create_mock_backend() -> Backend:
    """Create a mock/fake backend for testing the tui."""
    return MockBackend(
        [
            MockDevice(
                "AC",
                [
                    MockSensor("temperature", "numeric", 20),
                ],
                [
                    MockActuator("target_temperature", "numeric", 21),
                ],
            ),
            MockDevice(
                "Door",
                [
                    MockSensor("Open", "binary", False),
                    MockSensor("outside temperature", "numeric", 12),
                ],
                [
                    MockActuator("Alarmed", "binary", True),
                ],
            ),
        ]
    )


def main() -> None:
    """Start the controller."""
    logging.basicConfig(filename="controller.log", level=logging.DEBUG)
    logger.info("Starting app")

    if "--mock" in sys.argv:
        SmartHomeApp(_create_mock_backend()).run()
    else:
        SmartHomeApp(RealBackend(("127.0.0.1", 8043))).run()
