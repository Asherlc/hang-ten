# Wood Grips Compact II display prototype

This is an editable 3D display asset with a second-pass curvature refinement for Hang Ten. It recreates the
Metolius Wood Grips Compact II's two rows, tapered body, true carved recesses,
outer shelves, and top contacts. Mounting holes are deliberately omitted at the
user's request for app display. It is not manufacturing CAD.
The validated USDZ is bundled in Hang Ten for the original bundled Compact II
primary board. SceneKit `BoardModelView` maps its 19 logical hold IDs to picking
and highlighting. The canonical selection paths, 2D fallback, editor, and
presentation PNG remain in use for their existing workflows.

## Build and review

From the repository root, with Blender 5.2 installed:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/wood_grips_compact_ii.py
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/verify_wood_grips_compact_ii.py
```

The verifier accepts `-- /path/to/output`; `-- --format usdz --skip-renders`
checks only a changed USDZ, preserves the other format's report, and marks new
render fields as skipped. The model build accepts
`-- --output /path/to/output`. All three tools derive the default output from
the repository directory name: `.context/<workspace-name>-wood-grips-compact-ii/`
(for example, `.context/epic-whale-wood-grips-compact-ii/`). The highlight tool
uses its `highlights/` subdirectory. These defaults follow a renamed checkout
without editing the scripts. No server, simulator, or external
resource is created. `ownership.json` records the generated directory owner.

Outputs include editable `.blend`, image-textured `.glb`, iOS-friendly `.usdz`,
`front.png`, `three-quarter.png`, `selected-holds.png`, `clay-three-quarter.png`,
`clay-detail.png`, a 2048-pixel wood atlas,
and machine-readable `model-report.json`. Verification reimports both actual
exports with the source materials and images removed, checks dimensions within
one micrometer, all 19 hold IDs, 20 meshes, and loaded image textures, then
writes `glb-roundtrip.png`, `usdz-roundtrip.png`, close oblique `glb-clay-detail.png` /
`usdz-clay-detail.png`, and
`export-verification.json`. Inspect those rendered exports as well as the
source scene before refreshing the app bundle. The selected-holds view changes the actual
upper three-finger pocket meshes to amber.

The build operates solely on directly authored coordinates and analytic
profiles. It does not read, trace, segment, vectorize, crop, or align images.
Reference downloads are research evidence only. The mathematical grain is an
original material, baked to standard PBR base color for export compatibility.
The model uses meters, X across the board, Z up, and front facing negative Y in
Blender. glTF exports use the format's normal Y-up conversion. Each physical
hold is a mesh named with its existing `board.json` hold ID and carries a
`hold_id` custom property. USD prim paths may normalize hyphens to underscores;
the custom property retains the original identity. These mesh partitions are
experimental display surfaces, not replacements for canonical 2D hit paths.

## Refreshing the app bundle

The generator writes only to the workspace-owned `.context` output. It does
not automatically replace the app resource. After regenerating, run the
roundtrip verifier above, inspect the source/export clay views and all 19 hold
highlights, and copy the validated asset selected for app use:

```sh
model_output=".context/${PWD##*/}-wood-grips-compact-ii"
rtk proxy cp "$model_output/wood-grips-compact-ii.usdz" \
  HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz
rtk proxy shasum -a 256 \
  "$model_output/wood-grips-compact-ii.usdz" \
  HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz
