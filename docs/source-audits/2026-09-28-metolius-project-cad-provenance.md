# Metolius Project — native CAD provenance

Date: 2026-09-28. Package `metolius-project`, board ID `metolius.project`,
revision `2026-09-contact-first`.

## Retained manufacturer evidence

Both files came from the [Metolius Project product page](https://www.metoliusclimbing.com/products/project-training-board)
on 2026-09-28. The operator approved this exact two-image set before geometry
authoring on 2026-09-28.

| File | Original URL | SHA-256 | Evidence |
| --- | --- | --- | --- |
| `2026-09-28-metolius-project-cad-sources/front.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/Project-Board-black-white-swirl.jpg?v=1759459896> | `c28097811b3a53e8ed348b77f8c9382b29d79c00a701703e08b12dc5cb693a60` | Product shape, continuous top sloper, cavity openings, front outline. |
| `2026-09-28-metolius-project-cad-sources/depth.jpg` | <https://www.metoliusclimbing.com/cdn/shop/files/project-depth.jpg?v=1762201307> | `cf66c51d5cc805bbf07505ef917c14cff9ad285d28d55fb6163d38885e667857` | Numbered contact positions, published depths and finger capacities, and left/right symmetry. |

The page publishes 24.5 × 6 in (622 × 152 mm) and says the board has a
CAD/CAM master for perfect symmetry. It describes an arc tapering outward and
downward. No thickness, pocket mouth radius, rail section, or relief depth is
published. The [2026-08-12 Metolius package audit](2026-08-12-metolius-board-packages.md)
records the original contact mapping. The current schema-v3 package has 17
contacts and 18 nodes, including separate left/right flat slopers and the
center round sloper. That current inventory is the migration contract.

The [2026-09-13 cord audit](2026-09-13-model-hangboard-cord-audit.md) classifies
`metolius.project` as having no documented suspension. The general Metolius
[training-board installation manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)
describes screw installation of training boards. The display model omits
mounting hardware and has no cord or suspension metadata.

## Measurement frame and source mapping

This is a simplified **display model**, not a manufacturing or load-bearing CAD
plan. Native coordinates are millimetres: +X right, +Z up, front −Y; the back
plane is Y = 0. The envelope X ±311 and Z 0–152 is Metolius's published
622 × 152 mm. The front photograph supplies the symmetric arc, end-cheek shape,
three pocket rows and the continuous top sloper. The diagram supplies the
contact positions and the numbers below. The operator drew the outline, pocket
mouths and the end section directly; no image segmentation, tracing,
registration, contour generation or previous-mesh profile extraction was used.

| Stable contact IDs | CAD region | Published source fact |
| --- | --- | --- |
| `jug-1-left/right` | Top outer cheek surface | Two outer jugs (#1); no depth published. |
| `flat-sloper-2-left/right` | Recessed top terrace | 55 mm flat slopers (#2). |
| `round-sloper-8-center` | Continuous center cylindrical crest | 53 mm round sloper label (#8); 53 mm was **not** treated as a radius. |
| `pocket-3-left/right` | Upper outer rounded mouths | 45 mm, 3-finger pockets (#3). |
| `edge-4-left/right` | Middle outer rounded mouths | 30 mm edges (#4). |
| `pocket-5-left/right` | Middle inner rounded mouths | 40 mm, 2-finger pockets (#5). |
| `pocket-6-left/right` | Lower outer rounded mouths | 22 mm, 3-finger pockets (#6). |
| `pocket-7-left/right` | Lower inner rounded mouths | 22 mm, 2-finger pockets (#7). |
| `edge-9-center` | Middle center rounded mouth | 39 mm edge (#9). |
| `edge-10-center` | Lower center rounded mouth | 16 mm edge (#10). |

The 17 IDs and 18 importer-visible node IDs, including their exact pairing,
are unchanged from the previous model package. The older flat-board audit's
15-region reading grouped three continuous top surfaces; the later schema-v3
model already separated those into two flat-sloper IDs and one round-sloper ID.
The migration retains the live schema-v3 inventory. The embedded manifest has
the same parsed values, field order and numeric values as the deleted
`board.json`. No training instruction or metadata fact changed.

## Authored construction

The one-off FreeCAD authoring program is workspace scratch at
`.context/migrate-non-corded-hangboard-cad-2/author_metolius_project.py`; it is
not a build dependency. The saved FCStd stands alone. It contains a blocked
Sketcher front outline, an analytic Part body and face-copy contact regions.
The body is a drawn X/Z silhouette clipped against a drawn Y/Z section; each
half is an exact mirror. The 12 recessed mouths are rounded rectangles with
true circular corners and ruled 2 mm mouth chamfers. Every contact region is
copied from the *final body's own faces*, so the compiler partitions triangles
without duplicated coplanar surfaces. The cylinder crest and two top terraces
are likewise selected from final body faces. The document sets
`HangTenCurvedRegionPartition` and `HangTenSurfaceNormals`. All exported meshes
are unbound and carry no materials or textures.

Only the envelope and listed depths are published dimensions. Every other
number below is an **operator-selected display estimate**:

- Maximum front projection 70 mm; the old asset's 76 mm depth was a visual
  cross-check, never an authoring source.
- Symmetric front arc: bottom rises from Z 0 near X ±264 to Z 13 at center;
  the outer jug peaks at Z 152 near X ±285; the center top sits near Z 130.
  The outline is a blocked Sketcher profile and an extrusion clip.
- Sculpted three-tier section: top lip at Y −70/Z 130, middle face at
  Y −58/Z 95–53, lower face at Y −51/Z 48–8, with analytic circular connecting
  arcs. Outer cheeks extend from Z 84 toward the top, with an angled top face.
  The section is an approximation because the approved images supply no end
  view or thickness.
- Center round sloper: R19 cylinder centered at Y −46/Z 111, with a flat rear
  support. The R19 is an appearance choice and does not reinterpret the
  diagram's “53 mm” label.
- Flat-sloper top terraces: X −238…−100 and +100…+238, cut to Z 126 across
  exactly 55 mm front-to-back.
- Mirrored mouth windows (left X limits shown; right is exact reflection):
  #3 −278…−206, Z 88…113; #4 −260…−158, Z 56…83;
  #5 −152…−108, Z 57…82; #6 −258…−176, Z 16…44;
  #7 −151…−109, Z 18…44. Center #9 and #10 use X ±99,
  Z 54…87 and Z 18…47. Corner radii 9–11 mm and the 2 mm chamfer are
  display estimates. Cutter Y extents are exactly the published depths.

Mounting holes, screws, labels and color swirl are omitted from this neutral
model. That does not imply the physical board lacks mounting holes. The old
7.3 MB, 76 mm deep display mesh was used only for visual comparison; it was
neither a compiler input nor a measured geometric reference. Its smooth,
sculpted end section differs visibly from this analytic approximation.

## Verification and visual review

- `compile_board.py` reopened the FCStd and passed 17-contact and 18-node
  checks. Its published-depth gate measured exactly 55, 45, 30, 40, 22, 39
  and 16 mm for the corresponding regions. The compiled asset has 14,130
  triangles, and its descriptor was derived from the reopened USDZ.
- `verify_reproducible.py --package metolius-project` rebuilt the USDZ and
  descriptor byte-identically with pinned FreeCAD 1.1.3 and OpenUSD 26.8.
- `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  passed with generated `board.json` and no on-disk copy.
- Android staging regenerated the manifest with the same parsed values and
  omitted the FCStd. `scripts/verify-model-delivery.py` passed the refreshed
  descriptor/source lock.
- The retained CAD, model and package Python suites passed: 805 tests passed,
  10 skipped with the repository's pinned simplification dependencies.
- iOS: a workspace-owned iPhone 17 Pro simulator (iOS 26.5) ran a current
  Debug build at the board-detail review route. The app loaded the CAD model;
  deep links selected the left #1 jug, left #3 45 mm pocket, right #4 30 mm
  edge, right #7 22 mm pocket, center #10 16 mm edge and center #8 round
  sloper. Each screenshot shows only the named region highlighted with the
  existing board metadata in the selected-hold card. A direct tap on the
  rendered left #3 pocket also selected
  `boardDetail.selectedHold.pocket-3-left` in the accessibility tree.
  The dedicated simulator was deleted after capture, and its ownership
  manifests were consumed. Representative captures are
  [upper pocket](../pr-screenshots/metolius-project/app-upper-pocket.png),
  [middle edge](../pr-screenshots/metolius-project/app-middle-edge.png),
  [lower pocket](../pr-screenshots/metolius-project/app-lower-pocket.png),
  [center edge](../pr-screenshots/metolius-project/app-center-edge.png),
  [round sloper](../pr-screenshots/metolius-project/app-round-sloper.png) and
  [tap selection](../pr-screenshots/metolius-project/app-tap-upper-pocket.png).
- The full `xcodebuild test` command with parallel testing disabled did not
  start a test case after six minutes. Xcode repeatedly emitted debugger
  version lookup messages and left an incomplete `.xcresult`, so the run was
  stopped. This is an **unverified Swift test gate**, not a passing test result.
  The same simulator had completed the Debug build, app launch, deep-link
  highlights and direct model tap beforehand. The exact owned simulator and
  DerivedData were removed by the validation script's exit trap.

| Review view | Prior committed asset | Native CAD | Side-by-side |
| --- | --- | --- | --- |
| Front | [previous](../pr-screenshots/metolius-project/previous-front.png) | [CAD](../pr-screenshots/metolius-project/cad-front.png) | [comparison](../pr-screenshots/metolius-project/comparison-front.png) |
| Side | [previous](../pr-screenshots/metolius-project/previous-side.png) | [CAD](../pr-screenshots/metolius-project/cad-side.png) | [comparison](../pr-screenshots/metolius-project/comparison-side.png) |
| Top | [previous](../pr-screenshots/metolius-project/previous-top.png) | [CAD](../pr-screenshots/metolius-project/cad-top.png) | [comparison](../pr-screenshots/metolius-project/comparison-top.png) |

These are orthographic renders of the previous committed and new USDZ bytes.
Recessed planar floors receive a mild camera-depth tint in the review renderer
so their boundaries remain legible; no geometry was altered for the pictures.
The CAD's side section is visibly simpler than the previous mesh. No manufacturer
side view supports asserting the prior mesh's precise sculpting as product fact.

Previous asset SHA-256: `ce5cdbaaf6fa6cea29d9a5634b7c8a579ca99d3b3c1189dbd4e19148aa1108bb`.
FCStd SHA-256: `1d09434aebccc9e2facad80824fa8632fbfe14b92c0dce938a1812e263c6d72f`.
USDZ SHA-256: `060ba08fd0ea183f59166c34387004efbef8de247956f6e60ba72550ff11cec7`.
Descriptor SHA-256: `4f3a52b8cd9e556323d96632c5bd9c612a25ad16b3958c2d35fa5d188f628e78`.
