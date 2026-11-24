### Documentation note:
These reports were reconstructed retrospectively using GitHub Issues, Pull requests, commit history,
and the team's recollections. They describe actual progress rather than claiming that formal
sprint reviews took place.

# Sprint Reports - IDATA2304 IoT Project
## Project organization
The project was divided into three main components: Device, Server, and Controller.

Each team member was primarily responsible for one component. Since the components
communicate using a shared network protocol, we had to coordinate our implementations to ensure
compatibility between them.

We used GitHub issues to organize and distribute tasks. Development was done in separate branches,
allowing team members to work independently without directly affecting the main codebase.

Once changes were ready, Pull Requests were created for review. These had to be approved by
another team member before being merged into the main branch. This helped us review each other's
code, discuss improvements, and integrate our work. In addition, the PRs were checked by our 
countinious integration pipeline in GitHub actions. For a pr to be accepted it had to pass ruff 
(linting), basedpyright(static type checkign) and pytest(test suite).

### Team responsibilities

| Team member | Main responsibility |
|---|---|
| Luka | Server - Protocol, addressing, id allocation, broadcasting.  |
| Ole | Controller and shared-framing - TUI, User interaction, project setup, protocol framing. |
| Vetle | Device - sensors, actuators, TCP client and runtime |

---

## Sprint 1 - 21 September to 5 October

### Main Focus
Getting started with the project by establishing the initial communication protocol specification and setting up development environment.

