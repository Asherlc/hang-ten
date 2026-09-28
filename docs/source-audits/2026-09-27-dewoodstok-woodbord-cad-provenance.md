# deWoodstok Woodbord — native CAD provenance

Date: 2026-09-27. Package `dewoodstok-woodbord`, board ID
`dewoodstok-woodbord`, revision `2026-09-contact-first`. The FreeCAD source is
`Hangboards/dewoodstok-woodbord/dewoodstok-woodbord.FCStd`. Its embedded
`HangTenBoardManifest` replaces the committed `board.json`. The one-off
authoring script lives only in workspace scratch at
`.context/skinny-catfish/author_woodbord.py`. The saved document reopens and
recompiles without that script.

This is a simplified **display model**. It is not recovered manufacturing
geometry or a load-bearing CAD plan. The manufacturer's published dimensions
fix the overall size. The operator read the pocket layout by hand from the
manufacturer's straight-on photo. Every other number is a labeled display
estimate below.

The Woodbord is a fixed, wall-mounted board. It has no cords, suspension, or
attachment nodes, and none are authored.

## Sources

Retained primary sources (downloaded 2026-09-27):

| Retained file | Publisher and URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `2026-09-27-dewoodstok-woodbord-cad-sources/front.jpg` | deWoodstok media kit, <https://www.dewoodstok.nl/wp-content/uploads/2025/10/05_C_woodbord.jpg> | `51dc7198fb42931ccebba75a232960a5b70e68adacaffb8811c7f058bd4bf742` | Straight-on front: outline, the 6 / 4 / 6 pocket layout, every pocket's X/Z extent (measured, below) |
| `2026-09-27-dewoodstok-woodbord-cad-sources/oblique.jpg` | deWoodstok media kit, <https://www.dewoodstok.nl/wp-content/uploads/2025/10/05_B_woodbord.jpg> | `2f300da13c3c53425564cf07040559872b87603e7e6ff1aeac93e76bd6ee3c49` | Stadium pockets with a flat floor and flat back wall; rounded pocket mouths; rounded front perimeter; board end profile |
| `2026-09-27-dewoodstok-woodbord-cad-sources/oblique-high-res.jpg` | deWoodstok product page, <https://www.dewoodstok.nl/wp-content/uploads/2020/04/04_woodbord_01.jpg> | `dbd573fbe5931f5ffbf5c17fdfab17c205e5d9c105ae1714bb5b9cadee38767b` | Same features at a higher resolution; the end view used for the front-top round-over estimate |

