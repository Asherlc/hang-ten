# UNLEVEL front-entry comparison packet

Before correction is on the left: exact retained sidecar `d689a72…` from commit `3c770899…`. The revised native-solved result is on the right: `83d4fae…`. All 24 pairs cover four poses × front/side/top × detail/full. Native source, USDZ, descriptor, all 28 before files, and prior geometry/app evidence were hash-verified unchanged.

Start with the default 20 mm view: [front](edge20-front-front-detail.png), [side](edge20-front-side-detail.png), [top](edge20-front-top-detail.png). Then the 90° pocket view: [front](pocket-right-end-front-detail.png), [side](pocket-right-end-side-detail.png), [top](pocket-right-end-top-detail.png). The other front views are [inverted 25 mm](edge25-inverted-front-detail.png) and [reverse jug](jug-reverse-front-detail.png).

The corrected visible leads cross the front recess into the original floor holes. The default and vertical side/top comparisons show the change from the rear approach, while the reverse body continues to occlude the cord. Each pair shares numeric viewport limits and body position. Detail views clip only the generated scene at body bounds plus 15 mm; full views retain the complete routes. Source photographs are neither edited nor used to derive geometry.

[Complete image index](index.html) · [Render provenance and image hashes](render-provenance.json) · [Inspection report](preview-review.json) · [Immutable before snapshot](before/snapshot-provenance.json).

These are CPU z-buffer technical previews of actual unchanged model triangles and exact cached cord routes, with native occlusion. They are not Simulator screenshots or new clearance certificates. This preview lane performed no native solving or package/core edits. Final human acceptance remains pending the individual board review.

[Current native and runtime proof](runtime-validation.json) · [Source mapping and six prior entry failures](source-and-pre-fix-entry-regression.json) · [Independent review](final-independent-review.json) · [Exact regeneration](fresh-reproducibility-result.json). All four native poses reproduced exactly; 31 package tests and 1,258 iOS tests passed, with 3 iOS skips. The first app capture attempt exceeded its 45-second readiness limit; the unchanged warmed installation passed the same checks on retry. Owned simulator deletion and build-output cleanup are verified. Human UNLEVEL acceptance remains pending.
