# YY VerticalBoard Light native CAD provenance

Workspace owner: `supreme-zebra`. Prior asset revision:
`b7cc2c15df661a913ed0ea9dc14321badb7d6ef5`.

The user approved the two manufacturer photographs below with “y” in the
migration conversation before geometry authoring. Astra deliberately authored
the analytic geometry from those photographs. No image detection, tracing,
segmentation, registration, cropping, vectorization, or legacy path conversion
was used. The previous package was raster-only, so no previous side or top
geometry exists for comparison.

## Evidence and factual cross-check

- [Manufacturer product page](https://www.yyvertical.com/en/products/verticalboard-light),
  read 2026-09-29: 54 × 9 × 5 cm; 20/25/45 mm edges; center 40 mm edge;
  30° and 20° slopers; two jugs; center elastic-band notch; symmetric wooden
  wall-mounted board. These agree with the existing contact metadata.
- [Full front product photograph](https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY-VBL-1gris.webp?v=1770128011),
  YY Vertical, SHA-256
  `a3ab42089800dcf64dffcc01aca0928fc321ea62a606d28823fae35d5bde0c2a`:
  symmetric layout, top hold order, seven capsule cavities, rounded outer
  perimeter, center raised capsule and surrounding U notch.
- [Center detail photograph](https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY-VBL-8gris.webp?v=1770128011),
  YY Vertical, SHA-256
  `5181298718b4860562bc467a1dd818a31e94f18a7219dafd364c413c703e6320`:
  center U relief, recessed center floor, broad slopers and rounded mouths.

No factual dimension or contact-depth disagreement was found. The photograph
is not an engineering drawing: aperture sizes, positions, fillet radii, relief
depths and the rear profile remain display estimates. The geometry is not a
manufacturing model.

## Authored geometry and estimate table

Native coordinates are millimeters, X right, Z up, front Y = -50, back Y = 0.
All left/right geometry uses equal magnitudes and mirrored positions.

| Feature | Authored dimensions | Status |
| --- | --- | --- |
| Overall envelope | 540 X × 90 Z × 50 Y | Published |
| Outer face | Rounded rectangle, radius 18, center Z45 | Estimated silhouette |
| Front perimeter | Native 3 mm edge fillet | Estimated edge softening |
| Side 30° slopers | X -158…-70 and 70…158; rear Z90; front Z61.1325 | Published angle, estimated span |
| Sloper front transitions | Native 3 mm fillets on the front meeting edges | Estimated edge softening |
| Center 20° sloper | X -70…70; rear Z90; front Z71.8015 | Published angle, estimated span |
| Outer top jugs | Remaining top regions outside X±158, including rounded end edges | Estimated extent |
| Upper outer 20 mm pockets | Centers X±213, Z60; inner 82 × 23 opening | Published depth, estimated mouth/location |
| Lower outer 45 mm pockets | Centers X±213, Z23; inner 82 × 24 opening | Published depth, estimated mouth/location |
| Lower inner 25 mm pockets | Centers X±117, Z23; inner 82 × 24 opening | Published depth, estimated mouth/location |
| Center 40 mm pocket | Center X0, Z23; inner 82 × 24 opening | Published depth, estimated mouth/location |
| Cavity perimeter | Rounded rectangle; radius = half-height minus 0.01 mm | Operator-selected capsule approximation |
| Cavity entrance | Mouth expanded 3 mm each side, 3 mm linear chamfer to inner wall | Estimated rounded-mouth approximation |
| Central U notch | Outer 140 × 104, center Z6, radius37, cut from Y-51 to -27 | Estimated relief |
| Raised center island | 106 × 48, center Z17, radius23, retained in U notch | Estimated display shape |

The seven pockets are blind, with actual floors at their published depths.
The center island remains joined through the back of the board. The U notch
is a recessed elastic-band feature, not an invented suspension route. Sloper
front fillets and mouth chamfers approximate photographed soft transitions; no
unpublished manufacturing precision is claimed.

Mounting holes, screws, installation hardware, engraved labels and logos are
omitted from the display model. The omission does not imply that the physical
board lacks mounting holes or markings. This is a wall-mounted board; there is
no suspension sidecar or transient cord.

## Native package and metadata

`Hangboards/yy-verticalboard-light/yy-verticalboard-light.FCStd` contains native
fully constrained analytic Sketcher profiles, extrusions, a perimeter fillet,
ruled cavity lofts, booleans and live `PartDesign::SubShapeBinder` regions.
The source is self-contained with no external files or Python callbacks.
Bindings reference the final body's own faces, including cavity floors and
walls; no coplanar cap hides an opening.

The migration preserves the exact twelve `contacts` objects, including IDs,
names, kinds, depth ranges, finger/grip information and equipment identity.
Product text, dimensions and top-level presentation viewport ratio remain
unchanged. The default presentation changes from raster to model, its aspect
ratio becomes 6.0 to match the new envelope, and `revisionID` becomes
`2026-09-29-native-cad`. The manifest is embedded using
`Tools/HangboardCAD/set_board_manifest.py`; `board.json` is generated at build
time and is removed from the package. The old raster is removed.

The scratch authoring program lives at
`.context/supreme-zebra-light-cad/author.py`; it is not a build input. The
retained shared compiler exports the FCStd directly with the pinned FreeCAD
1.1.3 / OCCT 7.8.1 toolchain and OpenUSD 26.08. The USDZ has no materials or
textures, and its descriptor is generated from the actual exported triangles.

## Verification

`check_native.py` in the same scratch directory checks native reopen/recompute,
all sketch constraints, one connected valid solid, exact published envelope,
all seven published pocket depths, and every contact's membership in the
body's actual exterior shell. Editing `BoardBlank.Edge20Depth` from 20 to
23 mm deepens both 20 mm pockets and their semantic contacts while preserving
every other contact depth. Saving and reopening the edited scratch FCStd
preserves that result; the package source bytes remain unchanged. Results are
retained in `native-report.json`.

Front/side/top and three-quarter Hydra Storm renders of the final USDZ were
visually reviewed. Actual blind cavity floors and walls render cleanly; sorting
artifacts from the lightweight custom painter preview do not occur in Hydra.
`usdrecord` consumes a scratch camera stage referencing the exported package.
Front/side/top compiled-asset previews and the prior committed raster are
retained under `.context/supreme-zebra-light-cad`. The prior asset supplies
only a front/perspective comparison; absent prior side/top images are labeled.
Catalogue-wide validation, staging, reproducibility and native app selection
checks are recorded with the parent migration's delivery evidence.

Final compiled USDZ SHA-256: `1fa575d728b9063446451392db0c618de6ba7106801f8a304c9d70fe9c529876`; 20,108 triangles, 513,237 bytes. Native FCStd SHA-256: `c6c5fbb4377c4fdc8c49a675034746b7063ce891e2fb1b8e63947238b38ea723`. The final generated contacts equal the prior contact objects exactly; the descriptor model hash matches the actual USDZ, which has neither materials nor material bindings.

The primary model display uses an orthographic camera tilted 15° down with 8% fit padding. This is a presentation estimate to make pocket walls and floors visible, not a manufacturer geometry fact.

Final independent delivery results are recorded in [the batch delivery audit](2026-09-29-yy-verticalboards-delivery.md). The pinned rebuild reproduced both the USDZ and descriptor byte-identically.


## Current committed source provenance after finish integration

The standalone compile/rebuild evidence above refers to the source before main's runtime finish metadata integration: `c6c5fbb4377c4fdc8c49a675034746b7063ce891e2fb1b8e63947238b38ea723`. The current committed `yy-verticalboard-light.FCStd` SHA-256 (and Git LFS object ID) is `3963f05f982b4f852ec50aeb9e3db9c2d43dd72ea4fb0ffb464870fc9241dc9d`.

Merge commit `79373106a` added only `presentations[0].media.display.surfaceFinish = "neutral"` using the supported manifest authoring tool. Comparing both source archives confirms identical member inventories and byte-identical geometry members; only `Document.xml` changed. Parsed manifests differ only by that finish field, with every contact and factual field unchanged. The delivered USDZ and descriptor hashes remain those recorded above. This is metadata provenance reconciliation, not a new geometry build or a claim that the new source hash was the earlier reproducibility input.
