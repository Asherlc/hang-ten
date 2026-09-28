# Frictitious Megalith — native CAD provenance

Date: 2026-09-28. Package `frictitious-megalith`, board ID
`frictitious.megalith`, revision `2026-09-contact-first`. The FreeCAD source is
`Hangboards/frictitious-megalith/frictitious-megalith.FCStd`. Its embedded
`HangTenBoardManifest` replaces the committed `board.json`. The one-off
authoring script lives only in workspace scratch at
`.context/megalith/author_megalith.py`. The saved document reopens and
recompiles without that script.

This is a simplified **display model**. It is not recovered manufacturing
geometry or a load-bearing CAD plan. Frictitious publishes the overall size
(26.75 × 6.5 × 2.25 in = 679.45 × 165.1 × 57.15 mm), the shoulder-width edge
depths (40, 30, 20, 15, 12, 10 and 8 mm), the two-finger pocket on the 40 mm
edge, mono pockets, the 25 mm single-hand center hold, and the full-width
pull-up-bar jug. Those facts fix the envelope, the jug thickness, every edge
region's depth and the center hold's depth. The operator read the layout by
hand from Frictitious's straight-on front photograph and the tier section from
its end-grain photograph. Every other number is a labeled display estimate.

The Megalith is screwed to a wall or to the Frictitious Doorway Mount (the box
ships "6 screws"). It has no cords, suspension, or attachment nodes, and none
are authored. The 2026-09-13 cord audit already excludes it
(`noDocumentedSuspension`, user-approved 2026-09-20).

## Sources

