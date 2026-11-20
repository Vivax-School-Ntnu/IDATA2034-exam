"""Controller for the IoT network, connects to the server and provides a GUI."""

import logging

from controller.backend import Backend
from controller.backend.mock_backend import MockBackend, MockDevice, MockSensor
from controller.tui import SmartHomeApp

logger = logging.getLogger(__name__)


def create_mock_backend() -> Backend:
    return MockBackend(
        [
            MockDevice(
                "AC",
                [
                    MockSensor("temperature", "numeric", 20),
                    MockSensor("target_temperature", "numeric", 21),
                ],
            ),
            MockDevice(
                "Door",
                [
                    MockSensor("Open", "binary", False),
                    MockSensor("Alarmed", "binary", True),
                    MockSensor("outside temperature", "numeric", 12),
                ],
            ),
        ]
    )


def main() -> None:
    """Start the controller."""
    logging.basicConfig(filename="controller.log", level=logging.DEBUG)
    logger.info("Starting app")
    SmartHomeApp(create_mock_backend()).run()
