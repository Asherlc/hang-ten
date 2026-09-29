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
canonical source. It contains 61 fully constrained Sketcher profiles feeding
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

Each outer rail and jug is one continuous quadratic longitudinal loft through
25 explicitly authored polygon sections. Every section has seven straight
edges: a mounting-plane root, an outer rear edge, two outer/front facets, the
front crest, an inner/front facet, and a separate pocket-facing guard. This
makes the molded-looking facets run along the rail instead of stacking rounded
cross-sections into visible horizontal lumps. The rear root may turn inward
behind a pocket, while the guard remains outside its cutter. The source audit
requires each right-side cutter/rail common volume to equal zero; native
mirroring provides the identical left-side clearance. The quadratic degree is
also checked with OCCT's BOP self-intersection test; a cubic trial was rejected
because it overshot between the close clearance stations.

The right-side stations, written as `(Z, rear-root X, guard X, center X,
center Y, outer-X radius, Y radius)`, are:

```text
(0,230,240,256,-18,12,12)    (8,225,235,261,-20,16,15)
(15,220,232,263,-22,20,18)   (25,215,228,262,-24,24,20)
(40,210,221,260,-27,28,23)   (50,202,221,258,-28,30,24)
(60,195,221,256,-29,31,25)   (70,188,221,253,-30,32,26)
(77,183,220,251,-31,33,27)   (80,180,218,250,-31,34,27)
(90,173,218,248,-32,35,28)   (100,165,218,246,-33,37,29)
(110,158,218,244,-34,39,30)  (112,156,196,238,-34,40,30)
(113,155,190,232,-34,40,30)  (120,145,189,225,-35,41,31)
(130,136,189,222,-36,42,32)  (140,130,189,220,-38,43,33)
(148,126,188,213,-40,45,34)  (155,125,170,202,-41,46,34)
(170,128,140,190,-43,46,34)  (180,129,138,188,-44,45,35)
(190,131,138,187,-44,44,36)  (203,134,145,184,-40,36,29)
(216,146,158,184,-32,24,16)
```

The left rail is the native mirror. Live final-body subshape binders define the
right and center semantic contact regions; native mirrors define the left
regions. The binders deliberately omit the inaccessible Y = 0 mounting-plane
faces.

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

- Maximum compiled body projection is 80.011 mm. After excluding inaccessible
  mounting-plane faces, the exported jug regions span 70.3 mm; the lower
  variable-pinch regions span 77 mm. Both are display estimates, not
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
19 nodes. It measured the accessible paired jug regions at 70.3 mm and the
paired pinches at 77 mm, and the remaining authored regions at the exact
published 32 / 22 / 30 / 15 / 21 / 53 / 16 / 30 / 23 mm values. The saved
source audit additionally read the actual cutter sketches and confirmed every
manual grid center, every mirrored side-pocket angle, 25 seven-edge sections
per rail, no B-rep self-intersection, and `0.0 mm³` common volume between each
right rail and pocket cutters #3 through #7. Native mirroring provides the
same left-side clearance.

The final unbound USDZ has 28,161 triangles. Reproducible build verification
produced byte-identical USDZ and descriptor files. Package validation passed,
Android staging regenerated the same manifest and copied the same asset and
descriptor bytes while excluding the FCStd, and delivery-lock verification
passed for 47 models, 110 locked files and 31 source-backed packages. Explicit
USD inspection found no material prims, shader prims, material bindings or
texture archive entries; the archive contains only `stage.usdc`.

The retained automated results were:

- `Tools/HangboardModels/tests` plus `Tools/HangboardPackages/tests`: 744
  passed and 1 skipped on the pre-refresh run; its only failure was the
  intentionally stale delivery-lock checksum. After refreshing that checksum,
  the focused delivery-lock module passed all 8 checks.
- `Tools/HangboardCAD/tests`: 66 passed, 10 toolchain-gated skips; the
  Foundry native integration module separately passed both checks with the
  pinned FreeCAD environment enabled.
- Delivery alignment, hard-cut audit and approved-package inventory: 59
  passed.

Signed native-app acceptance passed on a workspace-owned iPhone 17 Pro
simulator `68FA5F07-FDC1-4864-873A-E57124370138` running iOS 26.4. The signed
Debug build opened the exact faceted-rail package on the board-detail route.
The default variable-pinch highlight and hold-map selections of the 32 mm deep
left pocket and 15 mm shallow right pocket remained confined to their intended
surfaces. Accessibility exposed `boardDetail.screen`, the tested
`boardModel.contact.<contactID>` values and matching
`boardDetail.selectedHold.<contactID>` values. A raw coordinate tap on the
rendered #3 opening asserted `boardDetail.selectedHold.pocket-3-left`,
exercising RealityKit picking independently of the hold map.

The installed ODR USDZ and bundled descriptor were byte-identical to the
validated package outputs, with SHA-256 values `ce7a54ef...` and `c910f0e7...`.
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

The faceted-rail correction was separately rendered against the prior committed
CAD in every required view:

| Corrective review | Side-by-side |
| --- | --- |
| Front | [faceted comparison](../pr-screenshots/metolius-foundry/rail-refinement-comparison-front.png) |
| Side | [faceted comparison](../pr-screenshots/metolius-foundry/rail-refinement-comparison-side.png) |
| Top | [faceted comparison](../pr-screenshots/metolius-foundry/rail-refinement-comparison-top.png) |
| Oblique | [faceted comparison](../pr-screenshots/metolius-foundry/rail-refinement-comparison-oblique.png) |

The [fine alignment grid](../pr-screenshots/metolius-foundry/alignment-grid-fine.png)
shows the manufacturer diagram and current orthographic CAD in separate panels,
each manually framed to the same published envelope and 40 × 16 grid. It is
review evidence only and was never a geometry input.

Representative signed-app captures are the [variable pinch](../pr-screenshots/metolius-foundry/app-pinch.png),
[32 mm pocket](../pr-screenshots/metolius-foundry/app-deep-pocket.png),
[15 mm pocket](../pr-screenshots/metolius-foundry/app-shallow-pocket.png),
[16 mm center edge](../pr-screenshots/metolius-foundry/app-center-edge.png),
[center sloper](../pr-screenshots/metolius-foundry/app-sloper.png), and
[direct model tap](../pr-screenshots/metolius-foundry/app-tap-deep-pocket.png).
The corrective pass also retains the
[orbited raw jug pick](../pr-screenshots/metolius-foundry/app-jug-oblique.png).
The final faceted package adds the [inactive/default pinch](../pr-screenshots/metolius-foundry/app-faceted-default.png),
[raw-picked 32 mm pocket](../pr-screenshots/metolius-foundry/app-faceted-deep-pocket.png),
and [15 mm pocket](../pr-screenshots/metolius-foundry/app-faceted-shallow-pocket.png)
captures from the exact installed build.

Final SHA-256 values are:

- FCStd: `156d6045c6a9c945efcab96ce21079977f50e47afbd9e775feb74ca2e39065e6`
- USDZ: `ce7a54ef2a5861fc6d29da3dde911de5d01eee1ba9b2417a3df1037113497576`
- Descriptor: `c910f0e78bf137a73bf5a321a570b919d657a65ff746fb784b6545ccbd0e754b`
- Delivery manifest: `809c5b8024edd1c5382bc5a1dd35fe06b9a6fb887e5743792abc343587ee6851`