Retained primary sources (downloaded 2026-09-28 from the Shopify product
gallery of <https://frictitiousclimbing.com/products/megalith>):

| Retained file | URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `2026-09-28-frictitious-megalith-cad-sources/front.jpg` | <https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front.jpg?v=1780436232> | `93d9089def4eaf45b58e9805540fbef2c7fb5fe84b278d4a03143a0243c9ef19` | Straight-on front: outline of the three tiers, center recess and bottom notch; every groove end, depth step and pocket lip; mono and center-hold positions; engraved labels 8 / 10 / 12, 30 / 40, 15 / 20 on the left half. The same bytes as the cord audit's M2 evidence. |
| `2026-09-28-frictitious-megalith-cad-sources/end-profile.jpg` | <https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front-1.jpg?v=1780436232> | `a524a3e675f760c8ecf1b206c754800112115ce9e063c745bc083e8a1573cd35` | End-grain section: tier fronts, the rear wrap notch behind the jug, jug top rounds, tier lower rounds. |
| `2026-09-28-frictitious-megalith-cad-sources/close-up.jpg` | <https://frictitiousclimbing.com/cdn/shop/files/Mega-4.jpg?v=1764914587> | `2fbe9fd9b3fe894e64223f27123744ab8303cbf8b930831d55991fde70542062` | Right half: rounded depth steps in the top groove, the raised lip and drawn outline of the two-finger pocket on the 40 mm edge, the mono and its neighboring screw hole. |
| `2026-09-28-frictitious-megalith-cad-sources/installed.jpg` | <https://frictitiousclimbing.com/cdn/shop/files/Mega_25791a01-108b-4b32-b931-aa2fa89df75a.jpg?v=1764914587> | `e85e216467185a32e8a31bd92562eb685673bbb22c72fa3c25a6952ecfe17648` | Installed view corroborating the layout and that both halves use the same left-to-right order. |
| `2026-09-28-frictitious-megalith-cad-sources/in-use.jpg` | <https://frictitiousclimbing.com/cdn/shop/files/Mega-2.jpg?v=1764914587> | `609d854bdd32fcac61e5bd5d98b75a27a69d3f83d08b667532612829a0bfae98` | Pull-up use of the full-width jug; the right end's three stacked tiers. |

The product page (retained as the cord audit's M1 snapshot,
`2026-09-13-model-cord-snapshots/frictitious.megalith-M1-2026-09-20.html`,
re-read 2026-09-28) publishes "Shoulder-Width Edges: 40mm, 30mm, 20mm, 15mm,
12mm, 10mm, 8mm", "2 finger pocket on 40mm edge", "Mono pockets", "25mm
single-hand center hold", "Full width pullup bar-style jug", "Size: 26.75”
wide, 6.5” tall, 2.25” thick" and "poplar wood". It also calls the center hold
"slightly incut". No source publishes pocket or mono depths, tier
thicknesses, or radii.

The superseded Git asset (LFS object
`f88f4c9cf989af88230b8c0937bfb37ef656e0d3df142b7377e11638363d904f`, a
generator-built delivery mesh prepared in
`2026-09-20-hangboards-batch-05-migration/native/FRICTITIOUS.md`) was a visual
cross-check only, never a compiler input or geometry source.

## Conflicts recorded

1. **The board is not mirror-symmetric; the superseded mesh was.** On both
   halves of the front photo the stepped edges deepen left to right: the
   rounded ends of the deeper steps all face left, and the left half's engraved
   labels read 8 → 10 → 12, 30 → 40 and 15 → 20. On each half the mono and its
   screw hole sit right of the 15 / 20 groove, and the pocket lip sits in the
   right part of the 40 mm edge. So the right half repeats the left half's
   order: the right mono is at the outer end, the right 12 mm and 40 mm edges
   are outboard, and the right 15 mm edge is inboard. The superseded mesh
   mirrored the right half. The source follows the photo. Contact IDs keep
   their meaning ("left" / "right" = the half), and no contact name asserts
   inner or outer, so no metadata change is needed.
   `Tools/HangboardPackages/tests/test_frictitious_model_migration.py` no
   longer asserts mirrored Megalith X bounds (it keeps the check for the
   DoorMount). It now asserts the photographed order instead.
2. **Tier thicknesses.** The superseded mesh used tier fronts of 37 / 52 /
   57.15 mm. The end-grain photo reads 26.6 / 50.8 / 57.25 mm (bottom /
   middle / jug) at 6.74 px/mm, taken from the published 165.1 mm height
   (1113 px). The jug front agrees with the published 2.25 in to 0.1 mm, so
   57.15 mm is used for it. The others are display estimates: middle 51,
   bottom 26.6. The photo also shows a notch behind the jug top (16.6 mm deep,
   from Z 139.3 to the top) that gives the pull-up-bar wrap. The superseded
   mesh did not have it.
3. **Front-photo scale.** The board spans 1279 px across 679.45 mm
   (1.8824 px/mm) and 306 px across 165.1 mm (1.8535 px/mm). That is 1.5 %
   anisotropy, from camera pitch or published rounding. X readings use the
   horizontal scale and Z readings the vertical, both from origin (719.5, 826)
   px (board center, bottom). Readings are good to about ±1 mm. The overlay
   (`docs/pr-screenshots/frictitious-megalith/cad-over-manufacturer-front.png`)
   uses one mean scale, 1.868 px/mm.
4. **Small left / right reading differences.** The monos read at Z 28.6 and
   28.9 mm; both are authored at 28.75. The bottom tier ends read −325.4 and
   +329.1 mm; both are authored at ±327.2. Groove and step X positions are
   authored as read for each half, because the halves are not mirror images.
5. **"Slightly incut" center hold.** No angle is published and the photos
   cannot resolve one, so the center hold's top is authored flat.

## Measurement frame

Native coordinates are millimetres: +X right, +Z up, front −Y, back plane
Y = 0, bottom Z = 0. The board spans X ±339.725 and Z 0–165.1 (published),
and Y 0 to −57.15 (published thickness). Below, *f* = −Y is the distance in
front of the back plane.

The operator read every point by eye off pixel-gridded, contrast-stretched
crops (a throwaway reader equivalent to `Tools/HangboardCAD/photo_grid.py
crop`). No image was segmented, traced, vectorized, fitted, registered, or used
as an automatic geometry input.

## CAD construction and field mapping

- **Tiers.** Each tier is an (f, Z) section extruded along X, clipped by a
  front-view `common` with its drawn outline. The tiers are fused, then
  refined.
  - **Jug tier**, Z 109–165.1:
    - front at f 57.15 (published), with an R10 top-front round and an R5
      lower-front round;
    - back at f 16.6 from Z 139.3 up, with an R4.5 top-back round: the wrap
      notch;
    - outline corners R19 (top) and R8 (bottom);
    - its underside rises to Z 115.5 over the center recess (X ±71), with R8
      corners.
  - **Middle tier halves**, X from ±71 out to the board ends:
    - front at f 51, with an R5 lower-front round;
    - underside at Z 51.5, rising to Z 55.5 right of X −145.8 on the left half
      and right of X +270.7 on the right half (the photographed 4 mm step);
    - lower corners R18 (outer) and R6 (inner).
  - **Bottom tier and center panel**, front at f 26.6 with an R2
    lower-front round:
    - the tier spans X ±327.2, with R17.5 lower corners;
    - the center panel spans X ±71 up to the jug;
    - the bottom notch is X ±68.5 up to Z 33.5, with R10 top corners.
  - **Center hold**: X ±45.7, Z 52.3–82.0, front-view corners R6. Its front is
    at f 51.6, exactly 25 mm (published) in front of the panel. It has R4
    top-front and bottom-front rounds.
- **Grooves.** Each edge is its own section cutter, extruded along X and
  clipped by a front-view region prism. The cutters are fused with one
  `multiFuse` and removed with one `cut` (no refine), so the faces split where
  one depth steps to the next. Each cutter section has:
  - an R2.5 ledge-lip round-over (R2 on the bottom tier);
  - the flat ledge;
  - an R3 floor fillet;
  - a vertical back wall at f = tier front − published depth;
  - an R3 roof fillet and an R2.5 roof-lip round-over.

  Each region's Y extent therefore equals its published depth exactly. The
  front-view regions reproduce the photographed rounded groove ends and
  rounded depth steps (R10, each step convex toward its shallower side). Each
  step arc starts 3 mm below the ledge so that no step surface is tangent to
  the ledge plane.
- **Two-finger pockets.** Within each 40 mm edge, a 42 mm span is its own
  cutter. Its ledge carries a raised lip at the front: 5 mm tall (read) and
  8 mm deep (display estimate). The floor behind the lip is at the ledge
  level and the back wall is at the 40 mm depth. **No pocket depth is
  asserted**, and none is published. The black outline drawn on the product
  is omitted.
- **Monos.** Elliptical openings, 19.7 × 22.4 mm (read). The mouth has a
  1.5 mm chamfer. They are blind, 18 mm deep (display estimate; no depth is
  published; the bottom tier is 26.6 mm thick).
- **Regions.** Each contact is a `Part::Feature` holding exact copies of the
  final body's faces:
  - an edge owns its ledge, lip round-over and floor fillet (the up-facing
    faces of its own cutter);
  - a two-finger pocket owns its lip top, lip round-over, lip back, floor and
    floor fillet;
  - a mono owns its chamfer, wall and floor;
  - the center hold owns its top and top-front round;
  - the jug owns its top, both top rounds and the wrap face behind it.

  Step faces, end walls, back walls, roofs and tier fronts stay on the body.
  Each contact carries a CAD-authored `HangTenHoldOutline`: the segment's
  window from the lip round-over to the roof. The 40 mm windows are notched
  around the pocket windows, so the outlines do not overlap. The document
  sets `HangTenCurvedRegionPartition` and `HangTenSurfaceNormals`. The face
  copies are static: after a geometry edit, re-run the classification.

Edge segments. The X value is the vertical part of each segment's rounded left
end or step, read from the front photo. Depths are published; each region's
Y extent equals its depth exactly.

| Contact ID → node | Tier (ledge Z) | X start → end (mm) | Published depth |
| --- | --- | --- | --- |
| `edge-8-left` → `hold__left_edge_8_001` | jug (122.7) | −324.6 → −225.1 | 8 |
| `edge-10-left` → `hold__left_edge_10_001` | jug | −225.1 → −128.8 | 10 |
| `edge-12-left` → `hold__left_edge_12_001` | jug | −128.8 → −34.3 | 12 |
| `edge-8-right` → `hold__right_edge_8_001` | jug | 37.5 → 135.1 | 8 |
| `edge-10-right` → `hold__right_edge_10_001` | jug | 135.1 → 229.7 | 10 |
| `edge-12-right` → `hold__right_edge_12_001` | jug | 229.7 → 326.5 | 12 |
| `edge-30-left` → `hold__left_edge_30_001` | middle (73.9) | −314.8 → −227.7 | 30 |
| `edge-40-pocket-left` → `hold__left_edge_40_001` | middle | −227.7 → −93.4, minus the pocket | 40 |
| `pocket-2finger-left` → `hold__left_pocket_2finger_001` | middle | −160.6 → −118.6 | — (none published) |
| `edge-30-right` → `hold__right_edge_30_001` | middle | 96.9 → 169.7 | 30 |
| `edge-40-pocket-right` → `hold__right_edge_40_001` | middle | 169.7 → 320.0, minus the pocket | 40 |
| `pocket-2finger-right` → `hold__right_pocket_2finger_001` | middle | 233.8 → 275.8 | — (none published) |
| `edge-15-left` → `hold__left_edge_15_001` | bottom (21.6) | −308.6 → −223.4 | 15 |
| `edge-20-left` → `hold__left_edge_20_001` | bottom | −223.4 → −144.8 | 20 |
| `edge-15-right` → `hold__right_edge_15_ownership_001` | bottom | 98.7 → 174.2 | 15 |
| `edge-20-right` → `hold__right_edge_20_ownership_001` | bottom | 174.2 → 260.8 | 20 |
| `mono-left` / `mono-right` → `hold__left/right_mono_001` | bottom | centers −108.5 / 289.5, Z 28.75 | — (none published) |
| `center-edge-25` → `hold__center_edge_25_001` | center | ±45.7, top Z 82.0 | 25 |
| `top-jug` → `hold__jug_001` | top | full width | — (none published) |

Groove roofs are at Z 149.7 (jug tier), 102.5 (middle) and 48.7 (bottom).
The engraved labels on the left half map depths to positions. The right half
has no labels; its depths follow the photographed step directions (conflict 1).

Omitted on purpose:
- the six screw openings (center panel, the 30 mm grooves' back walls, and
  beside each mono), as in the superseded asset (see
  `2026-09-22-mounting-bore-removal.md`);
- the logo, the engraved labels and the drawn pocket outlines;
- round-overs on the tier end faces (the front-view clip leaves them square);
- the sloped ramps at the ends of each pocket lip (authored as vertical steps);
- the center hold's slight incut (conflict 5).

## Manifest change

None. The embedded manifest generates a `board.json` whose parsed values, key
order and number spellings equal the deleted file's. Only the JSON escaping of
the multiplication sign in `dimensions` differs. The model presentation
`aspectRatio` stays 4.115384071192337, which is the new descriptor's
`modelBounds` x/y ratio (679.45 × 165.1 mm). The top-level `aspectRatio` stays
1.5. All 20 contact IDs, all 21 node IDs, and their pairing are unchanged.

## Verification

- `compile_board.py`: native-source and 20-contact gates passed. The
  published-depth gate was exact for all 14 edges and the 25 mm center hold.
  The asset is 16,834 triangles. The descriptor was derived from the reopened
  USDZ.
- `verify_reproducible.py --package frictitious-megalith`: byte-identical on the
  pinned toolchain (FreeCAD 1.1.3, OCCT 7.8.1, usd-core 26.8).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed. `scripts/verify-model-delivery.py` verified the refreshed lock.
- iOS: a workspace-owned iPhone 17 Pro simulator (iOS 26.5) ran the DEBUG
  board-detail route from a current-source Debug build. Deep links selected
  each of these, each confirmed via `boardDetail.selectedHold.<contactID>`:
  - `edge-8-left`, `edge-12-right`, `edge-15-right`, `edge-40-pocket-left`
    and `center-edge-25`: only that ledge highlighted, with its published
    depth. The right 12 mm edge lights at the outer right end and the right
    15 mm edge inboard, as photographed (conflict 1). The left 40 mm edge
    lights on both sides of the pocket.
  - `pocket-2finger-right` and `mono-right`: only that pocket highlighted,
    with finger capacity 2 / 1 and no depth.
  - `top-jug`: the full-width top highlighted.

  A deep link sent while the board was already open did not change the
  selection, so the app was relaunched before each link. The simulator was
  deleted after the run. App screenshots are in
  `docs/pr-screenshots/frictitious-megalith/app-*.png`.

| Review view | Previous asset | Native CAD |
| --- | --- | --- |
| Front | [previous](../pr-screenshots/frictitious-megalith/previous-front.png) | [CAD](../pr-screenshots/frictitious-megalith/cad-front.png) |
| Side | [previous](../pr-screenshots/frictitious-megalith/previous-side.png) | [CAD](../pr-screenshots/frictitious-megalith/cad-side.png) |
| Top | [previous](../pr-screenshots/frictitious-megalith/previous-top.png) | [CAD](../pr-screenshots/frictitious-megalith/cad-top.png) |
| Oblique | [previous](../pr-screenshots/frictitious-megalith/previous-oblique.png) | [CAD](../pr-screenshots/frictitious-megalith/cad-oblique.png) |

The views are OpenUSD `usdrecord` (Hydra Storm) renders from a scratch camera
stage that only references each USDZ. The committed bytes were never
modified. The model-over-photo overlay is
[`cad-over-manufacturer-front.png`](../pr-screenshots/frictitious-megalith/cad-over-manufacturer-front.png).

`compare_exports` was not used as evidence, because the superseded mesh
contradicts the photographed layout and section (conflicts 1 and 2).

Final source SHA-256: `f2c8ed561824139ec2c6aef8fc05eda9a89737e4839897ae2d47ea9f99c76fb8`.
Compiled USDZ SHA-256: `23a2e9078d2351710006cab3752dc57cfa33538499343e09d9d29a1887dbb4f9`.
Descriptor SHA-256: `cfe53835cc918b3250e98630d5e03aff9297049188ce08a4bf24b08913678b27`.
