"""The TUI/UI implementation for the controller."""

import threading
import logging
from typing import Callable
import functools

from controller.backend import Backend, Device, Sensor
from shared.base_packet import SensorValue
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Checkbox, Footer, Header, Label, Static

logger = logging.getLogger(__name__)


class SensorWidget(HorizontalGroup):
    value: reactive[SensorValue] = reactive(False)

    def __init__(self, sensor: Sensor) -> None:
        super().__init__(classes="sensor")
        self.sensor = sensor

    def on_mount(self) -> None:
        self.value = self.sensor.get_value()

    def compose(self) -> ComposeResult:
        match self.sensor.type_:
            case "numeric":
                yield Label(classes="sensor_numeric_value")
                yield Label(self.sensor.name, classes="sensor_name")
            case "binary":
                yield Checkbox(self.sensor.name, classes="sensor_binary_value", disabled=True)

    def watch_value(self, value: SensorValue) -> None:
        match self.sensor.type_:
            case "numeric":
                self.query_exactly_one(".sensor_numeric_value", Label).update(str(value))
            case "binary":
                self.query_exactly_one(".sensor_binary_value", Checkbox).value = bool(value)


class DeviceWidget(VerticalGroup):
    def __init__(self, device: Device) -> None:
        super().__init__(classes="device")
        self.device = device

    def compose(self) -> ComposeResult:
        yield Label(self.device.name, classes="device_name")
        yield from [SensorWidget(sensor) for sensor in self.device.get_sensors()]


class SmartHomeApp(App[None]):
    """The tui frontend for the controller node."""

    def __init__(self, backend: Backend) -> None:
        super().__init__()
        self.backend = backend

    CSS_PATH = "styles.tcss"
    BINDINGS = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="devices")
        yield Footer()

    def backend_on_device_added(self, device: Device) -> None:
        logger.debug(f"New device from backend: {device.name}.")
        self.query_exactly_one("#devices").mount(DeviceWidget(device))

    def on_mount(self) -> None:
        logger.debug("App on mount called.")

        self.backend.register_on_new_device(backend_handler(self, self.backend_on_device_added))
        self.backend.register_on_error(
            backend_handler(self, lambda msg: self.notify(msg, severity="error"))
        )
        threading.Thread(target=self.backend.start, daemon=True).start()


def backend_handler[**P](app: SmartHomeApp, function: Callable[P, None]) -> Callable[P, None]:
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
