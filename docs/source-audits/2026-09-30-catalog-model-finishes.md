# Model finish source mappings

Model presentations use a shared material palette. This is
an app display choice: wood uses the existing procedural wood finish, molded
plastic/resin uses mint, and granite uses the granite finish. These choices do
not assert manufacturer colorways or exact polymer chemistry. Raster packages
retain their authored image appearance; runtime model finishes do not recolor PNGs.

## Product evidence

The existing package identity, subtitle/contact inventory, descriptor and linked
manufacturer evidence govern each grouping. No geometry, contacts, cords, camera
poses or model bytes change. The two separately sourced Transgression revisions
both use plastic; their polyester/polyurethane distinction remains in their
identities and source audit. Their previous neutral choices are superseded.

| Package | Finish | Evidence and mapping |
| --- | --- | --- |
| `captain-fingerfood-dual` | `wood` | [Package product source](https://en.captainfingerfood.rocks/products/dual-hangboard); All body/contact meshes |
| `captain-fingerfood-unlevel` | `wood` | [Package product source](https://en.captainfingerfood.rocks/products/unlevel-hangboard); All body/contact meshes |
| `mammut-diamond-finger` | `wood` | [Package product source](https://www.mammut.com/us/en/products/2060-00020/diamond-finger-hangboard); All body/contact meshes |
| `metolius-contact` | `plastic` | [Package product source](https://www.metoliusclimbing.com/products/contact-training-board); All body/contact meshes |
| `metolius-simulator-3d` | `plastic` | [Package product source](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board); All body/contact meshes |
| `nature-stone-hanger` | `wood` | [Package product source](https://natureclimbing.com/products/stone-hanger-1); Oak body/wood contacts; the granite contact overrides to granite, bound to `edge-front-20mm-granite` |
| `owl-climb-poker` | `wood` | [Package product source](https://owlclimb.com/index.php/en/prds-2/poker/); All body/contact meshes |
| `surfaces-for-climbing-transgression-2011` | `plastic` | [Package product source](https://en-eva-lopez.blogspot.com/2012/04/transgression-fingerboard-for-high.html); All body/contact meshes; retained revision evidence in `2026-09-29-transgression-cad/sources.json` |
| `surfaces-for-climbing-transgression-2013` | `plastic` | [Package product source](https://en-eva-lopez.blogspot.com/2012/04/transgression-fingerboard-for-high.html); All body/contact meshes; retained revision evidence in `2026-09-29-transgression-cad/sources.json` |
| `tension-flash-board` | `wood` | [Package product source](https://tensionclimbing.com/products/flash-board-2); All body/contact meshes |
| `tension-grindstone-original` | `wood` | [Package product source](https://www.tensionclimbing.com/hangboards/new-board); All body/contact meshes |
| `tension-honestone` | `wood` | [Package product source](https://tensionclimbing.com/products/honestone); All body/contact meshes |
| `tension-whetstone` | `wood` | [Package product source](https://tensionclimbing.com/products/whetstone); All body/contact meshes |
| `trango-rock-prodigy-forge` | `plastic` | [Package product source](https://trango.com/products/rock-prodigy-forge); All body/contact meshes |
| `yy-baguette-evo` | `wood` | [Package product source](https://www.yyvertical.com/en/products/baguette-evo); All body/contact meshes |
| `yy-penta-evo` | `wood` | [Package product source](https://www.yyvertical.com/en/products/penta-evo); All body/contact meshes |
| `yy-verticalboard-evo` | `wood` | [Package product source](https://www.yyvertical.com/en/products/verticalboard-evo); All body/contact meshes |
| `zlagboard-evo` | `wood` | [Package product source](https://www.zlagboard.com/hangboards); All body/contact meshes |
| `zlagboard-pro` | `wood` | [Package product source](https://www.zlagboard.com/hangboards); All body/contact meshes |

Captain Fingerfood uses the wooden product shown in its manufacturer product
presentation; no wood species is asserted. YY Penta Evo explicitly lists poplar
plywood. Nature Stone Hanger explicitly lists oak and granite; its existing
descriptor identifies the granite contact, so no new mesh split is inferred.
[Mammut's retained manufacturer evidence](2026-09-29-remaining-cad/mammut-diamond-finger/source-audit.md)
shows the wooden working surfaces. The board-level wood finish covers the
exported body and contacts; it does not assert a new mapping for metal hardware
omitted from the display model. Original Grindstone uses its retained
archival wooden revision evidence rather than asserting a current product.

Change CAD display metadata with `set_board_manifest.py`, which changes only embedded
manifest metadata and verifies all non-Document.xml archive members unchanged.
The catalog finish coverage test now loads every model package through the real
package consumer and rejects omitted/neutral board finishes. Legacy neutral
decoding remains supported for external fixtures and attachments.

## Retained simulator review

These are unedited simulator screenshots. The controlled comparison uses identical executable and model bytes, with
only display metadata changed between the before and after views. Geometry is unchanged.
The Train view supplies the unselected thumbnail. Hold specs supplies the detail
view; DEBUG review routes select the named contact. Touch automation stalled, so
selection clearing is verified by the real RealityKit scene regression tests,
rather than claimed as a successful automated touch gesture.

| Review | Before | After |
| --- | --- | --- |
| Whetstone wood thumbnail | [Neutral](2026-09-30-catalog-model-finishes-review/whetstone-before-thumbnail.png) | [Wood grain](2026-09-30-catalog-model-finishes-review/whetstone-after-thumbnail.png) |
| Contact plastic thumbnail | [Neutral](2026-09-30-catalog-model-finishes-review/contact-before-thumbnail.png) | [Mint](2026-09-30-catalog-model-finishes-review/contact-after-thumbnail.png) |
| Stone Hanger mixed thumbnail, no selection | [Neutral](2026-09-30-catalog-model-finishes-review/stone-hanger-before-thumbnail.png) | [Wood and granite](2026-09-30-catalog-model-finishes-review/stone-hanger-after-thumbnail.png) |

Detail review: [Whetstone jug](2026-09-30-catalog-model-finishes-review/whetstone-after-detail-jug.png),
[Whetstone pocket](2026-09-30-catalog-model-finishes-review/whetstone-after-detail-pocket.png),
[Contact jug](2026-09-30-catalog-model-finishes-review/contact-after-detail-jug.png),
[Stone Hanger granite edge](2026-09-30-catalog-model-finishes-review/stone-hanger-after-detail-granite.png).
The jug returns to visible wood when the pocket is selected. Contact retains mint
outside the selected red jug; Stone Hanger retains wood outside the selected edge.
[Mammut Diamond Finger](2026-09-30-catalog-model-finishes-review/mammut-after-thumbnail.png)
shows the wood display assignment supported by its product evidence.
