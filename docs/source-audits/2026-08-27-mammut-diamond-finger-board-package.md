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
| `pocket-30-eight-center` | 30 mm, 8 fingers |
| `pocket-20-eight-left`, `pocket-20-eight-right` | 20 mm, 8 fingers |
| `pocket-20-four-left`, `pocket-20-four-right` | 20 mm, 4 fingers, `fourFingerPocket` |
| `pocket-10-four-left`, `pocket-10-four-right` | 10 mm, 4 fingers, `fourFingerPocket` |
| `pocket-18-eight-center` | 18 mm, 8 fingers |

`sizeMillimeters` is retained only for contacts explicitly named as pockets. The current schema limits both `fingerCapacity` and `gripType` to at most four fingers, so documented eight-finger pockets deliberately omit both fields rather than inventing a substitute type. No hand capacity, posture, feature tag, depth range, or sloper angle is invented.

## Geometry, art, and unmodeled facts

`assets/primary.png` is a new 1700 x 425 transparent-canvas, straight-on simplified walnut rendering, never a manufacturer or retailer photo. Each canonical normalized region was directly authored. Bilateral pairs are exact horizontal mirrors. Regular pockets/slopers have manually selected pill or rounded-rectangle constraints; lower jugs have separately written freeform paths. Saved canonical geometry remains the render, highlight, and hit-test source. No image-driven detection, segmentation, contour extraction, registration, vectorization, simplification, cropping, or generated geometry was used.

| Verified but unmodeled fact | Evidence | Why it stays out of `board.json` |
| --- | --- | --- |
| Mount plate, silicon phone mount, tilt mechanism, one user / 100 kg, 0.6 m clearance | Mammut manual | No mount/accessory/rating safety field; not a hand contact. |
| Single-hand rope attachment points; walnut; 19 lb 10 oz claimed weight; two-year warranty | Backcountry archive | No safe attachment/material/weight/warranty field. |
| Zlagboard plans and reported collaboration with Jakob Schubert and Ingo Filzwieser | Climb Smart Shop archive | Retailer-reported program/development fact, not physical hold data. |
| Eight-finger capacities for the 30 mm, 20 mm pair, and 18 mm pockets | Backcountry archive | Current `fingerCapacity` and `gripType` schemas reject capacities above four. |

`CONDUCTOR_WORKSPACE_NAME` was absent, so no owned simulator could be created under the lifecycle contract. This audit therefore claims no simulator normal, active/highlight, hit-test, or screenshot validation.
