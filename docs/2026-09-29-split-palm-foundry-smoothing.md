# Split Palm and Foundry surface refinement

The exact product revisions and retained evidence are documented in
[`docs/model-delivery-lock.json`](model-delivery-lock.json) for So iLL Split Palm
and [`2026-09-28-metolius-foundry-cad-provenance.md`](2026-09-28-metolius-foundry-cad-provenance.md)
for the Metolius Foundry. This pass changes display geometry only. Contact
identity, published dimensions, grip depths, and training metadata are carried
from those source audits without revision.

## So iLL Split Palm

The lumpy small pinch and two lower fingers of the canonical half were replaced
by a deliberately authored smooth implicit surface. The globe and two finger
axes, radii, forward depths, and blend width are display estimates chosen by
visual review against the retained [manufacturer front view](https://cdn.shopify.com/s/files/1/0424/1145/products/split-palm-so-ill-white-12-01-so-ill-385627.jpg?v=1677258498)
and [installed oblique view](https://cdn.shopify.com/s/files/1/0424/1145/files/Split-Palm-Lifestyle_S1460618-1800x1200.jpg?v=1658522760).
The implicit surface is meshed at 0.75 mm before export. The small pinch's
globe and right finger retain their pinch contact; the central finger remains
on the body. The other holds and the runtime mirrored instance are unchanged.
The open front surface also exposed backface culling on the reflected instance;
the app's neutral material now renders both sides of model triangles so the
left contact remains visible after reflection.

## Metolius Foundry

The two outer rails now use smooth, nonruled superellipse crown lofts through
the prior reviewed rear and nose profiles. A broad arch envelope uses closely
spaced ruled stations along a smooth scale curve. The 2.4 crown exponent,
stations, and envelope curve are display estimates, reviewed against the
retained [manufacturer oblique view](https://www.metoliusclimbing.com/cdn/shop/files/The-Foundry-Training-Board-white.jpg?v=1759460759)
and [installed oblique view](https://cdn.absolute-snow.co.uk/fullsize/img_C-60550-BLU_05.jpg).
All 18 contact bindings were rebound to the new body surface.

## Visual review

Each panel compares the prior committed USDZ (left) with the compiled result
(right), using the same orthographic camera and neutral renderer.

| Board | Front | Side | Top | Oblique |
| --- | --- | --- | --- | --- |
| Split Palm | [compare](pr-screenshots/soill-split-palm/smooth-refinement-comparison-front.png) | [compare](pr-screenshots/soill-split-palm/smooth-refinement-comparison-side.png) | [compare](pr-screenshots/soill-split-palm/smooth-refinement-comparison-top.png) | [compare](pr-screenshots/soill-split-palm/smooth-refinement-comparison-oblique.png) |
| Foundry | [compare](pr-screenshots/metolius-foundry/smooth-refinement-comparison-front.png) | [compare](pr-screenshots/metolius-foundry/smooth-refinement-comparison-side.png) | [compare](pr-screenshots/metolius-foundry/smooth-refinement-comparison-top.png) | [compare](pr-screenshots/metolius-foundry/smooth-refinement-comparison-oblique.png) |

The source meshes carry no materials or textures. The display omits mounting
hardware, consistent with the prior packages.

## Verification

Both packages pass package validation and rebuild their USDZ and descriptor
byte identically from their committed FCStd sources. The Foundry native source
checks pass, including contact bindings and the smooth crown control cases.
The iOS Debug app builds with both packages. A first board-detail capture
exposed culling on the reflected Split Palm half, prompting the two-sided
neutral material change. Two later isolated simulator attempts stalled in
`simctl launch` or screenshot capture; their exact simulator resources were
deleted. The post-fix appearance therefore still needs an app capture.
