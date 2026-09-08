# Wood Grips Compact II display prototype

This is an editable first-pass 3D display asset for Hang Ten. It recreates the
Metolius Wood Grips Compact II's two rows, tapered body, true carved recesses,
outer shelves, top contacts, and mounting holes. It is not manufacturing CAD.
The existing app package, canonical selection paths, and presentation PNG are
unchanged; installing a 3D viewer is separate work.

## Build and review

From the repository root, with Blender 5.2 installed:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/wood_grips_compact_ii.py
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/verify_wood_grips_compact_ii.py
```

The verifier accepts `-- /path/to/output`; the model build accepts
`-- --output /path/to/output`. Default output is the workspace-owned
`.context/epic-whale-wood-grips-compact-ii/`. No server, simulator, or external
resource is created. `ownership.json` records the generated directory owner.

Outputs include editable `.blend`, image-textured `.glb`, iOS-friendly `.usdz`,
`front.png`, `three-quarter.png`, `selected-holds.png`, a 2048-pixel wood atlas,
and machine-readable `model-report.json`. Verification reimports both actual
exports with the source materials and images removed, checks dimensions within
one micrometer, all 19 hold IDs, 20 meshes, and loaded image textures, then
writes `glb-roundtrip.png`, `usdz-roundtrip.png`, and
`export-verification.json`. Inspect those rendered exports as well as the
source scene before integration. The selected-holds view changes the actual
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

## Primary source audit — reviewed September 8, 2026

| Evidence | Fields justified |
| --- | --- |
| [Manufacturer product page](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards) | Compact identity, published 610 × 157 mm size, wood material. |
| [Official Compact product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg?v=1759460952&width=2000) | Visually reviewed tapered outline, two-row arrangement, five enclosed pockets and two open end shelves per row, top shoulders/channels, pale wood, six visible mounting holes. |
| [Official depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428&width=2000) | The **lower Compact diagram**, not the upper Deluxe: outer jugs, 56 mm flat slopers, 56 mm center round sloper; upper 29 mm edges and 3/2/4-finger pockets; lower 19 mm equivalents. |

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
channel slopes, back surface, screw-hole diameters/countersinks, and texture are
manually selected visual estimates. Bilateral hold symmetry is idealized.
The six mounting-hole positions follow the photograph visually; no hardware is
included. The back and internal pocket sections were not available as measured
evidence. Wood grain/knots vary between manufactured boards; this shader does
not reproduce a particular photographed specimen. Logos are omitted from this
first pass rather than approximating brand artwork.
