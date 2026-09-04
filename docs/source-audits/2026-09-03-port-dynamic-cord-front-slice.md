# Port-A-Board dynamic-cord front and back slice — source audit

Reviewed 2026-09-03. This audit covers only the Frictitious Port-A-Board
`primary`, `front-inverted`, and `back` presentations. The
implementation contract is recorded in
[`docs/superpowers/specs/2026-09-03-port-dynamic-cord-prototype-design.md`](../superpowers/specs/2026-09-03-port-dynamic-cord-prototype-design.md)
and its execution plan in
[`docs/superpowers/plans/2026-09-03-port-dynamic-cord-prototype.md`](../superpowers/plans/2026-09-03-port-dynamic-cord-prototype.md).

**Supersession note (2026-09-03):** `back` identifies the separate physical
8/10/12/15 face; it is not an orientation of the 20/25/30 front face. An
in-plane rotation changes only the position of one physical face and never
changes its face identity. The proposed `back-inverted` position was rejected
and removed from the package and review contract. The accepted
`front-inverted` presentation remains a 180-degree position of `primary`.

## Primary manufacturer evidence

- [Port-A-Board product page](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard)
- [Official front photograph](https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840)
- [Official back photograph](https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840)
- [Official pinch-side photograph](https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840)

The photographs support the board identity, wood faces, dark eyelet entries,
and near-black braided cord. They crop the upper suspension connection. The
compact bight and interwoven knot rendered above the board are therefore a
generic, physically plausible illustration, not a claim about the exact knot
supplied by Frictitious.

## Source-raster custody

Commit `e12e7f66` is the approved cord-free source for the three physical
faces. Each historical blob is a `1400 × 1400`, 8-bit RGBA PNG with a
transparent background.

| Physical face | Historical path | SHA-256 at `e12e7f66` | This slice |
| --- | --- | --- | --- |
| front | `assets/primary.png` | `6d345c8dd4bb9970b9b58a0800bbf340119cc74cc11028c9867551cc9a6a5cd0` | Restored byte-for-byte and promoted unchanged |
| back | `assets/back.png` | `39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e` | Restored byte-for-byte after explicit source review and promoted unchanged |
| pinch side | `assets/side.png` | `cf1fe06bef3c374fd980d1168cf0279e885bc260401df914579c025e1e55e7ad` | Verified only; not promoted or changed by this slice |

The promoted `primary.png` and `back.png` remain `1400 × 1400` RGBA and have
the SHA-256 values in the table above.
No detection, segmentation, mask or contour generation, registration,
alignment, vectorization, automatic cropping, generation, or recompression
was used. The exact source bytes are decoded by the app and drawn once.

The canonical JSON hash of the complete `holds` array before and after this
slice is
`c9ed1d63504559f02e33a17527ee028ac077767d57b9c44e2293e78bd515bb68`.
No hold path or hold metadata changed.

## Approved authored geometry

All values are deliberate authored coordinates. They were not extracted from
pixels or inferred from hold geometry.

| Item | Value |
| --- | --- |
| scene size | `1200 × 1464` |
| source frame in scene | `(x: 0, y: 214, width: 1200, height: 1250)` |
| inner face frame relative to source | `(x: -100, y: -10, width: 1400, height: 1400)` |
| scene face frame | `(x: -100, y: 204, width: 1400, height: 1400)` |
| face pivot, source-relative | `(600, 690)` |
| face pivot, scene | `(600, 904)` |
| normalized rotation anchor | `(0.5, 0.6174863387978142)` (`0.5, 113/183`) |
| front attachment points, source-relative | `(276, 804)` and `(920, 804)` |
| front attachment points, upright scene | `(276, 1018)` and `(920, 1018)` |
| front attachment points, inverted scene | `(924, 790)` and `(280, 790)`; screen-sorted before strand pairing |
| back attachment points, source-relative | `(203, 712)` and `(997, 712)` |
| back attachment points, upright scene | `(203, 926)` and `(997, 926)` |
| pull point, source-relative | `(600, 71.5)` |
| pull point, scene | `(600, 285.5)` |
| strand exits, scene | `(578, 285.5)` and `(622, 285.5)` |
| eyelet radius | `34` source units |

