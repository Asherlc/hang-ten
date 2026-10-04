# #17 Baguette Evo individual review

Human review is pending. This packet reviews the existing native CAD migration
and corrects its wood appearance and selected-contact hanging orientation.

## Retained evidence and native geometry

The [approved manufacturer source set](../source-register.json) is reused.
Whole product, end, relief and loaded photographs were visually inspected;
no images were measured, cropped, traced, segmented or registered. The maker
page identifies a wooden board. The opposed 10/20, 15/25 and central 25/30
labels and Turn & Pull end marking support rotating between bearing rails.

Native geometry, the material-free USDZ and descriptor remain byte-identical
to the initial migration. All thirty constrained sketches, one valid solid,
and twenty selectable regions for nineteen contact IDs reopen/recompute.
An independent in-memory depth edit changes the intended features and restores
the original volume; nothing from that temporary test is saved.

The 520 × 50 mm cylindrical envelope and published depths are preserved.
The native machined cavity ends are squarer than the original display mesh;
radii and other unspecified details remain display estimates. This is a
display model, not manufacturer CAD or a manufacturing/ergonomic specification.

[Original display mesh/native front, side and top](original-native-front-side-top.png)
compares the original asset from `d0e4e95191e4a76822815bb4eeef3a32caa6fea0`
with the unchanged current native export. Both are board-only views; cords
exist only as transient app geometry.

## Corrections

The existing renderer now receives `surfaceFinish: wood` from the embedded
manifest. No material, shader, texture or cord is added to the USDZ.
Only the manifest member of the FCStd archive changed; native shape members
and all nineteen contact identities, names, depths and kinds are preserved.

Ten flat bearings faced down in the former five shared poses. Native closed-solid
probes establish the outward normals of the source-depth witness rails. Nine
contact groups now select independent poses: paired 10/15, paired 20/25,
paired 12, paired 8/6, central 25, central 30, central 20, central 6 and tray.
All eighteen flat depth-witness bearings point upward. The tray's curved
bearing region also faces upward, including the former downward portion.
All five original position IDs are preserved for their original representative
contacts; four additional opposing positions are added.

Exact rotations and camera tilts are display adaptations derived from native
bearings, not published manufacturer angles. The [orientation audit](orientation-audit/recommendation.json)
retains the measured normals, before/after values and source observations.
The legacy `edge-6-upper` and `edge-6-lower` names identify native left/right
U-groove copies; their existing highlighted regions include both sidewalls
and the floor. Their IDs, names and physical contact geometry are preserved.

## Suspension

The four evidenced through-bores and two visible rear returns are retained.
No hidden U-channel, knot or connection is inferred. Native collision geometry,
cord radius, strand lengths, mouths, front-entry axes and support are unchanged.
The nine poses use newly generated native-solid routes. The supported A* search
option searches the same native visibility graph and reuses identical rotations.
The interrupted earlier Dijkstra run is retained with its actual status.

Cord sizes, visible strand length limits and support placement remain labeled
display estimates. Routes describe a static constrained approximation; they
do not establish friction, dynamic loading or full mechanical equilibrium.
The solver uses its existing 10 micrometre certificate tolerance.

## Verification

Independent package/source/pose proofs are retained in [package-checks](package-checks/).
The source editability and published depth proofs remain applicable because
the underlying native members and USDZ bytes are unchanged; no unchanged
CAD export was rerun. Fresh app and final cord results are appended below.

The first package staging attempt correctly rejected unsorted orientation
keys. The raw failure and exact temporary-resource cleanup are retained in
[ios-before-ordering-fix](ios-before-ordering-fix/). Sorting those keys changes
serialization order only. The independent corrected parser and iOS/Android
staging checks pass; native geometry, contact facts and solved cord data
remain unchanged by that ordering fix.

The source hash for the corrected review is
`7f1a6c34c92984b7f8ac89007051ce49ed3cd358290293018cdb8cb2ec8d69a7`.
Model hash stays `5532e902fb8b08fed6f7a6e1bafd2545e7bcd9ecd04347431e6430a9572efcf3`;
descriptor stays `6d2ebee364902217e14714444991f43654a52a8734c4d32076d27ba333137921`.
The new cord sidecar is `b2f47d3c3a036b942554c030dba9941e8254b270b29d520159a091f6fa62acd7`.

The regenerated routes pass all nine poses. Minimum conservative centerline
clearance is 1.99275 mm against the estimated 2 mm cord radius: this meets
the existing 10 micrometre numerical tolerance, not a strictly positive
wood-to-cord gap. Longest visible lead length ratios remain approximately 1.
The shorter strands are represented route portions, not a claim that all
separate visible length budgets independently form taut physical loops.

The [final source-bound cord check](pose-correction/final-sorted-cord-check.json)
reproduces every stored route and hanging height against the final native
source. The [collision comparison](pose-correction/collider-sort-preservation.json)
confirms the metadata key-order correction changed no collision geometry.
