# Tension Grindstone Mk2 — native CAD provenance

Date: 2026-09-26. Package `Hangboards/tension-grindstone`, board ID
`tension.grindstone`, revision `2026-09-contact-first` (unchanged).

This board had no 3D asset: its only presentation was the raster
`assets/primary.png`. It now has a native FreeCAD source,
`Hangboards/tension-grindstone/tension-grindstone.FCStd`, compiled by the shared
`Tools/HangboardCAD/compile_board.py` into `assets/primary.usdz` and
`assets/primary.model.json`. The raster asset and the hand-authored
`board.json` were deleted; `board.json` is now generated at build time from the
FCStd's `HangTenBoardManifest`, and its path is in `.gitignore`.

The document was created by a throwaway script
(`.context/terrible-shrimp-grindstone-cad/author_tension_grindstone.py`,
workspace scratch, not committed). The saved FCStd stands alone.

The result is a **measured display simplification** of the manufacturer's
front product image. It is not recovered manufacturing geometry, and nothing
here supports a product-accuracy or load-bearing claim.

## Sources

| Source | URL | SHA-256 (retrieved 2026-09-26) | Supports |
| --- | --- | --- | --- |
| Manufacturer product page | <https://tensionclimbing.com/products/grindstone> (JSON: `/products/grindstone.json`) | `1e3b99076826beca0e41e5bb67714dedb91f13c668cddb96d9a57c3724af86eb` (JSON) | Identity; `22"(W) x 6"(H) x 2 3/4"(D)`; full-width bar-style top jug; 50 mm centre one-arm edge; 30/25/20/15/10/8 mm edges; top phone slot |
| Front product image | <https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Grindstone1.png?v=1726542525> | `f75218bfd8144bc4712d7636ca3d20e0fac352e5d11fb2243fd3a0b95a96f738` | Front outline, slot/window/step positions, and the engraved depth labels |
| Close-up image | <https://cdn.shopify.com/s/files/1/0653/3706/5653/files/Grindstone2.png?v=1726542525> | `f0aa794ce154a7a64ed6103138ccde32f36826a5e403d65a60f8896805ea0187` | Engraved labels on the left slots (10 \| 8, 30 \| 25, 20 \| 15) |
| In-use images 3–6 | `Grindstone3.jpg` … `Grindstone6.jpg` on the same CDN path | 3 `cc7c1a74f39ff29ef450ffda383043899cd4084796b0021cd79b44ba95255838`; 4 `aed90dc7800abefb53f3389b3f631b010e840e6578eee680cdea5e4bfd44a0a5`; 5 `5edbe9046f79471eedeecca2daa99e26cf86196e040df28ec62fabe43ef414ef`; 6 `abfe9a22ac57513484177f1c69a950c9dec93becccbff3d25c36202900ecb769` | Wall mounting; three stacked tiers; engraved labels on the right slots; end profile of the tier stack |

The product page snapshot is also retained for the cord audit as
`docs/source-audits/2026-09-13-model-cord-snapshots/tension-grindstone.html`.

Superseded delivery: `assets/primary.png` sha256
`27c8312ade9f968bfb6fbca0b61d46cb08d994f367191cfb1aff7dc002cf9192`,
hand-authored `board.json` sha256
`09f59a4e19b4ef5fbeb4ebc4ec1514b5335c9775c7c0554c57753ab5dc7da749`.

New delivery: FCStd `a62e392e26ad36ae13acd9b453ce3b9315d70e8516272b24f1c429e5803ea723`,
USDZ `d69795c0f0c65e0c2070e3dc0c84fcfa7480a03c627157be4b8ed65cffcf5495`,
descriptor `2527466044e82c32bf5271cc48f4a909eb303146d8f951215d248a1ae18ef0d4`.

## Field mapping

Native frame: millimetres, +X right, +Z up, front −Y, wall at y = 0.

| Field | Value | Basis |
| --- | --- | --- |
| Overall width | 558.8 mm (top tier) | **Published** 22 in |
| Overall height | 152.4 mm | **Published** 6 in |
| Top tier front plane | y = −69.85 | **Published** 2 3/4 in overall depth |
| Middle tier front plane | y = −50 | **Published** 50 mm centre edge. The front image shows the background through the centre window, so the window is a through hole and its floor spans the middle tier's full thickness |
| Bottom tier front plane | y = −40 | **Display estimate.** Side photos (Grindstone4/6) show the bottom tier set back behind the middle tier; no depth is published |
| Front outline, tier boundaries, S-curve transitions, corner radii | see script constants | **Measured** by an operator from a gridded copy of `Grindstone1.png`. Horizontal scale 0.28322 mm/px (1973 px top-tier width = 558.8 mm); vertical scale 0.28864 mm/px (528 px = 152.4 mm). The two scales differ by 2%, a stated choice so both published dimensions hold. Readings are symmetric about px 1022 |
| Slot rows (z) | top 116.9–139.1 (stadium, r 11.1); middle 64.9–95.3 (r 8); bottom 8.7–43.3 (r 8) | **Measured**, same image |
| Slot ends (\|x\|) | top 70.4–262.4; middle 65.5–255.8; bottom 64.5–249.3 | **Measured** |
| Depth steps (x) | top −162.0 / +169.4; middle −156.3 / +158.0; bottom −154.9 / +157.5 | **Measured** at the visible step line |
| Window | x ±45, z 62.9–91.2, r 7 | **Measured** |
| Jug top-front round-over | r 8 mm on the top tier's top-front edge | **Display estimate.** The end-profile photo (Grindstone4) shows a rounded bar-jug edge; no radius is published |
| Edge depths | 10, 8, 30, 25, 20, 15 mm (slot back walls); 50 mm (window) | **Published**. Each region's Y extent equals its published depth exactly (compile gate) |
| Which segment is which depth | on **both** sides the deeper segment is the left one | **Engraved labels** in Grindstone1/2/5: left side reads 10 \| 8, 30 \| 25, 20 \| 15 (deep outboard); right side reads the same left to right (deep inboard) |

