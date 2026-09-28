# The Hangboard — native CAD provenance

Date: 2026-09-27. Package `the-hangboard`, board ID
`the-hangboard.the-hangboard`, revision `2026-09-contact-first`. The FreeCAD
source is `Hangboards/the-hangboard/the-hangboard.FCStd`. Its embedded
`HangTenBoardManifest` replaces the committed `board.json`. The one-off
authoring script lives only in workspace scratch at
`.context/migrate-cordless-hangboard-cad-2/author_the_hangboard.py`. The saved
document reopens and recompiles without that script.

This is a simplified **display model**. It is not recovered manufacturing
geometry or a load-bearing CAD plan. The manufacturer's published dimensions
fix the overall size, and its published edge depths fix every edge region's
depth. The operator read the layout and profile by hand from the
manufacturer's own photographs and end-profile render. Every other number is a
labeled display estimate below.

The Hangboard is a fixed, wall-mounted board. It has no cords, suspension, or
attachment nodes, and none are authored.

## Sources

Retained primary sources (downloaded 2026-09-27 from The Hangboard's Shopify
store and theme assets):

| Retained file | Publisher and URL | SHA-256 | Supports |
| --- | --- | --- | --- |
| `2026-09-27-the-hangboard-cad-sources/front.png` | Product gallery, <https://cdn.shopify.com/s/files/1/0764/5210/2426/files/hangboard-straight-2_ddf25e96-22ac-422d-9a62-7db961398ca4.png?v=1747623739> | `4db9e95721bd43cf6df3ee5974865948c9353f2f366c4f2957b08206442122d3` | Straight-on front: outline, the ear inner ends, the sloper front edge, both window rows, all 12 edge segment boundaries, the upper-slab lip (measured, below). The same bytes as the `TH-FRONT` evidence of 2026-09-15. |
| `2026-09-27-the-hangboard-cad-sources/end-profiles.png` | Landing-page jug/sloper guide render, <https://thehangboard.com/cdn/shop/t/7/assets/sloper-jugs-info2.png> | `eb07b98b489eb43b9b7fe904e38d77ddb769a7dfa0babe5670830e65b4241df0` | Orthographic end profile: full-round jug top, ear thickness, the open space behind the jug, lower-slab setback, the groove under the upper-slab lip |
| `2026-09-27-the-hangboard-cad-sources/back.png` | Product gallery, <https://cdn.shopify.com/s/files/1/0764/5210/2426/files/hangboard-back-2.png?v=1747623739> | `f66cd5f6ad6212e7c2eead158c96c6e6bec3166fe0e975e9ed5dd5ebb160f6ff` | Back plank height (jug floor); the sloper's back reaching the full board height |
| `2026-09-27-the-hangboard-cad-sources/top-bottom.png` | Product gallery, <https://cdn.shopify.com/s/files/1/0764/5210/2426/files/hangboard-top-bottom-2.png?v=1747623739> | `ebf975836bf8aa423fbdc0f0bc4e26f9c2e36937cd244a0a6c463a8534ff33d0` | Round jug tops with a floor behind them; one sloper plane across the depth; upper-slab overhang (bottom view) |
| `2026-09-27-the-hangboard-cad-sources/oblique-right.png` | Product gallery, <https://cdn.shopify.com/s/files/1/0764/5210/2426/files/half-right-hangboard.png?v=1747623739> | `128efa32244f2d0a20a70c468f483c135baec8797e88e8cc3732f88111eaf147` | Stepped back walls inside each window; the upper slab overhanging the lower slab; sloper front edge height relative to the ear |

