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
from textual.widgets import Checkbox, Footer, Header, Input, Label

from controller.backend import Actuator, Backend, Device, Sensor

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


class ActuatorWidget(HorizontalGroup):
    """Widget for displaying the name and value of a actuator, as well as changing the value."""

    value: reactive[SensorValue] = reactive(False)

    def __init__(self, actuator: Actuator) -> None:
        """Create a new actuator widget that subscribes to the given actuator."""
        super().__init__(classes="actuator")
        self.actuator = actuator

    def on_mount(self) -> None:
        """Register callbacks for actuator updates."""
        self.value = self.actuator.get_value()
        self.actuator.register_on_update(backend_handler(self.app, self.backend_actuator_update))

    def backend_actuator_update(self) -> None:
        """Update actuator value from actuator."""
        logger.debug("Got actuator update from backend.")
        self.value = self.actuator.get_value()

    def compose(self) -> ComposeResult:
        """Create widget layout."""
        match self.actuator.type_:
            case "numeric":
                input_widget = Input(type="integer", classes="actuator_numeric_value")
                input_widget.border_title = self.actuator.name
                yield input_widget
            case "binary":
                yield Checkbox(self.actuator.name, classes="actuator_binary_value")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Update the actuator on the server."""
        self.app.notify(f"Setting Actuator to {event.value}")
        try:
            self.actuator.update_value(int(event.value))
        except ValueError as exp:
            self.app.notify(str(exp), severity="error")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Update the actuator on the server."""
        self.app.notify(f"Setting Actuator to {event.value}")
        self.actuator.update_value(event.value)

    def watch_value(self, value: SensorValue) -> None:
        """Update widget with new actuator value.

        Called automatically by textual when `self.value` changes.
        """
        match self.actuator.type_:
            case "numeric":
                self.query_exactly_one(".actuator_numeric_value", Input).value = str(value)
            case "binary":
                checkbox = self.query_exactly_one(".actuator_binary_value", Checkbox)
                with checkbox.prevent(Checkbox.Changed):
                    checkbox.value = bool(value)


class DeviceWidget(VerticalGroup):
    """Card widget showing the sensors of a device."""

    def __init__(self, device: Device) -> None:
        """Create a widget for the specific device."""
        super().__init__(classes="device")
        self.device = device

    def compose(self) -> ComposeResult:
        """Create a list of sensors plus device name."""
        yield Label(self.device.name, classes="device_name")
        yield from [ActuatorWidget(actuator) for actuator in self.device.get_actuators()]
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
