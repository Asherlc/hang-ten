# Mammut Diamond Finger Hangboard source audit

Reviewed 2026-08-27 for product `2060-00020`, package `mammut-diamond-finger`, and board ID `mammut.diamond-finger`.

## Evidence and caveats

| Source | Package use | Caveat |
| --- | --- | --- |
| [Mammut product page](https://www.mammut.com/us/en/products/2060-00020/diamond-finger-hangboard) | First-party identity and canonical `productURL`; embeds the official product image below. | The discontinued-product page does not expose a named hold inventory or hold guide. |
| [Mammut official product image](https://static.mammut.com/master/2060-00020-7458_main_75743.jpg) | Primary first-party evidence for the exact wooden body silhouette, its stepped three-lobe lower profile, connected construction, visible rails/ledges, two small upper pockets, two lower oval pockets, central lower feature, and the location and shape of every distinguishable sculpted contact zone. | Near-front product photograph rather than a numbered hold guide. The removable phone mount, rear mounting hardware, metal brand plate/logo, and orange indicator inserts are visible but are not hand contacts and are omitted from presentation art. |
| [Mammut manual](https://static.mammut.com/file/2060-00020_man_en_070420_DiamondFingerHangboard_Manual.pdf) | First-party confirmation of Diamond Finger identity, mount plate and silicon phone-mount instructions, tilt warning, one-user/100 kg limit, and home/studio use. | Installation/safety document only: no named hold inventory, depth, capacity, or front-view hold guide. |
| [Backcountry archive](https://www.backcountry.com/mammut-diamond-finger-hangboard) | Archival 21-item inventory, 33.5 in width, walnut material, rope attachment points, and phone holder. | Retailer evidence, not manufacturer evidence. It supplies the hold names/counts and measurements, but no retailer image is used as primary geometry evidence or app art. |
| [Climb Smart Shop archive](https://climbsmartshop.com/products/diamond-finger) | Independent product-identity corroboration and reported Zlagboard/development attribution. | Retailer evidence; no geometry, measurement, dimension, or training content is taken from it. |
| [Soldier Systems 2018 announcement](https://soldiersystems.net/2018/11/09/orwm-18-mammut-diamond-finger-board/) | Historical launch-context corroboration. | Third party; no package fact or geometry is taken from it. |

The 21-contact names, sizes, and capacities remain conservatively labelled archival retailer evidence because Mammut supplies no equivalent numbered hold guide. Physical layout and distinguishable contact geometry are grounded primarily in Mammut's official product image.

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

`assets/primary.png` is a new 1980 x 495 transparent-canvas, straight-on photorealistic light-walnut product rendering, not a copied manufacturer or retailer photograph. The final asset was created with the built-in image-generation edit workflow. Mammut's official `2060-00020-7458_main_75743.jpg` was Image 1 and the edit target controlling the exact wooden silhouette, stepped body, carved shelves, rails, pockets, recesses, and spacing. The superseded generated package asset was Image 2 and only a broad reference for polished natural-wood catalog styling; the prompt explicitly prohibited copying its invented grid layout. The permitted edits removed the phone cradle/bracket, rear black mounting hardware, brand plate/logo/text, and orange indicator inserts; reconstructed only the small occluded wood areas; corrected the near-front product view minimally toward orthographic; and replaced the backdrop with chroma key. The prompt prohibited adding, deleting, subdividing, relocating, regularizing, or symmetrically redesigning any physical contact.

The selected generated output used a flat chroma-key backdrop. The installed image-generation helper removed that backdrop with border sampling, soft matte, despill, and a one-pixel edge contract; a final 97-pixel partial-alpha chroma despill pass neutralized the remaining green-biased edge pixels without changing alpha or physical layout. The operator then made one explicit canvas crop (`1980 x 495`, offset `x: 1`, `y: 150`) to preserve the package's exact 4:1 presentation ratio; no image analysis or automatic cropping selected that rectangle. The final primary is the newly generated render, not a copied or cropped source photograph.

Each canonical normalized region was directly reviewed and authored against the final asset and the official Mammut image. Bilateral pairs use exact mirrored frames and mirrored freeform commands where the product is physically symmetric. Regular deep and shallow pockets/slopers have manually selected pill or rounded-rectangle constraints; the sculpted outer panels, middle rail, lower channels, transitions, and center lower feature use separately written freeform paths. A first labeled Workbench capture exposed overlapping schematic-era bands, so the operator deliberately tightened those saved paths onto the manufacturer-visible contact zones and repeated the labeled capture review. Saved canonical geometry remains the render, highlight, and hit-test source. Image generation produced presentation art only; it did not produce or infer geometry. No image-driven detection, segmentation, contour extraction, registration, vectorization, simplification, automatic cropping, or generated geometry was used.

### Official-image geometry mapping

| Official manufacturer-visible feature | Canonical hold IDs | Evidence boundary |
| --- | --- | --- |
| Five zones along the sculpted upper sloper rail: outer left, inner left, center, inner right, outer right | `sloper-30-left`, `sloper-45-left`, `sloper-48-center`, `sloper-45-right`, `sloper-30-right` | Mammut image establishes the rail silhouette and its visible transitions; Backcountry supplies the 30/45/48 mm labels. |
| Broad upper side recessed panels | `pocket-30-four-left`, `pocket-30-four-right` | Mammut image establishes panel location/shape; Backcountry supplies 30 mm and four-finger labels. |
| Two dark small rounded pockets | `pocket-16-two-left`, `pocket-16-two-right` | Mammut image establishes location/shape; Backcountry supplies 16 mm and two-finger labels. |
| Two shallow rectangular pockets immediately inboard of the dark pockets | `pocket-16-three-left`, `pocket-16-three-right` | Mammut image establishes location/shape; Backcountry supplies 16 mm and three-finger labels. |
| Shallow upper center pocket | `pocket-30-eight-center` | Mammut image establishes location/shape; Backcountry supplies the 30 mm, eight-finger/full-width label. |
| Left and right contact zones on the continuous middle rail | `jug-left`, `jug-right` | Mammut image establishes the rail and its side zones; Backcountry supplies the two-jug inventory. |
| Lower left and right recessed side channels | `pocket-20-eight-left`, `pocket-20-eight-right` | Mammut image establishes location/shape; Backcountry supplies the 20 mm, eight-finger/full-width labels. |
| Sloping transitions from the side channels into the lower center feature | `pocket-20-four-left`, `pocket-20-four-right` | Mammut image establishes location/shape; Backcountry supplies 20 mm and four-finger labels. |
| Center section of the lower recessed channel | `pocket-18-eight-center` | Mammut image establishes location/shape; Backcountry supplies the 18 mm, eight-finger/full-width label. |
| Two bottom oval pockets | `pocket-10-four-left`, `pocket-10-four-right` | Mammut image establishes location/shape; Backcountry supplies 10 mm and four-finger labels. |

| Verified but unmodeled fact | Evidence | Why it stays out of `board.json` |
| --- | --- | --- |
| Mount plate, silicon phone mount, tilt mechanism, one user / 100 kg, 0.6 m clearance | Mammut manual | No mount/accessory/rating safety field; not a hand contact. |
| Single-hand rope attachment points; walnut; 19 lb 10 oz claimed weight; two-year warranty | Backcountry archive | No safe attachment/material/weight/warranty field. |
| Zlagboard plans and reported collaboration with Jakob Schubert and Ingo Filzwieser | Climb Smart Shop archive | Retailer-reported program/development fact, not physical hold data. |
| Full-width/two-hand “8-finger” labels for the 30 mm, 20 mm pair, and 18 mm pockets | Backcountry archive | Represented as `fingerCapacity: 4` and `gripType: fourFingerPocket`: a documented two-hands-times-four adaptation, while each remains one full-width physical contact. |
| Pocket recess depth/deep-or-shallow labels, rim insets, jug shelf insets, and generic surface treatment | No direct source mapping | The source inventory establishes contact type, size, and selected finger counts, but not these per-contact treatment values. All `treatment` metadata is intentionally absent. |

`CONDUCTOR_WORKSPACE_NAME` was absent, so no owned simulator could be created under the lifecycle contract. This audit therefore claims no simulator normal, active/highlight, hit-test, or screenshot validation.