The [landing page](https://thehangboard.com/) (HTML SHA-256
`a5913b51ad901b2d0f3970883f6ac54997e8b71ef522e86b95816cb0556e2d18` as fetched)
publishes "Dimensions 23.5" x 6.25" x 2"", "6 labeled depths from 40mm to
10mm", "40-degree slopers for open-hand strength", "Deep jugs for pullups and
warm-up hangs", and "The space behind the jug can be used to hold a phone".
The [product page](https://thehangboard.com/products/hangboard) (HTML SHA-256
`9f735847ee83257e3b14a8caab6a882a9ea3f11badcac090deb68fa800ccf268`) publishes the
asymmetrical layout and the 40-degree sloper. It gives no dimensions. The
[asymmetric edge-layout guide](https://thehangboard.com/cdn/shop/t/7/assets/asymmetrical-nobg-text2.png)
(SHA-256 `0b719ab54ec64121ada9cbbe11fd5d5a4f31f1b6e8a59e2818dfab05a5a6df45`)
maps the labels to the segments. The upper windows read 40 / 30 / 25 mm and the
lower windows 20 / 15 / 10 mm, left to right, in **both** halves. That matches
the engraved labels in `front.png` and the existing contact names.

Cited but not used for measurement: the end views
`hangboard-side-2.png` / `hangboard-side-2-right.png`, which agree with the
end-profile render, and the photos `IMG_0761` / `IMG_0762` of the board standing
on end.

The superseded Git asset at `585e8078a` was a visual cross-check only, never a
compiler input or geometry source: USDZ SHA-256
`7666ef014e2fd5be4af874d56caced26ba1202c8c18978f9fd8ff737ae23ff42` (LFS object),
descriptor SHA-256
`1708b5952623838dbd67001769e5d2079bf3078f96f2bfd602a3006ba8be340d`. It was
imported from an external GLB (2026-09-15 collection import); no generator is
retained in Git.

## Conflicts recorded

1. **The superseded mesh contradicts the photos.** Its jugs were solid domes
   filling the whole 50.8 mm depth, with no space behind them. The landing page
   and every end view show a 31.5 mm-thick ear with an open space behind it.
   Its ears sat on a narrower back block, below a separate proud upper band.
   The straight-on photo instead shows the ear front face continuous with the
   upper slab. Its sloper had a flat top 8 mm below the jugs. The new source
   follows the photos.
2. **Edge stepping agrees with the superseded mesh.** Within each window the
   floor is continuous, and the back wall steps. The 40 mm and 20 mm back
   walls are the deepest. The straight-on photo shows the shadow under each
   window's top lip growing with wall depth (about 27 px on the 40 mm wall,
   about 8 px on the lower row). In the upper-right window, the step faces
   show as dark strips on the camera's side.
3. **Depth: published 2 in vs the end-profile render.** The render's
   depth-to-height ratio implies about 53.8 mm deep at the published 6.25 in
   height. The published 2 in (50.8 mm) is used. Render depths (Y) were
   scaled by 50.8 / 253 px and heights (Z) by 158.75 / 746 px.
4. **Sloper crest.** The end-profile render and the side views show the
   sloper's rear crest about 27.7 mm below the jug tops at Y ≈ −7.5. A 40°
   face on that line would reach the front plane at Z ≈ 95, inside the upper
   edge windows (Z 80–105), which the straight-on photo contradicts. The
   photos agree with each other instead:
   - the straight-on photo puts the sloper's front edge at Z 128.2 on the
     front plane;
   - the back view shows the sloper back reaching the full board height;
   - the top view, corrected for its ≈ 32° tilt, fits a 40° plane over about
     35 mm of depth.

   The source uses the published 40° from the photographed front edge up to
   the board height. That puts the back face at Y −14.39 mm.
5. **Upper-slab lip height and plank height.** The straight-on photo puts the
   lip bottom at Z 59.1 mm; the render reads 50.0. The back photo puts the
   plank top (jug floor) at 120.3 mm; the render reads 116.6. The photographs
   are used for both.
6. **Photo perspective.** `front.png` is a close perspective shot. The left
   half reads 3.1865 px/mm and the right half 3.1027 px/mm about the centre
   divider and engraving (x = 1011 px). Each half's X readings use that half's
   own scale. Heights use 3.112 px/mm from the board bottom (y = 1017 px).
   Readings are good to about 1–2 mm. The window centre gap therefore reads
   −9.1 / +10.0 mm rather than exactly symmetric; the readings are used as
   read.

## Measurement frame

Native coordinates are millimetres: +X right, +Z up, front −Y, rear plane
Y = 0, bottom Z = 0. The board spans X ±298.45, Z 0–158.75, and Y 0 to −50.8,
which gives exactly the published 23.5 × 6.25 × 2 in.

The operator read every point by eye off pixel-gridded, contrast-stretched
crops. No image was segmented, traced, vectorized, fitted, registered, or used
as an automatic geometry input. The review overlay
(`docs/pr-screenshots/the-hangboard/cad-over-manufacturer-photo.png`,
`photo_grid.py overlay`, 3.13 px/mm, origin (1011, 1017)) blends the compiled
front view over the photo.

