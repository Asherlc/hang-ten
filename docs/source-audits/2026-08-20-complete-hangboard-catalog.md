# Complete hangboard catalog source audit

This audit records the primary-manufacturer evidence and direct geometry
decisions for the packages added by the 2026-08-20 catalog-completion plan.
Generated presentation art is app content, never product evidence.

## Metolius Foundry Training Board

Reviewed 2026-08-21.

### Official evidence

- [Current product page](https://www.metoliusclimbing.com/products/foundry-training-board)
  establishes the manufacturer, product name, dimensions, compact arching
  layout, tapered pinches, and CAD/CAM perfect symmetry.
- [Official front/oblique-lit product photograph](https://www.metoliusclimbing.com/cdn/shop/files/The-Foundry-Training-Board-white.jpg?v=1759460759)
  establishes the board silhouette, mounting-hole locations, visible contact
  boundaries, surface relief, and left/right layout. The current gallery does
  not publish a separate side-view photograph; this relief-lit front product
  photograph is the available official oblique-depth evidence and was checked
  together with the numbered diagram rather than supplemented by a reseller
  image.
- [Official numbered hold-depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/Foundry-depth.jpg?v=1762201186)
  establishes positions `1` through `11`, the exact contact types, the pocket
  finger counts, and the published millimeter values.
- [Official Training Board instructions](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)
  establishes that this is a fixed training board and documents installation
  and general use. It does not add model-specific holds or measurements.

### Field and inventory mapping

The product page maps directly to `manufacturer: Metolius`, `name: Foundry
Training Board`, the canonical `productURL`, and `dimensions: 22.75 × 8.5
in`. The subtitle is a conservative summary of only the product-page and
diagram facts. No material, grip-posture, training, or feature-tag claims were
added.

The diagram and product photograph show perfect bilateral symmetry. Positions
`1` through `7` therefore each map to distinct left and right physical contacts;
positions `8` through `11` are single center contacts. The frozen inventory is
18 contacts:

| Diagram position | `board.json` contacts | Source-backed mapping |
| --- | --- | --- |
| `1` | `pinch-1-left`, `pinch-1-right` | Variable pinches; no unsupported width or posture value. |
| `2` | `jug-2-left`, `jug-2-right` | Outer jugs. |
| `3` | `pocket-3-left`, `pocket-3-right` | 32 mm, four-finger pockets. |
| `4` | `pocket-4-left`, `pocket-4-right` | 22 mm, three-finger pockets. |
| `5` | `pocket-5-left`, `pocket-5-right` | 30 mm, two-finger pockets. |
| `6` | `pocket-6-left`, `pocket-6-right` | 15 mm, three-finger pockets. |
| `7` | `pocket-7-left`, `pocket-7-right` | 21 mm, two-finger pockets. |
| `8` | `sloper-8-center` | 53 mm flat sloper. The millimeter label remains in the source-backed name rather than being treated as edge depth. |
| `9` | `edge-9-center` | 16 mm center edge. |
| `10` | `edge-10-center` | 30 mm center edge. |
| `11` | `edge-11-center` | 23 mm center edge. |

Every contact belongs to the schema-v2 `front` presentation. The generated PNG
is 1774 × 887 pixels, so both the presentation and package aspect-ratio
metadata are exactly `2.0`.

### AI-simplified primary illustration

`assets/primary.png` was generated with the built-in image-generation tool.
The official product photograph was supplied as reference Image 1 for physical
silhouette, symmetry, surface openings, and layout; the official numbered
diagram was supplied as reference Image 2 for inventory and contact separation.
The generated image was not used to establish any physical fact.

Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog primary presentation image
>
> Input images: Image 1 is the official Metolius Foundry front/oblique product photograph and is the authoritative reference for silhouette, symmetry, surface openings, and layout; Image 2 is the official Metolius numbered hold-depth diagram and is supporting reference for the exact contact inventory and separation of recesses.
>
> Primary request: Create a clean AI-simplified front-facing catalog illustration of this exact hangboard. Preserve the exact symmetric Foundry silhouette and all 18 physical contacts: two outer jugs, two tapered outer pinches, mirrored rows of 32 mm four-finger, 22 mm three-finger, 30 mm two-finger, 15 mm three-finger, and 21 mm two-finger pockets, plus the center 53 mm flat sloper and three center edges (16 mm, 30 mm, 23 mm). Every recess must remain visibly distinct and in the same position as the references.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, smooth light-gray cast-resin board with subtle soft shading; remove the black-and-white swirl pattern and all labels/numbers.
>
> Composition/framing: straight-on, centered, landscape composition with generous even padding; board fully visible and level.
>
> Lighting/mood: soft neutral studio light that makes each usable recessed surface readable without dramatic shadows.
>
> Constraints: exact bilateral symmetry; preserve the board outline, four mounting-hole pairs/positions, opening count, spacing, and proportions from the references; no added or missing holds; no text; no logo; no numbers; no hands; no mounting wall; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.

Human acceptance compared the generated illustration directly with both official
images. The accepted result retains the outer jug/pinch surfaces, the ten
mirrored pocket recesses, the center flat-sloper surface, and the three distinct
center edges. It contains no extra recess, label, or contact and preserves the
officially documented symmetry. No crop, registration, segmentation,
vectorization, contour extraction, or automatic geometry operation was applied
after generation.

The prompt's phrase "four mounting-hole pairs/positions" was imprecise: the
official image shows five symmetric pairs (ten holes). The generated result was
accepted only after confirming that it also shows all five pairs; mounting holes
are not contacts and were not encoded as holds.

### Direct geometry mapping and review

All 18 closed paths were deliberately authored in normalized canvas coordinates
against the accepted illustration and checked against the official photograph
and numbered diagram. The left contacts at positions `1` through `7` were drawn
once and their frames and path direction were mirrored exactly for the right
contacts because Metolius expressly documents perfect symmetry. The irregular
outer pinches, jugs, and center sloper use freeform paths. The visually regular
pocket and center-edge openings use operator-selected `roundedRectangle`
constraints; their saved paths remain the rendering, highlighting, and hit-test
source of truth.

| Contact group | Canonical frame mapping | Evidence/review decision |
| --- | --- | --- |
| Position `1` pinches | Left `x 0.057, y 0.255, w 0.164, h 0.570`; exact right mirror | Direct irregular boundary follows each broad tapered outer rail and excludes the image background. |
| Position `2` jugs | Left `x 0.220, y 0.167, w 0.120, h 0.205`; exact right mirror | Direct curved surface path follows the raised outer top contact visible in the product photo and diagram. |
| Position `3` pockets | Left `x 0.222, y 0.385, w 0.112, h 0.078`; exact right mirror | Rounded-rectangle path encloses only the upper four-finger recess. |
| Positions `4`/`6` pockets | Left `x 0.172, w 0.094`; `y 0.514/0.621`; exact right mirrors | Separate rounded-rectangle paths enclose the outer middle/lower three-finger recesses. |
| Positions `5`/`7` pockets | Left `x 0.284, w 0.055`; `y 0.514/0.621`; exact right mirrors | Separate rounded-rectangle paths enclose the inner middle/lower two-finger recesses. |
| Position `8` sloper | `x 0.330, y 0.174, w 0.340, h 0.115` | Direct freeform path encloses the continuous center top surface above position `9`; it is not conflated with that edge. |
| Position `9` edge | `x 0.361, y 0.283, w 0.278, h 0.080` | Rounded-rectangle path encloses the shallow upper center opening. |
| Position `10` edge | `x 0.362, y 0.397, w 0.276, h 0.117` | Rounded-rectangle path encloses the middle center opening. |
| Position `11` edge | `x 0.363, y 0.585, w 0.274, h 0.105` | Rounded-rectangle path encloses the lower center opening. |

Workbench server review confirmed that the package is listed with 18 holds, the
`front` presentation serves the exact checked-in 1774 × 887 PNG, and its
editor document contains the expected 18 regions (13 operator-selected rounded
rectangles and five custom paths). The accepted illustration and every authored
frame/path were also inspected directly. No browser session was connected in
this environment, so an interactive Workbench canvas-overlay review was not
available and is not claimed here. Package validation and the focused invariant
tests check the 18-item numbered inventory, schema-v2 presentation ownership,
and exact mirrored frames. Interactive Workbench canvas review plus full in-app
active-highlight and hit-test review remain for the plan's final catalog-wide
visual-validation task.

## Metolius Prime Rib

Reviewed 2026-08-21.

### Official evidence

- [Current product page](https://www.metoliusclimbing.com/products/prime-rib)
  establishes the manufacturer, product name, three-edge inventory, the edge
  depths and their published imperial conversions, compact-design description,
  four-screw mounting, dimensions, and FSC certification.
- [Official straight-on product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Prime-Rib-board.jpg?v=1759459292)
  establishes the long symmetric board silhouette, top-to-bottom edge order,
  continuous full-width contact layout, relative spacing, four mounting-hole
  positions, and visible surface relief. The current gallery publishes only
  this straight-on product view; it does not provide a separate oblique or side
  photograph. No depth or contact count was inferred from the image because the
  product page explicitly supplies both.
- [Official Training Board instructions](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)
  establishes that this is a fixed training board and documents installation
  and general use. It does not add Prime Rib-specific contacts or measurements.

### Field and inventory mapping

The product page maps directly to `manufacturer: Metolius`, `name: Prime Rib`,
the canonical `productURL`, and `dimensions: 20 × 4.2 × 1.5 in`. The subtitle
is a conservative summary of the page's compact-design statement and explicit
three-edge inventory. FSC certification and the four mounting screws are not
hold facts and were therefore not encoded as hold metadata or selectable
regions. No finger capacity, grip posture, training, feature-tag, or material
field was added.

The page's sentence "Three edges" freezes the complete physical inventory at
three contacts. Its edge-depth list is presented in the same top-to-bottom order
printed on the official photograph, mapping one-to-one to the three continuous
rails:

| Official position | `board.json` contact | Source-backed mapping |
| --- | --- | --- |
| Top rail | `edge-38` | One continuous full-width edge, depth 38 mm (official page also publishes 1.49 in). |
| Middle rail | `edge-23` | One continuous full-width edge, depth 23 mm (official page also publishes 0.90 in). |
| Bottom rail | `edge-15` | One continuous full-width edge, depth 15 mm (official page also publishes 0.59 in). |

Every contact belongs to the schema-v2 `front` presentation. The generated PNG
is 1704 × 923 pixels, so both the presentation and package aspect-ratio metadata
are exactly `1704 / 923` (`1.8461538461538463`).

### AI-simplified primary illustration

`assets/primary.png` was generated with the built-in image-generation tool.
The official straight-on product photograph was supplied as reference Image 1
for the physical silhouette, three-rail layout, mounting-hole positions,
symmetry, spacing, and proportions. The generated image was not used to
establish any physical fact.

Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog primary presentation image
>
> Input images: Image 1 is the official Metolius Prime Rib straight-on product photograph and is the authoritative reference for the exact board silhouette, three full-width horizontal edge surfaces, four mounting-hole positions, symmetry, spacing, and proportions.
>
> Primary request: Create a clean AI-simplified straight-on catalog illustration of this exact Prime Rib hangboard. Preserve exactly three distinct continuous full-width horizontal edges in the documented top-to-bottom order: 38 mm, 23 mm, and 15 mm. Each edge must be visibly separate and span the usable board width.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, smooth pale natural wood with subtle soft shading; remove all printed depth labels and the Metolius logo.
>
> Composition/framing: straight-on, centered, wide landscape composition with generous even padding; board fully visible, level, and occupying most of the canvas width.
>
> Lighting/mood: soft neutral studio light that makes the upper contact surface of each of the three long edges clearly readable without dramatic shadows.
>
> Constraints: preserve the product's symmetric long rectangular outline, exactly three edge rails, four mounting holes, spacing, and proportions from the reference; no added or missing edges; no text; no logo; no numbers; no hands; no mounting wall; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.
>
> Avoid: extra grooves, pockets, jugs, pinches, slopers, screws, labels, brand marks, or decorative elements.

Human acceptance compared the generated illustration directly with the official
product photograph and product-page inventory. The accepted result retains the
three separate full-width rails in their documented order and all four mounting
holes, while removing the printed depths and logo. It contains no extra groove,
rail, recess, screw, label, or selectable contact. No crop, registration,
segmentation, vectorization, contour extraction, or automatic geometry
operation was applied after generation.

### Direct geometry mapping and review

All three closed paths were deliberately authored in normalized canvas
coordinates against the accepted illustration and checked against the official
photograph. Each path represents one continuous physical rail. The three
visually regular horizontal rails use operator-selected `roundedRectangle`
constraints; each saved path remains the sole rendering, highlighting, and
hit-test source of truth. The constraints were selected from the observed
regular product form, not inferred by image analysis.

| Contact | Canonical frame mapping | Evidence/review decision |
| --- | --- | --- |
| `edge-38` | `x 0.037, y 0.337, w 0.926, h 0.078` | Direct path follows the complete top rail from rounded end to rounded end and excludes the background, mounting channel, and holes below it. |
| `edge-23` | `x 0.037, y 0.483, w 0.926, h 0.065` | Separate direct path follows only the middle rail and excludes both adjacent recessed mounting channels. |
| `edge-15` | `x 0.037, y 0.609, w 0.926, h 0.068` | Separate direct path follows only the bottom rail and excludes the channel and mounting holes above it. |

The accepted illustration and every authored frame/path were inspected
directly. Workbench discovery lists `Metolius Prime Rib` with three holds;
loading `presentationID=front` returns the exact IDs `edge-38`, `edge-23`, and
`edge-15`, three regions, and three operator-selected rounded-rectangle
constraints. The Workbench image endpoint serves a byte-identical copy of the
checked-in PNG. Focused package tests lock the exact three-item source
inventory, schema-v2 presentation ownership, official dimensions, image aspect
ratio, and nonempty path geometry. The server was shut down after review and
port 4173 was verified free. Interactive Workbench canvas review plus full
in-app active-highlight and hit-test review remain for the plan's final
catalog-wide visual-validation task.

## Metolius Wood Grips II Deluxe

Reviewed 2026-08-21.

### Official evidence

- [Current Wood Grips II product page](https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards)
  establishes Metolius as manufacturer; distinguishes the Compact and Deluxe
  variants; describes the wood training boards; names jugs, slopers, edges,
  and pockets as the hold assortment; and publishes the Deluxe-specific
  dimensions as 24 × 8.5 in (610 × 216 mm).
- [Official Wood Grips II Deluxe straight-on product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Deluxe-Training-Board.jpg?v=1759460952)
  independently establishes the taller Deluxe silhouette, its five top
  contacts, three separate recessed rows, 26-contact layout, six mounting-hole
  positions, and bilateral arrangement. It is a Deluxe-specific image; the
  Compact photograph and package were not used for any geometry or product
  fact.
- [Official Wood Grips Deluxe numbered hold-depth guide](https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428)
  independently labels the Deluxe and Compact diagrams. Its Deluxe diagram
  establishes positions `1` through `15`, contact types, all published
  millimeter values, pocket finger counts, left/right duplication, and the
  three single center contacts.
- [Official Training Board instructions](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)
  establishes that this is a fixed training board and documents installation
  and general use. It does not add Deluxe-specific contacts or measurements.

### Field-by-field and inventory mapping

| `board.json` field | Exact source mapping |
| --- | --- |
| `id` | Repository-stable identifier for the product independently named Wood Grips II Deluxe by the product page and official Deluxe image. |
| `manufacturer` | `Metolius`, from the official product page and manufacturer domain. |
| `name` | `Wood Grips II Deluxe`, matching the official model name/variant while omitting the page's shared Compact/Deluxe title. |
| `subtitle` | Conservative restatement of the product page's wood training-board description and its explicit jugs/slopers/edges/pockets assortment. |
| `productURL` | Canonical current manufacturer product page above. |
| `dimensions` | `24 × 8.5 in`, the page's Deluxe-specific dimensions. The Compact-specific 24 × 6.2 in value was deliberately excluded. |
| `aspectRatio` and `presentations` | Presentation-art facts only: the accepted PNG is 1774 × 887 pixels, exactly `2.0`; every physical contact belongs to the single `front` presentation. |
| `holds[].kind` | Directly follows each numbered Deluxe guide label: outer jugs, flat/round slopers, edges, or pockets. |
| `holds[].sizeMillimeters` | Directly copies the millimeter value printed for that numbered Deluxe-guide position; no values came from Compact. |
| `holds[].fingerCapacity` and `gripType` | Present only for positions the Deluxe guide explicitly calls two-, three-, or four-finger pockets. No finger capacity or posture was inferred for jugs, slopers, or edges. |
| omitted optional fields | No depth ranges, feature tags, grip posture for non-pockets, training claims, or other optional measurements were added. |

The product photograph and numbered guide show bilateral symmetry. Numbered
positions `1` through `11` therefore map to distinct left and right physical
contacts. Positions `12` through `15` are single center contacts. This freezes
the Deluxe inventory at 26 contacts, independently of the existing Compact II
package:

| Guide position | `board.json` contacts | Exact Deluxe-guide mapping |
| --- | --- | --- |
| `1` | `jug-1-left`, `jug-1-right` | Two outer jugs. |
| `2` | `sloper-2-flat-left`, `sloper-2-flat-right` | Two 56 mm flat slopers. |
| `3` | `edge-3-31-left`, `edge-3-31-right` | Two 31 mm edges. |
| `4` | `pocket-4-32-three-left`, `pocket-4-32-three-right` | Two 32 mm three-finger pockets. |
| `5` | `pocket-5-38-two-left`, `pocket-5-38-two-right` | Two 38 mm two-finger pockets. |
| `6` | `edge-6-25-left`, `edge-6-25-right` | Two 25 mm edges. |
| `7` | `pocket-7-25-three-left`, `pocket-7-25-three-right` | Two 25 mm three-finger pockets. |
| `8` | `pocket-8-28-two-left`, `pocket-8-28-two-right` | Two 28 mm two-finger pockets. |
| `9` | `edge-9-19-left`, `edge-9-19-right` | Two 19 mm edges. |
| `10` | `pocket-10-19-three-left`, `pocket-10-19-three-right` | Two 19 mm three-finger pockets. |
| `11` | `pocket-11-19-two-left`, `pocket-11-19-two-right` | Two 19 mm two-finger pockets. |
| `12` | `sloper-12-round-center` | One center 56 mm round sloper. |
| `13` | `pocket-13-32-four-center` | One center 32 mm four-finger pocket. |
| `14` | `pocket-14-25-four-center` | One center 25 mm four-finger pocket. |
| `15` | `pocket-15-19-four-center` | One center 19 mm four-finger pocket. |

### AI-simplified primary illustration

`assets/primary.png` was generated with the built-in image-generation tool.
The official Deluxe photograph was supplied as reference Image 1 for product
silhouette and layout. The official numbered Deluxe depth guide was supplied
as reference Image 2 for inventory and contact separation. Neither the
generated image nor the Compact variant was used to establish a physical fact.

Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog primary presentation image
>
> Input images: Image 1 is the official Metolius Wood Grips II Deluxe straight-on product photograph and is the authoritative reference for the exact Deluxe board silhouette, three-row layout, opening placement, bilateral symmetry, and mounting-hole positions. Image 2 is the official Metolius Wood Grips Deluxe numbered hold-depth guide and is supporting reference for the exact 26-contact inventory, depth labels, and separation of contacts.
>
> Primary request: Create a clean AI-simplified straight-on catalog illustration of this exact Wood Grips II Deluxe hangboard. Preserve all 26 usable physical contacts in their documented positions: top row has two outer jugs, two 56 mm flat slopers, and one center 56 mm round sloper; upper recessed row has two outer 31 mm edges, mirrored 32 mm three-finger pockets, mirrored 38 mm two-finger pockets, and one center 32 mm four-finger pocket; middle recessed row has two outer 25 mm edges, mirrored 25 mm three-finger pockets, mirrored 28 mm two-finger pockets, and one center 25 mm four-finger pocket; lower recessed row has two outer 19 mm edges, mirrored 19 mm three-finger pockets, mirrored 19 mm two-finger pockets, and one center 19 mm four-finger pocket. Every recess and surface must remain visibly distinct and in the same position as the references.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, smooth pale natural wood with subtle soft shading and restrained grain; remove the Metolius/Wood Grips branding and all printed labels or numbers.
>
> Composition/framing: straight-on, centered, wide landscape composition with generous even padding; board fully visible and level, occupying most of the canvas width.
>
> Lighting/mood: soft neutral studio light that makes every usable recessed or raised surface readable without dramatic shadows.
>
> Constraints: exact bilateral symmetry; preserve the Deluxe board outline, three-row architecture, exactly 26 contacts, six mounting-hole positions, opening count, spacing, and proportions from the references; no added or missing holds; no text; no logo; no numbers; no hands; no mounting wall; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.
>
> Avoid: extra grooves, pockets, jugs, slopers, edges, screws, labels, brand marks, decorative objects, or perspective distortion.

Human acceptance compared the generated illustration directly with the two
official Deluxe images. The accepted 1774 × 887 result retains exactly five
top contacts and three rows of seven contacts, all six mounting holes, and the
documented bilateral layout. It contains no extra recess, surface, text, logo,
number, or selectable contact. No crop, registration, segmentation,
vectorization, contour extraction, automatic simplification, or other
image-driven geometry operation was applied after generation.

### Direct geometry mapping and review

All 26 normalized closed paths were deliberately authored against the accepted
illustration and then compared directly with the official Deluxe photograph
and numbered guide. All 11 left/right position groups use exact frame
mirroring; paired custom paths use x-reversed commands. The 15 visually regular
pocket openings use operator-selected `roundedRectangle`
constraints over manually saved canonical paths. The jugs, slopers, and six
outer edge surfaces use custom paths. The saved path remains the rendering,
highlighting, and hit-test source of truth in every case.

| Contact group | Canonical frame mapping | Direct review decision |
| --- | --- | --- |
| Position `1` jugs | Left `x 0.022, y 0.158, w 0.156, h 0.119`; exact right mirror | Custom paths follow only the two rounded outer top caps. |
| Position `2` flat slopers | Left `x 0.175, y 0.181, w 0.165, h 0.083`; exact right mirror | Separate custom surface paths exclude the center round sloper and outer jugs. |
| Position `12` round sloper | `x 0.340, y 0.180, w 0.320, h 0.084` | One continuous center-top custom path, separate from both flat slopers. |
| Position `3` edges | Left `x 0.037, y 0.287, w 0.151, h 0.128`; exact right mirror | Custom shelf paths follow only the upper-row outer edge surfaces. |
| Positions `4`/`5` pockets | Left frames `x 0.206/0.331, y 0.310, w 0.108/0.079, h 0.097`; exact right mirrors | Distinct rounded paths map the upper row's three- and two-finger pockets. |
| Position `13` pocket | `x 0.421, y 0.307, w 0.158, h 0.102` | One center upper-row four-finger pocket. |
| Position `6` edges | Left `x 0.052, y 0.436, w 0.151, h 0.151`; exact right mirror | Custom shelf paths follow only the middle-row outer edge surfaces. |
| Positions `7`/`8` pockets | Left frames `x 0.225/0.337, y 0.500, w 0.095/0.073, h 0.088`; exact right mirrors | Distinct rounded paths map the middle row's three- and two-finger pockets. |
| Position `14` pocket | `x 0.421, y 0.497, w 0.158, h 0.093` | One center middle-row four-finger pocket. |
| Position `9` edges | Left `x 0.064, y 0.612, w 0.151, h 0.174`; exact right mirror | Custom shelf paths follow only the lower-row outer edge surfaces. |
| Positions `10`/`11` pockets | Left frames `x 0.239/0.343, y 0.680/0.681, w 0.087/0.068, h 0.092/0.090`; exact right mirrors | Distinct rounded paths map the lower row's three- and two-finger pockets. |
| Position `15` pocket | `x 0.424, y 0.679, w 0.152, h 0.094` | One center lower-row four-finger pocket. |

Workbench discovery and extraction review lists `Metolius Wood Grips II
Deluxe` with one `front` presentation, 26 holds, and 26 regions. The image
endpoint serves a byte-identical copy of the checked-in 1774 × 887 PNG, and
the extracted editor document retains 15 operator-selected rounded-rectangle
constraints plus 11 custom paths. The accepted illustration, each contact
frame, and every saved path were inspected directly. Interactive Workbench
canvas overlay review plus full in-app active-highlight and hit-test review
remain for the plan's final catalog-wide visual-validation task.
