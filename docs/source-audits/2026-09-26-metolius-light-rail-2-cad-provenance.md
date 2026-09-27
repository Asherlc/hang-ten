# Metolius Light Rail 2.0 — native CAD provenance

Date: 2026-09-26. Package `Hangboards/metolius-light-rail-2`, board ID
`metolius.light-rail-2`, revision `2026-09-contact-first` (unchanged).

The board now has a native FreeCAD source,
`Hangboards/metolius-light-rail-2/metolius-light-rail-2.FCStd`, compiled by the
shared `Tools/HangboardCAD/compile_board.py` into `assets/primary.usdz` and
`assets/primary.model.json`. The hand-authored `board.json` was embedded as the
FCStd's `HangTenBoardManifest` (the generated file is byte-identical to it),
deleted, and added to `.gitignore`. No board metadata changed: IDs, names,
depths, positions, suspension, cord routes and cameras are the same bytes.

The document was created by a throwaway script
(`.context/electric-pig/author_light_rail_2.py`, workspace scratch, not
committed). The saved FCStd stands alone.

The result is a **measured display simplification**. It is not recovered
manufacturing geometry, and nothing here supports a product-accuracy or
load-bearing claim.

## Sources

| Source | URL / location | SHA-256 | Supports |
| --- | --- | --- | --- |
| Manufacturer product page (LR1) | <https://www.metoliusclimbing.com/products/light-rail> (re-read 2026-09-26) | page text, not archived | Identity "Light Rail 2.0"; "Size: 18" x 3" x 1.5" (45.7 cm x 7.6 cm x 3.8 cm)"; 0.54 kg; "Edges Depth: 15mm (0.71"), 20mm (0.79 in") and 40mm (1.57 in")"; reversible, four holds |
| Manufacturer front photo (LR2) | `Light-Rail-2-PT.jpg`, retained at `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/` | `7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272` | One long pocket with rounded ends and a stepped floor; engraved labels 40 / 20 (upright) and 15 / 40 (inverted); outline corner radius; two top cord entries |
| Field photo (Treeline, independent) | `metolius-light-rail-1.jpg`, same directory | `93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a` | Same pocket, stepped floor and labels on a second specimen |
| Pre-migration display mesh | `Hangboards/metolius-light-rail-2/assets/primary.usdz` at `94d48974e`, resolved with `Tools/HangboardCAD/reference.py` | `6fc0c73bfcd0a22d94a733fa7f8b482730a2423d4eec139539d92229ec64a598` | The approved analytic display estimate (Batch 04 task 9) whose numbers the source reuses, except the outline corner |

The earlier source register
(`…/evidence/metolius-light-rail-2-0/source-register.json`) already records
two conflicts, and this migration keeps its rulings:

- **40 mm jugs on a 38 mm rail.** Keep the published 1.5 in (shipped as 38 mm)
  thickness and treat 40 mm as the manufacturer's nominal grip depth. Neither the
  board nor the label is changed. See "Compiler changes" for how the depth gate
  handles it.
- **REI lists 40 / 26 / 19 / 15 mm.** The manufacturer page and both photos show
  40 / 20 / 40 / 15; no 26 mm contact is invented.
- **"15mm (0.71")"** on the manufacturer page is arithmetically inconsistent;
  the metric 15 mm (engraved on the board) is used.

## Geometry

Native frame: millimetres, +X right, +Z up, front −Y. The body is centred on
the origin.

| Feature | Authored value | Status |
| --- | --- | --- |
| Envelope | 457 × 76 × 38 mm | **Published** 18 × 3 × 1.5 in, as already shipped (the previous asset and descriptor used 457 × 76 × 38) |
| Outline corner radius (front view) | r 6 | **Display estimate.** The 1 mm-gridded crops of LR2 (`photo_grid.py`, 4.21 px/mm from the 457 mm length, origin at the board centre) read a silhouette corner of about r 5; the reference mesh uses r 6 at mid-thickness. See "Accepted deviation" |
| Perimeter round-over | r 5 fillet on the front and back perimeters (a true fillet, as a router round-over bit cuts it) | Reference value; display estimate |
| Pocket mouth | rounded rectangle x ±205.5, z −21.5 … 15.5, corner r 9 | Reference value (exact on its vertices); matches LR2 in the model-over-photo overlay |
| Pocket walls | six planar stations; inset from the mouth 0 / 1.5 / 2.4 / 2.7 / 3.6 / 4.6 mm (corner radius reduced by the same inset), at 0 / 0.06 / 0.16 / 0.80 / 0.95 / 1.00 of the local depth | Reference values: every reference wall vertex lies on these stations |
| Pocket depth | 20 mm along the lower lip, 15 mm along the upper lip; each station plane is tilted about X between them, and the last one is the sloped floor | **Published** 20 / 15 mm edges; the stepped floor is visible in LR2 and the field photo |
| Cord wells | x ±213 on the top face; r 3.4 at the face narrowing to r 2.8 at 1 mm, cylinder to a flat floor 3 mm deep | Reference values; the board's suspension provenance already calls the 3 mm depth a display estimate, not a blind-hole claim |

