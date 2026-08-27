# Mammut Diamond Finger Hangboard source audit

Reviewed 2026-08-27 for product `2060-00020`, package `mammut-diamond-finger`, and board ID `mammut.diamond-finger`.

## Evidence and caveats

| Source | Package use | Caveat |
| --- | --- | --- |
| [Mammut product page](https://www.mammut.com/int/en/products/2060-00020/diamond-finger-hangboard) | First-party identity and canonical `productURL`. | The live regional page resolved to the exact product but did not expose an inventory or front view to the reviewer. |
| [Mammut manual](https://static.mammut.com/file/2060-00020_man_en_070420_DiamondFingerHangboard_Manual.pdf) | First-party confirmation of Diamond Finger identity, mount plate and silicon phone-mount instructions, tilt warning, one-user/100 kg limit, and home/studio use. | Installation/safety document only: no named hold inventory, depth, capacity, or front-view hold guide. |
| [Backcountry archive](https://www.backcountry.com/mammut-diamond-finger-hangboard) | Archival 21-item inventory, 33.5 in width, walnut material, rope attachment points, phone holder, and front view manually reviewed for bilateral layout. | Retailer evidence, not manufacturer evidence. Its source image was never copied, cropped, registered, traced, vectorized, or used as app art. |
| [Climb Smart Shop archive](https://climbsmartshop.com/products/diamond-finger) | Independent product-identity corroboration and reported Zlagboard/development attribution. | Retailer evidence; no geometry, measurement, dimension, or training content is taken from it. |
| [Soldier Systems 2018 announcement](https://soldiersystems.net/2018/11/09/orwm-18-mammut-diamond-finger-board/) | Historical launch-context corroboration. | Third party; no package fact or geometry is taken from it. |

The 21-contact map is conservatively labelled archival retailer evidence: available first-party material supplies no equivalent hold diagram.

## Frozen contact and field mapping

Backcountry lists 2 jugs, 2 45 mm flat slopers, 1 48 mm flat sloper, 2 30 mm flat slopers, 2 30 mm 4-finger pockets, 2 16 mm 2-finger pockets, 2 16 mm 3-finger pockets, 1 30 mm 8-finger pocket, 2 20 mm 8-finger pockets, 2 20 mm 4-finger pockets, 2 10 mm 4-finger pockets, and 1 18 mm 8-finger pocket: 21 distinct physical contacts.

| IDs | Retained source-backed fields |
| --- | --- |
| `jug-left`, `jug-right` | `kind: jug`; no size or capacity |
| `sloper-45-left`, `sloper-45-right` | flat sloper kind/type; no invented depth/angle |
| `sloper-48-center` | flat sloper kind/type; no invented depth/angle |
| `sloper-30-left`, `sloper-30-right` | flat sloper kind/type; no invented depth/angle |
| `pocket-30-four-left`, `pocket-30-four-right` | 30 mm, 4 fingers, `fourFingerPocket` |
| `pocket-16-two-left`, `pocket-16-two-right` | 16 mm, 2 fingers, `twoFingerPocket` |
| `pocket-16-three-left`, `pocket-16-three-right` | 16 mm, 3 fingers, `threeFingerPocket` |
| `pocket-30-eight-center` | 30 mm, source-labelled 8-finger/full-width contact; represented as 4 fingers per hand, `fourFingerPocket` |
| `pocket-20-eight-left`, `pocket-20-eight-right` | 20 mm, source-labelled 8-finger/full-width contact; represented as 4 fingers per hand, `fourFingerPocket` |
| `pocket-20-four-left`, `pocket-20-four-right` | 20 mm, 4 fingers, `fourFingerPocket` |
| `pocket-10-four-left`, `pocket-10-four-right` | 10 mm, 4 fingers, `fourFingerPocket` |
| `pocket-18-eight-center` | 18 mm, source-labelled 8-finger/full-width contact; represented as 4 fingers per hand, `fourFingerPocket` |

`sizeMillimeters` is retained only for contacts explicitly named as pockets. Backcountry's “8-finger” labels identify full-width, two-hand contacts, not an eight-finger capacity for one hand. The 30 mm, 20 mm, and 18 mm full-width pockets are therefore represented as the supported per-hand capacity of four with `fourFingerPocket`; this is an explicit two-hands-times-four adaptation of the source label. No hand capacity, posture, feature tag, depth range, sloper angle, or treatment is invented.

## Geometry, art, and unmodeled facts

`assets/primary.png` is a new 1932 x 483 transparent-canvas, straight-on photorealistic walnut product rendering, never a manufacturer or retailer photo. The final asset was created with the built-in image-generation workflow. The Climb Smart front image was supplied only as a physical-layout reference; the superseded package asset was supplied only as a 21-region placement/count reference; and the repository's Beastmaker 1000 and Metolius Wood Grips Deluxe II assets were supplied only as catalog-style references. The generation prompt required one continuous connected board silhouette, exactly 21 integrated contact surfaces in a 5 + 6 + 7 + 3 arrangement, bilateral symmetry, routed wood cavities and ledges, a head-on view, and no phone mount, hardware, detached pieces, text, logo, watermark, labels, orange inserts, or schematic outlines.

The selected generated output used a flat chroma-key backdrop. The installed image-generation helper removed that backdrop with border sampling, soft matte, and despill. The operator then made one explicit canvas crop (`1932 x 483`, offset `x: 1`, `y: 180`) to preserve the package's exact 4:1 presentation ratio; no image analysis or automatic cropping selected that rectangle. The final primary is the newly generated render, not a copied, cropped, or edited source photograph.

Each canonical normalized region was directly reviewed and authored against the final asset. Bilateral pairs are exact horizontal mirrors. Regular pockets/slopers have manually selected pill or rounded-rectangle constraints; lower jugs have separately written freeform paths. A labeled Workbench capture exposed drift from the superseded schematic asset, so the operator deliberately repositioned the 21 saved frames against the new rendered contact surfaces and repeated the labeled capture review. Saved canonical geometry remains the render, highlight, and hit-test source. Image generation produced presentation art only; it did not produce or infer geometry. No image-driven detection, segmentation, contour extraction, registration, vectorization, simplification, automatic cropping, or generated geometry was used.

| Verified but unmodeled fact | Evidence | Why it stays out of `board.json` |
| --- | --- | --- |
| Mount plate, silicon phone mount, tilt mechanism, one user / 100 kg, 0.6 m clearance | Mammut manual | No mount/accessory/rating safety field; not a hand contact. |
| Single-hand rope attachment points; walnut; 19 lb 10 oz claimed weight; two-year warranty | Backcountry archive | No safe attachment/material/weight/warranty field. |
| Zlagboard plans and reported collaboration with Jakob Schubert and Ingo Filzwieser | Climb Smart Shop archive | Retailer-reported program/development fact, not physical hold data. |
| Full-width/two-hand “8-finger” labels for the 30 mm, 20 mm pair, and 18 mm pockets | Backcountry archive | Represented as `fingerCapacity: 4` and `gripType: fourFingerPocket`: a documented two-hands-times-four adaptation, while each remains one full-width physical contact. |
| Pocket recess depth/deep-or-shallow labels, rim insets, jug shelf insets, and generic surface treatment | No direct source mapping | The source inventory establishes contact type, size, and selected finger counts, but not these per-contact treatment values. All `treatment` metadata is intentionally absent. |

`CONDUCTOR_WORKSPACE_NAME` was absent, so no owned simulator could be created under the lifecycle contract. This audit therefore claims no simulator normal, active/highlight, hit-test, or screenshot validation.
