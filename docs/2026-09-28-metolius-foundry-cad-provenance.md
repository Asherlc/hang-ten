# Metolius Foundry — native CAD provenance

Date: 2026-09-28. Package `metolius-foundry`, board ID
`metolius.foundry`, revision `2026-09-contact-first`.

## Approved retained evidence

The operator approved this exact three-image set before geometry authoring.
The two Metolius files establish the current revision and published facts. The
Absolute Snow image fills only the otherwise-unpublished oblique-view gap and
cannot override manufacturer evidence.

| File | Original URL | SHA-256 | Permitted evidence |
| --- | --- | --- | --- |
| `2026-09-28-metolius-foundry-cad-sources/manufacturer-front-oblique.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/The-Foundry-Training-Board-white.jpg?v=1759460759> | `c46efe0f05503b5abf7b433d50b255fbccc72a158948e34275e8ae0fa2e15ff9` | Current-revision identity, complete front silhouette, contact layout and bilateral symmetry. |
| `2026-09-28-metolius-foundry-cad-sources/manufacturer-depth-diagram.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/Foundry-depth.jpg?v=1762201186> | `160f7e5f7730fe05369e489d7c83e66b859f6bac129035619a62208eef74ee42` | Exact numbered inventory, finger capacities and published grip dimensions. It does not establish body thickness. |
| `2026-09-28-metolius-foundry-cad-sources/installed-oblique.jpg` | <https://cdn.absolute-snow.co.uk/fullsize/img_C-60550-BLU_05.jpg> | `abd5fb752aae741503168756063adc455f6e73013a04e2b6dd5b3d736479b807` | Qualitative arch, outward taper, relief and side/profile continuity only. |

