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
canonical source. It contains 47 fully constrained Sketcher profiles feeding
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
`(-65,191)`, `(-69,180)`, `(-46,102)`, `(-33,36)`, and `(-15,0)`. Each outer
wing and jug is one continuous smooth loft, so the semantic boundary at
Z 170 mm does not create a physical seam. The right-side shoulder stations,
written as `(Z, X-center, Y-center, X-radius, Y-radius)`, are:

```text
(0,256,-18,12,12)   (15,267,-22,20,18)  (40,268,-26,25,22)
(80,251,-28,29,23)  (120,232,-32,31,27) (155,212,-39,33,30)
(170,204,-42,36,33) (180,198,-43,38,35) (190,190,-43,39,36)
(203,184,-40,35,29) (216,184,-32,24,16)
```

The left shoulder is the native mirror. Rounded D-shaped sections reach the
mounting plane and keep the upper jug rooted continuously into the shoulder.
Live final-body subshape binders define the right and center semantic contact
regions; native mirrors define the left regions. The binders deliberately omit
the inaccessible Y = 0 mounting-plane faces.

Only the 578 × 216 mm envelope, symmetry, inventory and numbered dimensions
above are published. Every remaining dimension is an **operator-selected
display estimate**:

- Maximum compiled body projection is 79.189 mm. After excluding inaccessible
  mounting-plane faces, the exported jug regions span 65.538 mm; the lower
  variable-pinch regions span 75 mm. Both are display estimates, not
  manufacturer-published grip dimensions.
- The #8 center surface is bounded to X ±110 mm. Its front edge is
  Y -65/Z 191 and its rear edge is Y -12/Z 208, preserving the published
  53 mm span without making the flat strip behind the outer jugs selectable.
- Left cavity mouth estimates (the right side is an exact native mirror) are:
  #3 centered X -155/Z 143, 84 x 24 mm, R10; #4 X -190/Z 99,
  62 x 22 mm, R8; #5 X -110/Z 111, 42 x 22 mm, R8; #6 X -205/Z 45,
  68 x 22 mm, R8; and #7 X -112/Z 63, 42 x 22 mm, R8. Center #9 is
  160 x 22 mm, R8 at Z 155; #10 is 158 x 22 mm, R8 at Z 111; and #11 is
  158 x 22 mm, R8 at Z 65. All mouths use a 3 mm analytic blend. The cavity
  floors are solved from the local analytic bearing surface so their spans are
  exactly the published 32 / 22 / 30 / 15 / 21 / 16 / 30 / 23 mm values.
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
19 nodes. It measured the accessible paired jug regions at 65.538 mm and the
paired pinches at 75 mm,
and the remaining authored regions at the exact published 32 / 22 / 30 / 15 /
21 / 53 / 16 / 30 / 23 mm values. The final unbound USDZ has 24,605
triangles. Reproducible build verification produced byte-identical USDZ and
descriptor files. Package validation passed, Android staging regenerated the
same manifest and copied the same asset and descriptor bytes while excluding
the FCStd, and delivery-lock verification passed for 47 models, 110 locked
files and 31 source-backed packages. Explicit USD inspection found no material
prims, shader prims, material bindings or texture archive entries; the archive
contains only `stage.usdc`.

The retained automated results were:

- `Tools/HangboardModels/tests` plus `Tools/HangboardPackages/tests`: 745
  passed, 1 skipped.
- `Tools/HangboardCAD/tests`: 66 passed, 10 toolchain-gated skips; the
  Foundry native integration module separately passed both checks with the
  pinned FreeCAD environment enabled.
- Delivery alignment, hard-cut audit and approved-package inventory: 59
  passed.

An exploratory collection from the two tool directories' roots also found one
unchanged legacy Training Center script that directly reads that other native
CAD package's intentionally absent `board.json`; two simplification cases in
that command lacked the required `MESHOPT_LIBRARY`. The simplification cases
passed when rerun with the workspace-owned meshoptimizer dylib, and the
maintained `tests/` suites above passed in full.