```

The two SHA-256 values must match. The current revision 3 asset, with mounting
holes omitted, is
`063dabb454817ad611d5f10f4f5fed7f2826b4c0cbcdb58286974f21912db1c6`.
After a refresh, rebuild and validate the app's 3D display and hold selection;
update this recorded checksum to the newly reviewed asset. The runtime uses
this resource for the original bundled primary board only. Other board
variants and the editor retain their 2D presentation and canonical paths.
The generated `.blend` and its highlight report remain linked by the report's
source SHA; copying the USDZ does not require modifying either artifact.

## Primary source audit — reviewed September 8, 2026

| Evidence | Fields justified |
| --- | --- |
| [Manufacturer product page](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) | Compact identity, published 610 × 157 mm size, wood material. |
| [Official Compact product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg?v=1759460952&width=2000) | Visually reviewed tapered outline, two-row arrangement, five enclosed pockets and two open end shelves per row, top shoulders/channels, pale wood, six visible mounting holes. |
| [Official depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428&width=2000) | The **lower Compact diagram**, not the upper Deluxe: outer jugs, 56 mm outer round slopers, 56 mm center flat sloper; upper 29 mm edges and 3/2/4-finger pockets; lower 19 mm equivalents. |

The photograph and diagram were downloaded and visually inspected before
authoring. Optional local copies belong under the output's `references/`
directory and are not redistributed in the repository.

| Existing hold IDs | Diagram labels / adaptation |
| --- | --- |
| `jug-left`, `jug-right` | Compact 1, outer jugs; rounded depth profile is an estimate. |
| `sloper-flat-left`, `sloper-flat-right` | Compact 2, 56 mm flat slopers; planar channel slope is an estimate. |
| `sloper-round-center` | Compact 9, 56 mm round sloper; curved profile radius is an estimate. |
| `edge-29-left`, `edge-29-right` | Compact 3, 29 mm edges. |
| `pocket-29-three-left`, `pocket-29-three-right` | Compact 4, 29 mm three-finger pockets. |
| `pocket-29-two-left`, `pocket-29-two-right` | Compact 5, 29 mm two-finger pockets. |
| `pocket-29-four-center` | Compact 10, 29 mm four-finger pocket. |
| `edge-19-left`, `edge-19-right` | Compact 6, 19 mm edges. |
| `pocket-19-three-left`, `pocket-19-three-right` | Compact 7, 19 mm three-finger pockets. |
| `pocket-19-two-left`, `pocket-19-two-right` | Compact 8, 19 mm two-finger pockets. |
| `pocket-19-four-center` | Compact 11, 19 mm four-finger pocket. |

There are 19 physical contacts; the diagram's 11 numbers denote **types** with
left/right repeats, not the physical hold count. No hold metadata is altered.

## Explicit display estimates

Only the overall width/height and labeled contact dimensions above are sourced
measurements. Front-to-back thickness is set to **56 mm as a display estimate**
from the top-contact annotation; the manufacturer does not specify that as a
full-body thickness. The 29/19 mm annotations are represented as perpendicular
front-to-back pocket recess depths, an explicitly labeled modeling adaptation
because the diagram does not define a measurement datum or section.

All aperture widths/heights, exact positions, taper, lip radii, top curves,
channel slopes, back surface, and texture are
manually selected visual estimates. Bilateral hold symmetry is idealized.
The six mounting holes visible in the photograph are intentionally absent from
the display model, following the user's September 8 request to remove screw
holes; this is a display simplification, not a claim about the physical product.
No hardware is included. The back and internal pocket sections were not available as measured
evidence. Wood grain/knots vary between manufactured boards; this shader does
not reproduce a particular photographed specimen. Logos are omitted rather than approximating brand artwork.

## Curvature refinement (revision 2)

The first pass represented the silhouette with straight polygon spans, the top
rolls with 11 depth rings, and pocket transitions with only a few straight
segments. A final global bevel was limited by small Boolean intersection edges;
weighted normals could not supply the missing shape. Revision 2 replaces those
features with deliberately authored geometry:

| Feature | Geometry / explicitly estimated section |
| --- | --- |
| Outer silhouette | 24 mirrored cubic Bézier spans sampled at eight intervals each; hand-selected control points follow the official front photograph. |
| Body edge rollover | 57 depth rings; 7 mm bottom-front, 2 mm upper-front and 2 mm back circular roundovers, independent of Boolean edge lengths. |
| Jugs | Fuller elliptical roll with 46 mm depth run and 14 mm drop; angular depth sampling resolves the steep front end. |
| Center round sloper | Continuous elliptical depth profile with 18 mm drop; side sloper channels retain their estimated planar 5 mm slope. Smooth width blends join the three profile types. |
| Pocket backs | 6 mm quarter-circle transition, 12 segments, tangent to the back and sidewalls. |
| Pocket mouths | 3.5 mm quarter-circle rim, 12 segments, tangent to the sidewall and front. Capsule corners use 16 segments per quadrant. |
| Open outer shelves | 6 mm mouth and back fillets give the shelf rails fuller rounded fronts. The upper aperture ends at 122 mm before its mouth fillet, retaining a substantial jug nose above it. |

These radii and cross sections are **display estimates**, not manufacturer
measurements. The official product photograph remains the visual authoring
source. A [2019 Compact II review](https://squamishclimbingmagazine.ca/metolius-wood-grips-ii-compact-hangboard-gear-review/)
also describes rounded pocket backs, corroborating the shape but supplying no
radius or measured section. No image analysis or automatic contour extraction
is used.

The revision keeps all 19 physical contact IDs and one body mesh. The export
ceiling is 150,000 triangles to permit real curvature for mobile display;
`model-report.json` records the actual count and sampling parameters. Curved strips use interpolated normals, and planar Boolean cap faces
are shaded flat to avoid pinched normals around recesses. The texture-free
clay views expose silhouette and surface continuity without wood grain. During
this refinement the original `.blend` and previews were preserved in `v1/`;
`v1/clay-detail.png` and `v1/clay-three-quarter.png` use exactly the same camera,
material, lighting and resolution as the revised clay views.

Revision 3 removes the six mounting-hole and countersink Boolean subtractions
without changing the authored hold curves, dimensions, or 19 contact IDs.
Its editable source, both exports, review renders, and highlight proofs are
regenerated together; the app continues to render the model head-on.

## Individual hold highlight review

After building, render every independently selectable physical hold:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/render_hold_highlights.py
```

The renderer accepts `-- --blend PATH --output DIR` and optional
`--overview-only`. The `highlights/` output includes a numbered overview,
contact sheet, 19 individual views, `index.html`, and a report recording the
source blend SHA. Use these to review contact partitions alongside the clay
geometry views. `--overview-only` refreshes the overview and preserves previous
individual-image and contact-sheet report entries only when the source SHA
matches and their referenced files still exist. A changed source invalidates
those report entries. `--contact-sheet-only` rebuilds the sheet from a complete
set of individual renders tied to the same source SHA.

Run the inexpensive output-path and report regressions without Blender:

```sh
rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py
```

## Native SceneKit export compatibility

Blender can roundtrip Boolean cap n-gons that SceneKit imports incorrectly.
The untriangulated USDZ exposed a filled front cap over the pockets, caused
camera-to-hold rays to hit the body, and left the body without a material.
Renaming the body material to ASCII alone did not fix these symptoms. Explicit
export triangles fixed both: native SceneKit inspection finds one image-backed
PBR material on each of 20 meshes, and the first ray hit matches each of the 19
expected hold IDs. The generator adds temporary triangulation modifiers only
for USDZ export, then removes them; editable geometry and vertex positions are
preserved. The body material now also uses the stable ASCII name
`wood_body_material`.

The screw-hole omission rebuild preserves this triangulation fix. Both exports
receive fresh texture/ID/dimension/triangle roundtrips and review renders; the
verification report records the new asset SHA. Native SceneKit material and
picking checks are recorded separately beside the generated output. Future bundle
refreshes should include native SceneKit checks and app selection validation,
because Blender-only import checks did not catch this platform-specific defect.
