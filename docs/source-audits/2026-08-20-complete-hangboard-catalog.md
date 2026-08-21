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

## The Hangboard

Reviewed 2026-08-21.

### Official evidence

Only the manufacturer's current product pages and their current gallery/feature
images were used as product evidence:

- [Current store product page](https://thehangboard.com/products/hangboard)
  establishes the product and manufacturer name, asymmetric incremental-depth
  layout, absence of dedicated pockets, 40-degree sloper, and jugs.
- [Current manufacturer product landing page](https://thehangboard.com/)
  establishes the six labeled depths (`40`, `30`, `25`, `20`, `15`, and `10`
  mm), deep jugs, 40-degree slopers, European beech, and dimensions of 23.5 ×
  6.25 × 2 in. Its feature text expressly calls these six edge depths rather
  than six total physical hand contacts.
- [Official straight-on product image](https://cdn.shopify.com/s/files/1/0764/5210/2426/files/hangboard-straight-2.png)
  establishes the complete front silhouette, four routed edge channels, three
  separately bounded contact surfaces per channel, relative placement, and the
  visible continuous center-top surface between two outer top contacts.
- [Official asymmetric edge-layout guide](https://thehangboard.com/cdn/shop/t/7/assets/asymmetrical-nobg-text2.png)
  maps the published labels directly to the 12 separated edge contacts: upper
  left and upper right each contain `40`, `30`, and `25` mm surfaces; lower
  left and lower right each contain `20`, `15`, and `10` mm surfaces. The guide
  also confirms that equal-depth contacts are deliberately arranged
  asymmetrically rather than as frame mirrors.
- [Official right oblique gallery image](https://thehangboard.com/cdn/shop/files/half-right-hangboard.png?v=1747623739)
  distinguishes the recessed edge contact floors, top relief, and the
  separations between the `40`/`30`/`25` and `20`/`15`/`10` surfaces.
- [Official left side gallery image](https://thehangboard.com/cdn/shop/files/hangboard-side-2.png?v=1747623739)
  and [official right side gallery image](https://thehangboard.com/cdn/shop/files/hangboard-side-2-right.png?v=1747623739)
  establish the rounded deep-jug overhang and the distinct sloped top surface.
- [Official jug/sloper profile guide](https://thehangboard.com/cdn/shop/t/7/assets/sloper-jugs-info2.png)
  is the manufacturer's labelled visual support for the deep-jug and
  40-degree-sloper classification. Together with the straight-on and oblique
  gallery images, it shows two physically separated outer jug contacts and one
  uninterrupted center sloper surface.
- [Official top/bottom gallery image](https://thehangboard.com/cdn/shop/files/hangboard-top-bottom-2.png?v=1747623739)
  confirms that the center top surface is continuous and that the outer top
  contacts are physically separated by the center relief.

No reseller page, review, search-result claim, generated artwork, or existing
board package supplied a product fact or inventory decision.

### Field-by-field and inventory mapping

| `board.json` field | Exact source mapping |
| --- | --- |
| `id` | Repository-stable identifier for the exact product named `The Hangboard` on the current store page. |
| `manufacturer` | `The Hangboard`, from the current product pages and manufacturer domain. |
| `name` | `The Hangboard`, matching the store-page product title. |
| `subtitle` | Conservative restatement of the pages' explicit asymmetric layout, six labeled edge depths, deep jugs, and 40-degree sloper. |
| `productURL` | Canonical current store product page above. |
| `dimensions` | `23.5 × 6.25 × 2 in`, copied from the current manufacturer landing page. |
| `aspectRatio` and `presentations` | Presentation-art facts only: the accepted PNG is 1774 × 887 pixels, exactly `2.0`; every contact belongs to the single `front` presentation. |
| `holds[].kind` | `edge` follows the page's “6 crimping edges”/edge-depth labels; `jug` follows “deep jugs”; `sloper` follows the labelled 40-degree sloper feature. |
| `holds[].sizeMillimeters` | Present only on the 12 edge contacts and copied from the six printed manufacturer labels shown once per physical left/right contact: 40, 30, 25, 20, 15, and 10 mm. |
| omitted optional fields | No finger capacity, grip posture, training cue, feature tags, weight, material field, or inferred measurement was encoded on a hold. |

The layout guide and straight-on photograph show two physically separated
contacts for every labelled edge depth. The two outer top contacts are also
physically separated, so they are separate jugs. The manufacturer calls the
top feature “40-degree slopers” in prose, but the front, top, and oblique gallery
views show one uninterrupted center surface; following the package rule for a
continuous physical contact, it is represented as one logical sloper rather
than an invented left/right split. This freezes the complete inventory at 15
contacts:

| Manufacturer-evidenced position | `board.json` contact | Source-backed mapping |
| --- | --- | --- |
| Outer top left/right | `jug-left`, `jug-right` | Two physically separated deep jugs; the right path is the exact x-reverse of the left because the official top silhouette is symmetric. |
| Continuous center top | `sloper-40-center` | One uninterrupted 40-degree sloper surface; no unsupported left/right split. |
| Upper-left channel | `edge-40-left`, `edge-30-left`, `edge-25-left` | Three separately bounded edge surfaces in the official left-to-right label order. |
| Upper-right channel | `edge-40-right`, `edge-30-right`, `edge-25-right` | Three separately bounded edge surfaces in the official left-to-right label order; this repeated order produces the manufacturer-described asymmetric layout. |
| Lower-left channel | `edge-20-left`, `edge-15-left`, `edge-10-left` | Three separately bounded edge surfaces in the official left-to-right label order. |
| Lower-right channel | `edge-20-right`, `edge-15-right`, `edge-10-right` | Three separately bounded edge surfaces in the official left-to-right label order. |

### AI-simplified primary illustration

`assets/primary.png` was generated with the built-in image-generation tool.
The official straight-on image was reference Image 1, the official asymmetric
layout guide was reference Image 2, the official jug/sloper profile guide was
reference Image 3, and the official right-oblique gallery image was reference
Image 4. These manufacturer images guided product appearance only. The
generated illustration was never used to establish, propose, trace, or validate
a physical fact or geometry path.

Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten app hangboard catalog primary illustration
>
> Primary request: Create a clean AI-simplified straight-on product illustration of the exact wooden climbing hangboard shown in the manufacturer references.
>
> Input images: Image 1 is the official straight-on front-view layout reference; Image 2 is the official asymmetrical edge-layout guide; Image 3 is the official jug/sloper side-profile guide; Image 4 is an official oblique construction reference.
>
> Scene/backdrop: plain warm-white seamless background.
>
> Subject: one complete light European-beech hangboard, centered and isolated. Preserve the manufacturer's distinctive low wide rounded rectangular body; two raised rounded top end sections; recessed center top surface; exactly four long routed horizontal recesses arranged as upper-left, upper-right, lower-left, lower-right; exactly three visibly separated edge contact sections inside each recess; and the manufacturer-evidenced top jug/sloper construction. Include only the mounting holes visible in the official front reference. Preserve the asymmetric edge depth layout and spacing from the references.
>
> Style/medium: polished simplified 3D catalog illustration matching the existing Hang Ten board assets; restrained wood grain; clean readable contact boundaries; realistic shallow shadows only.
>
> Composition/framing: exact orthographic front elevation, no perspective skew, whole board visible with generous even padding, landscape canvas exactly 2:1.
>
> Lighting/mood: soft neutral studio lighting, low contrast, no cast shadow that obscures contact edges.
>
> Color palette: pale natural beech on warm white.
>
> Text: no printed labels, no logo, no numbers, no captions.
>
> Constraints: prioritize correct count, placement, separation, and silhouette over decorative detail; keep left/right top features and four recesses unambiguous; do not invent pockets, pinches, extra edges, extra holes, or accessories.
>
> Avoid: people, hands, wall, hardware, watermark, text, dramatic perspective, dark background, cropped product, official-photo appearance.

Human acceptance compared the generated illustration directly with the current
official straight-on, layout, oblique, side, and top views. The accepted 1774 ×
887 result retains the two outer top contacts, uninterrupted center top
surface, four routed channels, three distinct surfaces within each channel,
and the visible mounting holes. It adds no pocket, pinch, edge channel, or
selectable contact. No crop, registration, detection, segmentation, mask,
contour extraction, vectorization, automatic simplification, or other
image-driven geometry operation was applied before or after generation.

### Direct geometry mapping and review

All 15 canonical normalized paths were deliberately authored against the
accepted illustration and checked individually against the official product
and gallery evidence. The right jug uses the exact frame mirror and x-reversed
path of the left jug because the official top silhouette is symmetric. The
asymmetric edge layout was authored contact by contact and was not mirrored by
depth. The 12 visibly regular edge surfaces use operator-selected
`roundedRectangle` constraints over saved canonical paths. The jugs and center
sloper use custom paths. Every saved path remains the sole rendering,
highlighting, and hit-test source of truth.

| Contact group | Canonical frame mapping | Direct review decision |
| --- | --- | --- |
| Outer jugs | Left `x 0.030, y 0.209, w 0.185, h 0.127`; exact right frame mirror | Custom x-reversed paths follow only the two raised outer top contacts and exclude the center top surface. |
| Center sloper | `x 0.210, y 0.242, w 0.580, h 0.091` | One custom path follows the uninterrupted center surface and its two sloped transitions. |
| Upper-left `40`/`30`/`25` mm edges | `x 0.083/0.209/0.344, y 0.426, w 0.126/0.135/0.128, h 0.061` | Three rounded paths follow the separately bounded contact floors in published label order. |
| Upper-right `40`/`30`/`25` mm edges | `x 0.514/0.641/0.776, y 0.426, w 0.127/0.135/0.127, h 0.061` | Three separately authored rounded paths retain the asymmetric repeated label order. |
| Lower-left `20`/`15`/`10` mm edges | `x 0.083/0.208/0.343, y 0.600, w 0.125/0.135/0.129, h 0.071` | Three rounded paths follow only the lower-left contact floors. |
| Lower-right `20`/`15`/`10` mm edges | `x 0.514/0.641/0.776, y 0.600, w 0.127/0.135/0.127, h 0.071` | Three rounded paths follow only the lower-right contact floors. |

The accepted illustration, all 15 frames, and every saved path were inspected
directly. Workbench discovery lists `The Hangboard The Hangboard` with one
`front` presentation and 15 holds. Opening that presentation extracts 15
regions with the exact source-backed hold IDs, retains all 12 operator-selected
rounded-rectangle constraints and three custom paths, and reports the accepted
1774 × 887 canvas. The Workbench image endpoint serves a byte-identical copy of
the checked-in PNG (both SHA-256
`81d1acd69995cffe8b413389ea27466882585b0709315f5abd089e30a0fc0789`).
The temporary Workbench server was shut down and its localhost port was verified
free. Interactive Workbench canvas review plus full in-app active-highlight and
hit-test review remain for the plan's final catalog-wide visual-validation
task.

## Tension Flash Board

Reviewed 2026-08-21.

### Official evidence

- [Current Flash Board product page](https://tensionclimbing.com/products/flash-board-2)
  establishes the manufacturer, exact product name, compact cylindrical form,
  portable cord suspension, and published edge list: Small Crimps, 8 mm,
  10 mm, 15 mm, and 20 mm. It does not publish overall dimensions or map a
  listed depth to any visible gallery position.
- [Current official hangboards page](https://tensionclimbing.com/pages/hangboards)
  independently describes the Flash Board as compact and cylindrical and
  publishes the same list, spelling the first item as approximately 6 mm
  crimps. That approximate value was not converted into an exact measurement.
- [Official straight-on three-edge gallery image](https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard2.png?v=1726542491)
  establishes one usable orientation with three separately bounded recessed
  contacts (left, center, right), the cylindrical body, and paired cord
  passages at both ends.
- [Official full oblique two-edge gallery image](https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard1.png?v=1726542491)
  establishes the opposite usable orientation: two separately bounded
  recesses, one narrow small-crimp surface outboard of each recess, and an
  uninterrupted center body area.
- [Official left two-edge detail](https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard3.png?v=1726542491)
  and [official right two-edge detail](https://cdn.shopify.com/s/files/1/0653/3706/5653/files/FlashBoard4.png?v=1726542491)
  independently confirm the recess/crimp separation at both ends. They were
  used as relief evidence, not for inferred measurements.
- [Official Flash Board overview page](https://tensionclimbing.com/blogs/training-tools/hangboard-overview-the-flash-board)
  links Tension's own overview video. It supplied no additional measurement or
  manufacturer face name.

No reseller measurement, review claim, generated illustration, or other board
package supplied a product fact. The official 2048 × 2048 gallery images were
manually inspected. No detection, segmentation, registration, crop, trace,
mask, contour, or vectorization workflow was used.

### Field and surface inventory mapping

| `board.json` field | Exact source mapping |
| --- | --- |
| `id` | Repository-stable identifier for the exact product named Flash Board by Tension. |
| `manufacturer` / `name` | `Tension` and `Flash Board`, from the manufacturer domain and product title. |
| `subtitle` | Conservative restatement of the page's compact cylindrical description and exact edge list. |
| `productURL` | Canonical current manufacturer product page above. |
| `dimensions` | The schema requires a nonempty string, while no current official Tension source publishes physical dimensions. `Not published by manufacturer` records that limitation without introducing a reseller value. |
| `aspectRatio` | Presentation-art metadata only: the default 1536 × 1024 PNG is exactly `1.5`; this is not a product dimension. |
| `presentations` | `three-edge` and `two-edge` are concise repository display descriptions of the two official-gallery orientations, not manufacturer face names. |
| `holds[].kind` | `edge` follows Tension's own `Edges` heading and `Crimps` label. |
| omitted optional fields | No individual depth, range, capacity, posture, feature tag, material, or training claim was added. |

The official pages publish the global size set but do not map 8, 10, 15, or
20 mm to a specific visible recess. Assigning those depths visually would be an
unsupported inference, so all seven contacts intentionally omit
`sizeMillimeters` while retaining the complete source-visible inventory:

| Presentation | `board.json` contact(s) | Exact source-backed mapping |
| --- | --- | --- |
| `three-edge` (default) | `three-edge-left`, `three-edge-center`, `three-edge-right` | Three distinct recesses in official `FlashBoard2.png`. |
| `two-edge` | `two-edge-left`, `two-edge-right` | Two distinct recesses confirmed by official `FlashBoard1.png`, `FlashBoard3.png`, and `FlashBoard4.png`. |
| `two-edge` | `small-crimp-left`, `small-crimp-right` | Two physically separate narrow outboard contacts mapped to Tension's plural `Small Crimps`; the approximately 6 mm category is not stored as an exact value. |

### AI-simplified presentation illustrations (NON-EVIDENCE)

Both PNGs were generated with the built-in image-generation tool. Official
Tension gallery images were references only for the already frozen silhouette,
surface count, cord passages, and contact layout. Generated art established no
product fact and supplied no geometry.

`assets/primary.png` is the default three-edge presentation, 1536 × 1024
(aspect `1.5`, SHA-256
`c7e3fe0813c3be33e2f61122a84a3d1421b32d081f0eba47a1a4509af602dcf2`).
Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog default presentation image
>
> Input images: Image 1 is Tension Climbing's official straight-on Flash Board photograph and is the authoritative reference for this exact three-edge cylindrical orientation, body silhouette, three separate edge recesses, end cord slots, spacing, and proportions.
>
> Primary request: Create a clean AI-simplified straight-on catalog illustration of this exact Tension Flash Board orientation. Preserve exactly three distinct rounded rectangular edge recesses aligned across the visible cylindrical wood surface, with one left, one center, and one right contact. Preserve the cylindrical portable body and the paired black cord slots near both ends.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, smooth pale natural wood with subtle soft shading, visually compatible with a clean hangboard catalog.
>
> Composition/framing: straight-on, centered, wide landscape composition with generous even padding; board fully visible, horizontal, level, and occupying most of the canvas width.
>
> Lighting/mood: soft neutral studio light that makes all three recessed usable surfaces clearly readable without dramatic shadows.
>
> Constraints: exact three-edge orientation from the reference; preserve exactly three edge recesses, their separation, spacing, overall long cylindrical outline, and four end cord slots; omit loose cord entirely so no cord crosses or obscures the board; no added or missing holds; no text; no logo; no numbers; no hands; no mounting wall; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.
>
> Avoid: extra grooves, pockets, jugs, pinches, slopers, mounting holes, labels, brand marks, decorative elements, rope loops, knots, or cast shadows crossing the product.

`assets/two-edge-surface.png` is the alternate presentation, 1774 × 887
(aspect `2.0`, SHA-256
`37eba0201081ffdc62d49d52841879a7fac702d51498a7549e94dfc8e17f8818`).
Initial prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog alternate presentation image
>
> Input images: Images 1–3 are Tension Climbing's official Flash Board photographs of the opposite cylindrical orientation. Together they are the authoritative references for this exact two-edge surface, body silhouette, two separate edge recesses, small end crimps, end cord slots, spacing, and proportions.
>
> Primary request: Create a clean AI-simplified straight-on catalog illustration of this exact Tension Flash Board orientation. Preserve exactly two distinct rounded rectangular edge recesses, one on the left and one on the right, with the broad unbroken wood/logo area at center. Preserve one small transverse crimp immediately outboard of each recess and the paired black cord slots near both ends.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, smooth pale natural wood with subtle soft shading, visually compatible with a clean hangboard catalog.
>
> Composition/framing: straight-on, centered, wide landscape composition with generous even padding; board fully visible, horizontal, level, and occupying most of the canvas width.
>
> Lighting/mood: soft neutral studio light that makes both recessed usable surfaces and both small crimps clearly readable without dramatic shadows.
>
> Constraints: exact two-edge orientation from the references; preserve exactly two edge recesses and two small crimps, their separation, spacing, overall long cylindrical outline, and four end cord slots; omit loose cord entirely so no cord crosses or obscures the board; remove the burned brand logo; no added or missing holds; no text; no logo; no numbers; no hands; no mounting wall; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.
>
> Avoid: center recess, third recess, extra grooves, pockets, jugs, pinches, slopers, mounting holes, labels, brand marks, decorative elements, rope loops, knots, or cast shadows crossing the product.

The initial alternate result kept every contact but rendered only one cord
passage per end. A focused built-in edit corrected that non-contact detail:

> Use case: precise-object-edit
>
> Asset type: Hang Ten hangboard catalog alternate presentation image
>
> Input image: Image 1 is the edit target, an accepted simplified straight-on two-edge Tension Flash Board illustration.
>
> Primary request: Correct only the cord-slot count. Add one matching narrow black cord slot immediately beside the existing slot at each end, producing exactly two parallel black cord slots at the left end and exactly two parallel black cord slots at the right end (four slots total), as on the official product.
>
> Constraints: change only the cord-slot count and placement; preserve the exact canvas, board position, cylindrical silhouette, pale wood, two rounded rectangular edge recesses, left and right small transverse crimps, broad center wood area, lighting, scale, and off-white background unchanged. Keep the board perfectly straight-on, horizontal, and centered. No loose cord, no text, no logo, no numbers, no hands, no watermark. Do not add, remove, resize, or shift any contact surface. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.

Human acceptance compared both finals with all four official gallery images.
The default retains exactly three recesses; the alternate retains exactly two
recesses, two small crimps, and paired end passages. Apart from the built-in
corrective generation step, the PNGs were only copied into the package. No
crop, registration, segmentation, mask, contour extraction, vectorization, or
automatic geometry operation was applied.

### Direct geometry mapping and review

All seven closed paths were deliberately authored in normalized canvas
coordinates and reviewed against the accepted illustration and corresponding
official orientation evidence. The five regular recesses use operator-selected
`roundedRectangle` constraints. The two narrow crimps use custom curves. The
saved paths remain the only rendering, highlight, and hit-test source.

| Contact | Canonical frame | Direct review decision |
| --- | --- | --- |
| `three-edge-left` | `x 0.139, y 0.456, w 0.212, h 0.112` | Follows only the left default-surface recess. |
| `three-edge-center` | `x 0.396, y 0.456, w 0.210, h 0.112` | Follows only the center recess. |
| `three-edge-right` | `x 0.645, y 0.456, w 0.216, h 0.112` | Follows only the right recess. |
| `two-edge-left` | `x 0.159, y 0.443, w 0.216, h 0.130` | Follows the left recess and excludes its crimp. |
| `two-edge-right` | `x 0.642, y 0.443, w 0.187, h 0.130` | Follows the right recess and excludes its crimp. |
| `small-crimp-left` | `x 0.118, y 0.411, w 0.024, h 0.174` | Custom path follows only the narrow left crimp. |
| `small-crimp-right` | `x 0.858, y 0.411, w 0.024, h 0.174` | X-reversed custom path follows only the narrow right crimp. |

Package validation checks both PNG ratios, exact asset set, hold IDs, explicit
presentation ownership, and path geometry. Focused package assertions freeze
the `3 + 4` inventory and require individual depths to remain omitted.
Workbench package extraction reports the ordered presentations as
`three-edge` (1536 × 1024, default) and `two-edge` (1774 × 887), returns exactly
the three default-surface IDs when switched to `three-edge`, and exactly the
four alternate-surface IDs when switched to `two-edge`. Focused Workbench v2
tests also pass for per-presentation filtering and preservation on save.
Interactive canvas overlay review and full in-app active-highlight/hit-test
review remain for the plan's final catalog-wide visual-validation task.

## Metolius Light Rail 2.0

Reviewed 2026-08-21.

### Official evidence

- [Current product page](https://www.metoliusclimbing.com/products/light-rail)
  establishes the manufacturer and model name, portable training-rail identity,
  reversible design, exactly four different holds, published edge depths of
  15, 20, and 40 mm, weight, body-weight-only limit, FSC certification, and
  dimensions of 18 × 3 × 1.5 in (45.7 × 7.6 × 3.8 cm).
- [Official straight-on suspended product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Light-Rail-2-PT.jpg?v=1767727616)
  establishes the long rounded rail silhouette, the single routed channel,
  end suspension-cord routing, and the two reversible orientation pairs. Its
  upright left-side engravings map one orientation to `40 mm` and `20 mm`; its
  inverted right-side engravings map the reversed orientation to `15 mm` and a
  second `40 mm` contact. This is the only still photograph in the current
  official gallery; no reseller imagery was used.
- [Official Metolius Light Rail usage video](https://www.youtube.com/watch?v=t208TAIW1LM),
  embedded on the current product page, identifies the demonstrated product as
  the newer Light Rail and Light Rail 2.0. The manufacturer presentation
  expressly distinguishes a 20 mm edge on one side, a 15 mm edge on the other
  side, and a rounded jug on top. Its close-up and hanging demonstrations were
  reviewed as oblique/use evidence for the channel edges and rounded outer
  contact; the video supplied no geometry.
- [Official Training Board instructions](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)
  expressly classify Light Rails as suspended devices and describe hanging
  them from a solid anchor point. The instructions are generic and do not add
  Light Rail-specific contacts, measurements, finger capacities, or posture
  prescriptions.

### Field and reversible-inventory mapping

| `board.json` field | Exact official-source mapping |
| --- | --- |
| `id`, `manufacturer`, `name`, `productURL` | Repository-stable identifier plus the exact current manufacturer/model identity and canonical product URL. |
| `subtitle` | Conservative restatement of the product page's portable, reversible rail and exact four-hold claim. |
| `dimensions` | Product-page size `18 × 3 × 1.5 in`; no dimension was inferred from the PNG. |
| `presentations` | The product page's reversible design, photograph's paired upright/inverted engravings, video side distinction, and manual's suspended-device classification map to `20mm-side` and `15mm-side`. |
| `holds[].kind` | The official video calls 20 and 15 mm contacts edges and the outer contact a rounded jug. |
| `holds[].sizeMillimeters` | The product page publishes 15, 20, and 40 mm; the photograph maps one 40 mm contact to each reversible orientation. |
| omitted optional fields | No finger capacity, grip posture, feature tags, training semantics, or additional physical measurement was added. Weight, body-weight limit, and FSC certification are product facts but are not board hold fields. |

The four-hold claim is reconciled without duplication or inference as two
distinct contacts on each usable orientation:

| Presentation | `board.json` contacts | Source-backed physical mapping |
| --- | --- | --- |
| `20mm-side` (default) | `jug-40-20mm-side`, `edge-20` | Upright `40 mm`/`20 mm` photograph engravings plus the video's rounded top jug and 20 mm side. |
| `15mm-side` | `jug-40-15mm-side`, `edge-15` | Inverted `15 mm`/`40 mm` photograph engravings plus the video's 15 mm other side and rounded top jug after reversal. |

The flat back/cord-routing area was not represented as a usable presentation:
none of the official sources calls it a hold. Each physical contact appears
once, on the orientation in which it is usable.

### AI-simplified presentation illustrations

Both PNGs were generated with the built-in image-generation tool using the
official Metolius photograph as reference Image 1. They are app presentation
content and were never treated as evidence for contact identity, count, kind,
depth, or geometry.

`assets/primary.png` is the default `20mm-side` illustration, 1536 × 1024
(aspect `1.5`, SHA-256
`ec94a25e2f653d7972eea4c755df5413aa70a81c393764365b0cdbaa8232fc12`).
Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog default presentation image
>
> Input images: Image 1 is the official Metolius Light Rail 2.0 product photograph and is the authoritative reference for the exact long rounded-rectangle wood rail silhouette, routed central channel, end shape, suspension-cord routing, proportions, and the 40 mm / 20 mm orientation.
>
> Primary request: Create a clean AI-simplified straight-on catalog illustration of this exact Light Rail 2.0 in the 40 mm rounded-jug plus 20 mm edge orientation. Preserve the physical rail as one long pale wooden bar with the same single long recessed channel. Make the currently usable upper outer rounded 40 mm jug surface and the 20 mm channel edge visually distinct through subtle relief and neutral shading.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, pale natural wood with restrained grain and soft studio shading.
>
> Composition/framing: straight-on, centered, wide landscape composition; rail fully visible, level, occupying most of the canvas width with even padding. Show the blue-and-pink suspension cord only where it exits both ends and rises out of frame; do not let it overlap the board.
>
> Lighting/mood: soft neutral studio light that makes the two usable contact surfaces readable without dramatic shadows.
>
> Constraints: preserve the exact product silhouette, one recessed channel, end rounding, proportions, and asymmetric channel lips from the reference; depict exactly the 40 mm outer rounded jug and 20 mm inner edge for this orientation; no added or missing grooves or holds; no hands; no mounting wall; no text; no logo; no numbers; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.
>
> Avoid: a second channel, pockets, pinches, slopers, screws, labels, decorative elements, or a generic fingerboard.

`assets/15mm-surface.png` is the reversed `15mm-side` illustration, 1672 ×
941 (aspect `1672 / 941`, SHA-256
`7b365965bb7d3c7b6f1fcd8c2503c5a77ddba8cc75084294c5a7766a90ef3705`).
Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog secondary presentation image
>
> Input images: Image 1 is the official Metolius Light Rail 2.0 product photograph and is the authoritative reference for the exact long rounded-rectangle wood rail silhouette, routed central channel, end shape, suspension-cord routing, proportions, and the inverted 15 mm / 40 mm orientation.
>
> Primary request: Create a clean AI-simplified straight-on catalog illustration of this exact Light Rail 2.0 after it has been reversed into the 15 mm edge plus 40 mm rounded-jug orientation. Preserve the physical rail as one long pale wooden bar with the same single long recessed channel, visibly reversed top-to-bottom from the reference orientation. Make the currently usable 15 mm channel edge and the opposite outer rounded 40 mm jug surface visually distinct through subtle relief and neutral shading.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, pale natural wood with restrained grain and soft studio shading.
>
> Composition/framing: straight-on, centered, wide landscape composition; rail fully visible, level, occupying most of the canvas width with even padding. Show the blue-and-pink suspension cord only where it exits both ends and rises out of frame; do not let it overlap the board.
>
> Lighting/mood: soft neutral studio light that makes the two usable contact surfaces readable without dramatic shadows.
>
> Constraints: preserve the exact product silhouette, one recessed channel, end rounding, proportions, and reversed asymmetric channel lips from the reference; depict exactly the 15 mm inner edge and opposite 40 mm outer rounded jug for this orientation; no added or missing grooves or holds; no hands; no mounting wall; no text; no logo; no numbers; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.
>
> Avoid: a second channel, pockets, pinches, slopers, screws, labels, decorative elements, or a generic fingerboard.

Human acceptance compared each generated view directly with the official
photograph, product-page inventory, video close-up/use evidence, and manual's
suspended-device classification. Both results retain one rail, one routed
channel, and exactly two source-supported contact surfaces for the shown
orientation. They add no recess, pocket, screw, label, or selectable contact.
The generated PNGs were only copied into the package: no crop, registration,
segmentation, mask, contour extraction, vectorization, or automatic geometry
operation was applied.

### Direct geometry mapping and review

Every closed path was deliberately authored in normalized canvas coordinates
after direct inspection of the accepted illustration and the corresponding
official orientation evidence. The four physically long, regular contacts use
operator-selected `roundedRectangle` constraints. Those constraints are
editing metadata only; each saved path remains the sole normal rendering,
highlight, and hit-test source.

| Contact | Canonical frame | Direct review decision |
| --- | --- | --- |
| `jug-40-20mm-side` | `x 0.025, y 0.436, w 0.950, h 0.101` | Follows only the default image's upper rounded outer rail surface, excluding cord, background, and channel. |
| `edge-20` | `x 0.099, y 0.558, w 0.802, h 0.053` | Follows only the default image's long lower channel shelf for the 20 mm contact. |
| `jug-40-15mm-side` | `x 0.034, y 0.406, w 0.932, h 0.103` | Follows only the reversed image's upper rounded outer rail surface. |
| `edge-15` | `x 0.083, y 0.551, w 0.834, h 0.047` | Follows only the reversed image's long lower channel shelf for the 15 mm contact. |

The package parser validates both declared PNGs, aspect ratios, four unique
hold IDs, nonempty normalized paths, and explicit presentation ownership.
Focused package assertions freeze the exact `2 + 2` reversible inventory,
published sizes and kinds, declared asset dimensions, and operator-selected
constraints. Workbench extraction/surface-switching and final visual-review
results are recorded in the Task 9 report.

## Metolius Rock Rings 3D

Reviewed 2026-08-21.

### Official evidence

- [Current product page](https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d)
  establishes the manufacturer and exact model name; a set of two independent
  units; portable identity; flexible single-point suspension; CAD/CAM perfect
  symmetry; and current dimensions of 184 × 146 × 57 mm. Its imperial
  dimension rendering is missing punctuation, so the exact current metric
  values are used in `board.json`.
- [Official straight-on paired product photograph](https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg?v=1759460123)
  establishes the two separately suspended left/right units, identical tapered
  body layout, cord routing, upper outer contact, and three vertically separated
  pocket openings on each unit. The alternate
  [official blue/white color photograph](https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-blue-white.jpg?v=1759460123)
  confirms that the physical layout is unchanged across the two current color
  variants; color is not encoded as a product fact or presentation.
- [Official numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/Rock-Ring-Depts.jpg?v=1762201543)
  establishes the exact per-unit top-to-bottom contact inventory: `1` jug,
  `2` 40 mm four-finger pocket, `3` 32 mm three-finger pocket, and `4` 25 mm
  two-finger pocket.
- [Official Rock Ring training guide](https://www.metoliusclimbing.com/pages/rock-ring-training-guide)
  independently describes the compact portable single-point-suspended pair and
  names jugs, four-finger edges, three-finger pockets, and two-finger pockets in
  its routine. Its
  [official pair image](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Rock_Rings-th.jpg?v=1759521022)
  and [official numbered layout image](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/roc-num-dep.jpg?v=1759521022)
  confirm the same paired front layout and numbered contact order. The routine
  text supplied no package coaching field or geometry.
- [Official Training Board and Rock Rings instructions](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826)
  expressly classify Rock Rings as suspended devices that hang from solid
  anchor points. The generic manual adds no model-specific contact, measurement,
  posture, or alternate usable face.

No reseller source, search-result summary, generated illustration, or existing
package supplied a product fact, contact, dimension, or geometry decision.

### Field, presentation, and inventory mapping

| `board.json` field | Exact official-source mapping |
| --- | --- |
| `id`, `manufacturer`, `name`, `productURL` | Repository-stable identifier plus the exact current Metolius/model identity and canonical current product URL. |
| `subtitle` | Conservative restatement of the product page's portable paired independent suspension plus the numbered diagram's one-jug/three-pocket inventory per unit. |
| `dimensions` | Exact current product-page metric values `184 × 146 × 57 mm`, without supplementing the page's malformed imperial rendering. |
| `presentations` | A single schema-v2 `front-pair` presentation follows every current official layout image. Single-point joint rotation is a suspension behavior, not evidence of another usable contact face, so no alternate presentation is fabricated. |
| `holds[].kind` | `jug` and `pocket` directly follow the official numbered depth diagram. |
| `holds[].sizeMillimeters` | Present only for the three pockets on each unit and copied from positions `2` through `4`: 40, 32, and 25 mm. |
| `holds[].fingerCapacity` | Present only for the pockets and copied from the official four-, three-, and two-finger labels. |
| omitted optional fields | No grip posture, depth range, feature tag, material, color, training cue, or other measurement was added. |

The product photograph requires left and right components to remain separately
selectable physical contacts. The explicit CAD/CAM perfect-symmetry statement,
the identical numbered layout, and the official paired images support exact
horizontal mirroring of the corresponding canonical frames. This freezes eight
contacts on one honest paired-front presentation:

| Diagram position | Left/right `board.json` contacts | Exact source-backed mapping |
| --- | --- | --- |
| `1` | `jug-left`, `jug-right` | One broad upper jug contact on each independently suspended unit. |
| `2` | `pocket-40-four-left`, `pocket-40-four-right` | One 40 mm four-finger pocket per unit. |
| `3` | `pocket-32-three-left`, `pocket-32-three-right` | One 32 mm three-finger pocket per unit. |
| `4` | `pocket-25-two-left`, `pocket-25-two-right` | One 25 mm two-finger pocket per unit. |

No rear or rotated presentation is declared: none of the current official
sources identifies a different usable contact on another side. The two color
variants share one physical package and are not duplicate presentations.

### AI-simplified primary illustration (NON-EVIDENCE)

`assets/primary.png` was generated with the built-in image-generation tool.
The official paired product photograph was reference Image 1 for silhouette,
two-unit arrangement, cord suspension, and contact placement. The official
numbered diagram was reference Image 2 for the already frozen contact inventory
and separation. Generated art established no product fact and supplied no
geometry.

The accepted PNG is 1536 × 1024 pixels (aspect `1.5`, SHA-256
`679f403f74b50b63099574b1fc8a39c75c54c27f1a70d66a1a0ec637d4ea6837`).
Prompt:

> Use case: product-mockup
>
> Asset type: Hang Ten hangboard catalog primary presentation image
>
> Input images: Image 1 is Metolius's official straight-on Rock Rings 3D pair photograph and is the authoritative reference for the two independent suspended units, paired left/right arrangement, each unit's silhouette, cord suspension, and physical contact placement. Image 2 is Metolius's official numbered Rock Ring depth guide and is supporting reference for the exact four-contact layout on each unit: upper outer jug surface, 40 mm four-finger pocket, 32 mm three-finger pocket, and 25 mm two-finger pocket.
>
> Primary request: Create a clean AI-simplified straight-on catalog illustration of this exact pair of Rock Rings 3D. Show exactly two separate suspended resin units, one left and one right, at equal height. Preserve exactly four usable contacts on each unit in the documented top-to-bottom layout: one broad upper jug surface surrounding the top opening, one wide 40 mm four-finger pocket, one medium 32 mm three-finger pocket, and one small 25 mm two-finger pocket. Keep the pair perfectly symmetric as documented by the manufacturer.
>
> Scene/backdrop: plain neutral off-white background.
>
> Style/medium: polished simplified 3D product illustration, smooth light-gray resin with restrained fine texture and subtle soft shading; remove all black/blue swirl coloration, printed branding, labels, and numbers.
>
> Composition/framing: exact straight-on view, centered landscape canvas, both complete units fully visible and separated by generous center space; show red-and-black suspension cords rising vertically and out of frame without knots dominating the composition and without overlapping any contact.
>
> Lighting/mood: soft neutral studio lighting that makes every jug and pocket contact boundary clearly readable without dramatic shadows.
>
> Constraints: exactly two independent units; exact bilateral pair symmetry; exactly four contacts per unit and eight total contacts; preserve the tapered rounded triangular body, top cord attachment positions, pocket count, relative pocket widths, vertical spacing, and proportions from the official references; the upper jug must remain visibly distinct from the 40 mm pocket floor directly beneath it; no added or missing holds; no text; no logo; no numbers; no hands; no wall; no watermark. Do not create geometry masks, contours, overlays, outlines, highlights, or annotations.
>
> Avoid: alternate rear surfaces, extra grooves, edges, pinches, slopers, mounting holes, labels, brand marks, decorative elements, perspective skew, contact overlap, ropes crossing the devices, or generic gymnastic rings.

Human acceptance compared the final directly with the official paired product
photograph, numbered depth diagram, training-guide images, and manual. The final
retains two separate suspended units, the three documented pocket openings on
each, and a distinct broad upper jug contact above each 40 mm pocket. It adds no
rear surface, recess, label, or selectable contact. The generated PNG was copied
directly into the package with no crop, registration, detection, segmentation,
mask, contour extraction, vectorization, simplification, or other automatic
geometry operation.

### Direct geometry mapping and review

All eight normalized closed paths were deliberately authored after direct
inspection of the accepted illustration and official evidence. The left unit's
four contacts were authored individually. The corresponding right frames and
paths are exact horizontal mirrors under Metolius's explicit perfect-symmetry
claim. The three regular pocket openings per unit use operator-selected
`roundedRectangle` constraints; the broad curved jug surfaces use custom paths.
Constraints are editing metadata only; the saved paths remain the sole normal,
active, and hit-test geometry.

| Contact pair | Left canonical frame; right mirror | Direct review decision |
| --- | --- | --- |
| `jug-left` / `jug-right` | Left `x 0.145, y 0.322, w 0.306, h 0.143`; exact right mirror | Custom curved path follows only the broad upper contact above the first opening and excludes cord, background, and the 40 mm pocket. |
| `pocket-40-four-left` / `pocket-40-four-right` | Left `x 0.206, y 0.454, w 0.176, h 0.091`; exact right mirror | Rounded path encloses only the upper four-finger pocket opening. |
| `pocket-32-three-left` / `pocket-32-three-right` | Left `x 0.231, y 0.615, w 0.136, h 0.082`; exact right mirror | Rounded path encloses only the middle three-finger pocket opening. |
| `pocket-25-two-left` / `pocket-25-two-right` | Left `x 0.248, y 0.760, w 0.096, h 0.068`; exact right mirror | Rounded path encloses only the lower two-finger pocket opening. |

The package parser validates the single declared PNG, exact ratio, eight unique
hold IDs, nonempty normalized paths, and explicit presentation ownership.
Focused assertions freeze the exact `4 + 4` inventory, measurements,
capacities, and perfect paired mirrors. Workbench extraction and final review
results are recorded in the Task 10 report.
