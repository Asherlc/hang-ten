# Griptonite Motherboard Bluetooth integration

**Date:** 2026-08-02

## Goal

Add native iOS support for the Griptonite Motherboard force-sensing backboard.
Hang Ten should be able to connect to the device, receive calibrated force
measurements, show them while a routine runs, and save the actual time spent
above a load threshold for later review.

The routine remains timer-led. Motherboard measurements describe what the
athlete actually loaded inside each scheduled active interval; they do not
pause, advance, or otherwise control the routine clock.

## Scope and non-goals

In scope:

- User-initiated discovery, connection, streaming, disconnection, and error
  state for a Griptonite Motherboard.
- Live current force, peak force, battery, and loaded/unloaded status.
- Per-step load intervals, actual loaded duration, peak force, and a session
  summary persisted in Hang Ten.
- Settings for force display unit and load-detection threshold.
- A DEBUG-only simulated stream for simulator review.
- Unit tests for the protocol, calibration, load detection, and persistence.

Not in scope:

- Classic Bluetooth pairing or a system-level pairing workflow. The
  Motherboard uses BLE GATT and normally does not require bonding.
- Force-controlled workout progression or automatic timer changes.
- Background streaming after the workout is suspended.
- Exporting raw sensor data outside the saved session. Eligible 30 Hz granular measurements are retained in the saved session, including raw ADC values.
- Supporting other force meters or arbitrary BLE UART devices.
- Replacing the existing Apple Health workout record with force samples.

## Device protocol

The integration follows the publicly documented, reverse-engineered
Motherboard protocol:

- Scan for the Nordic UART service
  `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`, then verify the device name is
  `Motherboard` when the name is available.
- Use RX
  `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` for commands and TX
  `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` for notifications.
- Enable TX notifications before sending commands.
- Send `C` to request the device calibration rows, then send `S30` to start
  a 30 Hz stream. Stop the stream and disconnect when the sensor is no longer
  needed.
- Notifications contain CRLF-delimited ASCII. BLE boundaries do not equal
  message boundaries, so the parser retains an incomplete line and processes
  every complete line in order.
- A stream report is a 32-character hexadecimal representation of 16 bytes:
  two little-endian bytes for the sample number, two for battery charge, and
  four little-endian signed 24-bit ADC readings. The fourth sensor is reserved
  by the protocol but remains available in the decoded model.
- Calibration rows use `sensor,calibrationPoint,mass,adc`. Each sensor is
  converted by linear interpolation between calibration points; values outside
  the table use the nearest endpoint. A software tare baseline is subtracted
  from calibrated mass before it is exposed as load.

The protocol parser must never crash on malformed input. It should retain
partial input up to a 4,096-byte receive-buffer cap. If the cap is exceeded,
the parser clears its buffered bytes and emits a typed protocol error so the
next notification starts cleanly. Invalid non-error lines are ignored, while
device `Error` lines and overflow errors are surfaced as typed protocol errors.

## Architecture

### `MotherboardProtocol`

A pure Swift value-type layer with no CoreBluetooth dependency. It owns:

- UUID constants and command construction;
- line buffering and CRLF framing;
- 32-character hex and signed 24-bit decoding;
- calibration row parsing and interpolation;
- conversion of decoded packets into `MotherboardMeasurement` values.

`MotherboardMeasurement` contains the received timestamp, sample number,
battery value, four calibrated sensor loads, and aggregate load in canonical
kgf. Unit conversion is a model/UI concern driven by settings, not a parser
concern. The parser is independently testable with captured notification
fixtures.

### `MotherboardBluetoothService`

An observable, main-actor-owned CoreBluetooth service injected into `AppStore`.
It owns the central manager, selected peripheral, discovered RX/TX
characteristics, notification subscription, command writes, and published
connection/measurement state. Its states are:

`bluetoothUnavailable`, `unauthorized`, `idle`, `scanning`, `connecting`,
`calibrating`, `streaming`, `disconnected`, and `failed`.

The service starts only after a user taps Connect. It does not request
Bluetooth permission or connect at app launch. If a peripheral disconnects,
the service publishes the failure and stops measurement recording; it does not
alter the workout clock or fabricate samples. A later user action can connect
again.

### `MotherboardWorkoutRecorder`

A pure stateful recorder that receives measurements with the current workout
time context. It accepts samples only when the current step is an active,
non-countdown, non-rest interval. It maintains one or more `LoadInterval`
values per step so routines that describe multiple hangs inside a minute can
be represented accurately.

