# Frictitious DoorMount Pro 7 — native CAD provenance

Reviewed 2026-09-27. Package `frictitious-doormount-pro-7`, physical board ID
`frictitious.doormount-pro-7`, revision `2026-09-contact-first`. The native
FreeCAD document contains the geometry and `HangTenBoardManifest`; its
`board.json` is generated at build time. The one-off construction and native
check scripts were kept in workspace-owned `.context` scratch. The saved FCStd
reopens and recompiles independently of them.

This is a simplified display model, not recovered manufacturing geometry or a
load-bearing design. The manufacturer supplies the overall size and labeled
edge depths; unlabelled geometry values below are deliberate display estimates.
The door clamp, rubber pads, engraved text, fasteners, and mounting interface
are omitted from the model. The board is fixed to the DoorMount Pro clamp; no
cord or suspension geometry is part of this package.

## Primary evidence and field mapping

| Retained source (SHA-256) | Exact manufacturer URL | Fields supported |
| --- | --- | --- |
| `2026-09-27-frictitious-doormount-pro-7-cad-sources/front.jpg` (`a67b16b6a84d2aa25c734990e43f56129ace1189a8291b3c4787ae35fd10497d`) | <https://frictitiousclimbing.com/cdn/shop/files/DMP-7-Front_d597f381-f23b-4d16-a5b2-d9d201171fa5.jpg?v=1784063035&width=3840> | Pro 7 front silhouette; left/right symmetry; one full-width upper jug; two 35, two 25, two pocket, and six 20/15/10 labeled selectable areas; hand-read X/Z positions and opening extents. The center clamp is visible but excluded. |
| `2026-09-27-frictitious-doormount-pro-7-cad-sources/in-use.jpg` (`8d38ccf812cb2ea6eaa3a56029e1f554c95ad08e61ea88ad1751d93bb243a59b`) | <https://frictitiousclimbing.com/cdn/shop/files/DMP-In-use.jpg?v=1779384096&width=3840> | Oblique view of the board projecting from the doorway, upper lip and recess depth, and the clamp as a separate mounting part. No measurement was taken from this perspective view. |
| `2026-09-27-frictitious-doormount-pro-7-cad-sources/pockets.jpg` (`e5ce3d81ce8b7567fea0e4ef89b2ac9b94e64f2516c277c8cb6bf1f7cc13186d`) | <https://frictitiousclimbing.com/cdn/shop/files/DMP-Pockets.jpg?v=1779384260&width=3840> | Independent use view corroborating the two smaller pocket regions under the 25 mm areas. It does not establish a fixed finger capacity or a pocket depth. |
| Product page, reviewed 2026-09-27 | <https://frictitiousclimbing.com/products/doormount-pro> | `manufacturer`, `name`, `productURL`, poplar material, published 25.5 × 4.5 × 2.25 in Pro 7 envelope, pull-up jug, pockets, and 35/25/20/15/10 mm edge depths. The page's “seven holds” counts families rather than left/right instances; the existing [contact audit](2026-08-12-evolv-frictitious-board-packages.md) maps its current engraved front to the package's 13 stable contact records. |

The existing `board.json` was embedded without changing any parsed field value.
Thus board ID, presentation ID, revision, all 13 contact IDs, names, kinds,
depth facts, and all 14 importer-visible node IDs keep their prior meanings.
The compiler's published-depth gate measures the ten scalar-depth edge regions
at exactly 35, 25, 20, 15, and 10 mm on their respective sides.

## Manual geometry construction

Native frame: millimetres, +X right, +Z up, front −Y. The published 25.5 ×
4.5 × 2.25 in envelope is 647.7 × 114.3 × 57.15 mm. The rear face is Y = 0;
front is Y = −57.15; bottom is Z = 0. The board outline is a fully constrained
24-segment Sketcher profile extruded across the published thickness, with a
5 mm front-top `Part::Fillet`. The lower wings and center rise are hand-drawn
from the straight-on view. The CAD omits the center clamp; the center rise is
the display interpretation of wood visible on each side of it.

The front photo's board runs approximately X = 64–1545 px and Z = 517–772 px
in its 1729 px square image. I read the feature boundaries manually using the
published 647.7 mm width as scale (about 2.29 px/mm); no image segmentation,
tracing, registration, vectorization, or pixel-generated path entered the CAD.
The photo's height reads about 111.5 mm at this scale versus the published
114.3 mm, so Z positions are rounded display estimates. Mirrored dimensions
were authored once for each pair.

| Stable contacts / nodes | Hand-authored X and Z ranges in mm | Depth basis |
| --- | --- | --- |
| `edge-35-left/right` / `hold__left/right_edge_35_001` | ±207–298; Z 63–94 | Published 35 mm |
| `mixed-25-pocket-left/right` / `hold__left/right_edge_25_001` | ±35–181; Z 76–94 | Published 25 mm |
| `hold-7` / `hold-6` / `hold__left/right_pocket_2finger_001` | ±143–177; Z 57–72 | Unpublished 40 mm display estimate; no capacity is asserted |
| `hold-12` / `hold-13` / `hold__left/right_edge_20_001` | ±192–277; Z 13–43 | Published 20 mm |
| `hold-11` / `hold-8` / `hold__left/right_edge_15_001` | ±110–188; Z 13–43 | Published 15 mm |
| `hold-10` / `hold-9` / `hold__left/right_edge_10_001` | ±36–106; Z 13–43 | Published 10 mm |
| `top-jug` / `hold__jug_001` | X ±307; Z 104–114.3 outline | Full 57.15 mm board thickness; no jug depth is published |

