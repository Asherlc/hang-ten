# Port-A-Board cord correction — review 5

The old cords changed sideways direction at the upper shoulder because each
route was constrained to a fixed-X section while the actual support was at the
board's center. The renderer faithfully drew that saved bend. The revised
native sections contain the actual support and mouth, so the visible leads
continue diagonally across the face. Remaining bends follow the upper rim and
the real mouth rims. The user accepted the shown revised cord routing with “Y”;
see the [human review record](../human-review.json).

Only `suspension.json` changes in the board package: authoring selects
`sectionPlane: "anchor"` and `pathSearch: "aStar"`; the native solver generates
new routes and hanging height. The support is `[0, 0.17, 0]` in world metres.
All six poses settle at translation Y `-0.12409166` m. The four 300 mm visible
lead lengths and 1.5 mm radii remain the prior audited display estimates. The
native source, USDZ, descriptor, contacts, actual mouths, rotations and cameras
are byte-identical to baseline commit
`3fd0418d9a66d489cdb515ca3a3e82b4ec52121e`.

The [retained manufacturer photos](../native-authoring.md) establish visible
front/rear entries and diagonal leads without a lateral shoulder guide:
[front reference](https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840)
and [manufacturer product page](https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard).
The native model has four blind entrance wells; the current evidence does not
establish their hidden connections. This correction keeps that topology and
adds no collar, guide, passage or inferred join. The photos were reviewed
directly; no geometry was extracted from pixels.

The optional A* search uses the existing native visibility graph and actual
three-dimensional endpoint distances. Obstacles, graph stations, edge costs
and all clearance gates are unchanged. Omission preserves the original
Dijkstra search. Exactly identical physical pose inputs can reuse a result
within one invocation; no symmetry is inferred, and height is still solved
from the cord lengths. The actual native one-lead benchmark produced exactly
the same path with both searches. The selector is authoring metadata and does
not appear in the generated app manifest.

Independent native review measured the front-projected first shoulder turn at
12.3291° before and 0.0108° after. The corresponding three-dimensional turn
fell from 12.2576° to 0.8014°, and the tangential unit-tension residual fell
from 0.212762 to 0.00005867. The revised first bearing follows the native
cylindrical upper rim. Across all poses, turns above 5° occur only near the
actual mouth rims; none has more than 0.25 mm physical gap. See the
[native surface review](physical-review/physical-acceptance.json).

All 24 exact rounded runtime paths pass native signed-distance, whole-tube,
self/interstrand, actual-mouth, outward-entry and length checks. The minimum
certified centerline clearance is 1.490419 mm, passing the unchanged 1.5 mm
radius minus 10 µm numerical gate. A separate fresh solve used the frozen
source and authoring facts without cache seeds: apply/check reports are
byte-identical at SHA-256
`c94c4fa845fd35f8e16260620eb9c5ce9dd952242d2662b1ac1ef850243b5acc`.
The [closure report](native-solve/fresh-reproducibility-result.json) binds the
final sidecar `0ca4bb1e…`, solver and source hashes, and confirms all other
205 baseline package files are unchanged.

Validation passed: the retained CAD/model/package Python collection has 671
passed and 10 skipped tests; the full `HangTenTests` target has 1,264 passed,
3 skipped and 0 failed tests. The current app was built for and installed on
the owned iPhone 17 Pro / iOS 26.5 simulator. Six canonical contact selections
were captured and inspected, with no cord accessibility or picking targets.
All 64 generated packages, 58 model packages and 60 ODR assets match the source
and installed delivery; Apple/Android generated manifests match. The exact
owned simulator, DerivedData and result bundle were deleted and verified.
Commands, raw logs and identities are in [validation](validation-summary.json).

[Fresh app before/after](app-before-after.png) shows the same selected 30 mm
edge and camera. [Front/side/top comparison](front-side-top-comparison.png)
puts the prior committed asset on the left and revised routes on the right.
The [full comparison gallery](previews/index.html) shows all six poses in four
views, using the unchanged USDZ and exact saved cord points in a common world
frame. These are technical capsule previews; the app captures are separate.
No cropping, source registration or path smoothing was used. Retained inputs,
raw evidence and logs are copied byte-for-byte and bound by
[artifact checksums](retained-artifact-sha256.json).

This is a finite native section/path approximation. The checks do not assert
dynamic equilibrium, a global minimum, manufacturer cord dimensions or
unknown hidden connections. Physical-device orbit was not checked.
Port-A-Board (#5) is reviewed; Mammut Diamond Finger (#6) is next. Earlier
boards retain their recorded acceptance.