The [product page](https://www.dewoodstok.nl/product/hangboard-woodbord/)
(HTML SHA-256 `c98c16cc2cd062491f77fe41e9873c57ebc0bf1183f9bf0c137413e48f3b19c5`
as fetched) publishes "590 x 148 x 40mm", "4-finger pockets with depths of 13,
16, 20, 25, 30, and 35 mm", "2-finger pockets with depths of 20 and 35 mm",
"4 stainless steel screws for wall mounting", and "All holds are nicely
rounded". It does not assign a depth to a position. The
[Bergfreunde listing](https://www.bergfreunde.eu/dewoodstok-woodbord-training-board/)
(a retailer, secondary) repeats the same figures and adds "A large declining
rim on top, perfect to warm-up".

Cited but not used for measurement: the product page's front photo
`https://www.dewoodstok.nl/wp-content/uploads/2020/04/04_woodbord_02.jpg`
(SHA-256 `66e808156e2f7eddd47eb75b9118e4953940f92ec5d199f87f28dc914162ed40`).
Its board spans 777 × 213.5 px, which is a 3.64 aspect ratio against the
published 3.99. The image is stretched vertically, so it was used only to
confirm the layout.

The superseded Git asset at `585e8078a` was a visual cross-check only, never a
compiler input or geometry source: USDZ SHA-256
`b8ffc338baa9c5bc4d961ad727d1c87dde5d0539c13fc78a848c579b3cda3186` (LFS
object), generated from `geometry-config.json` retained at
`2dd5182b4:.context/migration/source/hangboards-batch-01/models/dewoodstok-woodbord/source/`.

## Conflicts recorded

1. **The superseded mesh misplaced six pockets.** Its generator put the inner
   upper and lower pockets at |X| 74 and the middle-row inner pockets at
   |X| 74. The manufacturer photo puts the inner upper and lower pockets at
   |X| 57.5 (X 14.5–100.5). It puts the middle-row inner pockets at |X| 121.5,
   in line with the two-finger column (X 78–165), and leaves the centre open
   for the engraved logo. The new source follows the photo.
2. **The 14° top slope is not supported.** The generator cut the top as a
   plane falling 10 mm toward the front and labeled it a display estimate for
   "declining rim". The end views in both obliques show a level top with a
   rounded front edge, so the new top is flat at Z 148, with an 8 mm front
   round-over (a display estimate). "Declining rim" is the retailer's wording.
   The package kind `sloper` is unchanged.
3. **Per-pocket depths are not published.** The geometry keeps the superseded
   asset's per-position estimates. Each estimate is drawn from the published
   family, paired left/right. Upper row: outer 35, two-finger 35, inner 30.
   Middle row: outer 25, inner 16. Lower row: outer 20, two-finger 20,
   inner 13 mm. They are **display estimates, not manufacturer
   mappings**. The manifest publishes no depths, and the app shows none.
4. **Photo vertical scale.** At 1.1737 px/mm (published 590 mm over the
   board's 692.5 px width), the board reads 146.5 mm tall against the
   published 148. Row positions were multiplied by 148 / 146.5 = 1.0102.

## Measurement frame

Native coordinates are millimetres: +X right, +Z up, front −Y, rear plane
Y = 0, bottom Z = 0. The board spans X ±295, Z 0–148, and Y 0 to −40, which
gives exactly the published 590 × 148 × 40 mm.

`front.jpg` (800 px) was read on 1 mm grids with
`Tools/HangboardCAD/photo_grid.py crop`, at scale 1.1737 px/mm and origin
(396.75, 552.5) px. The left half was read. The right half was checked
against mirrored marks and agrees to about 2 mm, the reading limit at this
resolution. The review overlay
(`docs/pr-screenshots/dewoodstok-woodbord/cad-over-manufacturer-photo.png`)
blends the compiled front view over the photo. No image was segmented, traced,
vectorized, or used as an automatic geometry input.

## CAD construction and field mapping

- **Blank**: a `Sketcher::SketchObject` front outline (590 × 148 mm, R15 top
  and R20 bottom corners, read from the photo corners as display estimates),
  extruded 40 mm toward −Y.
- **Pockets**: 16 stadium cutters, each a ruled `Part::Loft` of seven stadium
  sketches. The first five stations form a 3 mm quarter-round mouth: at depth
  s = 3(1 − cos t) the wall is offset 3(1 − sin t), for t = 0, 22.5, 45, 67.5,
  and 90°. A straight wall then runs to the floor. One `Part::MultiFuse` and
  one `Part::Cut` remove them. The ruled bands are planes and cones. A
  toroidal `Part::Fillet` on the mouths gave 147k triangles (2.9 MB); the lofts
  give 32k (888 KB).
- **Body**: a `Part::Fillet` of R8 on the 8 front perimeter edges (display
  estimate: the front photo shows a ~6 mm band, the end view ~10 mm). The rear
  edges are left square.
- **Regions**: each contact is a `Part::Feature` holding exact copies of the
  final body's faces. A pocket owns every face inside its stadium grown by the
  3 mm mouth: 21 faces each. `top-rim` owns the top plane and the front-top
  round-over. Each contact carries a CAD-authored `HangTenHoldOutline`: the
  pocket's wall stadium, and for the rim, the front band X ±280, Z 140–148.
  The document sets `HangTenCurvedRegionPartition` and `HangTenSurfaceNormals`.
  The face copies are static: after a geometry edit, re-run the
  classification.

| Contact ID → node | Measured X (mm) | Row Z (mm) | Display-estimate depth |
| --- | --- | --- | --- |
| `front-upper-1` / `-6` → `hold_upper_outer_left/right_001` | ∓272 to ∓186 | 104–128 | 35 |
| `front-upper-2` / `-5` → `hold_upper_two_finger_left/right_001` | ∓165 to ∓121 | 104–128 | 35 |
| `front-upper-3` / `-4` → `hold_upper_inner_left/right_001` | ∓100.5 to ∓14.5 | 104–128 | 30 |
| `front-middle-1` / `-4` → `hold_middle_outer_left/right_001` | ∓272 to ∓186 | 62–86 | 25 |
| `front-middle-2` / `-3` → `hold_middle_inner_left/right_001` | ∓165 to ∓78 | 62–86 | 16 |
| `front-lower-1` / `-6` → `hold_lower_outer_left/right_001` | ∓272 to ∓186 | 20–44 | 20 |
| `front-lower-2` / `-5` → `hold_lower_two_finger_left/right_001` | ∓165 to ∓121 | 20–44 | 20 |
| `front-lower-3` / `-4` → `hold_lower_inner_left/right_001` | ∓100.5 to ∓14.5 | 20–44 | 13 |
| `top-rim` → `hold_top_rim_001` | ±280 | 140–148, full 40 mm top | — |

The photo shows 24 mm (23–24 mm read) pocket walls, with the round-over band
outside them. The authoring script asserted that each pocket region's Y extent
equals its depth exactly. The compiler gates nothing here, because the manifest
publishes no scalar depths.

Omitted on purpose: the four mounting screws and their bores (as in the
superseded asset; see `2026-09-22-mounting-bore-removal.md`), the engraved
"DE WOOD STOK" and "woodbord" marks, the bamboo lamination, and any radius at
the pocket floor or back wall.

## Manifest change

The embedded manifest is value-identical to the deleted `board.json` except
the model presentation `aspectRatio`. It changed from 4.011387803216873 (the
superseded mesh bounds) to **3.9864862569393753**, the new descriptor
`modelBounds` x/y ratio (590 × 148 mm in float32). The top-level `aspectRatio`
of 3.6236559139784945 is unchanged. All 17 contact IDs and 18 node IDs, and
their pairing, are unchanged.

## Verification

- `compile_board.py`: native-source and 17-contact gates passed. The
  descriptor was derived from the reopened USDZ.
- `verify_reproducible.py --package dewoodstok-woodbord`: byte-identical on
  the pinned toolchain (FreeCAD 1.1.3, OCCT 7.8.1, usd-core 26.8).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed. `scripts/verify-model-delivery.py` verified the refreshed lock.
- `Tools/HangboardPackages` pytest: 718 passed.
  `Tools/HangboardModels/tests/test_model_delivery_alignment.py`: 8 passed.
  `Tools/HangboardCAD/tests`: 65 passed, 9 skipped.
- iOS: a workspace-owned iPhone 17 Pro simulator (iOS 26.5) ran the DEBUG
  board-detail route. It loaded the model with `top-rim` selected by default
  (the whole top edge highlighted). Hold-map taps selected
  `boardDetail.selectedHold.front-middle-3` (right middle-inner pocket) and
  `front-upper-2` (upper-left two-finger pocket). Each highlighted exactly one
  pocket. The simulator was deleted after the run.

| Review view | Previous asset | Native CAD |
| --- | --- | --- |
| Front | [previous](../pr-screenshots/dewoodstok-woodbord/previous-front.png) | [CAD](../pr-screenshots/dewoodstok-woodbord/cad-front.png) |
| Side | [previous](../pr-screenshots/dewoodstok-woodbord/previous-side.png) | [CAD](../pr-screenshots/dewoodstok-woodbord/cad-side.png) |
| Top | [previous](../pr-screenshots/dewoodstok-woodbord/previous-top.png) | [CAD](../pr-screenshots/dewoodstok-woodbord/cad-top.png) |
| Oblique | [previous](../pr-screenshots/dewoodstok-woodbord/previous-oblique.png) | [CAD](../pr-screenshots/dewoodstok-woodbord/cad-oblique.png) |

The views are OpenUSD `usdrecord` (Hydra Storm) renders, not SceneKit output.
The previous asset's meshes carry a `material:binding` to a removed material,
which renders black in Storm. The review copy drops that relationship before
rendering. The committed bytes were never modified. App screenshots:
[default top rim](../pr-screenshots/dewoodstok-woodbord/app-default.png),
[middle pocket 3](../pr-screenshots/dewoodstok-woodbord/app-front-middle-3.png),
[upper pocket 2](../pr-screenshots/dewoodstok-woodbord/app-front-upper-2.png).
`compare_exports` was not used as evidence, because the superseded mesh
contradicts the photos (conflicts 1 and 2).

Final source SHA-256:
`dfac5b76e9f625a380c710218c4d9fc0c1a257735fc00a8f887e1a4ad403ec82`.
Compiled USDZ SHA-256:
`62a43523b873e2c4fc87d9a0c41bf4be862720eed499d5635236822bbb709a52`.
Descriptor SHA-256:
`f81201b61af8ffb544af5687708c720ad2ebca7b80b9e1daf23e34cce01977ae`.
