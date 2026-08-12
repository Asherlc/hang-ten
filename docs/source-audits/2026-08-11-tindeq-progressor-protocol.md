# Tindeq Progressor protocol audit

## Sources

- Official Tindeq Progressor API: https://tindeq.com/progressor_api/
- Upstream implementation reference: https://github.com/Stevie-Ray/hangtime-grip-connect/blob/68791aab75cea3f5e1de453057f98d9099b3a452/packages/core/src/models/device/progressor.model.ts
- Audited upstream file blob SHA: `c19d8b73885edda5ea8cfb2b567024f0a6e2a35b`

## Implementation mapping

| Fact | Source | Hang Ten mapping |
| --- | --- | --- |
| Progressor service, notification, and write UUIDs | Official API; upstream adapter | `ProgressorProtocolAdapter` BLE contract and write characteristic |
| `Progressor` advertised-name prefix | Official API; upstream adapter | Named profile matching |
| Progressor service UUID used as the generic discovery signal | Upstream adapter | Explicit adaptation: the generic profile matches only that advertised service UUID, without requiring the named profile's `Progressor` prefix |
| Tare/start/stop bytes `0x64`/`0x65`/`0x66` | Official API; upstream adapter | `payload(for:)` |
| Type-1 notifications are TLV: byte 0 is the response type, byte 1 is the one-byte payload length, and the remaining bytes are little-endian Float32 kgf/UInt32 microsecond records | Official API; upstream adapter | `decode(_:receivedAt:)` requires the declared payload length to exactly equal all bytes after the two-byte header, then parses the payload in eight-byte records |

The generic profile deliberately accepts only the advertised Progressor service UUID; it does not infer compatibility from an arbitrary peripheral name.
