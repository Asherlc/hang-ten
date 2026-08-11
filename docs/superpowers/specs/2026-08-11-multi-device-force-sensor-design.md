# Multi-Device Bluetooth Force Sensor Design

## Goal

Allow Hang Ten to connect to and stream force measurements from Tindeq
Progressor, PitchSix Force Board, Weiheng WH-C06, Entralpi, Climbro, and
mySmartBoard hardware, plus user-selected generic Progressor-compatible and
WH-C06-compatible devices.

## Approved Product Behavior

- Rename the existing user-facing "Training sensor" surface to "Force sensor".
- Present a profile picker: Automatic, Tindeq/Progressor, PitchSix Force
  Board, WH-C06, Entralpi, Climbro, mySmartBoard, Generic
  Progressor-compatible, and Generic WH-C06-compatible.
- In Automatic mode, scan for recognized advertisements and use the matching
  adapter. A generic profile scans broadly and only completes connection once
  its required GATT contract has been verified.
- Normalize every device sample to kilograms-force and feed it through the
  existing meter, bodyweight capture, workout recording, unit formatting, and
  interruption behavior.
- Surface only the controls supported by the connected adapter. Do not expose a
  tare, battery, start, or stop action that the hardware cannot perform.
- Show the selected device profile in connection, protocol, and timeout errors
  so a user can take the appropriate recovery action.

## Architecture

The current `MotherboardTransport` and `MotherboardBluetoothService` couple
transport lifecycle to the Griptonite Motherboard UART calibration protocol.
Replace that boundary with a profile-aware force-sensor transport and a
device-adapter protocol. Adapters own advertisement matching, service and
characteristic discovery, packet decoding, and device commands. They report a
common stream of normalized force measurements and capability metadata to a
single service, which retains the existing session, tare, bodyweight, and
recording responsibilities.

CoreBluetooth remains the only production BLE implementation. There is no web
or JavaScript runtime dependency. The existing Motherboard adapter is retained
so this is additive rather than a protocol replacement.

### Adapter Contract

Each adapter must define:

- A stable `ForceSensorProfile` identifier and visible label.
- Advertisement matching rules, with a separate opt-in generic matcher where
  device names alone are insufficient for reliable automatic selection.
- Required GATT services and characteristics; the connection fails before
  subscribing if the selected profile's contract is not present.
- Commands and capability flags for streaming, tare, battery, and explicit
  stop.
- A packet decoder that produces finite, non-negative kilogram-force samples
  with receipt timestamps. Adapters with no reliable side-channel data must
  leave battery and channel distribution unavailable rather than fabricate
  values.

The service assigns monotonically increasing sample numbers when an adapter
does not provide them. A single-load device maps its aggregate load to one
sensor-load entry; existing left/right distribution remains unavailable rather
than inferred.

### Connection and Error Flow

1. The user selects Automatic or an explicit profile and starts a scan.
2. Automatic mode chooses only a recognized profile. Explicit generic modes
   permit broader matching but require the adapter's service validation after
   connection.
3. The adapter discovers and validates its GATT characteristics, enables
   notifications, and starts streaming if that protocol requires an explicit
   command.
4. The normalized stream enters the existing workout meter and recorder.
5. Disconnections, malformed data, absent characteristics, or missed stream
   acknowledgements fail the session with the active profile's name and existing
   reconnect semantics.

## Data and Compatibility

`MotherboardMeasurement` evolves into a source-neutral persisted force-sensor
measurement without losing its existing Codable keys. Session history gains
the selected profile identifier while preserving legacy
`motherboardIdentifier` records on decode. Existing Motherboard sessions,
settings, simulator support, workout behavior, and previously saved history
must remain readable.

## Testing

- Unit-test profile selection and generic-mode restrictions using synthetic
  advertisements and discovered services.
- Unit-test every protocol decoder with complete, fragmented, malformed, and
  non-finite packet cases.
- Test capabilities so unavailable controls cannot be issued.
- Extend the simulated transport for each profile and run service-state tests
  for successful connection, missing service, stream timeout, disconnect, and
  recording interruption.
- Run the focused Bluetooth, protocol, recorder, app-store, and history test
  suites plus the complete iOS test target before release.

## Protocol Sources and Field Audit

| Profile | Source | Fields or behavior justified by source |
| --- | --- | --- |
| Tindeq Progressor and generic Progressor-compatible | [Tindeq Progressor API](https://tindeq.com/progressor_api/) | Custom service; control and data points; notification subscription; TLV payloads; little-endian values; start/stop/tare and battery commands only where documented. |
| PitchSix Force Board | [Grip Connect device support and credits](https://jsr.io/@hangtime/grip-connect) and the linked [PitchSix public API](https://pitchsix.com/) | Adapter existence, connection capability boundary, and the upstream public-protocol reference. Exact UUIDs and packet fields must be copied from the public API into the implementation audit before code is written. |
| Weiheng WH-C06 and generic WH-C06-compatible | [Grip Connect device support](https://jsr.io/@hangtime/grip-connect) and upstream [WH-C06 adapter listing](https://app.unpkg.com/@hangtime/grip-connect@0.10.9/files/src/models/device) | Device-family adapter and generic fallback. Exact advertisement and packet formats must be recorded from the upstream source before implementation. |
| Entralpi | [Grip Connect device support](https://jsr.io/@hangtime/grip-connect) and upstream [Entralpi adapter listing](https://app.unpkg.com/@hangtime/grip-connect@0.10.9/files/src/models/device) | Device-family adapter. Exact GATT and packet mappings must be recorded before implementation. |
| Climbro | [Grip Connect device support and acknowledgements](https://jsr.io/@hangtime/grip-connect) and upstream [Climbro adapter listing](https://app.unpkg.com/@hangtime/grip-connect@0.10.9/files/src/models/device) | Device-family adapter and externally verified protocol-testing provenance. Exact GATT and packet mappings must be recorded before implementation. |
| mySmartBoard | [Grip Connect device support](https://jsr.io/@hangtime/grip-connect) and upstream [mySmartBoard adapter listing](https://app.unpkg.com/@hangtime/grip-connect@0.10.9/files/src/models/device) | Device-family adapter and capability boundary. Exact GATT and packet mappings must be recorded before implementation. |

The non-Tindeq protocols are not presented as manufacturer-sourced facts.
Their implementations must carry a field-level audit under
`docs/source-audits/` that records the exact upstream file URL, revision,
byte layout, unit conversion, service UUID, characteristic UUID, and command
mapping used for each adapter. Unsupported fields remain omitted.

## Out of Scope

- LED-system-board control, saved-device browsing, cloud synchronization,
  firmware updates, and importing historical device data.
- Any device family not named in this specification.
- Manufacturer compatibility claims beyond the protocol evidence captured in
  the implementation audit.