### Issues associated with this period
- [#1] - Write protocol spec
- [#3] - Setup Python workspace and CI
- [#4] - Write README
- [#6] - Sensors
- [#7] - Implement Actuators

### Work completed

**Server - Luka**
- Discussed the protocol spec in person with Ole while it was being written.
- Reviewed and approved the device-to-server protocol spec.
- PRs reviewed: [#2]

**Controller - Ole**
- Wrote the first version of the protocol spec, covering how devices register with the server
  and send sensor data.
- Set up the project as a `uv` workspace, with `ruff`, `pytest` and GitHub Actions CI.
- Created the initial issues for the README, sensors and actuators.
- Issues: [#1], [#3]. PRs: [#2], [#5]

**Device - Vetle**
- Reviewed the protocol spec and the project setup.
- Assigned to sensors ([#6]) and actuators ([#7]).
- PRs reviewed: [#2], [#5]

### Retrospective
- **What went well**: We established the initial communication protocol specification, set up the python development environment and CI pipeline, and organized the first tasks using GitHub issues. Discussing the protocol design in person helped us agree on the basics of the protocol quickly.
- **What could be improved**: We could have defined clearer priorities and smaller milestones to help us begin implementation earlier.
---

## Sprint 2 - 6 October to 1 November

### Main Focus
Developing the shared communication protocol infrastructure, starting the sensor implementation and preparing for the server core development. 

### Issues associated with this period
- [#6] - Sensors
- [#11] - Server Core

### Work completed

**Server - Luka**
- Reviewed and approved the shared protocol infrastructure.
- Assigned to the server core ([#11]).
- PRs reviewed: [#8]

**Controller - Ole**
- Implemented the shared protocol infrastructure: `TypedDict` definitions for the JSON packets,
  and functions for writing and reading framed packets, with tests.
- Updated all dependencies, including a `uv` version that fixes CVE-2026-111943.
- Opened the README PR and created the Server Core issue.
- Issues: [#11]. PRs: [#8], [#9], [#12] (opened)

**Device - Vetle**
- Started the sensor implementation: an abstract sensor class with type hints, docstrings and
  unit tests for names, types and generated values.
- Issues: [#6]. PRs: [#10] (opened), reviewed [#9]

### Retrospective
- **What went well**: The initial shared protocol infrastructure was implemented, including JSON packet definitions, message framing, and tests. Work on the sensor implementation also began.
- **What could be improved**: Considering the length of this period, we could have dedicated more time to development and made further progress on the individual components.
---

## Sprint 3 - 2 November to 19 November

### Main Focus
Implementing the server, completing the sensor implementation, and further developing the shared communication infrastructure.

### Issues associated with this period
- [#4] - Write README
- [#6] - Sensors
- [#11] - Server Core
- [#14] - Should device ids be random
- [#15] - Create and document controller part of protocol
- [#16] - Implement basic controllers
- [#17] - Implement Device class to manage sensors

### Work completed

**Server - Luka**
- Implemented the server core: listens on port 8043, accepts clients in a loop, gives each
  client its own thread and a unique client id, and runs a read loop per connection.
- Added message dispatch: incoming packets are routed to handlers by type, malformed or
  unknown packets get an error reply, and a failing handler returns an error instead of
  dropping the connection.
- Added disconnect handling, safe sending to other clients, a stoppable accept loop, and
  tests for the server core.
- Started work on stable device ids based on a device UUID (merged in Sprint 4).
- Issues: [#11]. PRs: [#13], reviewed [#12] and [#18]

**Controller - Ole**
- Made the server connection handling generic, following up on the review comments from [#13].
  This also set up logging and replaced `TypedDict` with `pydantic`.
- Added `basedpyright` type checking to the CI workflow.
- Merged the README.
- Created issues for stable device ids and for the controller protocol and controllers.
- Issues: [#4], [#14], [#15], [#16]. PRs: [#12], [#18], [#19], reviewed [#10] and [#13]

**Device - Vetle**
- Finished and merged the sensor implementation.
- Created the issue for the Device class, which manages multiple sensors.
- Opened the Device class PR.
- Issues: [#6], [#17]. PRs: [#10], [#20] (opened)

### Retrospective
- **What went well**: The initial server core was implemented, the sensor implementation was completed, and the shared connection handling was improved.
- **What could be improved**: We could have integrated the different components earlier, giving us more time to test the complete system before the deadline.
---

## Sprint 4 - 20 November to 23 November

### Main Focus
Finish the project. Implement all remaining device functionality, expanding the controller and server communication, and integrating the different components of the system.

### Issues associated with this period
- [#7] - Implement Actuators
- [#14] - Should device ids be random
- [#15] - Create and document controller part of protocol
- [#17] - Implement Device class to manage sensors
- [#22] - Implement TCP client for Device
- [#24] - Implement TUI for read-only controller
- [#25] - Persist device id to hardware id mappings
- [#30] - Implement Device Runtime
- [#33] - Implement TUI part of new controller spec
- [#35] - Connect controller to server

### Work completed

**Server - Luka**
- Made `connect_device` require a UUID, which the server maps to a device id so that a device
  keeps its id when it reconnects. Updated the protocol documentation accordingly.
- Persisted the UUID-to-device-id mappings to a JSON file so they survive server restarts.
- Fixed flaky server tests that checked the client count before the server thread had
  registered the client.
- Took on the controller part of the protocol: designed and documented it, including the
  device-side packets needed for actuators and an acknowledgement for device registration.
- Implemented server-side handling of the controller protocol: device lists, subscriptions,
  actuator commands, role checks and disconnect handling, with a test suite covering the full flow.
- Issues: [#14], [#15], [#25]. PRs: [#21], [#23], [#26], [#28], [#32], reviewed [#29] and [#34]

**Controller - Ole**
- Implemented a read-only controller TUI that shows live updates from a mock backend.
- Implemented the `Backend` and `MockBackend` interfaces for the new controller protocol, and
  updated the TUI so it can display and update actuators.
- Created the issue for connecting the controller to the real server.
- Issues: [#24], [#33], [#35]. PRs: [#27], [#34], reviewed [#21], [#26], [#28], [#29], [#32], [#36]

**Device - Vetle**
- Merged the Device class, which supports multiple sensors, reports its capabilities and
  validates sensor ids.
- Implemented the device TCP client on top of the shared `Connection` class. It sends
  `connect_device` and `sensor_update` packets, handles connection errors and handles the
  `DeviceConnected` acknowledgement.
- Added actuator support: an abstract actuator class, binary and numeric actuators, handling of
  actuator updates over TCP, and unit and TCP integration tests.
- Implemented the device runtime, which sends sensor updates automatically and stores a persistent
  UUID.
- Created the sprint report template.
- Issues: [#17], [#22], [#30]. PRs: [#20], [#29], [#36], [#31], [#37]

**Final status:** All remaining pull requests were subsequently merged, and the implementation was completed before submission.

### Retrospective
- **What went well**: Significant progress was made across all components. The server gained support for controller communication and persistent device IDs. The controller interface was developed to display sensor readings and control actuators. On the device side, the TCP client, actuator support, and runtime were implemented.
- **What could be improved**: A more evenly distributed workload throughout the semester would have given us more time for integration testing, debugging, and final documentation.
---

## Overall Reflection
Throughout the project, we worked on three main components: Device, Server, and Controller, with each team member having primary responsibility for one component. We used GitHub issues, branches, pull requests, and code reviews to organize our work and collaborate.

One thing we could have improved was distributing the workload more evenly throughout the semester. A significant amount of development happened towards the end, which left less time for integration testing, debugging, and documentation.

We could also have benefited from clearer milestones and more consistent progress tracking over the course of the project

Overall we successfully implemented the system and gained practical experience with network programming, TCP communication, and integrating independently developed components.


[#1]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/1
[#2]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/2
[#3]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/3
[#4]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/4
[#5]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/5
[#6]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/6
[#7]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/7
[#8]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/8
[#9]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/9
[#10]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/10
[#11]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/11
[#12]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/12
[#13]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/13
[#14]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/14
[#15]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/15
[#16]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/16
[#17]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/17
[#18]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/18
[#19]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/19
[#20]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/20
[#21]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/21
[#22]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/22
[#23]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/23
[#24]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/24
[#25]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/25
[#26]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/26
[#27]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/27
[#28]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/28
[#29]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/29
[#30]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/30
[#31]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/31
[#32]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/32
[#33]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/33
[#34]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/34
[#35]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/issues/35
[#36]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/36
[#37]: https://github.com/Vivax-School-Ntnu/IDATA2034-exam/pull/37
