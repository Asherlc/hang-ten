# WH-C06 force sensor protocol audit

- Audited upstream file: [`packages/core/src/models/device/wh-c06.model.ts`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/02dd6ff227ffb0fc521fd547a83e85453351eb3b/packages/core/src/models/device/wh-c06.model.ts)
- Audited file blob SHA: `90d693c649ea1cce4157d73c9a04caa8b77dfc47`

## Mapped facts

| Hang Ten field | Audited source fact |
| --- | --- |
| Discovery scope | Advertisement-only source. No GATT services, write characteristics, or commands are mapped. |
| Company identifier | Manufacturer company ID `0x0100` / `256`. |
| Force value | Manufacturer payload bytes 10 and 11 are read as a big-endian UInt16 and divided by 100. |
| Source unit | The low nibble of manufacturer payload byte 14 selects the unit: `1` is kg and `2` is lb. Hang Ten converts the raw hundredths value through `ForceSensorSourceUnit` into canonical kgf; unknown unit nibbles are rejected rather than assumed. |
| Liveness | Advertisement liveness interval is 10 seconds. |
| Named automatic discovery | No active advertised-name rule is mapped. The named `.whC06` profile automatically matches only company ID `0x0100` plus the implementation-captured 17-byte payload signature beginning `02 03`; this capture is not vendor-authoritative protocol documentation. |
| Collision handling | The published 13-byte Hi-Link HLK-LD2410B presence-radar payload under company ID `0x0100` does not match or decode as named `.whC06`. |
| Generic fallback | `.genericWHC06` remains an explicitly selected generic fallback, rather than an automatic-discovery candidate. |

The generic fallback adapter rejects manufacturer payloads shorter than 15 bytes and reads payload indexes relative to the payload collection start, so sliced `Data` values decode the same way as zero-indexed buffers. No unit conversion is claimed for unsupported unit nibbles.
