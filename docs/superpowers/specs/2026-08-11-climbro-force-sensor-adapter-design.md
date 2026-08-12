# Climbro force-sensor adapter design

## Goal

Add a source-faithful, protocol-level Climbro adapter that identifies a Climbro peripheral, exposes its BLE notification contract, and converts its stateful byte stream into normalized kilogram-force samples. This scope does not connect the adapter to the app's runtime Bluetooth flow.

## Sources and evidence boundary

- Primary implementation: [`climbro.model.ts` at upstream commit `02dd6ff227ffb0fc521fd547a83e85453351eb3b`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/02dd6ff227ffb0fc521fd547a83e85453351eb3b/packages/core/src/models/device/climbro.model.ts). Its blob SHA is `4257b024609ebf545f6131319d65fd61e2cadd3e`.
- Upstream parser tests: [`device-parsers.test.mjs` at the same commit](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/02dd6ff227ffb0fc521fd547a83e85453351eb3b/packages/core/test/device-parsers.test.mjs).
- UART characteristic properties: [Microchip Transparent UART specification](https://onlinedocs.microchip.com/oxy/GUID-26457D23-798C-47B0-9F40-C5DA6E995C6F-en-US-2/GUID-4346AC32-EFE5-4C3D-9D47-59BDC6EF7B7C.html).

The source demonstrates notification parsing and GATT identifiers. It does not provide Climbro-specific write payloads, a hardware-tare command, stream start/stop commands, physical packet captures, MTU limits, or a valid battery-byte range. The adapter must not add behavior for those missing facts.

## Architecture

`ClimbroProtocolAdapter` follows the existing Progressor and PitchSix adapter shape. It accepts only `.climbro`, matches an advertised local name with the `Climbro` prefix, declares the UART and Device Information services, and identifies the UART notification characteristic. Its capability set is `[.batteryLevel]`; it has no write characteristic or command-payload API.

`ClimbroProtocolParser` owns the stream state that cannot live in a stateless `decode` function. Its `append(_:receivedAt:)` method receives exactly one BLE `Data` value and returns every force sample decoded from it. A single `receivedAt` applies to every returned sample because the upstream implementation uses one timestamp per notification.

The parser has three modes: uninitialized, battery, and sensor. Byte `0xF0` changes mode to battery and emits nothing; byte `0xF5` changes mode to sensor and emits nothing. In battery mode, each subsequent non-marker byte updates `batteryPercentage` to `100 * (byte - 112) / 118` and emits no sample. In sensor mode, each subsequent non-marker byte is a kilogram-force sample, except `0xF6`, which represents 36 kg. Modes persist across `append` calls until another marker arrives. Bytes in uninitialized mode emit nothing.

The parser preserves the source's unbounded battery conversion and sentinel ordering: `0xF6` is transformed to 36 before mode-specific handling. The adapter does not claim that a `0xF6` battery byte is valid; the test suite only covers source-supported sensor behavior.

## BLE contract

| Purpose | UUID |
| --- | --- |
| UART Transparent Service | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| Notification characteristic | `49535343-1e4d-4bd9-ba61-23c647249616` |
| UART client-write characteristic (known but unused) | `49535343-8841-43f4-a8d4-ecbe34729bb3` |
| Transparent Control Point (known but unused) | `49535343-4c8a-39b3-2f49-511cff073b7e` |
| Device Information Service | `0000180a-0000-1000-8000-00805f9b34fb` |

The notification UUID is the Microchip UART TX characteristic despite the upstream adapter's internal `rx` label. Hang Ten will name it by behavior, not by that label.

## Error handling and limits

The input is a byte stream with marker-based framing, so there is no packet length or endianness validation to invent. `ForceSensorSample` remains the normalization boundary and rejects values it cannot represent. The parser is intentionally source-faithful rather than adding timeout, automatic resynchronization, battery clamping, or write-side recovery policy.

## Testing

The test target will include the upstream fixture `F0 70 F5 0A F6 14`, expecting battery 0% and samples 10, 36, and 20 kg. It will also cover prefix-only discovery, BLE contract values, split sensor notifications, marker transitions, pre-marker suppression, and the absence of hardware-tare/start-stop capabilities and command payloads.

## File scope

- Create `HangTen/Models/ClimbroProtocol.swift`.
- Create `HangTenTests/ClimbroProtocolTests.swift`.
- Create `docs/source-audits/2026-08-11-climbro-protocol.md`.
- Modify `HangTen.xcodeproj/project.pbxproj` only to register the two Swift files in their existing groups and source build phases.

`ForceSensorModels.swift` and `ForceSensorModelsTests.swift` already contain the Climbro profile, label, and named matching policy. They remain unchanged.