Signed native-app acceptance passed on a workspace-owned iPhone 17 Pro
simulator running iOS 26.4. The DEBUG board-detail route exposed
`boardDetail.screen` and all 18 `boardModel.contact.<contactID>` identities.
Cold deep links selected the representative variable pinch, 32 mm deep pocket,
15 mm shallow pocket, 16 mm center edge and center sloper, with each
`boardDetail.selectedHold.<contactID>` assertion matching the highlighted
region and detail metadata. After the native-contact correction, the exact
current package was rebuilt and installed: a hold-map selection highlighted
only the accessible left-jug surface, the model was orbited, a different hold
was selected, and a raw coordinate tap on the rendered jug changed the asserted
identity to `boardDetail.selectedHold.jug-2-left`. This exercises the
RealityKit `SpatialTapGesture` path independently of deep links and hold-map
controls and confirms that the removed mounting-plane faces are not part of
the visible highlight. The installed ODR USDZ and bundled descriptor were
byte-identical to the validated package outputs, with SHA-256 values
`ace5309b...` and `419064da...`; the generated manifest and installed
executable also matched their build outputs. The signed build carried
`com.apple.developer.healthkit = true` and both non-empty HealthKit usage
descriptions. The exact owned simulator was deleted after review and its
ownership manifests were consumed.

An initial signed run on the installed iOS 26.5 runtime built and installed,
but remained blank before SwiftUI rendered. Process samples showed the app
waiting synchronously in `HKHealthStore.authorizationStatus(for:)`, while that
runtime's `healthd` was stuck submitting a `BGSystemTaskScheduler` request.
Restarting `healthd` and fully rebooting the exact simulator reproduced the
same service deadlock. The unchanged build rendered and completed all checks
above on iOS 26.4, isolating the blank launch to the iOS 26.5 simulator service
stack rather than the board package.

| Review view | Prior committed asset | Native CAD | Side-by-side |
| --- | --- | --- | --- |
| Front | [previous](../pr-screenshots/metolius-foundry/previous-front.png) | [CAD](../pr-screenshots/metolius-foundry/cad-front.png) | [comparison](../pr-screenshots/metolius-foundry/comparison-front.png) |
| Side | [previous](../pr-screenshots/metolius-foundry/previous-side.png) | [CAD](../pr-screenshots/metolius-foundry/cad-side.png) | [comparison](../pr-screenshots/metolius-foundry/comparison-side.png) |
| Top | [previous](../pr-screenshots/metolius-foundry/previous-top.png) | [CAD](../pr-screenshots/metolius-foundry/cad-top.png) | [comparison](../pr-screenshots/metolius-foundry/comparison-top.png) |
| Oblique | [previous](../pr-screenshots/metolius-foundry/previous-oblique.png) | [CAD](../pr-screenshots/metolius-foundry/cad-oblique.png) | [comparison](../pr-screenshots/metolius-foundry/comparison-oblique.png) |

These are orthographic renders of the exact prior and candidate USDZ bytes.
The review renderer mildly tints recessed planar floors by camera depth so
their boundaries remain legible; it does not change geometry. The CAD is an
intentionally cleaner analytic approximation than the prior sculpted mesh.

Representative signed-app captures are the [variable pinch](../pr-screenshots/metolius-foundry/app-pinch.png),
[32 mm pocket](../pr-screenshots/metolius-foundry/app-deep-pocket.png),
[15 mm pocket](../pr-screenshots/metolius-foundry/app-shallow-pocket.png),
[16 mm center edge](../pr-screenshots/metolius-foundry/app-center-edge.png),
[center sloper](../pr-screenshots/metolius-foundry/app-sloper.png), and
[direct model tap](../pr-screenshots/metolius-foundry/app-tap-deep-pocket.png).
The corrective pass also retains the
[orbited raw jug pick](../pr-screenshots/metolius-foundry/app-jug-oblique.png).

Final SHA-256 values are:

- FCStd: `f8347379dd853b25379e3ca91a88c5b99e587d679e724f522a63fba5b8b8712c`
- USDZ: `ace5309bf78f8c7853a479f2207d4bd02e49371a56c3e5482b2a420a8f5b75cc`
- Descriptor: `419064da025e29a709d07d68ec35f2456951c799ff800cbfe0c9b561f978f8b9`
- Delivery manifest: `d446886830a659bc7f707f80eed3dba79702d8f9a1969ec780088b3e11d5ce0f`
