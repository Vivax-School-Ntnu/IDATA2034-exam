# Protocol

This document describes the binary protocol for the <TODO> smart home system.

## Terminology
| Term | Definition                                                                                                                                   |
| :---: |:---------------------------------------------------------------------------------------------------------------------------------------------|
| length-prefixed | A encoding scheme where the length of a payload is sent before the payload itself, allowing readers to pre-allocate buffers.                 |
| big-endian | A byte encoding where the most significant byte comes first, matches most intuitions, <https://en.wikipedia.org/wiki/Endianness>             |
| json | A common plaintext structured format, thats self describing and supported by a wide range of languages, <https://en.wikipedia.org/wiki/JSON> |
| tcp | A low level transport-layer protocol that provides reliability and ordering, <https://en.wikipedia.org/wiki/TCP>                             | 
| UTF-8 | The most common text encoding that handles all of unicode, and widely supported. <https://en.wikipedia.org/wiki/UTF-8>                       |
| Node | A client in the network, either an iot device or a controller.                                                                               |
| Server | The central server/brooker                                                                                                                   |
| Controller | A controller-node that connects to the central server in order to issue commands and view the status of the network                          |
| Device | A Physical iot device, acts as one network client/node, may contain multiple local sensors/acctutors                                         |


## Payloads and connections

### Connection
We use a persistent TCP connection to a central server on port `8043`.

All clients, control-nodes and sensor-nodes, will connect to the central server which will act as a broker as described later on. Each device will then be responsible for multiple sensors/actuators.
```mermaid
flowchart LR
    S[Server]
    Control-Node-1 & Control-Node-2 <-- tcp/8043 --> S
    S <-- tcp/8043 --> Device-1 & Device-2 & Device-3

    Device-1 <-- IPC --> Sensor-1-1 & Sensor-1-2 & Actuator-1-1
    Device-2 <-- IPC --> Sensor-2-1 & Sensor-2-2
    Device-3 <-- IPC --> Actuator-3-1 & Actuatos-3-2
```

> [!NOTE]
> communication between devices and its onboard sensors/actuators are outside the scope of this specification, as long as the device exposes the required addressing capabilities which will be described later on in this document.

### Packets

The core message format is length-prefixed json.
Specifically each packet start with 8 bytes (64 bits) in big-endian encoding a length `n`, the next `n` bytes are the json payload encoded as utf-8.

For example the payload `{"value": 20}` would be sent as (in hexadecimal) `000000000000000d7b2276616c7565223a2032307d`, where:
```
000000000000000d            - 13
7b2276616c7565223a2032307d  - {"value": 20}
```

### Communication model / message flow
For devices we will use a push based model in both directions (device pushes sensor updates to the server, and the server pushes actuator commands to the device),
For the controller to server we will use primarly pull based, with the option for the controller to subscribe to push based updates for certain sensors.

The diagram below provides a high level overview of the nominal flow of the protocol, which will be laid out in more detail below.

```mermaid
sequenceDiagram
    participant Controller
    participant Server
    participant Device

    Device ->> Server : device_connect
    activate Device
    Device ->> Server : sensor reading
    Device ->> Server : sensor reading
    Device ->> Server : sensor reading

    Controller ->> Server : connect_controller
    activate Controller
    Controller ->> Server : "subscribe sensors"
    note over Controller,Server: Gets sent the latest value
    Server ->> Controller : sensor reading
    Controller ->> Server : "update lights"
    Server ->> Device : update_actuator

    Device ->> Server : sensor reading
    Server ->> Controller : sensor reading
    Device ->> Server : sensor reading
    Server ->> Controller : sensor reading
    deactivate Device
    deactivate Controller
```

## Payload structure

All payloads have a root level `type` key, which indicates the kind of command/message it is. 
In addition each message will contain a `request_id`, if the message is a request this will be a new id minted by the client, any responses to that request will have their `request_id` field set to the same value.

> [!WARNING]
> It is the clients responsibility to ensure request ids are unique for that connection, if requests ids are re-used the server behaviour is undefined. 

### Addressing 
Devices get allocated an id upon connection, and enumerate their internal sensor/actuators addressing. The global sensor/actuators addresses are then `{device_id}.{sensor_id}`. for example a device with id `3`, with a sensor at id `2` would be addressed as `3.2`.

The exact allocation and format of ids is up to the server and individual devices, the only restriction is that the ids must not contain a `.`.

### Error handling

In the event of a processing error the server will respond with a `error` payload, containing a `msg` field, and a *optional* `request_id` field (if the server fails to read the json completely it will not include the request id).

```json
{
    "type": "error",
    "request_id": "...",
    "msg": "Expected field ...."
}
```

### Sensor configuration
A sensor is a abstract source of values attached to a specific device, devices and the server use the following structure to define sensors:
```jsonc
{
    // Always "sensor" for sensors
    "type": "sensor"
    // A  user facing name for the sensor, this is allowed to be non-unique
    "name": "Temprature",
    // The kind of sensor in an abstract sense, see table below
    "sensor_type": "numeric"
}
```

| Type | Description |
| --- | --- |
| `numeric` | A sensor providing numeric data, such as temprature, humidity, etc. | 
| `binary` | A binary sensor provides a true/false reading, often representing the on/off state of a device, or for example wether a motion sensor is detecting motion. | 


### Device connection flow

On connection the device will send a `connect_device` payload containing user facing metadata such as names, as well as its sensors/actuators.
```jsonc
{
    "type": "connect_device",
    "request_id": "...",
    "name": "IKEA ...",
    // A mapping from local addresses to sensor definitions (as defined above)
    "capabilities": {
        "temperature": {
            "type": "sensor"
            "name": "Temperature",
            "sensor_type": "numeric"
        },
        "fire": {
            "type": "sensor"
            "name": "Is on fire",
            "sensor_type": "binary"
        },
    } 
}
```

If the server allocates this device for example the id `1`, then the global address of the two sensors are `1.temprature` and `1.fire` respectively. 

```mermaid
sequenceDiagram
    participant Device
    participant Server

    Device ->> Server : Tcp connection
    activate Device
    Device ->> Server : {"type": "connect_device", ...}
    deactivate Device

```

### Sensor updates

Devices push updates to the server on their own schedule, its up to each device if it wants to send updates at a fixed time interval or when it detects changes.
Each update consists of a mapping of local addresses to the sensors new values, unchanged sensors are allowed to be ommited.

Devices should send a sensor update for all their sensors shortly after connecting to ensure the server has up to date state. 

```jsonc
{
    "type": "sensor_update",
    "sensors": {
        "temperature": 22,
        "fire": false,
    }
}
```

Then on future updates unchanged sensors can be left out.

```jsonc
{
    "type": "sensor_update",
    "sensors": {
        "temperature": 21,
    }
}
```

```mermaid
sequenceDiagram
    participant Device
    participant Server

    Device ->> Server : Tcp connection
    activate Device
    Device ->> Server : {"type": "connect_device", ...}
    Device ->> Server : {"type": "sensor_update", ...}
    Device ->> Server : {"type": "sensor_update", ...}
    Device ->> Server : {"type": "sensor_update", ...}
    deactivate Device

```

