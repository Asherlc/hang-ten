# Metolius Climber's Edge — native CAD provenance

Date: 2026-09-27. Package `metolius-climbers-edge`, board ID
`metolius.climbers-edge`, revision `2026-09-contact-first`. The FreeCAD source is
`Hangboards/metolius-climbers-edge/metolius-climbers-edge.FCStd`. Its embedded
`HangTenBoardManifest` replaces the committed `board.json`. The one-off
authoring script lives only in workspace scratch at
`.context/lumpy-quail/author_climbers_edge.py`. The saved document reopens and
recompiles without that script.

This is a simplified **display model**. It is not recovered manufacturing
geometry or a load-bearing CAD plan. Metolius publishes the overall size
(600 × 160 mm), the six edge depths, the 20° flat slopers and the 40 mm-radius
round sloper. Those facts fix the envelope, every edge region's depth and the
two sloper shapes. The operator read the layout and the end profile by hand
from Metolius's own spec drawing and product photographs. Every other number
is a labeled display estimate below.

The Climber's Edge is screwed to a wall or door header (the installed photo
shows screws through its three rails). It has no cords, suspension, or
attachment nodes, and none are authored. The 2026-09-13 cord audit already
excludes it.

## Sources

Retained primary sources (downloaded 2026-09-27 from Metolius's Shopify
product gallery for <https://www.metoliusclimbing.com/products/climbers-edge-board>):

| Retained file | URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `2026-09-27-metolius-climbers-edge-cad-sources/spec.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/Climber_s-Edge-Spec.jpg?v=1765309719> | `a96263a9b46e148ddc6817f5173494c871e38871d7c02c6b8ce5ba1e98ee38c8` | 600 × 160 mm; front outline and end taper; rail and row heights; all eight segment boundaries; jug / flat-sloper / round-sloper X extents and top heights; the depth-to-position map (1 = 10, 2 = 7.5, 3 = 15, 4 = 12.5, 5 = 20, 6 = 17.5 mm). The same bytes as the `CE-DIAGRAM` evidence of 2026-09-15. |
| `2026-09-27-metolius-climbers-edge-cad-sources/end-profile.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/climbers-edge-board---side.jpg?v=1789409411> | `6bb2b788467b5799a6b215077c4871736aeb1b1504fa3e0f39fa116384005da9` | End-grain section at the 20 / 17.5 mm end: rail fronts, ledge heights, scoop floors, the curved scoop tops, the jug top; the curved step lines where one scoop depth meets the next |
| `2026-09-27-metolius-climbers-edge-cad-sources/front.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/climbers-edge-board-front.jpg?v=1789409411> | `1e4074868adc80a87cd39b1bfa0457e04eccd6ba3b27d68d2928ffc1477d10dd` | Straight-on photo: engraved labels 20 / 15 / 10 mm (middle rail) and 17.5 / 12.5 / 7.5 mm (bottom rail), matching the drawing; the rails shorten toward the bottom (real taper, not drawing perspective) |
| `2026-09-27-metolius-climbers-edge-cad-sources/top.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/climbers-edge-board---top.jpg?v=1789409411> | `abaf61b345e6d2cb49fa829740090ad7058751b5baa44579da792bb6c52aacd8` | Round sloper spanning the full depth; recessed flat slopers with curved end walls; rail taper |
| `2026-09-27-metolius-climbers-edge-cad-sources/close-up.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/climbers-edge-board-close-up.jpg?v=1789409411> | `1c12bd651f08c14f692b28b05ac2a0af1107d25606cf8759d56d633cefd7d923` | Step between segments running up the scoop and fading at the top; rounded rail edges |

The product page publishes "23.6"x 6.3" (300 mm x 160 mm)", the edge depths
"7.5 mm, 10 mm, 12.5 mm, 15 mm, 17.5 mm, and 20 mm", "40 mm radius round
sloper", "20-degree flat sloper" and "Jugs". The Gripped review
(<https://gripped.com/gear/a-look-at-the-new-metolius-climbers-edge-hangboard/>,
secondary) repeats 60 × 16 cm and the same holds. No source found publishes
the board's thickness.

The superseded Git asset (LFS object
`19c0d57881561f8c5a8a28af79148253137bc9135828f9e8ac1308a6c3ea4b32`, imported
from a user-supplied GLB on 2026-09-15, see
`2026-09-15-hangboard-collection-model-imports.md`) was a visual cross-check
only, never a compiler input or geometry source.

## Conflicts recorded

1. **Product page width: "300 mm" vs 23.6 in.** The product page prints
   "23.6"x 6.3" (300 mm x 160 mm)". 23.6 in is 600 mm, and the spec drawing
   and Gripped both say 600 mm / 60 cm. 600 mm is used.
2. **The superseded mesh contradicts the end-grain photo.** It had rail fronts
   at 55 / 47 / 41 mm, a groove floor 27 mm in front of the back for the
   20 mm edge, square-stepped grooves, and a rectangular outline. The end-grain
   photo instead shows:
   - rail fronts in the proportion ≈ 48 : 31 : 28.5;
   - curved scoops whose deepest floors sit ≈ 11 mm in front of the back in
     **both** rows;
   - a jug rail with a flat top.

   The spec drawing shows tapered ends. The source follows Metolius's images.
3. **Thickness is unpublished.** Depths were read from the end-grain photo at
   the 20 mm and 17.5 mm ledges. At 10.8 px/mm (horizontal image scale), the
   20 mm ledge reads 20 mm and the 17.5 mm ledge reads 18.5 mm, so the scale is
   good to ±5 %. Rail fronts are **display estimates**: jug 48, middle 31,
   bottom 28.5 mm. Those give floors at 11 / 16 / 21 mm for both rows' deep /
   middle / shallow edges. The same floor depths in both rows is consistent
   with one set of router depths.
4. **Spec drawing perspective.** The drawing is a slightly downward-pitched
   perspective render. Its dimension lines are schematic: they are offset
   from the drawn board by up to 11 mm. The board silhouette itself is
   isotropic at 3.0 px/mm: 1802 px across 600 mm and 480 px across 160 mm.
   Heights and X positions were read in that frame (origin (1137.5, 1248) px).
   Readings are good to about 1–2 mm, and both halves agree to within 1 mm.
   The outer segment boundaries lean about 4.5 mm over each row in the
   drawing, as a pitched camera predicts. They are authored vertical at their
   mean X. The overlay
   (`docs/pr-screenshots/metolius-climbers-edge/cad-over-manufacturer-spec.png`)
   shows the modelled end up to about 3 mm outboard of the drawn end between
   Z 90 and 124.
5. **End run-outs.** The straight-on photo shows each groove's end as a
   concave run-out between rails. The drawing and the end-grain photo show
   one planar end cut. The single slanted end plane of the drawing is used.
   The run-outs are omitted.

## Measurement frame

Native coordinates are millimetres: +X right, +Z up, front −Y, back plane
Y = 0, bottom Z = 0. The board spans X ±300 and Z 0–160 (published), and Y 0
to −48 (display estimate). Below, *f* = −Y is the distance in front of the
back plane.

The operator read every point by eye off gridded, contrast-stretched crops
(`Tools/HangboardCAD/photo_grid.py crop`). The end-grain photo was rotated and
rescaled into an (f, Z) frame for this. No image was segmented, traced,
vectorized, fitted, registered, or used as an automatic geometry input.

## CAD construction and field mapping

- **Sections** (`Sketcher::SketchObject`, blocked; extruded along X, fused,
  refine off):
  - **Rails, shared by all sections.** The back plane and the bottom.
    - Bottom rail front at f 28.5 with an R3 bottom-front round.
    - Middle rail front at f 31.
    - Jug rail front at f 48.
    - Back-bottom R2 and back-top R3 corners.
  - **Jug section** (outboard of the jug wall): a flat top at Z 151 (drawing)
    with an R12 front round-over (display estimate).
  - **Flat-sloper section** (|X| 100–215): the published 20° plane from the
    back top (Z 151) down to f 48 (Z 133.53), with an R5 front round-over
    (display estimate).
  - **Round-sloper section** (|X| ≤ 104.5): the published R40 arc. Its top is
    at the published 160 mm. It meets the jug-rail front at Z 126.5, which puts
    the arc centre at f 8.53, Z 120.
  - **Jug wall.** Each jug section is clipped by a front-view `Part::Common`
    to the drawn wall. The wall slants from (|X| 203, Z 151) to
    (|X| 190, Z 127).
  - **Round-sloper shoulders.** The round sloper is clipped by a front-view
    profile with R16 shoulders (display estimate). This gives a plateau to
    |X| 94.1 and a base at |X| 104.5 (drawing: plateau to 89–90, base 104).
- **Front outline**: a `Part::Common` with the drawn taper:
  - |X| 270 at Z 0, 286.2 at Z 80, and 300 at Z 124–133;
  - R5 bottom corners and R19 top corners (read from the drawing; the radii
    are display estimates).
- **Edges**: 10 section cutters, one per segment, fused with one
  `Part::MultiFuse` and removed with one `Part::Cut` (refine off). Each cutter
  profile is:
  - an R3 ledge round-over;
  - the ledge, at Z 80.6 for the upper row (under the jug rail) and Z 24.5 for
    the lower row;
  - an R3 floor fillet;
  - the vertical floor at f = rail front − published depth, up to Z 103
    (upper) or 41.3 (lower);
  - a cubic B-spline scoop, tangent to the floor, ending horizontally at the
    rail above (jug underside Z 122.8, middle-rail underside Z 56.3);
  - an R3 round-over onto that rail's front.

  Every segment's scoop ends at the same point, so the step between adjacent
  depths tapers to nothing at the top of the scoop. The close-up and end-grain
  photos show the same. The scoop control points and all Z levels are display
  estimates from the end-grain photo, scaled so that the jug top matches the
  drawing's Z 151.
- **Regions**: each contact is a `Part::Feature` holding exact copies of the
  final body's faces:
  - an edge owns its ledge, round-over and floor fillet, inside its segment;
  - a jug owns its flat top, front round-over, back round and outline corner
    round;
  - a flat sloper owns its 20° face and rounds;
  - the round sloper owns its R40 face, plateau, back round and shoulders.

  Step faces, end faces, walls, floors and rail fronts stay on the body. Each
  contact carries a CAD-authored `HangTenHoldOutline`. The document sets
  `HangTenCurvedRegionPartition` and `HangTenSurfaceNormals`. The face copies
  are static: after a geometry edit, re-run the classification.

Edge segments (X read from the drawing; depth published; each region's Y extent
equals it exactly):

| Contact ID → node | Row (ledge Z) | X (mm) | Floor f | Published depth |
| --- | --- | --- | --- | --- |
| `edge-20-left` → `edge_20_left_001` | upper (80.6) | end to −191 | 11 | 20 |
| `edge-15-left` → `edge_15_left_001` | upper | −191 to −96.5 | 16 | 15 |
| `edge-10-center` → `edge_10_center_001` | upper | −96.5 to 96.5 | 21 | 10 |
| `edge-15-right` → `edge_15_right_001` | upper | 96.5 to 191 | 16 | 15 |
| `edge-20-right` → `edge_20_right_001` | upper | 191 to end | 11 | 20 |
| `edge-17-5-left` → `edge_17_5_left_001` | lower (24.5) | end to −184 | 11 | 17.5 |
| `edge-12-5-left` → `edge_12_5_left_001` | lower | −184 to −92.5 | 16 | 12.5 |
| `edge-7-5-center` → `edge_7_5_center_001` | lower | −92.5 to 92.5 | 21 | 7.5 |
| `edge-12-5-right` → `edge_12_5_right_001` | lower | 92.5 to 184 | 16 | 12.5 |
| `edge-17-5-right` → `edge_17_5_right_001` | lower | 184 to end | 11 | 17.5 |
| `jug-left` / `jug-right` → `jug_left/right_001` | top, Z 139–151 | end to ∓203 | — | — (none published) |
| `flat-sloper-left` / `-right` → `flat_sloper_left/right_001` | top | ∓104.5 to ∓203 | — | — (20° published) |
| `round-sloper-center` → `round_sloper_center_001` | top, Z 126.5–160 | ±104.5 | — | — (R40 published) |

The mapping of depths to positions comes from the drawing's legend and the
engraved labels. Both agree with the existing contact names.

Omitted on purpose:
- the eight mounting screws and their counterbores, as in the superseded
  asset (see `2026-09-22-mounting-bore-removal.md`);
- the engraved labels and wordmark;
- the groove-end run-outs (conflict 5);
- the lean of the outer segment boundaries (conflict 4);
- router radii at the step corners.

## Manifest change

None. The embedded manifest generates a `board.json` byte-identical to the
deleted one. The model presentation `aspectRatio` stays 3.75, which is exactly
the new descriptor's `modelBounds` x/y ratio (600 × 160 mm). All 15 contact
IDs and 16 node IDs, and their pairing, are unchanged.

## Verification

- `compile_board.py`: native-source and 15-contact gates passed. The
  published-depth gate was exact for all 10 edges. The asset is 17,312
  triangles. The descriptor was derived from the reopened USDZ.
- `verify_reproducible.py --package metolius-climbers-edge`: byte-identical
  on the pinned toolchain (FreeCAD 1.1.3, OCCT 7.8.1, usd-core 26.8).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed. `scripts/verify-model-delivery.py` verified the refreshed lock.
- The superseded Blender verifier `Tools/HangboardModels/verify_metolius_climbers_edge.py`
  and its test were retired. They hash-checked the imported mesh's bore caps,
  which no longer exist.
- iOS: a workspace-owned iPhone 17 Pro simulator (iOS 26.5) ran the DEBUG
  board-detail route. It loaded the model with `jug-left` selected by default.
  Deep links then selected each of these, each confirmed via
  `boardDetail.selectedHold.<contactID>`:
  - `edge-20-left`, `edge-15-left`, `edge-7-5-center`, `edge-12-5-right`:
    only that segment's ledge highlighted, with its published depth;
  - `flat-sloper-right`, `round-sloper-center` and `jug-right`: only that top
    region highlighted.

  The simulator was deleted after the run.

| Review view | Previous asset | Native CAD |
| --- | --- | --- |
| Front | [previous](../pr-screenshots/metolius-climbers-edge/previous-front.png) | [CAD](../pr-screenshots/metolius-climbers-edge/cad-front.png) |
| Side | [previous](../pr-screenshots/metolius-climbers-edge/previous-side.png) | [CAD](../pr-screenshots/metolius-climbers-edge/cad-side.png) |
| Top | [previous](../pr-screenshots/metolius-climbers-edge/previous-top.png) | [CAD](../pr-screenshots/metolius-climbers-edge/cad-top.png) |
| Oblique | [previous](../pr-screenshots/metolius-climbers-edge/previous-oblique.png) | [CAD](../pr-screenshots/metolius-climbers-edge/cad-oblique.png) |

The views are OpenUSD `usdrecord` (Hydra Storm) renders, not SceneKit output.
The review copy drops any `material:binding`. The committed bytes were never
modified. App screenshots are in `docs/pr-screenshots/metolius-climbers-edge/app-*.png`.

`compare_exports` was not used as evidence, because the superseded mesh
contradicts the photographed profile (conflict 2).

Final source SHA-256:
`02943657a02d83c59daf75ed473e2f841cd7a07003e907cb04a5eecf8dcb9239`.
Compiled USDZ SHA-256:
`4de00eb9e9d60dd70fbcbd0f1e9cd141c09b74470dbb72755847ac1a333fd341`.
Descriptor SHA-256:
`3cd49d64e8c8dc5bbd8d5f3fefdf784f24ea1e444de2c4276fa0f1af5fb0efce`.
