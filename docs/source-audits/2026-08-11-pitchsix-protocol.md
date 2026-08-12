# PitchSix Force Board protocol audit

- Audited upstream file: [`packages/core/src/models/device/forceboard.model.ts`](https://github.com/Stevie-Ray/hangtime-grip-connect/blob/68791aab75cea3f5e1de453057f98d9099b3a452/packages/core/src/models/device/forceboard.model.ts)
- Audited file blob SHA: `565d58d9603f41e0ea82097fe9e10541dc9aefa8`

## Mapped facts

| Hang Ten field | Audited source fact |
| --- | --- |
| Named discovery | Filter name is exactly `Force Board`. |
| Force notification | Service `9a88d67f-8df2-4afe-9e0d-c2bbbe773dd0`, characteristic `9a88d682-8df2-4afe-9e0d-c2bbbe773dd0`. |
| Mode writes | Service `467a8516-6e39-11eb-9439-0242ac130002`, characteristic `467a8517-6e39-11eb-9439-0242ac130002`. |
| Commands | Streaming `0x04`, tare `0x05`, idle/stop `0x07`. |
| Packet format | First two bytes are a big-endian sample count. Each sample is three bytes: `byte0 * 32768 + byte1 * 256 + byte2`, in pounds. |

Hang Ten only accepts packet counts 1 through 6 and requires the frame length to match the count exactly. Those bounds are a defensive parser constraint, based on the documented packet shape rather than a device behavior claim.
