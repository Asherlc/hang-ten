# Metolius board-package evidence audit

Checked 2026-08-12 and re-reviewed 2026-08-19 and 2026-08-25. This audit records the official
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
- The source publishes half-millimeter depths. The package records the exact
  17.5 mm, 12.5 mm, and 7.5 mm values in `sizeMillimeters` for the mapped lower
  edge contacts; no rounding is applied.

### Contact — 33 contacts

- Mirrored surface positions: `1` variable-width pinches, `2` outer jugs, and
  `3` 63 mm round slopers. Center `15` is the 53 mm flat sloper.
- Mirrored pocket positions `4` through `14` map exactly to the diagram's
  published depth/finger pairs: 30/4, 40/2, 20/3, 30/3, 32/2, 20/4, 25/3,
  25/2, 12/4, 17/3, and 17/2.
- Center edges `16` through `19` map to 15, 35, 28, and 23 mm.

### Project — 15 continuous contacts

- Mirrored positions `1` and `3` through `7`: outer jug; 45 mm 3-finger
  pocket; 30 mm edge; 40 mm 2-finger pocket; 22 mm 3-finger pocket; and 22 mm
  2-finger pocket.
- The diagram places mirrored position `2` flat-sloper labels and center
  position `8` round-sloper label on one uninterrupted top contact with no
  separator. The package therefore maps all three labels to the single
  continuous `round-sloper-8-center` stable ID. Center positions `9` and `10`
  are separate 39 mm and 16 mm edges.

### Simulator 3-D — 29 continuous contacts

- Mirrored positions `1` and `4` through `13`: outer jug; 30 mm 3-finger
  pocket; 25 mm edge; 19 mm edge; 36 mm edge; 15 mm 3-finger pocket; 35 mm
  3-finger pocket; 17 mm 3-finger pocket; 14 mm edge; 30 mm 2-finger pocket;
  and 14 mm 2-finger pocket.
- On each side, the diagram's position `2` flat-sloper and position `3`
  round-sloper labels occupy one uninterrupted top contact with no separator.
  Each label pair maps to one continuous stable ID,
  `round-sloper-3-left` or `round-sloper-3-right`.
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

## 2026-08-25 source-audited metadata pilot

The current product pages and the exact official diagrams linked above were
re-opened on 2026-08-25. Stable-ID overlays were manually reviewed under
`.context/hangboard-metadata-backfill-icky-cow/metolius/`; `icky-cow` is the
workspace-owned fallback because `CONDUCTOR_WORKSPACE_NAME` was unset. The
overlays are review aids only and did not alter geometry. Each source label
maps to these visible stable IDs on presentation `front`:

### Climber's Edge reviewed label map

| Exact manufacturer label | Stable hold ID(s) | Verified kind |
| --- | --- | --- |
| `Jug` | `jug-left`, `jug-right` | `jug` |
| `Flat Sloper` (product page: 20-degree flat sloper) | `flat-sloper-left`, `flat-sloper-right` | `sloper` |
| `Round Sloper` (product page: 40 mm radius round sloper) | `round-sloper-center` | `sloper` |
| `1 — 10 mm edge` | `edge-10-center` | `edge` |
| `2 — 7.5 mm edge` | `edge-7-5-center` | `edge` |
| `3 — 15 mm edge` | `edge-15-left`, `edge-15-right` | `edge` |
| `4 — 12.5 mm edge` | `edge-12-5-left`, `edge-12-5-right` | `edge` |
| `5 — 20 mm edge` | `edge-20-left`, `edge-20-right` | `edge` |
| `6 — 17.5 mm edge` | `edge-17-5-left`, `edge-17-5-right` | `edge` |

### Contact reviewed label map

| Exact manufacturer label | Stable hold ID(s) | Verified kind |
| --- | --- | --- |
| `1 — variable pinches` | `pinch-left`, `pinch-right` | `pinch` |
| `2 — outer jugs` | `jug-left`, `jug-right` | `jug` |
| `3 — 63 mm round slopers` | `round-sloper-3-left`, `round-sloper-3-right` | `sloper` |
| `4 — 30 mm 4-finger pockets` | `pocket-4-left`, `pocket-4-right` | `pocket` |
| `5 — 40 mm 2-finger pockets` | `pocket-5-left`, `pocket-5-right` | `pocket` |
| `6 — 20 mm 3-finger pockets` | `pocket-6-left`, `pocket-6-right` | `pocket` |
| `7 — 30 mm 3-finger pockets` | `pocket-7-left`, `pocket-7-right` | `pocket` |
| `8 — 32 mm 2-finger pockets` | `pocket-8-left`, `pocket-8-right` | `pocket` |
| `9 — 20 mm 4-finger pockets` | `pocket-9-left`, `pocket-9-right` | `pocket` |
| `10 — 25 mm 3-finger pockets` | `pocket-10-left`, `pocket-10-right` | `pocket` |
| `11 — 25 mm 2-finger pockets` | `pocket-11-left`, `pocket-11-right` | `pocket` |
| `12 — 12 mm 4-finger pockets` | `pocket-12-left`, `pocket-12-right` | `pocket` |
| `13 — 17 mm 3-finger pockets` | `pocket-13-left`, `pocket-13-right` | `pocket` |
| `14 — 17 mm 2-finger pockets` | `pocket-14-left`, `pocket-14-right` | `pocket` |
| `15 — 53 mm flat sloper` | `flat-sloper-center` | `sloper` |
| `16 — 15 mm edge` | `edge-16-center` | `edge` |
| `17 — 35 mm edge` | `edge-17-center` | `edge` |
| `18 — 28 mm edge` | `edge-18-center` | `edge` |
| `19 — 23 mm edge` | `edge-19-center` | `edge` |

