"""Manage the runtime of a simulated device."""

from threading import Event

from device.client import DeviceClient
from device.device import Device


class DeviceRuntime:
    """Run a simulated device and send sensor updates."""

    def __init__(
        self,
        device: Device,
        client: DeviceClient,
        name: str,
        update_interval: float = 2.0,
    ) -> None:
        """Initialize the device runtime."""
        if update_interval <= 0:
            raise ValueError("Update interval must be positive")

        self.device = device
        self.client = client
        self.name = name
        self.update_interval = update_interval
        self._stop_event = Event()

    def run(self) -> None:
        """Connect and send sensor updates periodically."""
        try:
            self.client.connect()
            self.client.send_connect_device(self.device, self.name)

            if not self.client.wait_for_registration():
                raise TimeoutError("Device registration timed out.")

            while not self._stop_event.wait(self.update_interval):
                self.client.send_sensor_update(self.device)
        finally:
            self.client.close()

    def stop(self) -> None:
        """Request the runtime to stop."""
        self._stop_event.set()
