# YY VerticalBoard First — native CAD source audit, 2026-09-29

Owner: `supreme-zebra`. Package: `yy-verticalboard-first`. Original package reference: `b7cc2c15df661a913ed0ea9dc14321badb7d6ef5`. The user approved the exact retained two-image evidence set with “y” before native authoring. Astra authored the final analytic geometry. The prior package was raster-only: there is no reference mesh, and no prior side/top asset exists.

## Primary evidence and conflicts

- [YY Vertical product page](https://www.yyvertical.com/en/products/verticalboard-first), checked 2026-09-29: technical details specify 54 × 13 × 5 cm, edge depths 45/33/25/22/20 mm, 35°/20° slopers and two large jugs. The marketing feature list says 25° side slopes, conflicting with the technical section and the approved photograph's 35° labels. This migration follows the technical section and photograph; existing contact facts remain unchanged.
- [Manufacturer full front photograph](https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY-VBF-1gris.webp?v=1770127846), retained as `.context/supreme-zebra-cad-evidence/first-0.webp`; SHA-256 `9979cb00ab74b45d9c53c732671dc1b10949d66b190e13f4eb578e50ddb42ac3`. Supports symmetric inventory, lower recessed tier, raised center island, surrounding recess and the printed center depths 40/24 mm omitted from the page's abbreviated depth list.
- [Manufacturer left-detail photograph](https://cdn.shopify.com/s/files/1/0285/5010/3128/files/YY-VBF-7gris.webp?v=1770127846), retained as `.context/supreme-zebra-cad-evidence/first-3.webp`; SHA-256 `4f11cdc22d36299f45a10a33d02546802ca313b820a773f44b308cc8c17ce9e4`. Supports round cavity mouths, the raised upper tier and printed 25/45/33/20/22 mm depths.

No image detection, tracing, segmentation, cropping, registration, vectorization or raster-driven geometry was used. The operator selected analytic primitives and their unpublished dimensions by visual judgment. Existing raster path coordinates did not supply CAD geometry. The old raster's overall contact layout agrees with the approved product photographs; the photographs govern the modeled relief.

## Facts preserved

All 17 `contacts` objects are retained byte-for-value after JSON decoding, including identifiers, equipment bindings, names, kinds, depth ranges, shape and grip types. Manufacturer, product URL, name, subtitle, dimensions, equipment objects, top-level aspect ratio and presentation identity are preserved. The revision changes to `2026-09-29-native-cad`; primary media becomes model-only and its aspect ratio becomes the authored front envelope 540/130. The existing top-level aspect ratio remains 2.0 as historical viewport metadata, not a physical dimension claim.

## Authored geometry and estimate table

Native axes are millimeters: X right, Z up, front negative Y. Overall envelope is X ±270, Z 0…130, Y −50…0. The published envelope, published slopes, and contact depths are sourced facts. All aperture dimensions, positions, corner radii, tier/relief offsets and round-overs below are display estimates, not manufacturing measurements.

| Feature | Deliberately authored parameters in mm | Basis |
| --- | --- | --- |
| Upper tier | 540 wide × 90 high, center (X,Z)=(0,85), front Y=−50, rear 0, 18 corner radius, 2 front bevel | Published width/depth; photographed broad upper tier; remainder estimated |
| Lower tier | 500 × 56, center (0,28), front −28, rear 0, 25 corner radius, 2 front bevel | Estimated recessed lower rail within published envelope |
| Center surrounding relief | 138 × 70, center (0,63), 34 radius, removal from front to Y=−28 | Estimated photographed U-shaped relief |
| Center island kept inside relief | 108 × 44, center (0,65), 21 radius | Estimated raised 40 mm center cavity surround |
| Left/right 35° slopers | X −160…−70 / 70…160; Y −50…0; plane Z=128+Y·tan(35°) | Angle sourced; span/crest estimated |
| Center 20° sloper | X −70…70; Y −50…0; plane Z=128+Y·tan(20°) | Angle sourced; span/crest estimated |
| Upper outer 25 mm cavities | centers (±212,101), 84 × 24 mouth; front −50; floor −25 | Sourced depth; other dimensions estimated |
| Upper outer 45 mm cavities | centers (±212,65), 84 × 24 mouth; front −50; floor −5 | Sourced depth; other dimensions estimated |
| Upper inner 33 mm cavities | centers (±117,65), 84 × 24 mouth; front −50; floor −17 | Sourced depth; other dimensions estimated |
| Upper center 40 mm cavity | center (0,65), 84 × 24 mouth; front −50; floor −10 | Depth printed in approved manufacturer photo; other dimensions estimated |
| Lower outer 20 mm cavities | centers (±187,21), 84 × 24 mouth; front −28; floor −8 | Sourced depth; other dimensions estimated |
| Lower inner 22 mm cavities | centers (±93.5,21), 84 × 24 mouth; front −28; floor −6 | Sourced depth; other dimensions estimated |
| Lower center 24 mm cavity/notch | center (0,21), 84 × 24 mouth; front −28; floor −4 | Depth printed in approved manufacturer photo; other dimensions estimated |
| All cavity mouths | 11 mm corner radius, 3 mm round-over approximation through stations 0/22.5/45/67.5/90°; throat 78 × 18 with 8 mm radius; flat pocket floor at source depth | Estimated analytic display treatment |
| Left/right jugs | Outer upper wing top and front lip surfaces beyond X ±160, including rounded silhouette corner | Contact presence sourced; exact ergonomic profile estimated |

Exact left/right symmetry is deliberate. Each cavity is an analytic rounded-rectangle loft with a genuine recessed floor; the mouth rounding uses ruled conical/planar stations rather than an imported faceted shape. The top sloper transitions, center relief and small scallops between pocket surrounds are simplified display geometry. Side/back shape remains estimated because the approved images do not dimension those surfaces.

Mounting bores, screws, magnetic-insert mounting hardware, engraved logos and printed labels are intentionally omitted under repository display policy. This does not imply the product lacks them. No suspension is present: this is a wall-mounted board. No materials, textures or material bindings are exported.

## Native source and verification

`yy-verticalboard-first.FCStd` contains 85 fully constrained Sketcher profiles and 139 native objects, using built-in sketch, loft, extrusion, fuse, cut and semantic subshape-binder features. It is a connected valid solid. No imported mesh, static `Part::Feature`, Python feature, external link or per-board build script is required. Floor sketches carry editable `GripDepth` length properties driving native placement expressions. Contact binders track the finished body's actual native cavity faces and are open surfaces.

The throwaway authoring program remains only at `.context/supreme-zebra-first-cad/author.py`; it is not a build input. SHA-256: `0061645e97da5157af52c2ea3d8a08b5e2bd9abc223285a388a55260e08f06a9`.

Embedded metadata was installed with `Tools/HangboardCAD/set_board_manifest.py`. The old committed `board.json` and raster are removed; apps stage generated metadata plus the USDZ/descriptor only. The shared compiler uses pinned macOS FreeCAD 1.1.3 / OCCT 7.8.1 / Python 3.11 and OpenUSD 26.08.

Native reopen/recompute checks passed: all 85 sketches are fully constrained, the 540 × 130 × 50 envelope is exact, all 17 contact IDs bind to open surfaces, and all 12 cavity depths match their published values. Editing `edge_25_leftFloor.GripDepth` from 25 to 27 mm moves that cavity and contact to 27 mm while every other contact's bounds remain unchanged; resetting restores 25 mm. Source archive bytes remain unchanged by checks. Detailed evidence is in `.context/supreme-zebra-first-cad/native-checks.json`.

The shared pinned compiler completed all ten stages, including reimport of the actual USDZ, descriptor regeneration and staged-package validation. Result: 18 nodes (body plus all 17 contacts), 27,228 triangles, 794,699 USDZ bytes, material-free. Model SHA-256: `c945d2fa6433a0416367f80372b3aa4060a7a7c777c80cb58bb0951b2dc664c4`. All twelve scalar contact depths pass the compiler's geometry gate. The report is `.context/supreme-zebra-first-cad/compile-report.json`.

The retained `preview.py` front/side/top diagnostics and independent Storm USD renderer screenshots were generated from the compiled asset and inspected. Screenshots are `.context/supreme-zebra-first-cad/hydra-{front,side,top,three-quarter}.png`. `.context/supreme-zebra-first-cad/comparison.png` presents native front/side/top against the prior committed raster. The comparison explicitly labels the lack of prior side/top geometry; it does not invent those views from the raster. Both the real renderer and analytic preview confirm recessed pocket floors, the upper/lower tier offset, central raised island and sloper planes. The front screenshot's uniform grey shading is the unbound renderer appearance, not a texture or material.

Reproducibility, cross-platform staging and in-app picking validation are performed by the parent migration task and recorded in its review. No external resources were created by this board subtask; FreeCAD and usdrecord subprocesses exited and their exact scratch wrappers were removed by the shared runner.

The primary model display uses an orthographic camera tilted 15° down with 8% fit padding. This is a presentation estimate to make pocket walls and floors visible, not a manufacturer geometry fact.

Final independent delivery results are recorded in [the batch delivery audit](2026-09-29-yy-verticalboards-delivery.md). The pinned rebuild reproduced both the USDZ and descriptor byte-identically.


## Current committed source provenance after finish integration

The standalone compile/rebuild evidence above refers to the source before main's runtime finish metadata integration: `b1a2a3f92522200ee328b1a326187a6f55a6fbcc9bf4ebc2ed9d941a4aaf84b2`. The current committed `yy-verticalboard-first.FCStd` SHA-256 (and Git LFS object ID) is `63b257876d9de260afc6557a1dcc3011711d571772fefb6087da2eea0390eeea`.

Merge commit `79373106a` added only `presentations[0].media.display.surfaceFinish = "neutral"` using the supported manifest authoring tool. Comparing both source archives confirms identical member inventories and byte-identical geometry members; only `Document.xml` changed. Parsed manifests differ only by that finish field, with every contact and factual field unchanged. The delivered USDZ and descriptor hashes remain those recorded above. This is metadata provenance reconciliation, not a new geometry build or a claim that the new source hash was the earlier reproducibility input.


Material-policy integration, 2026-09-30: https://www.yyvertical.com/en/products/verticalboard-first identifies the product body as poplar wood. The generated display metadata now selects `surfaceFinish=wood`, using the shared app renderer palette introduced by PR530. This supersedes the earlier metadata-only neutral selection; no material or texture is bound into the USDZ. `set_board_manifest.py` changed only Document.xml; all geometry archive members remain byte-identical. Current FCStd SHA-256: `7272fc88543714d4fca319648f973dd57c017440d8da9283f8cd361e0bf7205b`. This current metadata hash is not the original compile/reproducibility input stated above. Only the surfaceFinish field changes logically.
