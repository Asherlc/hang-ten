# WH-C06 force sensor protocol audit

- Audited upstream file: [`packages/core/src/models/device/wh-c06.model.ts`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/02dd6ff227ffb0fc521fd547a83e85453351eb3b/packages/core/src/models/device/wh-c06.model.ts)
- Audited file blob SHA: `90d693c649ea1cce4157d73c9a04caa8b77dfc47`

## Mapped facts

| Hang Ten field | Audited source fact |
| --- | --- |
| Discovery scope | Advertisement-only source. No GATT services, write characteristics, or commands are mapped. |
| Company identifier | Manufacturer company ID `0x0100` / `256`. |
| Force value | Manufacturer payload bytes 10 and 11 are read as a big-endian UInt16 and divided by 100. |
| Source unit | Upstream exposes the value in kg and uses software tare. Hang Ten stores force samples as kgf, so kg to kgf is an explicit adaptation pending vendor confirmation. |
| Liveness | Advertisement liveness interval is 10 seconds. |
| Automatic discovery | No active advertised-name rule is mapped. Both WH-C06 profiles remain explicit-selection-only because company ID `256` is not unique enough for automatic discovery. |

The adapter rejects manufacturer payloads shorter than 12 bytes and reads payload indexes relative to the payload collection start, so sliced `Data` values decode the same way as zero-indexed buffers.
