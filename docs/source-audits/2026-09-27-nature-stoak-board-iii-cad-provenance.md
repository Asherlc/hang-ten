# Nature Climbing Stoak Board III — native CAD provenance

Date: 2026-09-27. Package `nature-stoak-board-iii`, board ID
`nature.stoak-board-iii`, revision `2026-09-contact-first`. The FreeCAD source
is `Hangboards/nature-stoak-board-iii/nature-stoak-board-iii.FCStd`. Its
embedded `HangTenBoardManifest` replaces the committed `board.json`. The one-off
authoring script lives only in workspace scratch at
`.context/migrate-nature-stoak-board-iii-cad/author_stoak.py`. The saved
document reopens and recompiles without that script.

This is a simplified **display model**. It is not recovered manufacturing
geometry or a load-bearing CAD plan. The manufacturer's published dimensions
and contact map fix the overall size, the hold inventory, and every depth. The
operator measured the hold layout by hand from the manufacturer's straight-on
photo. Coordinates and radii that are not published are labeled display
estimates below.

## Sources

Retained primary sources (downloaded 2026-09-27 from the Shopify product feed
`https://natureclimbing.com/products/stoak-board-iii.json`):

| Retained file | Publisher and URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `2026-09-27-nature-stoak-board-iii-cad-sources/front.png` | Nature Climbing, <https://cdn.shopify.com/s/files/1/0657/7736/9334/files/6_2a2069e0-b45e-4eca-aa65-59febfe7c958.png?v=1763577563> | `640afba4b4c148a155f97106676ee3632308480e28796c7e8059f5f796aba77d` | Straight-on front silhouette and every front-plane hold position (measured, below) |
| `2026-09-27-nature-stoak-board-iii-cad-sources/annotated-map.png` | Nature Climbing, <https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Comfortable_jug_1.png?v=1763986786> | `27682e5ddc5b8ee13c912f47128fd1b7c036b06ad287dc7130e1307896d93fb6` | Which physical surface carries each published depth: comfortable jug, 22 mm, 55 mm open hand, gradient 10–25 mm edge, 20 mm granite, 30 mm, 30 mm granite or ergo wood edge |
| `2026-09-27-nature-stoak-board-iii-cad-sources/oblique.png` | Nature Climbing, <https://cdn.shopify.com/s/files/1/0657/7736/9334/files/4_671cc28f-ab91-4566-ad88-887bace217be.png?v=1764017417> | `9bc53be5ae91a1572297728b3cef3d5b623b89d883ac0fe1105adaa00a03c055` | Upper channel under the jug lip; stepped back wall in the lower side slots at the granite/wood change |
| `2026-09-27-nature-stoak-board-iii-cad-sources/side-profile.jpg` | Nature Climbing, <https://cdn.shopify.com/s/files/1/0657/7736/9334/files/FullSizeRender_faff5719-c63b-42ff-81f2-382d51875de3.jpg?v=1764017405> | `8e29c5752f7ac36d9eae5a32301b6b7a83ddbc55039ac376b2f6b9dfe2fabd2b` | End profile: the jug lip overhangs, the upper channel is open at the board end, flat rear |

Corroborating manufacturer images, cited but not retained:

| URL | SHA-256 | Supports |
| --- | --- | --- |
| <https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Comfortable_jug.png?v=1763578828> | `5429779d6c62a39c5ef8fcc6e6fea56ed6d0624496f12d86ad7c372163f653bc` | End close-up: upper channel reaches the board end; granite insert in the lower slot |
| <https://cdn.shopify.com/s/files/1/0657/7736/9334/files/10_63223a82-c987-4a63-9b9e-cbd12abae45e.png?v=1764017297> (Beech listing) | `91b3e70b7f72fae11377fcccd7e56a9d941aa14c76cfcd872b2ab96e844bf312` | End view of the same shape in beech: rounded jug rail over an open channel |
| <https://natureclimbing.com/cdn/shop/files/Comfortable_jug_2_1600x.png?v=1763986786> | `24a770fd9f3378bd60ab0e45c7ffb1e58c7ce319e9da007535a6c2d86af4ae7d` | Earlier annotated map cited by the 2026-08-12 metadata audit (beech board); the same labels and arrow targets as `annotated-map.png` |

