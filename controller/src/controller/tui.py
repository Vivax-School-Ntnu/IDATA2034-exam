"""The TUI/UI implementation for the controller."""
# textual doesnt fully type `Widget.app`
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false

import functools
import logging
import threading
from collections.abc import Callable

from shared.base_packet import SensorValue
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Checkbox, Footer, Header, Label

from controller.backend import Backend, Device, Sensor

logger = logging.getLogger(__name__)


class SensorWidget(HorizontalGroup):
    """Widget for displaying the name and value of a sensor."""

    value: reactive[SensorValue] = reactive(False)

    def __init__(self, sensor: Sensor) -> None:
        """Create a new sensor widget that subscribes to the given sensor."""
        super().__init__(classes="sensor")
        self.sensor = sensor

    def on_mount(self) -> None:
        """Register callbacks for sensor updates."""
        self.value = self.sensor.get_value()
        self.sensor.register_on_update(backend_handler(self.app, self.backend_sensor_update))

    def backend_sensor_update(self) -> None:
        """Update sensor value from sensor."""
        logger.debug("Got sensor update from backend.")
        self.value = self.sensor.get_value()

    def compose(self) -> ComposeResult:
        """Create widget layout."""
        match self.sensor.type_:
            case "numeric":
                yield Label(classes="sensor_numeric_value")
                yield Label(self.sensor.name, classes="sensor_name")
            case "binary":
                yield Checkbox(self.sensor.name, classes="sensor_binary_value", disabled=True)

    def watch_value(self, value: SensorValue) -> None:
        """Update widget with new sensor value.

        Called automatically by textual when `self.value` changes.
        """
        match self.sensor.type_:
            case "numeric":
                self.query_exactly_one(".sensor_numeric_value", Label).update(str(value))
            case "binary":
                self.query_exactly_one(".sensor_binary_value", Checkbox).value = bool(value)


class DeviceWidget(VerticalGroup):
    """Card widget showing the sensors of a device."""

    def __init__(self, device: Device) -> None:
        """Create a widget for the specific device."""
        super().__init__(classes="device")
        self.device = device

    def compose(self) -> ComposeResult:
        """Create a list of sensors plus device name."""
        yield Label(self.device.name, classes="device_name")
        yield from [SensorWidget(sensor) for sensor in self.device.get_sensors()]


class SmartHomeApp(App[None]):
    """The tui frontend for the controller node."""

    def __init__(self, backend: Backend) -> None:
        """Create a new smart home app with the given backend."""
        super().__init__()
        self.backend = backend

    CSS_PATH = "styles.tcss"
    BINDINGS = []  # noqa: RUF012

    def compose(self) -> ComposeResult:
        """Create a simple app layout."""
        yield Header()
        yield VerticalScroll(id="devices")
        yield Footer()

    def backend_on_device_added(self, device: Device) -> None:
        """Add the given device to the tui."""
        logger.debug(f"New device from backend: {device.name}.")
        self.query_exactly_one("#devices").mount(DeviceWidget(device))

    def on_mount(self) -> None:
        """Start the backend and register callbacks."""
        logger.debug("App on mount called.")

        self.backend.register_on_new_device(backend_handler(self, self.backend_on_device_added))
        self.backend.register_on_error(
            backend_handler(self, lambda msg: self.notify(msg, severity="error"))
        )
        threading.Thread(target=self.backend.start, daemon=True).start()


def backend_handler[**P](app: App[None], function: Callable[P, None]) -> Callable[P, None]:
    """Convert a given callback to one that can be passed to a different thread.

    This wraps `call_from_thread` to ensure ui methods run in the ui thread, as well as handles catching and logging errors in the ui thread instead of crashing the backend thread.
    """

    def on_ui_thread(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            return function(*args, **kwargs)
        except Exception:
            logger.exception(f"UI handler {function.__qualname__} failed")
            app.notify(f"UI error in {function.__qualname__}", severity="error")

    @functools.wraps(function)
    def thread_safe_function(*args: P.args, **kwargs: P.kwargs) -> None:
        return app.call_from_thread(on_ui_thread, *args, **kwargs)

    return thread_safe_function
