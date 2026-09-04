# Port-A-Board dynamic-cord front slice — source audit

Reviewed 2026-09-03. This audit covers only the Frictitious Port-A-Board
`primary` and `front-inverted` presentations. The implementation contract is
recorded in
[`docs/superpowers/specs/2026-09-03-port-dynamic-cord-prototype-design.md`](../superpowers/specs/2026-09-03-port-dynamic-cord-prototype-design.md)
and its execution plan in
[`docs/superpowers/plans/2026-09-03-port-dynamic-cord-prototype.md`](../superpowers/plans/2026-09-03-port-dynamic-cord-prototype.md).

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
| back | `assets/back.png` | `39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e` | Verified only; not promoted or changed by this slice |
| pinch side | `assets/side.png` | `cf1fe06bef3c374fd980d1168cf0279e885bc260401df914579c025e1e55e7ad` | Verified only; not promoted or changed by this slice |

The promoted `Hangboards/frictitious-port-a-board/assets/primary.png` remains
`1400 × 1400` RGBA and has SHA-256
`6d345c8dd4bb9970b9b58a0800bbf340119cc74cc11028c9867551cc9a6a5cd0`.
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
| attachment points, source-relative | `(276, 804)` and `(920, 804)` |
| attachment points, upright scene | `(276, 1018)` and `(920, 1018)` |
| attachment points, inverted scene | `(924, 790)` and `(280, 790)`; screen-sorted before strand pairing |
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

The user approved one stored PNG per physical face. The redundant
`assets/front-inverted.png` was removed. The
`cord-option-4-20mm-incut` presentation described the same physical front face
at the same 180-degree rotation as `front-inverted`; its duplicate metadata and
PNG were removed together. Back, back-inverted, and side presentations are
outside this slice.

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

Both were visually inspected for complete uncropped cords, head-on face
geometry, continuous eyelet entry, world-up support, tension, and transparent
background. They remain pending explicit one-by-one production review.

## Verification

- Focused geometry/render test: `1` test executed, `0` failures; artifact
  dimensions and transparent corners passed.
- Package inventory validation:
  `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed with no drafts.
- Package status:
  `scripts/hangboard-packages.sh status --root Hangboards` passed with no
  drafts.
- Focused iOS package gates: `2` tests executed, `0` failures (one loader and
  alias-resolution test; one canonical writer round-trip test).
- Focused Python package-parser gate: `1` test passed.
- Generic iOS Simulator app build: `BUILD SUCCEEDED`.

Workbench parsing/preview parity is intentionally handled by a separate task
and is not claimed by this audit. No app-review screenshots or contact sheet
were produced for this visual gate.
