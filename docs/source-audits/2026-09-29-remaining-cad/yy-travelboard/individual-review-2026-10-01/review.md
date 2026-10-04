# #19 TravelBoard individual review

**Human acceptance: pending.** This is the individual review of the wood finish and shorter cord presentation, with the existing native geometry preserved.

## Source and geometry

Reused the approved whole manufacturer evidence in [sources.json](../sources.json). Published dimensions are 340 × 100 × 30 mm; edge depths are 25, 15 and 10 mm. All six logical contact records are unchanged. Other opening dimensions, radii, shallow well depths and placements remain estimated display geometry, as labeled in the [native audit](../native-authoring.md). No source image was measured, traced, cropped, segmented or registered.

Astra found no demonstrated geometry or pose correction: one valid native solid, six contact skins with exactly zero off-body area, and upward-facing bearing witnesses in both existing poses. Each recessed edge includes thirteen actual floor, rail, curved-end and mouth-round faces. Mono regions include the bore and both mouth rounds; the tray includes the top and front/rear rounds. See [shape/pose review](shape-audit/review-summary.json) and [whole native views](shape-audit/native-six-whole-views.png).

The original display was raster-only. [Whole original front/rear rasters beside the native export](comparison/original-raster-native-front-rear.png), [native front/side/top](comparison/native-front-side-top.png), and [whole maker/native angles](comparison/maker-native-angles.png) are retained. Original 3D side/top views do not exist and are not synthesized.

Straight-on neutral shading hides the shallow rear wells because their flat floors share the rear face's lighting. Both native measurement and independent actual USDZ triangle checks confirm both rear wells and all four side mouths: [actual export proof](package-checks/actual-usdz-mouth-verification.json). The [depth-buffered rear oblique](comparison/rear-depth-cue-final.png) shows them. The first painter-sorted oblique produced overlap artifacts; its exact image and limitation report remain separate. No geometry was changed to fix a preview renderer.

## Finish and native preservation

The only FCStd change is the existing `display.surfaceFinish: wood` field, set through `set_board_manifest.py`. All other document properties, native object data and geometry archive members are byte-identical. [Setter provenance](metadata/wood-manifest-provenance.json) and [independent geometry bridge](package-checks/wood-bridge.json) connect the final source to the original hash-bound native edit, compiler and reproducibility proofs. Those historical proofs are unchanged; an identical export was not repeated.

The actual USDZ and descriptor are byte-identical to the original native migration. Seven meshes remain unbound, with no materials, shaders, bindings or textures. The existing app renderer supplies wood appearance; grain is a display treatment.

## Shorter cord presentation

The four visible leads retain the same evidenced side mouths, anchor, two poses and native bearing planes. Rear wells remain shallow and unconnected. No hidden passage, end-to-rear connection or supplied rope length is inferred.

The prior 380 mm display lengths made a tall presentation and did not individually match the upper lead paths. A scratch 280 mm lower-lead solve derived upper visible lengths of approximately 255.5401 mm. The matched trial and official native solver regeneration preserve the actual geometry and produce a hanging height of −1.618635 mm in both poses. Each final path/rest-length ratio is approximately one. Lengths, radius, support and plane inclinations are display estimates, not manufacturer rope measurements.

[Official apply](cord-final/apply.json) and [independent regeneration check](cord-final/check.json) bind the final source and unchanged model. The collider's measured geometry is unchanged; its final metadata-only source binding has [explicit derivation provenance](cord-final/collider-provenance.json), while the original measured collider is retained unchanged.

Conservative continuous clearance bounds are 1.4904368–1.4912207 mm for a 1.5 mm cord radius, passing the unchanged 0.01 mm numerical tolerance; these values do not claim a positive air gap. Exact native checks place bend centers 1.6857–1.7000 mm from real rim/outlet surfaces, consistent with the estimated 0.2 mm clearance. Whole [front-pose cord views](shape-audit/front-25-15-short-review.png) and [rear-pose cord views](shape-audit/reverse-10-short-review.png) show supported turns without a distant free-air kink. These constrained static routes do not certify unrestricted sliding, frictional equilibrium or safety.

## Validation and retained history

Final source/sidecar hashes and principal proofs are in [verification-index.json](verification-index.json). Final parser, actual USD inspection, iOS/Android staging and all six unchanged contact facts pass. [Final package checks](package-checks/final/published-package-verification.json) and [native/freeze comparison](package-checks/final/native-metadata-and-freeze.json) preserve exact raw output.

Fresh isolated app validation is retained in [the runtime record](ios/final-runtime-validation.json): all six selections, both poses and gentle orbits, actual scene picking/reset, cord non-pickability, and an unchanged existing Horst routine using the 15 mm edge. That routine is a runtime example, not a YY training prescription. No renderer, solver or routine code changed for this board.

The fresh build and one focused native-pose test passed. Physical interaction checks passed eleven assertions covering actual selection, orbit/reset and non-pickable cords. Main visual review inspected all six selections, both obliques, and settled active/rest workout highlights. The first immediate-launch accessibility query failed with “No translation object returned”; its exact raw failure remains retained, and a separate retry after launch settled succeeded.

The exact owned Simulator, DerivedData and both result bundles were deleted and independently verified absent. The 245 retained runtime files were copied byte-for-byte; see [copy and cleanup verification](ios-copy-and-cleanup-verification.json).

Historical source/export/app reports and failure or superseded-preview statuses remain intact. Display checks do not establish manufacturing or ergonomic accuracy. Acceptance requires the user's reply to the displayed review.