### Project reviewed label map

| Exact manufacturer label | Stable hold ID(s) | Verified kind |
| --- | --- | --- |
| `1 — outer jugs` | `jug-1-left`, `jug-1-right` | `jug` |
| `2 — 55 mm flat slopers`; `8 — 53 mm round sloper` | `round-sloper-8-center` (one continuous top contact) | `sloper` |
| `3 — 45 mm 3-finger pockets` | `pocket-3-left`, `pocket-3-right` | `pocket` |
| `4 — 30 mm edges` | `edge-4-left`, `edge-4-right` | `edge` |
| `5 — 40 mm 2-finger pockets` | `pocket-5-left`, `pocket-5-right` | `pocket` |
| `6 — 22 mm 3-finger pockets` | `pocket-6-left`, `pocket-6-right` | `pocket` |
| `7 — 22 mm 2-finger pockets` | `pocket-7-left`, `pocket-7-right` | `pocket` |
| `9 — 39 mm edge` | `edge-9-center` | `edge` |
| `10 — 16 mm edge` | `edge-10-center` | `edge` |

### Simulator 3-D reviewed label map

| Exact manufacturer label | Stable hold ID(s) | Verified kind |
| --- | --- | --- |
| `1 — outer jugs` | `jug-1-left`, `jug-1-right` | `jug` |
| `2 — 55 mm flat slopers`; `3 — 65 mm round slopers` | `round-sloper-3-left`, `round-sloper-3-right` (one continuous contact per side) | `sloper` |
| `4 — 30 mm 3-finger pockets` | `pocket-4-left`, `pocket-4-right` | `pocket` |
| `5 — 25 mm edges` | `edge-5-left`, `edge-5-right` | `edge` |
| `6 — 19 mm edges` | `edge-6-left`, `edge-6-right` | `edge` |
| `7 — 36 mm edges` | `edge-7-left`, `edge-7-right` | `edge` |
| `8 — 15 mm 3-finger pockets` | `pocket-8-left`, `pocket-8-right` | `pocket` |
| `9 — 35 mm 3-finger pockets` | `pocket-9-left`, `pocket-9-right` | `pocket` |
| `10 — 17 mm 3-finger pockets` | `pocket-10-left`, `pocket-10-right` | `pocket` |
| `11 — 14 mm edge` | `edge-11-left`, `edge-11-right` | `edge` |
| `12 — 30 mm 2-finger pockets` | `pocket-12-left`, `pocket-12-right` | `pocket` |
| `13 — 14 mm 2-finger pockets` | `pocket-13-left`, `pocket-13-right` | `pocket` |
| `14 — center jug` | `jug-14-center` | `jug` |
| `15 — 50 mm 3-finger pocket` | `pocket-15-center` | `pocket` |
| `16 — 37 mm 3-finger pocket` | `pocket-16-center` | `pocket` |
| `17 — 28 mm 2-finger pocket` | `pocket-17-center` | `pocket` |
| `18 — 32 mm 2-finger pocket` | `pocket-18-center` | `pocket` |

The exact words `jug`, `sloper`, `edge`, `pocket`, and `pinch` in these
manufacturer labels independently verify every declared `kind`; no type came
from path shape or board metadata. Exact two-/three-/four-finger pocket labels
also verify both `fingerCapacity` and the matching structural pocket
`gripType`. This added 22 Contact, 8 Project, and 16 Simulator pocket grip
enums; Climber's Edge had no pocket label. Existing exact scalar edge/pocket
sizes and finger counts were retained; no field was removed on these four
packages.

Every hold has an explicit ledger outcome for all seven audited fields. The
manufacturer material publishes no lower/upper depth ranges, per-contact hand
capacities, or exact package feature-tag sets. Finger capacity is
`notApplicable` for non-pockets. Non-pocket grip posture remains unavailable.
Sloper angles, radii, and other non-depth measurements stay source-backed in
the names and are absent from `sizeMillimeters`; in particular, the continuous
Project and Simulator slopers have multiple labelled sloper measurements and
no single source-supported scalar contact depth.
