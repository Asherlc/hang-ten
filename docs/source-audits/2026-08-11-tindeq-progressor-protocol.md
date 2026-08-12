# Tindeq Progressor protocol audit

## Sources

- Official Tindeq Progressor API: https://tindeq.com/progressor_api/
- Upstream implementation reference: https://github.com/Stevie-Ray/hangtime-grip-connect/blob/c19d8b73885edda5ea8cfb2b567024f0a6e2a35b

## Implementation mapping

| Fact | Source | Hang Ten mapping |
| --- | --- | --- |
| Progressor service, notification, and write UUIDs | Official API; upstream adapter | `ProgressorProtocolAdapter` BLE contract and write characteristic |
| `Progressor` advertised-name prefix | Official API; upstream adapter | Named profile matching |
| Service-only generic discovery | Upstream adapter | Generic Progressor-compatible matching |
| Tare/start/stop bytes `0x64`/`0x65`/`0x66` | Official API; upstream adapter | `payload(for:)` |
| Type-1 notifications carrying little-endian Float32 kgf and UInt32 microsecond timestamps | Official API; upstream adapter | `decode(_:receivedAt:)` |

The generic profile deliberately accepts only the advertised Progressor service UUID; it does not infer compatibility from an arbitrary peripheral name.