Every cavity is an analytic rounded-rectangle Sketcher section. Three sections
form a ruled solid cutting loft: an opening 1.5 mm wider at the front, an inner
wall 2 mm behind it, and a flat floor at the labeled depth (40 mm for the
unlabeled pockets). The 1.5 mm mouth bevel, corner radii (6–8 mm), top lip
radius (5 mm), and unlabelled 40 mm pocket depth are display estimates read
qualitatively from the manufacturer views. One `Part::MultiFuse` and
`Part::Cut` build the cavity solid. Each selectable contact carries exact
copies of its final body's analytic faces and a hand-authored
`HangTenHoldOutline`; the top jug takes the top plane and its round-over.
The FCStd sets `HangTenCurvedRegionPartition` and `HangTenSurfaceNormals`.
Its fixed face-copy regions require reclassification if the pocket construction
is edited; the reopened, unchanged source passes native validation, but sketch
edit propagation is not claimed for the region copies.

The old display mesh put the 35 mm region at normalized Z 0.517–0.668 and
the lower 20 mm region at 0.084–0.221. The new photo-authored openings occupy
about 0.538–0.836 and 0.101–0.389 respectively, consistent with the
manufacturer's taller cavities. The old model's upper cutouts, lower trough,
and side profile are retained only in the committed before/after review. They
were not used as a geometry input. Its USDZ SHA-256 at main `ca38bd4a1` is
`089f8989ca05e0339e46cc1c6334c21a12409cc2c07c450529934101d664d89b`.
The simplified new model uses individual lower openings where the photograph
shows subtle transitions within a visually continuous row; this is the main
remaining presentation approximation.

## Visual review

The following committed renders compare the actual prior USDZ with the new
compiled USDZ. `preview.py` supplies neutral normal-shaded orthographic views;
Hydra Storm supplies an independent front render, which shows the mouths more
clearly because the flat pocket floors share the front plane's neutral shade.
I inspected all three projections and the Hydra front. The board envelope,
symmetry, opening placement, top roll, and 13 contact footprints are visible.
These are CPU/Hydra review images, not native app screenshots.

| View | Previous asset | Native CAD |
| --- | --- | --- |
| Front | [previous](../pr-screenshots/frictitious-doormount-pro-7/previous-front.png) | [CAD](../pr-screenshots/frictitious-doormount-pro-7/cad-front.png), [Hydra](../pr-screenshots/frictitious-doormount-pro-7/cad-hydra-front.png) |
| Side | [previous](../pr-screenshots/frictitious-doormount-pro-7/previous-side.png) | [CAD](../pr-screenshots/frictitious-doormount-pro-7/cad-side.png) |
| Top | [previous](../pr-screenshots/frictitious-doormount-pro-7/previous-top.png) | [CAD](../pr-screenshots/frictitious-doormount-pro-7/cad-top.png) |

The current-source iPhone 17 Pro simulator (iOS 26.5, DEBUG board-detail
route) also loaded the compiled model. Its [normal board view](../pr-screenshots/frictitious-doormount-pro-7/app-normal.png)
selected `top-jug` by default. A deep link selected
[`edge-35-left`](../pr-screenshots/frictitious-doormount-pro-7/app-edge-35-left.png):
the app's accessibility tree reported `boardDetail.selectedHold.edge-35-left`,
the left 35 mm cavity highlighted, and the detail panel showed 35 mm. The
owned simulator was deleted and its Derived Data removed after capture. A
second simulator build succeeded, but its first `simctl launch` stalled and
was stopped after about a minute; its exact owned simulator was also deleted.
Pocket and shallow-edge native selection remain unreviewed in this PR.

## Verification

The pinned FreeCAD 1.1.3 / OCCT 7.8.1 / OpenUSD 26.08 compiler reopened and
recomputed the source, validated the package, exported unbound meshes, and
derived the descriptor from the exported USDZ. A separate native check reopened
the saved FCStd, checked all Sketcher profiles fully constrained, the solid
and every cutting loft valid, exact board frame and published depths, all 13
region surfaces at zero distance from the final body, and unchanged source
bytes. The remaining package, delivery, reproducibility, and iOS results are
recorded in the PR checks. The pinned toolchain's independent
`verify_reproducible.py` rebuilt the USDZ and descriptor byte-identically;
package validation, delivery-lock verification, Android staging parity, and
the CAD test suite (65 passed, 9 skipped) passed. The focused model tests
passed (20 tests), as did the delivery alignment tests (8 tests). The full
package suite initially found two tests that assumed every package had an
on-disk `board.json`; they were changed to read the FCStd manifest for CAD
packages. The full suite then passed all 718 tests. The current-source iOS
Debug build succeeded and the two app screenshots above were reviewed.

FCStd SHA-256: `e9a070923b099f9ff44f2ea9faf8e4c858a3a1ea7aac56e3e3f0f8f7e58e7333`.
USDZ SHA-256: `eac54ae185cc0d62db3f421ca0c3bb39fdac50d76fc24824a8b24720f3042777`.
Descriptor SHA-256: `e78def2362000903d34a4fa09b8afb3e4ae629bef45dab28d6e68844352d576d`.