The [product page](https://natureclimbing.com/products/stoak-board-iii)
(HTML SHA-256 `144e275b956a302fce0d1704fedc3fd51d8b8bbdd04febdfb57146c29afa5f23`
as fetched) publishes "Measures 57 cm x 12 cm x 5.5 cm", "a 22mm edge designed
for one-arm hangs", "a comfortable top jug", and 5 mm magnetic inserts. A web
search found no other manufacturer statement about the gradient edge.

The superseded Git asset at `0304335e25d611267b3a3f7b2627118f03b11686` was a
visual cross-check only, never a compiler input or geometry source: USDZ SHA-256
`fc48bd058d8404047ffedb5f6ca1f00ed733caf61cd879ba3e7374651dadffe0`,
descriptor `dd48e006b28f7ba2db39513350b7324a1cd503d8c081658c016cef6bcd4c4de2`,
and retired board metadata
`7545d5aca4b1fe3e7af6dd8abe4c876f9e653859f43d6957e6fe3f9429a6eb23`.

## Conflicts recorded

1. **The superseded mesh bound three contacts to the wrong surfaces.** Compared
   with the annotated map, the old descriptor placed `edge-22-center` (22 mm) on
   the lower centre granite slot. It placed `lower-composite-center` (30 mm
   granite / ergonomic wood) on the upper centre pocket, which the map labels
   22 mm. It placed both `gradient-edge-*` contacts on the wood sections of the
   lower side slots, which the map labels 30 mm. It reduced
   `lower-composite-*` to the granite sections only. The old mesh also had no
   upper channel: its top was a sculpted hook, which does not match the
   photographs. The new source follows the annotated map. The contact IDs,
   names, kinds, and depths in the manifest were already correct and are
   unchanged.
2. **Legacy node names.** Every contact keeps the node ID it had before, as the
   migration requires. As a result, three node names now describe a different
   surface than their region:
   - `centre_granite_edge_001` → `edge-22-center`, the upper centre **wood**
     pocket.
   - `upper_centre_wood_edge_001` → `lower-composite-center`, the lower centre
     **granite** slot.
   - `left/right_granite_edge_001` → `lower-composite-left/right`, the whole
     lower side slot (granite **and** wood sections).

   Node IDs are opaque binding keys. The app binds contacts through the
   descriptor, so this affects only readability. Renaming would be a separate
   ID migration.
3. **Gradient direction is not published.** The map gives a 10–25 mm range but
   not which end is shallow. The source puts 10 mm at the board end and 25 mm at
   the inner end, near the centre. This is a **display estimate**, weakly
   supported by the oblique photo: more of the lip underside shows toward the
   centre, even though that part is farther from the camera. Swapping the two
   values in the authoring script would reverse it.
4. **The 55 mm open-hand callout** points at the top of the jug rail. It equals
   the full published 5.5 cm depth. As the 2026-08-12 audit decided, it does
   not create a second contact. The jug region spans the full 55 mm, and the
   compiler does not gate it, because `top-jug` has no published depth.

## Measurement frame

Native coordinates are millimetres: +X right, +Z up, front −Y, rear plane
Y = 0, bottom of the end feet Z = 0. The board spans X ±285, Z 0–120, and Y
0 to −55, which gives exactly the published 570 × 120 × 55 mm.

The front photo (`front.png`, 2048 px) was read on 1 mm grids
(`Tools/HangboardCAD/photo_grid.py crop`). The scale is **2.637 px/mm**: the
board's extreme left and right edges are at x ≈ 275 and 1778 px, which is
1503 px for the published 570 mm. The frame origin (native X 0, Z 60) is at
photo pixel (1026.5, 988). The camera is slightly above the board, so the top
faces of the ledges show as thin bands. Only edges in the front plane were read.
No image was segmented, traced, vectorized, or used as an automatic geometry
input.

## CAD construction and field mapping

The blank is the intersection of two `Part::Extrusion` prisms of
`Sketcher::SketchObject` loops:

- a front outline (XZ) with R15 lower-end corners, R20 top corners, and end feet
  that drop from Z 10 to 0 beyond |X| 155–180 (measured);
- a side profile (YZ) with a flat rear, an R18 front-top round, and the jug lip
  at Y −55 above Z 86, over a face set back to Y −52.5 below it.

The 2.5 mm lip overhang is a display estimate from `side-profile.jpg`.

The holds are cut with `Part::Cut` (Sketcher profiles extruded as cutters). A
`Part::Fillet` then rounds every hold mouth by 2 mm (display estimate). Each
contact is a `Part::Feature` holding exact copies of the final body's faces,
classified with `optimalBoundingBox()`. Each contact carries `NodeID`,
`NodeRole`, `ContactID`, and a CAD-authored `HangTenHoldOutline`. The document
sets `HangTenCurvedRegionPartition` (cylindrical pocket and slot ends, fillets)
and `HangTenSurfaceNormals`. The face copies are static: after a geometry edit,
re-run the classification.

| Contact ID → node | Source fact | Authored region |
| --- | --- | --- |
| `top-jug` → `top_jug_001` | "Comfortable jug", "55mm open hand" (map); top jug (page) | Top rail: flat top, R18 front round, the Y −55 lip front above Z 86, and the lip underside. The underside rises to Z 100 over the centre block between \|X\| 78 and 62 (measured photo S-curve, R8 blends). Full 55 mm. |
| `edge-22-center` → `centre_granite_edge_001` | "22mm" (map, arrow on the upper centre pocket); 22 mm edge (page) | Stadium pocket X ±45, Z 80–97 (measured), **22.000 mm** deep |
| `gradient-edge-left/right` → `left/right_tapered_wood_edge_001` | "gradient 10-25mm edge" (map, arrow under the jug lip) | Channel Z 65–86 (measured, photo z 5–26) from \|X\| 80 through the board end, as the side photos show. The ledge is the middle-bar top. The back wall slants linearly from **10.000 mm** at the board end to **25.000 mm** at \|X\| 80. The direction is a display estimate (conflict 3). |
| `lower-composite-left/right` → `left/right_granite_edge_001` | "20mm granite", "30mm" (map, both on this slot); continuous contact (2026-08-12 audit) | One slot, \|X\| 78–262 and Z 23–48 (measured). It has R6 outer corners and a full-round inner end. The granite section \|X\| 180–262 is **20.000 mm** deep. The wood section \|X\| 78–180 is **30.000 mm** deep. A planar step joins them where the photo shows a blended back wall. |
| `lower-composite-center` → `upper_centre_wood_edge_001` | "30mm granite or ergo wood edge" (map) | Slot X ±52, Z 36–62 (measured), R6 corners, **30.000 mm** deep |

The compiler's published-depth gate checks only scalar depths: 22 and 30 mm,
both exact. The authoring script asserted both ends of each range: gradient
10.000 / 25.000 mm and composite 20.000 / 30.000 mm.

Omitted on purpose: mounting holes, screws, the engraved logo, magnetic inserts
and their seats, the granite/wood material split (USDZ ships without materials),
the slight inset of the jug ends, and the photographed forward bulge of the
middle bar. The front face below the lip is one plane, and the rounded bands
seen in the photos are simplified to 2 mm mouth rounds.

## Manifest change

The embedded manifest is value-identical to the deleted `board.json` except for
the model presentation `aspectRatio`. It changed from 4.718998795731431 (the
superseded mesh bounds) to **4.750000052083334**, the new descriptor
`modelBounds` x/y ratio (570 × 120 mm in float32). The geometry requires this:
`test_fixed_front_model_presentation_ratios_match_descriptor_bounds` holds it to
1e-9. The top-level `aspectRatio` of 2.0 is unchanged.

## Verification

- `compile_board.py --check`, then publish: native-source, 7-contact, and
  published-depth gates passed. The descriptor was derived from the reopened
  USDZ.
- `verify_reproducible.py --package nature-stoak-board-iii`: the USDZ and
  descriptor rebuild byte-identically on the pinned toolchain (FreeCAD 1.1.3,
  OCCT 7.8.1, usd-core 26.8).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  accepted all 64 boards. `scripts/verify-model-delivery.py` verified the
  refreshed 47-package lock.
- `Tools/HangboardPackages` pytest: 718 passed.
  `Tools/HangboardModels/tests/test_model_delivery_alignment.py`: 8 passed.
  `test_coderabbit_mirrored_geometry.py` no longer needs its Stoak-specific
  mesh tolerance. The new regions mirror exactly at the default 1e-6 bound, so
  the exception was removed.
- iOS: a workspace-owned iPhone 17 Pro simulator (iOS 26.5) ran the DEBUG
  board-detail route. It loaded the model with `top-jug` selected by default.
  `hangten://board/nature.stoak-board-iii/hold/edge-22-center` selected
  `boardDetail.selectedHold.edge-22-center`: the upper centre pocket was
  highlighted, with Depth 22 mm. Hold-map taps selected `gradient-edge-left`
  (upper-left channel highlighted, 10–25 mm) and `lower-composite-right` (whole
  lower-right slot highlighted, 20–30 mm). The simulator was deleted after the
  run.

| Review view | Previous asset | Native CAD |
| --- | --- | --- |
| Front | [previous](../pr-screenshots/nature-stoak-board-iii/previous-front.png) | [CAD](../pr-screenshots/nature-stoak-board-iii/cad-front.png) |
| Side | [previous](../pr-screenshots/nature-stoak-board-iii/previous-side.png) | [CAD](../pr-screenshots/nature-stoak-board-iii/cad-side.png) |
| Top | [previous](../pr-screenshots/nature-stoak-board-iii/previous-top.png) | [CAD](../pr-screenshots/nature-stoak-board-iii/cad-top.png) |
| Oblique | [previous](../pr-screenshots/nature-stoak-board-iii/previous-oblique.png) | [CAD](../pr-screenshots/nature-stoak-board-iii/cad-oblique.png) |

App screenshots:
[default top jug](../pr-screenshots/nature-stoak-board-iii/app-default.png),
[22 mm edge](../pr-screenshots/nature-stoak-board-iii/app-edge-22-center.png),
[left gradient edge](../pr-screenshots/nature-stoak-board-iii/app-gradient-edge-left.png),
[right lower composite](../pr-screenshots/nature-stoak-board-iii/app-lower-composite-right.png).

The oblique views are a painter's-algorithm CPU render made for this review, not
SceneKit output. `compare_exports` was not used as evidence. The new source was
re-authored from manufacturer evidence, and the superseded mesh contradicts
those photos (conflict 1).

Final source SHA-256:
`7cad136c2f10ca4bdddd4f0817d58b87a14d018faf80d08d61c529c8da96b696`.
Compiled USDZ SHA-256:
`808e8a7f058c8b62b5cf0e9180b86df68861022670598decf8db25f75d3c3274`.
Descriptor SHA-256:
`225a2c5282e5dfdac09c20ac96abc5a976f71ce8644283114199f0a414b5e142`.
