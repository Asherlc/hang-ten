# Entralpi Force-Sensor Integration Design

**Date:** 2026-08-11

## Goal

Integrate Entralpi as a live CoreBluetooth force sensor through a profile-driven
connection stack. Preserve Motherboard behaviour while removing its transport
and service layer's hard-coded assumption that every sensor uses Motherboard's
UART protocol.

## Scope

- Refactor the CoreBluetooth transport and connection service around a
  profile-specific protocol contract.
- Keep Motherboard's calibration, command, parser, reconnect, software-tare,
  workout, and UI behaviour intact.
- Add Entralpi discovery, GATT subscription, standing calibration, and pulling
  force conversion.
- Add unit and lifecycle tests before implementation code.

This work does not add undocumented Entralpi commands, subscribe to its UART
`FFF4` characteristic, or change unrelated sensor profiles.

## Protocol evidence

The immutable upstream adapter blob is
`c6cdd037207bee0299bf94000e1fdb40ac3b7ca9`, at
`packages/core/src/models/device/entralpi.model.ts` in commit
`e486d230922d749448106c56396997d50976062c`.

Entralpi's public versioned web-app bundle and source map provide primary
protocol evidence. Their exposed `utils/WebBluetooth.ts` selects a device with
the `ENTRALPI` name prefix, discovers Weight Scale service `0x181D`, and
subscribes only to characteristic `0000FFF1-0000-1000-8000-00805F9B34FB`.
It rejects payloads shorter than two bytes and reads `getUint16(0) / 100`.
Because `getUint16` omits the little-endian parameter, it is big-endian.

The vendor's exposed `utils/GlobalBluetoothWrapper.ts` collects ten standing
samples, accepts a mean from 1 through 200 kg with standard deviation at most
0.5 kg, and stores the rounded-to-0.1 kg bodyweight baseline. Its
`utils/ForceCalculation.ts` defines lifted force as:

```
max(0, bodyweightBaselineKG + addedLoadKG - rawScaleLoadKG)
```

The vendor hardware page states BLE 5.0 and a 100 Hz sensor sampling rate.
The sampling-rate claim does not establish notification delivery frequency.

## Architecture

### Protocol profiles

Define an internal force-sensor protocol contract that provides the
advertisement matcher, required services, notification characteristics, optional
write characteristics and commands, and a raw-frame decoder.

The Motherboard profile retains its current UART UUIDs, `C` calibration command,
`S30` stream command, line parser, and measurements. The Entralpi profile has:

- name-prefix matcher: `ENTRALPI`;
- Weight Scale service `0000181D-0000-1000-8000-00805F9B34FB`;
- notification characteristic
  `0000FFF1-0000-1000-8000-00805F9B34FB`;
- no write characteristic or hardware commands;
- a raw decoder that accepts frames of at least two bytes and returns the first
  two bytes as a big-endian unsigned centigram kilogram reading.

### Bluetooth transport

Refactor the existing CoreBluetooth transport to receive a profile contract
instead of referring directly to `MotherboardProtocol`. Scanning, device
retention, GATT discovery, characteristic lookup, notification enablement,
writes, and disconnect handling use that contract. The transport reports the
same lifecycle events used by the connection service.

### Connection service

Make the current connection service profile-aware. Motherboard follows its
existing calibration-to-streaming sequence. Entralpi begins notifications once
its characteristic is ready, then enters a calibration state rather than
publishing force samples.

Entralpi calibration records ten stable readings while the user stands on the
plate. It rejects invalid readings, a mean outside 1...200 kg, or standard
deviation greater than 0.5 kg. On success it stores a bodyweight baseline and
enters streaming. A raw Entralpi reading converts to non-negative pulling force
using the vendor formula. No Entralpi hardware tare, start, or stop action is
advertised.

### Consumers and UI

Maintain the normalized measurement supplied to existing workout-recorder and
display consumers. Entralpi's profile-specific preparation directs the user to
stand still for baseline capture; it does not reuse the Motherboard empty-board
tare or hanging bodyweight instructions. Motherboard's current preparation
remains unchanged.

## Failure handling

- Ignore Entralpi frames shorter than two bytes; do not publish a measurement.
- Report missing required service/characteristic, failed notification setup,
  invalid calibration, and disconnects through existing connection error state.
- Preserve the current bounded reconnect policy.
- Never synthesize a force sample before calibration completes.

## Verification plan

Use TDD for every production change:

1. Entralpi protocol tests cover prefix matching, UUID contract, big-endian
   centigram preservation, short-frame rejection, and absence of commands.
2. Transport tests cover contract-driven scanning/discovery and ensure the
   Entralpi route uses `181D/FFF1`, while all Motherboard transport tests stay
   green.
3. Connection-service tests cover ten-sample calibration, instability/range
   rejection, baseline-minus-raw conversion, no pre-calibration samples, and
   disconnect/reconnect behaviour.
4. Run the targeted tests, complete test suite, and relevant iOS build before
   merge.

## Explicitly missing evidence

- A physical Entralpi GATT capture proving actual advertised name variants.
- Evidence that `FFF4` produces useful data; the vendor app does not subscribe
  to it.
- Any vendor-documented write command or verified hardware tare/start/stop
  command.
- Proof that BLE notifications arrive at the hardware's stated 100 Hz sample
  rate.
