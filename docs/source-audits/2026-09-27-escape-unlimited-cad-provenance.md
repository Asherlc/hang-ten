# Escape Unlimited Board — native CAD provenance

Date: 2026-09-27. Package `escape-unlimited`, board ID `escape.unlimited`,
revision `2026-09-contact-first` (unchanged). The FreeCAD source is
`Hangboards/escape-unlimited/escape-unlimited.FCStd`. Its embedded
`HangTenBoardManifest` replaces the committed `board.json`. The seven contact
IDs and eight node IDs are unchanged. The one-off authoring script lives only in
workspace scratch at
`.context/famed-falcon-dual-cad/author_escape_unlimited.py`, and the saved
document reopens and recompiles without it.

This is a **measured display model**, not recovered manufacturing geometry, and
nothing here supports a product-accuracy or load-bearing claim. This board has
no cord or suspension.

## Sources

All sources are Escape Climbing first-party images listed on the
[product page](https://escapeclimbing.com/products/ec72000) (product JSON
`/products/ec72000.json`, SHA-256
`4ce170744bf9473f3102284961d8e590753272ef3abfff793e0951ba7b7529df`, retrieved
2026-09-27). The SHA-256 values are for the original-resolution downloads. The
retained copies in
[`2026-09-27-escape-unlimited-cad-sources/`](2026-09-27-escape-unlimited-cad-sources/)
are JPEG copies downsized to 1200 px for review.

| Retained copy | Original URL (`cdn.shopify.com/s/files/1/0051/0374/7160/…`) | SHA-256 | Supports |
| --- | --- | --- | --- |
| `front.jpg` | `files/PDP_EC72000_UnlimitedBoard-01.png?v=1690380978` | `a87c2483e07e32212ebdc2e6b3df98a4d7f976fd5a523b2789d83df7562cd41c` | Straight-on front: slot positions, full-round slot ends, tier boundaries, slanted top-tier ends |
| `width-graphic.jpg` | `products/2022_Website_ProductImage_UnlimtedBoardListing_Final-B.png?v=1690380978` | `4c9fb31b8798262cb0f02ebdd6da9f870d3c8a12557d19e41d096d167d283547` | **Published** 23.75 in overall width and 21.75 in grip-surface width |
| `side-profile.jpg` | `products/2022_Website_ProductImage_UnlimtedBoardListing_Final-C.png?v=1690380978` | `983dbbbad041a2704ce1a92d2676bc77ccc129f39466da8d517fe31d7756a0ef` | **Published** 7.25 in height and 1.875 in depth; the end profile (quarter-round top, three stepped tiers) |
| `depth-graphic.jpg` | `products/2022_Website_ProductImage_UnlimtedBoardListing_Final-E.png?v=1690380978` | `9862cab30493bc06bdac15633f0cbd6a76c8ed3c41dc02217c3f7e030d0a106f` | **Published** tier depths 60 / 45 / 20 / 15 mm, each measured from the lip to the back of the hold |
| `oblique.jpg` | `products/PDP_EC72000_UnlimitedBoard-05.png?v=1690380978` | `4075285e9cadc35e7b6715f4a42d11fa3d31cbfbe629ae86533cf8aa380d37a6` | Corroboration only: slot mouths are rounded, and the tiers step back |

The superseded asset at `HEAD` before this change (`0304335e2`) is used only as
a visual cross-check and never as a compiler input. Its values: USDZ
`4d0fde630f301c41d8b3ef8e209a5c3b520df70edc0543afc90d960a44f28d7f`, descriptor
`7a6a17f1d4141b24d85ab7f2b08348acccba3291df2b736e59cccac475d6a696`, and retired
`board.json` `d1566c25419d92a79f82ccc14c88f506a1ff31d1ca14be15a74c06c4bf628b2c`.

### Recorded conflicts

- **Overall dimensions.** The product page text says `Tall: 6”` and
  `Wide: 23.5”`, and the manifest `dimensions` string (`23.5 × 6 in`) quotes it.
  The manufacturer's dimension graphics say 23.75 in overall width, 7.25 in
  height, and 1.875 in depth. The geometry follows the graphics, because they
  are the only source that gives all three axes, and the superseded mesh already
  used them (±301.1 × 183.6 × 47.6 mm). The `dimensions` string was left
  unchanged because it faithfully quotes the page text.
- **Side-profile proportion.** In the side-profile image, the depth-to-height
  ratio is 0.290 (463 / 1599 px), not the 0.259 given by the labels on the same
  image. Profile readings were therefore scaled separately on each axis: depth
  by 47.625 mm / 463 px and height by 184.15 mm / 1599 px.
- **Top sloper depth.** The graphic's 60 mm is measured along the rounded top.
  The body is only 47.625 mm deep, so the compiler's depth gate applies its
  full-body rule: the region spans the whole 47.625 mm Y extent.

## Field mapping

Native frame: millimetres, +X right, +Z up, front −Y, wall at y = 0.

