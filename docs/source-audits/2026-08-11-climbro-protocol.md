# Climbro protocol audit

Source authority: [`climbro.model.ts` at immutable commit `1cf3d4f7a00ffd5de6000e4aa77f86819765ee43`, blob `4257b024609ebf545f6131319d65fd61e2cadd3e`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/1cf3d4f7a00ffd5de6000e4aa77f86819765ee43/packages/core/src/models/device/climbro.model.ts).

Additional audited context:

- [`climbro.md` at immutable commit `1cf3d4f7a00ffd5de6000e4aa77f86819765ee43`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/1cf3d4f7a00ffd5de6000e4aa77f86819765ee43/packages/docs/src/devices/climbro.md)
- [`device.model.ts` at immutable commit `1cf3d4f7a00ffd5de6000e4aa77f86819765ee43`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/1cf3d4f7a00ffd5de6000e4aa77f86819765ee43/packages/core/src/models/device.model.ts)

| Hang Ten field or behavior | Audited source mapping |
| --- | --- |
| Named discovery | Device name begins with case-sensitive `Climbro`. No advertised-service condition is required. |
| UART service | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| Notification characteristic | `49535343-1e4d-4bd9-ba61-23c647249616` |
| TX characteristic | Declared as `49535343-8841-43f4-a8d4-ecbe34729bb3`, but no Climbro write protocol is evidenced. Hang Ten records the UUID only and does not expose writes. |
| Control-point characteristic | Declared as `49535343-4c8a-39b3-2f49-511cff073b7e`, but no Climbro write protocol is evidenced. Hang Ten records the UUID only and does not expose writes. |
| Streaming | Docs state force data streams automatically via BLE notifications once connected; this adapter exposes only the notification contract. |
| Battery marker | `0xF0` enters battery mode; subsequent values use `100 * (value - 112) / 118`. |
| Sensor marker | `0xF5` enters sensor mode; subsequent values are kilograms. |
| Sensor sentinel | `0xF6` represents a 36 kg sensor value. |
| Parser state | The source keeps a `flagSynchro` field on the device; Hang Ten models this as explicit parser state preserved across `decode` calls. |
| Unit adaptation | The source treats sensor bytes as kg. Hang Ten stores force samples as kgf; mapping kg to kgf is an explicit adaptation pending vendor proof. |

Device Information reads are documented upstream but are not part of this adapter-only PR's Hang Ten BLE contract. The cited Climbro source does not provide a Climbro command payload, so the adapter contains no write characteristic, command API, start/stop behavior, or hardware tare behavior.