### Correction to the right-side contact positions

The previous raster `board.json` placed `edge-8-right`, `edge-25-right`, and
`edge-15-right` on the inboard half of each right slot, and the 10/30/20 mm
contacts outboard, which mirrored the left side. The manufacturer's engraved
labels show the opposite: the right slots also run deep → shallow from left to
right. The CAD source follows the engraving: `edge-10-right`, `edge-30-right`,
and `edge-20-right` are now inboard, and the shallow segments are outboard. Contact
IDs, names, kinds, and depths are unchanged.

## Holds (contact regions)

Every region is a cap-free parametric surface whose own shape is the exported
hold mesh; the body is partitioned around it (`HangTenCurvedRegionPartition`
set for the rounded slot ends).

- Edge segments: the lateral walls of the segment opening, extruded from the
  back wall to the tier front by the published depth, plus the back wall face.
  The deeper segment also carries the step wall between the two back walls.
  `HangTenHoldOutline` is the segment opening.
- `edge-50-center`: the four walls of the through window, 50 mm long.
  `HangTenHoldOutline` is the window opening.
- `top-jug`: the 8 mm top-front round-over plus the planar top face of the top
  tier, extruded from one side-profile sketch run. The round-over makes the
  jug visible to the front camera. No depth is published, so no depth gate
  applies. `HangTenHoldOutline` is a 9.5 mm band along the top edge,
  matching the height of the previous operator-drawn top-jug path.

Every slot cut sets `Refine = False`. A refined cut merges the coplanar floors
of the two segments across the step, and the partition cannot then split them.

## Presentation

The model presentation uses an orthographic camera tilted 20° downward
(`viewDirection` [0, −0.342, −0.940]), which is a display choice like the J Bryant
FTG-32's. A dead-front camera sees the through window's walls, and every
slot floor, edge-on, so the 50 mm edge could not be highlighted. `aspectRatio` is
the descriptor `modelBounds` x/y ratio (3.6666665004374477).

## Simplifications (not modelled)

- The lip radii of the edges ("Tension's signature edge radius profile"; no
  radius is published) and the tier round-overs. Apart from the jug round-over,
  all front edges are sharp.
- The rounded end of the deeper pocket at the depth step. The photos show a
  rounded end there; the model uses a flat step wall.
- The top phone slot. It is published, but its size and position are not.
- Engraving, fastener holes, and the concealed back and mounting.

## Verification

- `compile_board.py`: reopen and recompute are clean, source bytes are
  unchanged, and the published-depth gate passes for all 13 depth-bearing
  regions (exact). The output has 15 nodes and 5,676 triangles.
- `verify_reproducible.py --package tension-grindstone`: rebuilds
  byte-identically on the pinned toolchain (FreeCAD 1.1.3, OCCT 7.8.1, macOS
  arm64).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`:
  exit 0.
- Hydra Storm (`usdrecord`) front, side, top, three-quarter, and below renders
  were reviewed with each contact tinted by depth. They show the three tiers
  stepping back towards the bottom, the through window, and the deeper segment
  on the left of every slot.
- In the app: an iOS 26.5 iPhone 17 Pro simulator on the DEBUG board-detail route
  (`HANGTEN_REVIEW_BOARD_ID=tension.grindstone`). The model loaded with all 14
  `boardModel.contact.*` elements. `top-jug` (the default),
  `edge-50-center`, `edge-10-right`, and `edge-20-left` were selected, the last
  three by deep link. Each was confirmed through
  `boardDetail.selectedHold.<contactID>`, and its highlight landed on the
  expected region: `edge-10-right` on the inboard half of the right top slot,
  `edge-20-left` on the outboard half of the left bottom slot. Suspension does
  not apply. Accessibility and performance were not checked.
- There is no reference mesh, so `compare_exports` does not apply. The sketch
  dimensions are Block-constrained, not expression-linked, so no
  edit-propagation suite is claimed.
