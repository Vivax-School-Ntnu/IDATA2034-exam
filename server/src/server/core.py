"""Accepts clients and keeps track of them."""

import logging
import socket
import threading
from pathlib import Path

from pydantic import TypeAdapter
from shared.base_packet import ActuatorConfiguration, DisconnectPacket, ErrorPacket
from shared.connection import Connection
from shared.controller_protocol import (
    ConnectionConfirmation,
    ControllerConnection,
    DeviceAdded,
    DeviceInfo,
    DeviceRemoved,
    SensorReading,
    SetActuator,
    Subscribe,
)
from shared.device_protocol import DeviceConnected, DeviceConnection, SensorUpdate, UpdateActuator

from server.state import ControllerState, DeviceState
from shared import PORT, ToServerPacket

logger = logging.getLogger(__name__)

type ConnectionId = int
"""Identifies every instance of a connection, new every time, gone on a disconnect."""
type DeviceId = int
"""Handed out by the server, tied to the devices specific HardwareId. Short, used for addressing."""
type HardwareId = str
"""Identity a device generates once and keeps forever. Works like a MAC address."""

_ID_MAP_ADAPTER = TypeAdapter(dict[HardwareId, DeviceId])


class Server:
    """Central server that devices and controllers connect to."""

    def __init__(
        self, port: int = PORT, accept_timeout: float = 1.0, id_file: Path | None = None
    ) -> None:
        """Create the server.

        `accept_timeout` is how often the accept loop wakes up to check whether it should stop.

        `id_file` is where hardware_ids is persisted. None disables persistence.
        """
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._id_file = id_file
        self._hardware_ids: dict[HardwareId, DeviceId] = {}
        if self._id_file is not None and self._id_file.exists():
            self._hardware_ids = _ID_MAP_ADAPTER.validate_json(self._id_file.read_bytes())

        self._clients: dict[ConnectionId, Connection] = {}
        self._device_ids: dict[ConnectionId, DeviceId] = {}
        self._clients_lock = threading.Lock()
        self._next_connection_id: ConnectionId = 1
        self._next_device_id: DeviceId = max(self._hardware_ids.values(), default=0) + 1
        self.accept_timeout = accept_timeout
        self.running = False
        self._devices: dict[DeviceId, DeviceState] = {}
        self._controllers: dict[ConnectionId, ControllerState] = {}

    def _bind(self, host: str) -> None:
        """Bind and listen on the given host.

        If the server was created with port 0, `self.port` is updated to the port the OS picked.
        """
        self._sock.bind((host, self.port))
        self._sock.listen()
        self._sock.settimeout(self.accept_timeout)
        self.port = self._sock.getsockname()[1]
        logger.info(f"Server listening on {host}:{self.port}")

    def _serve(self) -> None:
        """Accept clients until `close` is called.

        Accept uses a short timeout so the loop can notice `close` and Ctrl+C on Windows.
        """
        self.running = True
        while self.running:
            self._accept_client()

    def start(self, host: str) -> None:
        """Bind to the given host and accept clients until stopped."""
        self._bind(host)
        self._serve()

    def _add_client(self, conn: socket.socket, address: tuple[str, int]) -> Connection:
        """Register a new client and return its connection."""
        with self._clients_lock:
            connection_id = self._next_connection_id
            self._next_connection_id += 1
            logger.info(f"Got client with id {connection_id} from {address}")

            connection = Connection(
                conn, TypeAdapter(ToServerPacket), lambda: self._remove_client(connection_id)
            )
            connection.register(
                DeviceConnection, lambda packet: self._handle_device_connection(connection_id, packet)
            )
            connection.register(
                ControllerConnection, lambda packet: self._handle_controller_connection(connection_id, packet)
            )
            connection.register(ErrorPacket, lambda packet: self._handle_error(connection_id, packet)
                                )
            connection.register(SensorUpdate, lambda packet:self._handle_sensor_update(connection_id, packet)
            )
            connection.register(Subscribe, lambda packet: self._handle_subscribe(connection_id, packet)
                                )
            connection.register(SetActuator, lambda packet: self._handle_set_actuator(connection_id, packet)
                                )
            self._clients[connection_id] = connection
        return connection

    def _handle_disconnect(self, connection_id: ConnectionId, _packet: DisconnectPacket) -> None:
        """Handle the disconnect packet."""
        with self._clients_lock:
            connection = self._clients[connection_id]
        connection.close()

    def _remove_client(self, connection_id: ConnectionId) -> None:
        """Remove a client from the registry."""
        removed: DeviceRemoved | None = None
        controller_connections : list[Connection] = []
        with self._clients_lock:
            device_id = self._device_ids.pop(connection_id, None)
            if device_id is not None:
                state = self._devices.get(device_id)
                if state is not None and state.connection is self._clients[connection_id]:
                    removed = DeviceRemoved(request_id=None, device_id=device_id)
                    controller_connections = [controllers.connection for controllers in self._controllers.values()]
                    del self._devices[device_id]
            self._controllers.pop(connection_id, None)
            del self._clients[connection_id]
        logger.info(f"Client {connection_id} got removed")
        if removed is not None:
            for connection in controller_connections:
                connection.send(removed)

    def _accept_client(self) -> None:
        """Wait up to `accept_timeout` for a client, then register it and serve it in a thread."""
        try:
            conn, address = self._sock.accept()
        except TimeoutError:
            return
        except OSError:
            if self.running:
                raise
            return
        conn.settimeout(None)
        connection = self._add_client(conn, address)
        connection.start()

    def _handle_error(self, connection_id: ConnectionId, packet: ErrorPacket) -> None:
        logger.error(f"Error from {connection_id}, request {packet.request_id}: {packet.msg}")

    def _handle_device_connection(self, connection_id: ConnectionId, packet: DeviceConnection) -> None:
        """Handle the device connection packet."""
        with self._clients_lock:
            connection = self._clients[connection_id]
            if packet.uuid in self._hardware_ids:
                self._device_ids[connection_id] = self._hardware_ids[packet.uuid]
                logger.info(
                    f"Device reconnected. Client id: {connection_id}, Device id: {self._device_ids[connection_id]}"
                )
            else:
                self._hardware_ids[packet.uuid] = self._next_device_id
                self._device_ids[connection_id] = self._next_device_id
                logger.info(
                    f"New device. Client id: {connection_id}. Device id: {self._next_device_id}"
                )
                self._next_device_id += 1
                self._save_hardware_ids()
            device_id = self._device_ids[connection_id]
            device_state = self._devices[device_id] = DeviceState(connection, packet.name, packet.capabilities)
            device_info = DeviceInfo(device_id=device_id, name=device_state.name, capabilities=device_state.capabilities, values=device_state.values)
            controller_connections = [c.connection for c in self._controllers.values()]
        connection.send(DeviceConnected(request_id=packet.request_id, device_id=device_id))
        for controller_connection in controller_connections:
            controller_connection.send(DeviceAdded(request_id=None, device=device_info))

    def _handle_sensor_update(self, connection_id: ConnectionId, packet: SensorUpdate) -> None:
        """Store a device's new values and push them to subscribed controllers."""
        to_send: list[tuple[Connection, SensorReading]] = []
        with self._clients_lock:
            device_id = self._device_ids[connection_id]
            self._devices[device_id].values.update(packet.sensors)
            for state in self._controllers.values():
                for local_address, value in packet.sensors.items():
                    address = f"{device_id}.{local_address}"
                    if address in state.subscriptions:
                        to_send.append(
                            (state.connection, SensorReading(request_id=None, address=address, value=value))
                        )
        for connection, reading in to_send:
            connection.send(reading)

    def _handle_subscribe(self, connection_id: ConnectionId, packet: Subscribe) -> None:
        """Subscribe a controller to addresses and send their current values."""
        to_send: list[SensorReading] = []
        with self._clients_lock:
            connection = self._clients[connection_id]
            unknown: list[str] = []
            for address in packet.addresses:
                device_part, _, local_id = address.partition(".")
                device = self._devices.get(int(device_part)) if device_part.isdigit() else None
                if device is None or local_id not in device.capabilities:
                    unknown.append(address)
            if not unknown:
                self._controllers[connection_id].subscriptions.update(packet.addresses)
                for address in packet.addresses:
                    device_part, _, local_id = address.partition(".")
                    value = self._devices[int(device_part)].values.get(local_id)
                    if value is not None:
                        to_send.append(SensorReading(request_id=None, address=address, value=value))
        if unknown:
            connection.send(
                ErrorPacket(request_id=packet.request_id, msg=f"Unknown addresses: {', '.join(unknown)}")
            )
            return
        for reading in to_send:
            connection.send(reading)

    def _handle_set_actuator(self, connection_id: ConnectionId, packet: SetActuator) -> None:
        """Set the value of an actuator."""
        device_id, _, local_id = packet.address.partition(".")
        with self._clients_lock:
            device = self._devices[int(device_id)]
            if not isinstance(device.capabilities[local_id], ActuatorConfiguration):
                raise TypeError(f"{packet.address} is not an actuator")
            self._controllers[connection_id].subscriptions.add(packet.address)
            device.connection.send(UpdateActuator(request_id=None, actuator=local_id, value=packet.value))
    

    def _handle_controller_connection(self, connection_id: ConnectionId, packet: ControllerConnection) -> None:
        """Handle a new controller getting connected to teh server."""
        with self._clients_lock:
            connection = self._clients[connection_id]
            self._controllers[connection_id] = ControllerState(connection, role=packet.role)
            devices: list[DeviceInfo] = []
            for device_id, state in self._devices.items():
                devices.append(DeviceInfo(device_id=device_id, name=state.name, capabilities=state.capabilities, values=state.values))
        connection.send(ConnectionConfirmation(request_id=packet.request_id))
        for device in devices:
            connection.send(DeviceAdded(request_id=None, device=device))


    def _save_hardware_ids(self) -> None:
        """Save hardware IDs to a persistent file. Does nothing if persistence is not enabled.
        
        Caller must call under _clients_lock.
        """
        if self._id_file is None:
            return
        data = _ID_MAP_ADAPTER.dump_json(self._hardware_ids)
        tmp = self._id_file.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(self._id_file)
    
    def client_count(self) -> int:
        """Return the amount of currently connected clients."""
        return len(self._clients)

    def device_count(self) -> int:
        """Return the amount of currently connected devices."""
        return len(self._devices)

    def controller_count(self) -> int:
        """Return the amount of currently connected devices."""
        return len(self._controllers)
    
    def device_id_for(self, uuid: HardwareId) -> DeviceId | None:
        """Return the device id assigned to `uuid`, or `None` if that device has never connected."""
        with self._clients_lock:
            return self._hardware_ids.get(uuid)

    def close(self) -> None:
        """Stop accepting clients and close the listening socket."""
        self.running = False
        self._sock.close()
        logger.info("Server closed")