## CAD construction and field mapping

- **Sections**: two `Sketcher::SketchObject` end profiles (Y–Z), extruded
  along X, fused, and refined off. The shared lower part has:
  - the back plane;
  - the bottom;
  - the lower slab front at Y −36.3 (render);
  - a 1.6 × 13.4 mm groove under the upper-slab lip (render);
  - the upper-slab front at Y −50.8 down to the lip bottom at Z 59.1 (photo).
  - Corner rounds are display estimates: back-bottom R2, front-bottom R2.5,
    lip R2.5.

  The two sections differ above that:
  - The **jug section** (|X| ≥ 181, from the photo's 179.2 / 182.7) is an ear
    from Y −50.8 to −19.3 with a full-round top, R15.75, reaching the
    published height. The open space behind it runs from Y −19.3 to 0, above
    the plank top at Z 120.3.
  - The **sloper section** (|X| ≤ 181) is a 40° plane (published). It runs
    from the front edge at Z 128.2 up to the published height at
    Y −14.39. The crest has an R3 round (display estimate). A back face drops
    to the plank top, leaving a 14.4 mm space behind it.
- **Front outline**: a `Part::Common` with an X–Z outline: ±298.45 ×
  0–158.75, with R13 top and R16 bottom corners (display estimates). Two
  corner cutters round the lip's bottom end corners to R10 (display estimate).
- **Edges**: 12 segment cutters. Each is a ruled `Part::Loft` through six
  stations (a pre-station 1 mm in front, then 3 mm quarter-round stations at
  0 / 22.5 / 45 / 67.5 / 90°). A prism then runs to the published depth. The
  segment outline has R5 window-end corners (display estimate) and square
  ends where one depth steps to the next. Because each segment is its own
  cutter, the body faces split exactly on the step planes. One
  `Part::MultiFuse` and one `Part::Cut` remove them (refine off).
- **Regions**: each contact is a `Part::Feature` holding exact copies of the
  final body's faces:
  - an edge owns every face of its segment inside its mouth outline, back to
    its back wall (12–27 faces);
  - a jug owns its round top, its back face and its floor;
  - the sloper owns its 40° face and crest round;
  - end faces normal to X stay on the body.

  Each contact carries a CAD-authored `HangTenHoldOutline`: the segment mouth
  for an edge, the round-top band for a jug, and the front band for the
  sloper. The document sets `HangTenCurvedRegionPartition` and
  `HangTenSurfaceNormals`. The face copies are static: after a geometry edit,
  re-run the classification.

Edge segments (X measured from `front.png`; the depth is published and
equals each region's Y extent exactly):

| Contact ID → node | Row (Z, measured) | X (mm) | Published depth |
| --- | --- | --- | --- |
| `edge-40-left` → `edge_40_left_001` | upper 80.3–105.1 | −281.8 to −180.1 | 40 |
| `edge-30-left` → `edge_30_left_001` | upper | −180.1 to −94.8 | 30 |
| `edge-25-left` → `edge_25_left_001` | upper | −94.8 to −9.1 | 25 |
| `edge-40-right` → `edge_40_right_001` | upper | 10.0 to 90.9 | 40 |
| `edge-30-right` → `edge_30_right_001` | upper | 90.9 to 179.5 | 30 |
| `edge-25-right` → `edge_25_right_001` | upper | 179.5 to 280.7 | 25 |
| `edge-20-left` → `edge_20_left_001` | lower 21.5–47.2 | −282.6 to −186.2 | 20 |
| `edge-15-left` → `edge_15_left_001` | lower | −186.2 to −99.5 | 15 |
| `edge-10-left` → `edge_10_left_001` | lower | −99.5 to −10.0 | 10 |
| `edge-20-right` → `edge_20_right_001` | lower | 10.3 to 93.9 | 20 |
| `edge-15-right` → `edge_15_right_001` | lower | 93.9 to 185.1 | 15 |
| `edge-10-right` → `edge_10_right_001` | lower | 185.1 to 284.4 | 10 |
| `jug-left` / `jug-right` → `jug_left/right_001` | round top, Z 120.3–158.75 | ∓298.45 to ∓181 | — (none published) |
| `sloper-40-center` → `sloper_40_center_001` | Z 128.2–155.3 | ±181 | — (40° published) |

The upper row's edges are on the Y −50.8 front plane, and the lower row's on
the Y −36.3 plane.

Omitted on purpose:
- the mounting screws and their bores, as in the superseded asset (see
  `2026-09-22-mounting-bore-removal.md`);
- the engraved labels and wordmark;
- each window's darker outer end zone, where the outermost edge instead runs
  to the window end;
- the router radius at each step corner;
- the slant of the sloper's end faces in plan (the top view shows a small
  wedge gap beside each ear).

## Manifest change

The embedded manifest is value-identical to the deleted `board.json` except
the model presentation `aspectRatio`. It changed from 2.0 to
**3.759999959181102**, the new descriptor `modelBounds` x/y ratio
(596.9 × 158.75 mm in float32). The top-level `aspectRatio` of 2.0 is
unchanged. All 15 contact IDs and 16 node IDs, and their pairing, are
unchanged.

## Verification

- `compile_board.py`: native-source and 15-contact gates passed. The
  published-depth gate was exact for all 12 edges. The asset is 10,788
  triangles. The descriptor was derived from the reopened USDZ.
- `verify_reproducible.py --package the-hangboard`: byte-identical on the
  pinned toolchain (FreeCAD 1.1.3, OCCT 7.8.1, usd-core 26.8).
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed. `scripts/verify-model-delivery.py` verified the refreshed lock.
- `Tools/HangboardPackages` pytest: 718 passed.
  `Tools/HangboardModels/tests/test_model_delivery_alignment.py`: 8 passed.
  `Tools/HangboardCAD/tests`: see the PR description.
- iOS: a workspace-owned iPhone 17 Pro simulator (iOS 26.5) ran the DEBUG
  board-detail route. It loaded the model with `jug-left` selected by default
  (the left ear's round top highlighted). Hold-map taps selected, each
  confirmed via `boardDetail.selectedHold.<contactID>`:
  - `edge-30-left` and `edge-30-right`: only the middle segment of each upper
    window, "Depth 30 mm";
  - `edge-10-left`: the inner segment of the lower-left window, "Depth 10 mm";
  - `sloper-40-center`: the whole sloper face.

  The simulator was deleted after the run.

| Review view | Previous asset | Native CAD |
| --- | --- | --- |
| Front | [previous](../pr-screenshots/the-hangboard/previous-front.png) | [CAD](../pr-screenshots/the-hangboard/cad-front.png) |
| Side | [previous](../pr-screenshots/the-hangboard/previous-side.png) | [CAD](../pr-screenshots/the-hangboard/cad-side.png) |
| Top | [previous](../pr-screenshots/the-hangboard/previous-top.png) | [CAD](../pr-screenshots/the-hangboard/cad-top.png) |
| Oblique | [previous](../pr-screenshots/the-hangboard/previous-oblique.png) | [CAD](../pr-screenshots/the-hangboard/cad-oblique.png) |

The views are OpenUSD `usdrecord` (Hydra Storm) renders, not SceneKit output.
The previous asset's meshes carry a `material:binding` to a removed material,
which renders black in Storm. The review copy drops that relationship before
rendering. The committed bytes were never modified. App screenshots:
- [default left jug](../pr-screenshots/the-hangboard/app-default-jug-left.png);
- [left 30 mm](../pr-screenshots/the-hangboard/app-edge-30-left.png);
- [right 30 mm](../pr-screenshots/the-hangboard/app-edge-30-right.png);
- [left 10 mm](../pr-screenshots/the-hangboard/app-edge-10-left.png);
- [sloper](../pr-screenshots/the-hangboard/app-sloper-40-center.png).

`compare_exports` was not used as evidence, because the superseded mesh
contradicts the photos (conflict 1).

Final source SHA-256:
`1ff13aaf7b4442b682333c8cb845c2550ebe7170c75bf1936042d70e3aee3f0d`.
Compiled USDZ SHA-256:
`baa39c97ac15c6ad5775af55801eb6a0419df6e251aca81c2624046cba49c2e9`.
Descriptor SHA-256:
`6d0d41548748408a8a4b0d5c0037a498f17589aafddb1817cab83a221f75444b`.
