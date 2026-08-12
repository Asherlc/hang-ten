# Climbro force-sensor adapter design

## Goal

Add a source-faithful, protocol-level Climbro adapter that identifies a Climbro peripheral, exposes only its evidenced UART notification contract, and decodes its stateful byte stream into Hang Ten `ForceSensorSample` values. Runtime Bluetooth integration, shared transport, UI, history, and session routing are deferred.

## Sources and evidence boundary

- Primary implementation: [`climbro.model.ts` at upstream commit `1cf3d4f7a00ffd5de6000e4aa77f86819765ee43`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/1cf3d4f7a00ffd5de6000e4aa77f86819765ee43/packages/core/src/models/device/climbro.model.ts), verified blob `4257b024609ebf545f6131319d65fd61e2cadd3e`.
- Device docs: [`climbro.md` at the same commit](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/1cf3d4f7a00ffd5de6000e4aa77f86819765ee43/packages/docs/src/devices/climbro.md).
- Shared behavior: [`device.model.ts` at the same commit](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/1cf3d4f7a00ffd5de6000e4aa77f86819765ee43/packages/core/src/models/device.model.ts).

The source demonstrates name-prefix discovery, GATT identifiers, automatic notification streaming, marker-based parsing, and battery conversion. It does not evidence Climbro command payloads, writes, hardware tare, start/stop control, battery clamping, packet-size limits, or timeout/resynchronization behavior.

## Architecture

`ClimbroProtocolAdapter` accepts only `.climbro`, matches a case-sensitive advertised name prefix `Climbro`, and declares only the UART service plus RX notification characteristic used for streamed notifications. It records the declared TX and Transparent Control Point UUIDs as constants, but exposes no write characteristic and no command payloads. Capabilities are empty because Hang Ten capabilities represent actionable device behavior, and the audited write/control protocols are absent.

`ClimbroProtocolParser` owns explicit stream state that persists across `decode(_:receivedAt:)` calls:

- `.waitingForMarker`: pre-marker bytes emit no samples.
- `.battery`: bytes after `0xF0` update `batteryPercentage` using `100 * (byte - 112) / 118`, unclamped.
- `.sensor`: bytes after `0xF5` emit direct unsigned kg samples, except `0xF6`, which emits exactly 36 kg.

Hang Ten stores force as kgf. Mapping the upstream kg values to `.kilogramsForce` is a documented adaptation pending vendor proof. Every emitted value passes through `ForceSensorSample` validation; invalid conversions cannot emit samples.

## BLE contract

| Purpose | UUID |
| --- | --- |
| UART Transparent Service | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| Notification characteristic | `49535343-1e4d-4bd9-ba61-23c647249616` |
| TX characteristic, recorded only | `49535343-8841-43f4-a8d4-ecbe34729bb3` |
| Transparent Control Point, recorded only | `49535343-4c8a-39b3-2f49-511cff073b7e` |

Device Information reads are documented upstream but are outside this adapter-only Hang Ten BLE contract.

## Testing

Focused XCTest coverage verifies name prefix matching, UUID contract, no capabilities, no writes/commands, state transitions split across notifications, `0xF6 -> 36 kgf`, direct byte samples, raw unclamped battery conversion, and pre-marker suppression.

## File scope

- `HangTen/Models/ClimbroProtocol.swift`
- `HangTenTests/ClimbroProtocolTests.swift`
- `docs/source-audits/2026-08-11-climbro-protocol.md`
- `HangTen.xcodeproj/project.pbxproj` registration only
