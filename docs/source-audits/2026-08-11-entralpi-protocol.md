# Entralpi force sensor protocol audit

- Audited upstream file: [`packages/core/src/models/device/entralpi.model.ts`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/e486d230922d749448106c56396997d50976062c/packages/core/src/models/device/entralpi.model.ts)
- Audited file blob SHA: `c6cdd037207bee0299bf94000e1fdb40ac3b7ca9`

## Mapped facts

| Hang Ten field | Audited source fact |
| --- | --- |
| Named discovery | Filter name is exactly `ENTRALPI`; matching is case-sensitive and has no advertised-service requirement. |
| Services | Device Information `0000180a-0000-1000-8000-00805f9b34fb`, Battery `0000180f-0000-1000-8000-00805f9b34fb`, vendor Generic Attribute `f000ffc0-0451-4000-b000-000000000000`, UART `0000fff0-0000-1000-8000-00805f9b34fb`, and Weight Scale `0000181d-0000-1000-8000-00805f9b34fb`. |
| Notification characteristics | UART RX characteristic `0000fff4-0000-1000-8000-00805f9b34fb` is scoped to UART service `0000fff0-0000-1000-8000-00805f9b34fb`; Weight Scale notify characteristic `0000fff1-0000-1000-8000-00805f9b34fb` is scoped to Weight Scale service `0000181d-0000-1000-8000-00805f9b34fb`. The overlapping `FFF1` UUID is intentionally service-scoped. |
| Battery level | Battery Level characteristic `00002a19-0000-1000-8000-00805f9b34fb` is read from Battery service as a one-byte level value. Battery level is the only sourced device capability mapped by this adapter. |
| Commands | No device tare, start, or stop command bytes are defined in the source, so Hang Ten exposes no write characteristic and no command payloads. |
| Force value | Notification handling reads bytes 0 and 1 with `getUint16(0)`, divides by 100, and rounds to one decimal place before emitting a force measurement. Payloads shorter than two bytes are rejected. |
| Source unit | Upstream exposes the stream value as kg and applies software tare. Hang Ten stores force samples as kgf, so kg to kgf is an explicit adaptation pending vendor confirmation. |

The source frame does not define headers, timestamps, checksums, or multi-record framing. Hang Ten therefore decodes only the first two bytes of a valid frame, never emits partial force from a truncated frame, and reads byte indexes relative to the `Data` collection start so sliced payloads decode correctly.