Each pocket station is a fully constrained Sketcher rounded rectangle on its
tilted plane, with true circular arcs in that plane. The reference lifted
plan-view circles onto the same planes, which are ellipses in the plane; the
difference is at most r·(1 − 1/√(1 + b²)) < 0.08 mm, where b ≤ 5/37 is the
tilt. The pocket cutter is a ruled `Part::Loft` through a lead station 6 mm in
front of the face and the six stations. The wells are ruled lofts of circle
sketches. One `Part::MultiFuse` of all cutters is cut from the filleted body
(`Refine = False`).

Every sketch is fully constrained (`solve() == 0`, no dependent parameters).

## Holds (contact regions)

Every region is a cap-free parametric surface whose own shape is the exported
mesh; the body is partitioned around it (`HangTenCurvedRegionPartition` set).

| Node | Contact | Region | Measured Y extent |
| --- | --- | --- | --- |
| `lr_top_jug_40_001` | `jug-40-20mm-side` | Top face plus both r 5 round-overs, extruded from a side-section sketch over the straight span x ±222.5, with the two cord wells cut out | 38.000 mm (full depth) |
| `lr_recess_lower_20_001` | `edge-20` | Ruled loft of each station's straight bottom line (x ±196.5) | 20.000 mm |
| `lr_bottom_jug_40_001` | `jug-40-15mm-side` | Bottom face plus both round-overs over x ±222.5 | 38.000 mm (full depth) |
| `lr_recess_upper_15_001` | `edge-15` | Ruled loft of each station's straight top line | 15.000 mm |
| `left_upper_entry_001`, `right_upper_entry_001` | attachments | Well wall (ruled loft) and floor (`Part::Face`), each reversed where needed so it faces out of the body | — |

Node IDs and roles are unchanged from the previous asset. The jug span x ±222.5
equals the previous jug nodes' span. The lip regions end where the straight
wall ends (x ±196.5); the previous lip nodes ran to x ±198.44, into the corner
arc. The authoring script asserts that every region face points out of the
body.

## Compiler changes

Two changes to the shared `Tools/HangboardCAD/compile_board.py`, both covered
by `verify_reproducible.py` (all 16 CAD boards rebuild byte-identically):

1. **Published depth deeper than the board.** `_validate_published_depths` now
   takes the body's depth extent. When a published depth exceeds it, the region
   must span the full body depth instead. Every other region is gated exactly
   as before. Unit tests are in `Tools/HangboardCAD/tests/test_compile_v2_depths.py`.
2. **`HangTenSurfaceNormals` (opt-in).** The default crease-angle averaging
   tilts the normal where a long planar triangle meets a tangent fillet's small
   ones, and shaded a visible band across the flat front face near each end. With
   the flag, each triangle is shaded with the analytic normal of the B-rep face
   it tessellates. See "Surface normals" in `Tools/HangboardCAD/README.md`.
   Only this source sets it.

## Accepted deviation

`compare_exports.py` against the reference: two-way sampled worst **0.554 mm**
(limit 0.5 mm; 2,492 reference vs 16,586 candidate triangles; 99th percentile
0.51 / 0.54 mm). Every sample over 0.5 mm lies on the eight corner round-overs.
There, the reference sweeps a constant r 6 corner through its round-over, so its
front face keeps an r 6 corner. A round-over bit cannot cut that. The source is
a true r 5 fillet of an r 6 outline, so its front-face corner is r 1. The
pocket, lips, jugs and wells agree to within 0.5 mm. As the migration guide
says, this is evidence, not a gate; do not re-tune the model against it.

A first build used an r 11 outline, read from the reference's front face; that
gave a 2.07 mm deviation at the silhouette corners, and the manufacturer photo
shows a much tighter corner.

The round-over's toroidal corner faces tessellate densely (the body has 14,290
triangles; the asset is 377 KB, up from 118 KB).

## Simplifications (not modelled)

- Engraving (logos and depth labels).
- Wood grain and any finish. The asset ships unbound meshes per the model
  material policy.
- The cord's interior path. As before, only the two top entries are modelled.

## Verification

- `compile_board.py`: reopen and recompute clean, source bytes unchanged,
  published-depth gate passed (20.000 / 15.000 mm, jugs 38.000 mm full depth);
  7 nodes, 16,586 triangles.
- `verify_reproducible.py`: all 16 source-backed boards, including this one,
  rebuild byte-identically on the pinned toolchain (FreeCAD 1.1.3, OCCT 7.8.1,
  macOS arm64).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passes; `board_manifest.py --package metolius-light-rail-2` is byte-identical
  to the previous `board.json`.
- Review renders:
  [`2026-09-26-metolius-light-rail-2-cad-preview.png`](2026-09-26-metolius-light-rail-2-cad-preview.png)
  shows `preview.py` front / side / top and `usdrecord` (Hydra Storm) oblique
  views with each hold tinted, next to the prior committed asset. The
  model-over-photo overlay (`photo_grid.py overlay`) aligns the outline, the
  corners and the pocket mouth with LR2.
- In the app (iPhone 17 Pro simulator, iOS 26.5, DEBUG board-detail route): the
  board loads its 3D model with `boardModel.contact.*` for all four contacts.
  Selecting each hold from the hold map confirmed
  `boardDetail.selectedHold.<contactID>` and the published kind and depth. The
  highlight lands on the top jug and the pocket's lower lip upright, and on the
  flipped jug and lip in the inverted `15mm-side` pose. Screenshots:
  `docs/pr-screenshots/metolius-light-rail-2/`.