The recorder uses a canonical 2.5 kgf threshold by default. A short debounce
and hysteresis window prevents BLE/sample noise from creating false intervals.
The threshold crossing timestamps come from measurement arrival times; brief
gaps below the release threshold are merged. Pauses, rest boundaries,
disconnects, and session completion flush any open interval.

Each step result contains:

- step ID and planned active duration;
- zero or more loaded intervals;
- total actual loaded duration;
- peak calibrated load;
- sample count and a measured/unmeasured status.

The recorder never changes the elapsed value calculated by `WorkoutView`.

### `WorkoutSessionStore`

A Codable local store injected into `AppStore`. A saved `WorkoutSessionRecord`
contains the plan identity, date, routine start/end, Motherboard identifier
when available, battery snapshot, and per-step recorder results. It persists
derived results plus each eligible granular `MotherboardMeasurement` received
after countdown completion and before the plan duration ends, including rest
intervals and raw ADC values. Samples are not downsampled before reaching the
collector; a session is capped at
`MotherboardWorkoutMeasurementCollector.maximumMeasurementCount`
(20,000). Additional measurements are dropped and the `WorkoutSessionRecord`
records that truncation occurred. The store retains only the 20 newest session
records and removes older session files.
It supports loading history and appending a completed summary without making
Apple Health responsible for force data.

## User experience

### Training sensor card

Add a Training sensor card to the Progress experience. It shows Bluetooth
permission state, connection status, Connect/Disconnect, current force,
battery, and the last error. Permission-denied and Bluetooth-off states
explain the cause and offer the existing app-settings route where iOS permits
one. A Motherboard already connected to another app is reported as a
connection failure with a release-the-device instruction.

### Workout meter

Both portrait and landscape workout layouts receive the same compact sensor
content: connection status, current load, peak load for the active interval,
and actual loaded time versus the scheduled active duration. The meter is
hidden or marked “Not measured” when the sensor is unavailable. It must not
make the existing board, cue, countdown, pause, audio, or orientation behavior
depend on Bluetooth availability.

### Session summary and progress

The completion path presents a session summary before dismissing the workout.
For each step, show planned duration, total actual loaded time, each loaded
interval when there is more than one, peak force, and an unmeasured label when
no usable sample was received. Saving the summary appends it to local history,
increments the existing session count, and continues to use the current Apple
Health completion path.

### Settings

Add a Settings destination reachable from the Progress experience. The
Motherboard section stores:

- display unit, defaulting to kgf, with lbf and N options;
- load threshold, stored canonically as kgf and defaulting to 2.5 kgf;
- a software tare action that captures a short unloaded baseline.

Changing display units must not rewrite saved canonical measurements. The
threshold is applied in canonical kgf and only affects future load detection.

## Failure handling and safety

- Bluetooth authorization, powered-off, scanning timeout, connection failure,
  missing characteristics, calibration failure, malformed data, and
  disconnects are separate user-visible states.
- The timer and audio behavior remain functional when no sensor is connected.
- A partial measurement remains in the summary with its actual recorded
  interval and a disconnected/unmeasured status for the remainder.
- No automatic workout progression, threshold coaching, or medical conclusion
  is derived from force data.
- Because the protocol is not an official manufacturer SDK, the README and
  implementation documentation should link the protocol reference and state
  that physical-device validation is required.

## Verification

Add an XCTest target and write tests before production implementation for:

1. fragmented lines, multiple lines per notification, malformed input, and
   protocol error lines;
2. little-endian 16-bit fields, signed 24-bit ADC values, calibration parsing,
   interpolation, endpoint behavior, and aggregate load;
3. threshold hysteresis, debounce, short-gap merging, step/rest boundaries,
   pauses, disconnects, and completion flushes;
4. Codable session round trips, unit conversion, and summary persistence.

Add a DEBUG-only deterministic simulated measurement source and review route so
the live meter, disconnect states, workout summary, and settings can be
validated on an isolated iOS Simulator. Run the simulator build and visual
review flow after implementation, then validate real BLE connection, stream
rate, calibration, tare, and timing on a physical iPhone with a Motherboard.

## References

- [Griptonite Motherboard protocol notes](https://jtvjan.nl/documents/grippynotes.md)
- [Grip Connect Motherboard device reference](https://stevie-ray.github.io/hangtime-grip-connect/devices/motherboard.html)
- [Griptonite Motherboard overview](https://climbingbusinessjournal.com/griptonites-motherboard-a-training-tool-thats-now-advancing-research-into-shoe-size-and-fit-too/)
