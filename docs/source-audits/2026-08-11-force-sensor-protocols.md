# Force Sensor Protocol Source Audit

Date: 2026-08-11

## Evidence boundary

Tindeq Progressor mappings below are manufacturer-documented by Tindeq's
official API. Every other device mapping in this audit is **upstream
open-source evidence**, from `Stevie-Ray/hangtime-grip-connect`; it is not a
manufacturer assertion. mySmartBoard has no protocol source in scope and
remains absent from the profiles.

## Sources observed during design

| Device | Source URL | Git blob SHA | Evidence used |
| --- | --- | --- | --- |
| Tindeq Progressor | https://tindeq.com/progressor_api/ | N/A (manufacturer web API) | custom BLE service, control/data characteristics, TLV, commands, little-endian data |
| Progressor implementation reference | https://api.github.com/repos/Stevie-Ray/hangtime-grip-connect/git/blobs/c19d8b73885edda5ea8cfb2b567024f0a6e2a35b | `c19d8b73885edda5ea8cfb2b567024f0a6e2a35b` | upstream open-source compatibility reference only |
| PitchSix Force Board | https://api.github.com/repos/Stevie-Ray/hangtime-grip-connect/git/blobs/565d58d9603f41e0ea82097fe9e10541dc9aefa8 | `565d58d9603f41e0ea82097fe9e10541dc9aefa8` | name, GATT contract, stream/tare/idle modes, UInt24 pound samples |
| Weiheng WH-C06 | https://api.github.com/repos/Stevie-Ray/hangtime-grip-connect/git/blobs/90d693c649ea1cce4157d73c9a04caa8b77dfc47 | `90d693c649ea1cce4157d73c9a04caa8b77dfc47` | company ID, advertising-byte layout, kgf source unit |
| Entralpi | https://api.github.com/repos/Stevie-Ray/hangtime-grip-connect/git/blobs/c6cdd037207bee0299bf94000e1fdb40ac3b7ca9 | `c6cdd037207bee0299bf94000e1fdb40ac3b7ca9` | advertised name, GATT and battery contract, kgf source unit |
| Climbro | https://api.github.com/repos/Stevie-Ray/hangtime-grip-connect/git/blobs/4257b024609ebf545f6131319d65fd61e2cadd3e | `4257b024609ebf545f6131319d65fd61e2cadd3e` | name prefix, UART contract, marker-state packet handling, battery formula |

## Audited protocol map

| Profile | Recognition and capability | BLE contract | Wire layout and source unit | Commands |
| --- | --- | --- | --- | --- |
| Progressor | name prefix `Progressor`; hardware tare, explicit start and stop | service `7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57`; notify `7E4E1702-1EA6-40C9-9DCC-13D34FFEAD57`; write `7E4E1703-1EA6-40C9-9DCC-13D34FFEAD57` | TLV type `1`; payload length divisible by 8; repeated `(Float32 LE kgf, UInt32 LE microseconds)` | tare `0x64`, start `0x65`, stop `0x66` |
| PitchSix | exact name `Force Board`; hardware tare, explicit start and stop | force service `9A88D67F-8DF2-4AFE-9E0D-C2BBBE773DD0`, notify `9A88D682-8DF2-4AFE-9E0D-C2BBBE773DD0`, tare `9A88D683-8DF2-4AFE-9E0D-C2BBBE773DD0`; mode service `467A8516-6E39-11EB-9439-0242AC130002`, write `467A8517-6E39-11EB-9439-0242AC130002` | `UInt16 BE count`, then `count` × `UInt24 BE pounds`; preserve pounds here (conversion belongs to the service task) | stream `0x04`, tare `0x05`, idle `0x07` |
| WH-C06 | manufacturer company ID `0x0100`; advertisement-only; no GATT, commands, or hardware battery | none | manufacturer bytes 10–11: `UInt16 BE / 100` kgf | none |
| Entralpi | exact name `ENTRALPI`; notify-only streaming, battery available | service `0000FFF0-0000-1000-8000-00805F9B34FB`, notify `0000FFF1-0000-1000-8000-00805F9B34FB`; battery service `180F`, characteristic `2A19` | first `UInt16 BE / 100` kgf | none |
| Climbro | name prefix `Climbro`; notify-only streaming, battery available | UART service `49535343-FE7D-4AE5-8FA9-9FAFD205E455`, notify `49535343-1E4D-4BD9-BA61-23C647249616` | marker state persists across notifications: `0xF0` selects battery; `0xF5` selects kgf force; in force state `0xF6` is 36 kgf, otherwise the byte is kgf; battery percent is `clamp((raw - 112) * 100 / 118, 0...100)` | none |

Generic Progressor-compatible and generic WH-C06-compatible profiles are manual
choices only and must never be automatically matched. The generic Progressor
profile uses the Progressor contract; generic WH-C06 uses the WH-C06
advertisement contract.
