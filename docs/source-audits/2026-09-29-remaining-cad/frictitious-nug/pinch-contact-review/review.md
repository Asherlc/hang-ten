# The NUG pinch: upper and lower rims onto front/back

Selecting the 60 mm pinch now highlights both opposing rims and their returns onto the front and rear faces. The shared upper surface stays the primary 40 mm jug when picked; selecting jug still lights only that upper surface. Each physical contact mesh is exported once, and selection uses the union of its contact memberships.

The user clarified “Upper and lower rims onto front/back” and accepted the displayed result with “looks good, cord is too long tho”. This accepts the pinch highlight; the separate shorter-cord request keeps review #4 active.

Four operator-selected 94 × 9 mm planar returns join the original rounded upper/lower bearing surfaces. The straight grip span and existing CAD tangent/cavity-mouth boundaries define these display regions. Exact finger-placement boundaries are user-directed display choices, not manufacturer anatomical measurements. The [manufacturer page](https://frictitiousclimbing.com/products/the-nug) supports the 130 × 60 × 40 mm size, published grip dimensions and 6 mm cord; retained source evidence remains in the parent evidence packet. The in-use photo shows an edge grip and does not establish the pinch boundaries.

Native face seams meet all four patches exactly. The assembled wood remains one valid solid with zero added/removed solid volume, zero added/removed boundary area and zero boundary distance. Original native wood/sketch and five other contact archive members remain byte-identical to the baseline. The final exported jug and four edge vertices, normals and triangles match the baseline exactly. Body triangulation changes at the authored seams; identical whole-model triangulation or raster pixels is not claimed.

- [Front/side/top/oblique beside prior committed asset](pinch-60-overview.png)
- [Final front/rear/oblique extent](pinch-60-wraparound-overview.png)
- [Jug selection comparison](jug-40-overview.png), [all comparison views](index.html)
- [Fresh six app views](app-review/index.html), [pinch app screen](app-review/outer-lower-front.png), [jug app screen](app-review/outer-upper-front.png)
- [Verification and exact capture-time hashes](verification.json), [native authoring](native-authoring/authoring-provenance.md)
- [Independent final mesh coverage](independent-geometry-validation/final-coverage-verification.json), [native solid/seam proof](native-authoring/seamed-native-proof.json)
- [Byte-identical rebuild](native-cord/fresh-reproduction.log), [24 full-route native certificates](native-cord/post-apply-native-certificates.json)
- [Python code review](independent-code-review/python-review.md), [Swift code review](independent-code-review/swift-review.md), [fixture correction](runtime-contract/runtime-fixture-review-supplement.json)
- [Exact retained artifact hashes](retained-artifact-sha256.json), [prior committed package/app snapshot](before/snapshot-provenance.json)

Validation: 647 Python tests passed (10 skipped); 1,264 iOS tests passed (3 skipped), including actual NUG membership, primary picking and highlight transitions. All 64 generated packages and 60 ODR assets match the installed Apple bundle and canonical Android staging. Fresh native solve checks and all 24 complete cord certificates pass across six poses. These canonical app captures do not establish physical UI orbit behavior or full rope equilibrium.

This packet records the accepted pinch revision with the previously displayed 300 mm cord leads. Its sidecar SHA is capture-time evidence; the follow-up shorter-cord packet supplies the current cord identity after promotion. The prior 6 mm diameter packet and original migration reports remain byte-preserved historical evidence.