The official front source was manually reviewed with eyelet centers near
`(375, 813)` and `(1019, 813)` in source-image coordinates. The authored rig
endpoints deliberately land at the exact approved inverted screen endpoints
above after the cardinal clock-face transform.

The pull-point raise preserves the previously approved scale:

```text
old vertical distance = 712 - 285  = 427
new vertical distance = 712 - 71.5 = 640.5
640.5 = 1.5 × 427
```

The board and all face-owned layers rotate only in the image plane. The upper
support stays world-up, both strands remain straight and tensioned, projected
eyelets are paired by screen position to avoid crossing, and a directional
foreground crescent makes each cord enter its eyelet continuously.

## Storage and presentation decisions

| Presentation | Stored artwork | Runtime treatment | Decision |
| --- | --- | --- | --- |
| `primary` | `assets/primary.png` | canonical face at `0°`; dynamic cord rig | Included; isolated runtime output awaits final one-by-one review |
| `front-inverted` | shares `assets/primary.png` | same face at `180°`; same world-up support | Approved geometry/reference proof; isolated runtime output awaits final one-by-one review |
| `back` | `assets/back.png` | separate physical 8/10/12/15 face at `0°`; dynamic cord rig with attachment points `(203, 712)` and `(997, 712)` | Approved source and production output |

The user approved one stored PNG per physical face. The redundant
`assets/front-inverted.png` was removed. No `back-inverted` presentation or
asset remains after the correction recorded above. The
`cord-option-4-20mm-incut` presentation described the same physical front face
at the same 180-degree rotation as `front-inverted`; its duplicate metadata and
PNG were removed together. The side presentation remains outside this slice.

## Review evidence

The exact user-approved inverted proof is tracked at
`docs/source-audits/review-assets/2026-09-03-port-dynamic-cord-front-inverted-approved.png`.
It is `1200 × 1464` RGBA with transparent corners and SHA-256
`7b8c3b78dddf4a8ab4648fd0aaa42cbcf969b1c82a95de1dc9d015694c7f2576`.
It records the accepted geometry and cord treatment; production uses the
deterministic SwiftUI renderer rather than this flattened review raster.

The isolated production renders are workspace-owned, untracked review
artifacts:

| Presentation | Path | SHA-256 | Format check |
| --- | --- | --- | --- |
| `primary` | `.context/joyful-donkey-port-dynamic-cord-front-review/primary.png` | `125350a675166e4dd4f6ba2b914151893fe5176833a15b24e1bd308726545504` | `1200 × 1464` RGBA; four transparent corners |
| `front-inverted` | `.context/joyful-donkey-port-dynamic-cord-front-review/front-inverted.png` | `b039bf5181d6cf041ed74442e27a7e8f99664163967915396b9c83e966fd6a15` | `1200 × 1464` RGBA; four transparent corners |
| `back` | `.context/joyful-donkey-port-dynamic-cord-back-production-review-20260903/back.png` | `88e447dfae0844a343d16f3f1b5b2700e058153bc0b85130675a7d007b1e9994` | `1200 × 1464` RGBA; four transparent corners |

Both front renders were visually inspected for complete uncropped cords, head-on face
geometry, continuous eyelet entry, world-up support, tension, and transparent
background. The fresh `back` production render was also inspected at original
size for complete cords, tension, eyelet continuity, head-on geometry, and
transparency, then approved in one-by-one review. The rejected rotated-back
output is intentionally excluded from the package and acceptance evidence.

## Verification

- Focused geometry/render test: `1` test executed, `0` failures; both fresh
  back artifact dimensions and transparent corners passed.
- Package inventory validation:
  `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed with no drafts.
- Package status:
  `scripts/hangboard-packages.sh status --root Hangboards` passed with no
  drafts.
- Focused iOS package gates: `2` tests executed, `0` failures (one loader and
  alias-resolution test; one canonical writer round-trip test).
- Focused Python package/parser and production custody gates: `2` tests passed.
- Generic iOS Simulator app build: `BUILD SUCCEEDED`.

Workbench parsing/preview parity is intentionally handled by a separate task
and is not claimed by this audit. No app-review screenshots or contact sheet
were produced for this visual gate.