The source pages were the [Metolius Foundry product page](https://www.metoliusclimbing.com/products/foundry-training-board)
and the [Absolute Snow product page](https://www.absolute-snow.co.uk/metolius-foundry-rock-climbing-training-hangboard).
All three retained images show the same topology despite finish differences:
two outer jugs, two variable side pinches, five mirrored pocket pairs, one
center flat sloper and three center edges. Metolius publishes 22.75 × 8.5 in,
represented as 578 × 216 mm, and describes a CAD/CAM master with perfect
symmetry. It does not publish board thickness, aperture sizes, mouth radii,
jug depth or the variable-pinch section.

## Measurement frame and inventory mapping

This is a simplified **display model**, not manufacturing or load-bearing CAD.
Native coordinates are millimetres: +X right, +Z up, front −Y; the mounting
plane is Y = 0. The tessellated body envelope is exactly X −289…+289 and
Z 0…216. The right half is deliberately drawn and the left half is its exact
reflection.

| Stable contact IDs | CAD region | Published source fact |
| --- | --- | --- |
| `pinch-1-left/right` | Mirrored outer side surfaces | #1 variable pinches; no fixed depth published. |
| `jug-2-left/right` | Upper outer rounded cavities | #2 outer jugs; no depth published. |
| `pocket-3-left/right` | Upper mirrored cavities | #3 32 mm 4-finger pockets. |
| `pocket-4-left/right` | Middle outer mirrored cavities | #4 22 mm 3-finger pockets. |
| `pocket-5-left/right` | Middle inner mirrored cavities | #5 30 mm 2-finger pockets. |
| `pocket-6-left/right` | Lower outer mirrored cavities | #6 15 mm 3-finger pockets. |
| `pocket-7-left/right` | Lower inner mirrored cavities | #7 21 mm 2-finger pockets. |
| `sloper-8-center` | Center rising flat surface | #8 53 mm flat sloper. |
| `edge-9-center` | Upper center cavity | #9 16 mm edge. |
| `edge-10-center` | Middle center cavity | #10 30 mm edge. |
| `edge-11-center` | Lower center cavity | #11 23 mm edge. |

The 18 contact IDs and 19 importer-visible node IDs are unchanged from the
previous package. The deleted `board.json` is embedded byte-for-byte as parsed
manifest data except that the front presentation aspect ratio is corrected
from the prior image-era value `2.6588197894316767` to the published-envelope
ratio `578 / 216 = 2.675925925925926`, and the already-published 53 mm sloper
dimension is represented as a structured exact depth range so the compiler can
gate it. No contact inventory, label, ordering, or training metadata changed.

## Authored construction

The one-off authoring program is workspace scratch at
`.context/hanging-fly-metolius-foundry-cad/author_metolius_foundry.py`; it is
not a build input. The committed FCStd stands alone and is the package's only
canonical source. It contains 39 fully constrained Sketcher profiles feeding
native lofts, extrusions, mirrors and booleans. Final-body
`PartDesign::SubShapeBinder` surfaces define the right and center semantic
regions; native mirrors define their left mates. `HangTenCurvedRegionPartition`
and `HangTenSurfaceNormals` are set. The compiler emits unbound meshes with no
materials or textures.

The front boundary is twenty explicitly authored cubic Bézier spans: ten on
the right from the center plateau around the jug, shoulder and lower wing to
the raised center-bottom arc, followed by an exact reflected return. The right
half's `(start, control 1, control 2, end)` X/Z millimetre points are:

```text
(0,208)   (24,208)  (54,208)  (95,208)
(95,208)  (112,208) (125,207) (137,207)
(137,207) (151,207) (160,216) (181,216)
(181,216) (199,216) (215,205) (230,190)
(230,190) (241,177) (245,157) (250,141)
(250,141) (264,106) (289,58)  (289,29)
(289,29)  (289,7)   (274,0)   (256,0)
(256,0)   (236,0)   (218,4)   (200,9)
(200,9)   (164,17)  (137,28)  (100,33)
(100,33)  (63,38)   (28,38)   (0,38)
```

The two outer jug crests are therefore the 216 mm maxima; the manufacturer
views overrode the superseded display mesh's contrary center-crown emphasis.
The center sloper plateau is Z 208 mm with shallow Z 207 mm saddles into the
jugs.

Ordered cross-sections of the approved pre-migration display USDZ were used
only as a qualitative station guide while the operator deliberately redrew the
macro outline and relief, then normalized the result to the published 578 x 216
mm envelope. No automated fitting or point reduction was performed, so there
is no claimed sample count, reduction tolerance, or maximum/RMS fit deviation;
the authored values below are explicitly unmeasured display estimates rather
than a quantitatively fitted recovery. Manufacturer evidence governed the
contact topology, continuous ribs and shoulders, and the crown correction
above. No source photograph was traced, registered, segmented, vectorized,
cropped, or processed into geometry, and no reference triangles were imported.

A three-section broad-arch loft uses Y/X-scale stations `(0, 0.98)`,
`(-15, 1.00)`, and `(-85, 0.98)`. It is intersected with one continuous shelf
solid whose key Y/Z stations are `(0,0)`, `(0,208)`, `(-12,208)`,
`(-65,191)`, `(-69,180)`, `(-46,102)`, `(-33,36)`, and `(-15,0)`.

Each outer rail and jug is one uninterrupted ruled longitudinal loft through
three deliberately authored, fully constrained, full-height profiles. All
three profiles use the same eight-span X/Z arch boundary. Their depth-wise
parameters `(width scale, height scale, front offset, depth slope)` are
`(1.00, 1.00, 0, 0)` at the rear/root, `(0.68, 0.99, 32.5, 0.20)` at the
shoulder and `(0.22, 0.97, 36, 0.20)` at the nose. The nose is therefore
3.5 mm proud of the shoulders. The resulting physical section has a narrow
nose, two gentle shoulders and two steeper rear bevels. Every facet seam runs
through the complete arch: there are no horizontal stations or hold-height
controls that could create local lobes.

The saved B-rep is intersected at Z 35 / 80 / 125 / 170 mm by the native-source
regression. Every section has five distinct facet normals and four positive
convex turns. The nose occupies 22.0–22.4% of the projected section, shoulder
angles are 8.84–32.51 degrees, and the rear bevels are at least 12 degrees
steeper than their adjacent shoulders.

A second output gate intersects the physical B-rep at 81 heights, every 2.5 mm
from Z 10 through 210 mm. After merging only incidental collinear OCCT edge
splits, all 81 sections retain exactly five facets. The largest adjacent change
is 0.01679 of normalized width, 0.00120 of normalized depth and 1.181 degrees;
the gate also limits second differences and repeated direction reversals. A
valid deliberately flat five-facet control, whose nose occupies 64% of its
section, fails the crown gate. A valid deliberately lumpy five-facet loft fails
the continuity gate. Both negative controls are rebuilt and rejected on every
native-source test run.

The right rail passes OCCT BOP self-intersection checking. Its left mate is a
native mirror. The source audit requires all ten left/right side-pocket
cutter/rail common volumes to equal zero. Live final-body subshape binders
define the right and center semantic contact regions; native mirrors define
the left regions. The binders deliberately omit the inaccessible Y = 0
mounting-plane faces.

The recessed openings were manually reviewed against a 40 × 16 normalized
grid over the published 578 × 216 mm envelope (minor cells 14.45 × 13.5 mm;
stronger lines every fourth cell). This was a deliberate operator reading, not
image detection, tracing, registration, segmentation or fitted geometry. The
selected aperture-sketch centers are:

```text
#3: X ±138, Z 130      #4: X ±178, Z 92       #5: X ±118, Z 97
#6: X ±178, Z 58       #7: X ±118, Z 63
#9: X 0, Z 160         #10: X 0, Z 112         #11: X 0, Z 65
```

The left-side pockets rise toward board center by `+3 / +6 / +6 / +7 / +6`
degrees for #3 through #7; the right-side source sketches use the exact
opposite angles and are mirrored natively. The saved-source test reads the
actual cutter sections and gates every center to ±0.75 mm and every angle to
±1 degree.

Only the 578 × 216 mm envelope, symmetry, inventory and numbered dimensions
above are published. Every remaining dimension is an **operator-selected
display estimate**:

- Maximum compiled body projection is 79.198 mm. After excluding inaccessible
  mounting-plane faces, the exported jug regions span 65.535 mm; the lower
  variable-pinch regions span 70 mm. Both are display estimates, not
  manufacturer-published grip dimensions.
- The #8 center surface is bounded to X ±110 mm. Its front edge is
  Y -65/Z 191 and its rear edge is Y -12/Z 208, preserving the published
  53 mm span without making the flat strip behind the outer jugs selectable.
- Left cavity mouth estimates (the right side is an exact native mirror) are:
  #3 centered X -138/Z 130, 84 x 24 mm, R10 at +3 degrees; #4 X -178/Z 92,
  62 x 22 mm, R8 at +6 degrees; #5 X -118/Z 97, 42 x 22 mm, R8 at +6
  degrees; #6 X -178/Z 58, 68 x 22 mm, R8 at +7 degrees; and #7 X -118/Z
  63, 42 x 22 mm, R8 at +6 degrees. Center #9 is 160 x 22 mm, R8 at Z 160;
  #10 is 158 x 22 mm, R8 at Z 112; and #11 is 158 x 22 mm, R8 at Z 65. All
  mouths use a 3 mm analytic blend. The cavity floors are solved from the local
  analytic bearing surface so their spans are exactly the published 32 / 22 /
  30 / 15 / 21 / 16 / 30 / 23 mm values.
- The thirteen recessed pocket/edge contacts carry CAD-authored mouth outlines for
  stable UI framing and picking. The broad sloper, jug and pinch contacts omit
  optional outlines; their frames derive from the exported contact meshes.

Mounting holes, screws, labels, logos and the swirled finish are omitted under
the repository display-model and no-material policies. Their omission does
not imply that the physical product lacks mounting holes or surface markings.

The superseded runtime asset was resolved from pre-migration commit
`aee1c81defbf93918b69d7682602e698662c55cf` and has SHA-256
`ea9c293327bc2d5125792b35d3c61fc01b8d6ed15d345440ad8afc0a51e41998`.
Its ordered cross-sections served only as the qualitative station guide
described above, while the manufacturer sources overrode it where the crown
silhouette conflicted. It was never compiler input and none of its triangles
are retained in the FCStd.

## Verification and visual review

`compile_board.py` reopened and recomputed the FCStd, found all 18 contacts and
19 nodes. It measured the accessible paired jug regions at 65.535 mm and the
paired pinches at 70 mm, and the remaining authored regions at the exact
published 32 / 22 / 30 / 15 / 21 / 53 / 16 / 30 / 23 mm values. The saved
source audit additionally read the actual cutter sketches and confirmed every
manual grid center, every mirrored side-pocket angle, three constrained
full-height rail profiles, the five-facet convex crown at four heights, no
B-rep self-intersection, and `0.0 mm³` common volume between all ten left/right
rail and side-pocket cutter pairs.

The final unbound USDZ has 19,310 triangles. Reproducible build verification
produced byte-identical USDZ and descriptor files. Package validation passed,
Android staging regenerated the same manifest and copied the same asset and
descriptor bytes while excluding the FCStd, and delivery-lock verification
passed for 49 models, 115 locked files and 34 source-backed packages. Explicit
USD inspection found no material prims, shader prims, material bindings or
texture archive entries; the archive contains only `stage.usdc`.

The retained automated results were:

- `Tools/HangboardModels/tests` plus `Tools/HangboardPackages/tests`: 745
  passed and 1 skipped with the retained, checksum-pinned meshoptimizer v1.0
  library selected explicitly.
- `Tools/HangboardCAD/tests`: 76 passed with the pinned FreeCAD environment;
  the Foundry native integration module accounted for both of its checks.
- Delivery alignment, hard-cut audit and approved-package inventory: 59
  passed.

Signed native-app acceptance passed on a workspace-owned iPhone 17 Pro
simulator `EB912790-8CB2-44A7-B0B8-79D9A3592CD2` running iOS 26.4. The signed
Debug build opened the exact crowned-rail package on the board-detail route.
The default variable-pinch highlight and hold-map selections of the 32 mm deep
left pocket and 15 mm shallow right pocket remained confined to their intended
surfaces. Accessibility exposed `boardDetail.screen`, the tested
`boardModel.contact.<contactID>` values and matching
`boardDetail.selectedHold.<contactID>` values. A raw coordinate tap on the
rendered #3 opening asserted `boardDetail.selectedHold.pocket-3-left`,
exercising RealityKit picking independently of the hold map.

The installed ODR USDZ and bundled descriptor were byte-identical to the
validated package outputs, with SHA-256 values `201e0126...` and `39c4ff35...`.
The signed build carried `com.apple.developer.healthkit = true` and both
non-empty HealthKit usage descriptions. The exact owned simulator was deleted,
its pending/owned records were consumed, and the workspace-local Derived Data
was removed before completion.

An earlier signed run of the initial migration on the installed iOS 26.5
runtime built and installed,
but remained blank before SwiftUI rendered. Process samples showed the app
waiting synchronously in `HKHealthStore.authorizationStatus(for:)`, while that
runtime's `healthd` was stuck submitting a `BGSystemTaskScheduler` request.
Restarting `healthd` and fully rebooting the exact simulator reproduced the
same service deadlock. The unchanged build rendered and completed all checks
above on iOS 26.4, isolating the blank launch to the iOS 26.5 simulator service
stack rather than the board package.

| Review view | Superseded display asset | Native CAD | Side-by-side |
| --- | --- | --- | --- |
| Front | [previous](pr-screenshots/metolius-foundry/previous-front.png) | [CAD](pr-screenshots/metolius-foundry/cad-front.png) | [comparison](pr-screenshots/metolius-foundry/comparison-front.png) |
| Side | [previous](pr-screenshots/metolius-foundry/previous-side.png) | [CAD](pr-screenshots/metolius-foundry/cad-side.png) | [comparison](pr-screenshots/metolius-foundry/comparison-side.png) |
| Top | [previous](pr-screenshots/metolius-foundry/previous-top.png) | [CAD](pr-screenshots/metolius-foundry/cad-top.png) | [comparison](pr-screenshots/metolius-foundry/comparison-top.png) |
| Oblique | [previous](pr-screenshots/metolius-foundry/previous-oblique.png) | [CAD](pr-screenshots/metolius-foundry/cad-oblique.png) | [comparison](pr-screenshots/metolius-foundry/comparison-oblique.png) |

These are orthographic renders of the exact superseded display and current CAD
USDZ bytes. The review renderer applies the same neutral directional lighting
and shadow map to both; it does not change geometry. The CAD is an intentionally
cleaner analytic approximation than the prior sculpted mesh.

The crowned-rail correction was separately rendered against the prior committed
CAD in every required view. Those panels read the exact prior `ce7a54ef...`
and current `201e0126...` USDZ bytes with the same camera and lighting:

| Corrective review | Side-by-side |
| --- | --- |
| Front | [crowned comparison](pr-screenshots/metolius-foundry/rail-refinement-comparison-front.png) |
| Side | [crowned comparison](pr-screenshots/metolius-foundry/rail-refinement-comparison-side.png) |
| Top | [crowned comparison](pr-screenshots/metolius-foundry/rail-refinement-comparison-top.png) |
| Oblique | [crowned comparison](pr-screenshots/metolius-foundry/rail-refinement-comparison-oblique.png) |

The [fine alignment grid](pr-screenshots/metolius-foundry/alignment-grid-fine.png)
shows the manufacturer diagram and current orthographic CAD in separate panels,
each manually framed to the same published envelope and 40 × 16 grid. It is
review evidence only and was never a geometry input.

Representative signed-app captures are the [variable pinch](pr-screenshots/metolius-foundry/app-pinch.png),
[32 mm pocket](pr-screenshots/metolius-foundry/app-deep-pocket.png),
[15 mm pocket](pr-screenshots/metolius-foundry/app-shallow-pocket.png),
[16 mm center edge](pr-screenshots/metolius-foundry/app-center-edge.png),
[center sloper](pr-screenshots/metolius-foundry/app-sloper.png), and
[direct model tap](pr-screenshots/metolius-foundry/app-tap-deep-pocket.png).
The corrective pass also retains the
[orbited raw jug pick](pr-screenshots/metolius-foundry/app-jug-oblique.png).
The final crowned package adds the [inactive/default pinch](pr-screenshots/metolius-foundry/app-faceted-default.png),
[raw-picked 32 mm pocket](pr-screenshots/metolius-foundry/app-faceted-deep-pocket.png),
and [15 mm pocket](pr-screenshots/metolius-foundry/app-faceted-shallow-pocket.png)
captures from the exact installed build.

Final SHA-256 values are:

- FCStd: `d20c657c4a004a88556dc32f89d4fda3ca2c34f23e049c58219991f93bab96d6`
- USDZ: `201e01266d9b95e8305b428e681a64ba39d95c02693aeb1330d40789ec11ce05`
- Descriptor: `39c4ff3594ff8ab05fccf9746f455ed5666d4aa0932bd330e5591fce7e79be1d`
- Delivery manifest: `d2a0e85862156a32c78b6ea84cb9216666ed584fc4d0e9f29a76eb48c6d8fc2b`