| Field | Value | Basis |
| --- | --- | --- |
| Overall width | 603.25 mm (x ±301.625) | **Published** 23.75 in |
| Grip-surface width | 552.45 mm at the top (x ±276.225) | **Published** 21.75 in; used as the top edge of the slanted top-tier ends |
| Height | 184.15 mm | **Published** 7.25 in |
| Depth / top-tier front | 47.625 mm, y = −47.625 | **Published** 1.875 in |
| Middle-tier front | y = −40.0 | **Measured** from the side profile (x px 1230 → −40.1) |
| Bottom-tier front | y = −27.0 | **Measured** from the side profile (x px 1102 → −26.9). The superseded mesh used about −29 |
| Tier steps | z = 44.5 (bottom/middle), z = 93.5 (middle/top) | **Measured** from the side profile (rows 1590 and 1180). The front image gives 94.4 for the upper step |
| Top quarter-round | r 30 mm; flat top from y = −17.625 to 0 | **Measured** from the side profile: the flat top ends 18.4 mm from the back, and the arc spans 29.2 × 31.4 mm |
| Top-tier ends | Straight slant from x ±276.225 at the top to ±301.625 at z = 93.5 | Published widths at both ends. The front image gives a 24.8 mm run over 85 mm, and the model uses 25.4 mm over 90.65 mm |
| Middle/bottom-tier ends | Vertical at x ±301.625 | Front image |
| Slot x extents | \|x\| 13 … 287 mm, all rows | **Measured** from the front image at 0.4676 mm/px (1290 px = 603.25 mm; centre px 752). The rows agree to within ±1.5 mm, so one common value is used |
| Slot z extents | upper 108.5–140.5, middle 59.5–84.5, lower 12.5–37.5 | **Measured** from the front image at 0.4722 mm/px (390 px = 184.15 mm) |
| Slot ends | Full semicircles | Front image |
| Slot depths | 45 / 20 / 15 mm, measured from each tier front | **Published** (depth graphic). The back walls are at y = −2.625, −20, and −12 |
| Slot lip | 2 mm fillet on every slot mouth | **Display estimate**. The oblique image shows rounded mouths, but no radius is published. This matches the Escape Beta 22 estimate |
| Contact identity | Top = `top-sloper-60`; rows top→bottom = 45 / 20 / 15 mm, split left and right | Existing audited mapping (`2026-08-12-dewoodstok-escape-board-packages.md`), unchanged |

Readings were taken by an operator from gridded copies of the images. No image
was segmented, traced, or used as an automatic geometry input.

## CAD construction

- `SideProfile` (a Sketcher profile in the Y–Z plane, block-constrained) is
  extruded across the full width. `FrontOutline` (a Sketcher polygon in the
  X–Z plane) is extruded through the depth. Their `Part::Common` is the stepped
  blank.
- `Slots_upper`, `Slots_middle`, and `Slots_lower` are Sketcher pill pairs, one
  sketch on each tier's front plane. Each is extruded by its published depth,
  fused, and cut from the blank. A `Part::Fillet` then rounds the 24 mouth
  edges.
- Regions are exact face copies of the filleted body (`Part::Feature`). Each
  slot region contains its lip toroids and cylinders, the floor, the ceiling,
  both rounded ends, and the back wall. The sloper region is the flat top and
  the quarter-round. Every region carries `HangTenHoldOutline`: the lip pill for
  a slot, and the front-plane band of the quarter-round for the sloper.
  `HangTenCurvedRegionPartition` is set.
- As on Escape Beta 22, the face copies are not expression-linked to later
  Sketcher edits. After a pocket or profile change, reselect them.

The manifest changed in one place: the model presentation's `aspectRatio` went
from `3.2884058722385614` to `3.275862299100252`, the new `modelBounds` x/y
ratio. The camera is unchanged: a straight-on front view, in which every slot's
back wall faces the camera.

## Simplifications (not modelled)

- The four countersunk mounting holes, the engraved logo, and the engraved
  ruler.
- The small chamfer at the upper tier step visible in the side profile. The
  steps are sharp.
- Any end chamfers in depth on the top tier (a possible bevel in the oblique
  image). The top-tier ends are planar slants.

## Verification

- `compile_board.py`: reopen and recompute are clean, and the source bytes are
  unchanged. The published-depth gate passes exactly: 45.000, 20.000, and
  15.000 mm, and the sloper spans the full 47.625 mm. The output has 8 nodes
  and 52,400 triangles.
- `verify_reproducible.py --package escape-unlimited` rebuilds byte-identically
  on the pinned toolchain (FreeCAD 1.1.3, OCCT 7.8.1, macOS arm64).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passes. `scripts/verify-model-delivery.py` passes with the refreshed lock.
- Each left/right `facePlaneAABB` pair is an exact mirror. The pairs agree with
  the superseded descriptor to within 0.01–0.02 normalized units. The lower row
  sits about 3 mm higher, following the front image.
- Previous-versus-CAD previews: front
  ([previous](../pr-screenshots/escape-unlimited/previous-front.png),
  [CAD](../pr-screenshots/escape-unlimited/cad-front.png)), side
  ([previous](../pr-screenshots/escape-unlimited/previous-side.png),
  [CAD](../pr-screenshots/escape-unlimited/cad-side.png)), and top
  ([previous](../pr-screenshots/escape-unlimited/previous-top.png),
  [CAD](../pr-screenshots/escape-unlimited/cad-top.png)). The CAD model follows
  the manufacturer's side profile with sharp tier steps, where the superseded
  mesh used sloped transitions.
- `compare_exports` was not run as a gate. The model deliberately departs from
  the superseded mesh's tier transitions.
- In the app: an iOS 26.5 iPhone 17 Pro simulator ran the DEBUG board-detail
  route (`HANGTEN_REVIEW_BOARD_ID=escape.unlimited`). The model loaded with all
  seven `boardModel.contact.*` elements. `top-sloper-60`, the default, was
  highlighted on the quarter-round
  ([screenshot](../pr-screenshots/escape-unlimited/app-default.jpg)).
  `edge-20-right` was selected by deep link and confirmed through
  `boardDetail.selectedHold.edge-20-right`. Its highlight filled the right
  middle slot, and the card showed a 20 mm depth
  ([screenshot](../pr-screenshots/escape-unlimited/app-edge-20-right.jpg)).
  The simulator that ran this check was deleted afterwards. Accessibility and
  performance were not checked.
