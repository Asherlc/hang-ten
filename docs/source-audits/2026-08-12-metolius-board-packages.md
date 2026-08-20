# Metolius board-package evidence audit

Checked 2026-08-12 and re-reviewed 2026-08-19. This audit records the official
Metolius evidence used to create four complete flat packages. Every canonical
region was directly authored against the official front view and checked against
the model-specific numbered/depth diagram. The presentation PNGs are lossless
format conversions of the official JPEGs; they were not cropped or geometrically
processed.

The Metolius material below labels visible hold groups and, where stated, depth
and pocket-finger counts. Official diagrams and imagery support direct
boundaries; optional capacity, posture, and feature values remain omitted unless
the model-specific source establishes them.
In particular, the Wood Grips Compact II diagram and manual are model-specific
and were not used for any conclusion here.

| Candidate | Dedicated official sources reviewed | What the documents establish | Historical evidence limitation |
| --- | --- | --- | --- |
| `metolius-climbers-edge` | [product](https://www.metoliusclimbing.com/products/climbers-edge-board); [official front](https://www.metoliusclimbing.com/cdn/shop/files/The-Climber_s-Edge-Training-Board_67ebe212-d205-4f2c-9ca9-048b1792351d.jpg?v=1765309719); [official specification/depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/Climber_s-Edge-Spec.jpg?v=1765309719); [shared training-board manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826) | Identity, dimensions, visible boundaries, exact symmetric 15-contact inventory, six edge depths, one 40 mm-radius round sloper, two 20-degree flat slopers, and two jugs. | No optional grip posture or capacity facts were added. |
| `metolius-contact` | [product](https://www.metoliusclimbing.com/products/contact-training-board); [official front](https://www.metoliusclimbing.com/cdn/shop/files/Contact-Hangboard-black-white.jpg?v=1759459002); [official numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/con-num-dep_341f2901-a11e-4256-a4c3-0531110c730e.jpg?v=1762201170); [training guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Identity, dimensions, perfect symmetry, visible boundaries, two pinches, two jugs, two round slopers, 22 mirrored pockets, one center flat sloper, and four center edges: 33 contacts. | No app-specific cue or feature values were added. |
| `metolius-project` | [product](https://www.metoliusclimbing.com/products/project-training-board); [official front](https://www.metoliusclimbing.com/cdn/shop/files/Project-Board-black-white-swirl.jpg?v=1759459896); [official numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/project-depth.jpg?v=1762201307) | Identity, dimensions, perfect symmetry, visible boundaries, mirrored positions 1 through 7, and center positions 8 through 10: 17 contacts. | No app-specific cue or feature values were added. |
| `metolius-simulator-3d` | [product](https://www.metoliusclimbing.com/collections/training-boards/products/simulator-training-board); [official front](https://www.metoliusclimbing.com/cdn/shop/files/Simulator-black-white.jpg?v=1759460469); [official numbered depth diagram](https://www.metoliusclimbing.com/cdn/shop/files/sim-num-dep_c543622d-e670-4601-8d4d-792cc8e46dea.jpg?v=1762201085); [training guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | Identity, dimensions, symmetric visible boundaries, mirrored positions 1 through 13, and center positions 14 through 18: 31 contacts. | No app-specific cue or feature values were added. |

## Frozen inventories and field mappings

The product pages supply `manufacturer`, `name`, `productURL`, `dimensions`,
and the conservative subtitle. The official front JPEG for each model supplies
`assets/primary.png` and the visible boundary of every geometry region. The
official diagram supplies the numbered position, kind, millimeter value, and
finger count where it explicitly labels them. `sizeMillimeters` records the
published edge/pocket depth only; radius/diameter labels on slopers stay in the
source-backed name because they are not edge depth. Every unmentioned optional
field is omitted.

### Climber's Edge — 15 contacts

- Top surfaces: two jugs, two 20-degree flat slopers, and one center 40
  mm-radius round sloper.
- Upper edge row: mirrored 20 mm (`5`) and 15 mm (`3`) contacts around one
  center 10 mm (`1`) contact.
- Lower edge row: mirrored 17.5 mm (`6`) and 12.5 mm (`4`) contacts around one
  center 7.5 mm (`2`) contact.
- The source publishes half-millimeter depths; the current package schema only
  accepts positive integer `sizeMillimeters`, so 17.5, 12.5, and 7.5 remain in
  the hold names and are not rounded into structured values.

### Contact — 33 contacts

- Mirrored surface positions: `1` variable-width pinches, `2` outer jugs, and
  `3` 63 mm round slopers. Center `15` is the 53 mm flat sloper.
- Mirrored pocket positions `4` through `14` map exactly to the diagram's
  published depth/finger pairs: 30/4, 40/2, 20/3, 30/3, 32/2, 20/4, 25/3,
  25/2, 12/4, 17/3, and 17/2.
- Center edges `16` through `19` map to 15, 35, 28, and 23 mm.

### Project — 17 contacts

- Mirrored positions `1` through `7`: outer jug; 55 mm flat sloper; 45 mm
  3-finger pocket; 30 mm edge; 40 mm 2-finger pocket; 22 mm 3-finger pocket;
  22 mm 2-finger pocket.
- Center positions `8` through `10`: 53 mm round sloper, 39 mm edge, and 16 mm
  edge.

### Simulator 3-D — 31 contacts

- Mirrored positions `1` through `13`: outer jug; 55 mm flat sloper; 65 mm
  round sloper; 30 mm 3-finger pocket; 25 mm edge; 19 mm edge; 36 mm edge;
  15 mm 3-finger pocket; 35 mm 3-finger pocket; 17 mm 3-finger pocket; 14 mm
  edge; 30 mm 2-finger pocket; 14 mm 2-finger pocket.
- Center positions `14` through `18`: jug; 50 mm 3-finger pocket; 37 mm
  3-finger pocket; 28 mm 2-finger pocket; 32 mm 2-finger pocket.

The manufacturer expressly identifies Contact and Project as CAD/CAM symmetric;
the Simulator and Climber's Edge diagrams also present mirrored physical
contacts. Paired geometry therefore uses exact normalized frame mirroring. The
regular recessed contacts use manually selected constraints; sculpted jugs,
slopers, and pinches remain freeform except the visibly circular Contact round
slopers. Canonical geometry, not the constraint metadata, remains the runtime
render/highlight/hit-test source.

During the 2026-08-19 visual re-review, the Contact `1` pair was deliberately
redrawn around the narrow, visible side-pinch rails in the official front view;
the surrounding white image background is excluded. Simulator positions `2`
and `3` were likewise redrawn around only the visible flat- and round-sloper
top surfaces, with their upper boundaries inset to the product silhouette.
Every freeform paired top/outer surface is stored as an exact horizontal mirror.
All 74 constrained paths were materialized from the checked-in Workbench
primitive definitions (including its current cubic circle constant) and then
saved as tight canonical path frames; reapplying each saved constraint is an
exact no-op.
