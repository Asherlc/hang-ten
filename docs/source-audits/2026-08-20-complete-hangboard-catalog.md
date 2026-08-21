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
