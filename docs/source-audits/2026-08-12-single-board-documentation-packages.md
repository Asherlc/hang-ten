# Single-board documentation package source audit

Checked 2026-08-12. This historical audit preserves the primary sources reviewed
for four models. The incomplete draft directories and their art were removed;
they are not retained inputs. Future geometry is directly authored from primary
manufacturer evidence under `docs/ADDING_A_BOARD.md`. A product page or gallery
image still cannot establish non-visible capacity, grip posture, or measurement
facts unless the manufacturer labels them.

The source rows below separate established product facts from optional facts
that must remain omitted. Visible boundaries are directly authored from the
manufacturer views and then reviewed; they are not treated as measurements.

## Lattice Triple Rung (`lattice.triple-rung`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, dimensions, material, three named edge depths, and continuous extruded design | [Lattice Triple Rung product page](https://latticetraining.com/product/triple-rung-wooden-hangboard/) | Lattice lists 55 x 13 x 5 cm, wood construction, and 45 mm flat, 20 mm, and 10 mm edges. It says the board is continuous and has no pockets. |
| Front presentation and visible ordering | [Lattice Triple Rung product gallery](https://latticetraining.com/product/triple-rung-wooden-hangboard/) | Product-gallery imagery establishes visible silhouette and rung layout only. |
| Usage/test protocol | [Triple Rung instructions](https://latticetraining.com/app/uploads/2020/07/Triple-Run-Instructions-130x500mm-Folded-Print-Ready-PDF.pdf) | Installation and general training instructions; not a physical hold map. |

### `lattice-triple-rung`

**Authoring note:** Lattice identifies three continuous edges and their sizes.
Author those three visible contacts directly; omit fixed capacity, posture, and
other unsupported optional tags. This package was later completed.

## Moon Armstrong Fingerboard (`moon.armstrong`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, dimensions, material, aggregate hold inventory, and central one-arm contacts | [Moon Armstrong Fingerboard Beech](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) | Moon identifies the beech Armstrong model and `65 × 16.5 × 5.5 cm`. Current product copy names in-cut jugs, 35-degree slopers, paired 25/20/15/10/8 mm slots, 22 mm two-finger and one-finger pockets, plus central 22 mm and 18 mm one-arm edges and a central one-arm jug. |
| Straight-on layout and engraved depth assignment | [Official front image](https://moonclimbing.com/media/catalog/product/cache/8fbd88411911f97522c3f864e19b1b09/6/0/60-112-bec_moon_armstrong_fingerboard_bec_01.jpg) | Establishes the exact visible 21-contact layout and one-to-one placement of the five paired edge depths, paired 22 mm two-finger pockets, paired 22 mm monos, and central 22/18 mm edges. |
| Oblique contact corroboration | [Official oblique detail](https://moonclimbing.com/media/catalog/product/cache/8fbd88411911f97522c3f864e19b1b09/6/0/60-112-bec_moon_armstrong_fingerboard_bec_02.jpg) | Corroborates that the upper side cavities are in-cut jugs and that the raised upper contacts are surfaces rather than extra recesses. |

### `moon-armstrong`

**Frozen inventory:** 21 physical contacts: one central jug, one central 22 mm
edge, one central 18 mm edge, mirrored side jugs, mirrored 35-degree slopers,
ten paired edge slots (25/20/15/10/8 mm), two 22 mm two-finger pockets, and two
22 mm monos. The official copy assigns capacity only to the 22 mm pockets, so
capacity remains omitted from edges and jugs. No grip-posture or app-semantic
metadata is added. The selected presentation is the manufacturer front image,
converted from JPEG to PNG without cropping or geometric alteration.

## Nature Climbing Stoak Board III (`nature.stoak-board-iii`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, dimensions, material, 22 mm edge, top jug, and configurable inserts | [Nature Climbing Stoak Board III Oak](https://natureclimbing.com/products/stoak-board-iii) | Nature lists `57 × 12 × 5.5 cm`, FSC-certified oak and granite, a 22 mm edge, a comfortable top jug, and four 5 mm inserts with the Oak version. |
| Straight-on selected configuration | [Official front image](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/6_2a2069e0-b45e-4eca-aa65-59febfe7c958.png?v=1763577563) | Establishes the exact visible region boundaries and the selected Oak/granite presentation. |
| Contact map and depth/material assignment | [Official annotated image](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/Comfortable_jug_1.png?v=1763986786) | Maps the comfortable jug, 22 mm center edge, 55 mm open-hand contact, mirrored gradient 10–25 mm edges, mirrored lower 30 mm wood / 20 mm granite contacts, and center lower 30 mm granite or ergonomic wood contact. |
| Oblique corroboration | [Official oblique image](https://cdn.shopify.com/s/files/1/0657/7736/9334/files/4_671cc28f-ab91-4566-ad88-887bace217be.png?v=1764017417) | Confirms the continuity of the lower wood/granite contact surfaces and distinguishes contact faces from the board silhouette. |

### `nature-stoak-board-iii`

**Frozen inventory:** eight physical contacts under the continuous-contact rule:
top jug; 55 mm upper open-hand contact; center 22 mm edge; mirrored gradient
10–25 mm contacts; mirrored lower continuous 30 mm wood / 20 mm granite
contacts; and one center lower continuous 30 mm granite / ergonomic wood
contact. Material transitions do not split a continuous contact into extra
holds. The package depicts the official Oak gallery configuration. Magnetic
inserts are product accessories/configuration facts and are not modeled as
additional holds or as a fixed adjusted depth.

## target10a Linebreaker Base (`target10a.linebreaker-base`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, dimensions, material, categories, depths, and capacities | [Linebreaker BASE product page](https://www.target10a.com/en/linebreaker-boards/409-linebreaker-base-trainingsboard.html) | target10a lists `58 × 15 × 5.5 cm`, yellow poplar, two jugs, 32.5- and 22.5-degree slopers, 16/20/18 mm bars, 37/28/45/24/30/50 mm pockets with four-/three-/two-finger capacity assignments, and a 35-degree 35 mm sloper bar. |
| Straight-on physical layout | [Official front image](https://www.target10a.com/934-thickbox_default/linebreaker-base-trainingsboard.jpg) | Establishes the exact 24 visible physical contacts and mirrored placement. |
| Manufacturer hold map | [Official depth/capacity map](https://www.target10a.com/935-thickbox_default/linebreaker-base-trainingsboard.jpg) | Maps each contact family, depth, finger capacity, and sloper angle to the straight-on layout. |
| Oblique contact corroboration | [Official oblique image](https://www.target10a.com/931-thickbox_default/linebreaker-base-trainingsboard.jpg) | Distinguishes the top sloper surfaces, center sloper bars, jugs, and recessed bars/pockets. |

### `target10a-linebreaker-base`

**Frozen inventory:** 24 physical contacts: two jugs; two 32.5-degree outer
slopers; one 22.5-degree center sloper; paired 16 mm four-finger bars; paired
28 mm three-finger pockets; paired 37 mm four-finger pockets; paired 45 mm
three-finger pockets; paired 50 mm two-finger pockets; one 35-degree, 35 mm
center sloper bar; paired 30 mm and 24 mm two-finger pockets; paired 20 mm
four-finger bars; and paired 18 mm three-finger bars. Those values and
capacities are retained because the official page and manufacturer map agree.
Grip posture and app-semantic tags remain omitted. The presentation image is
the official straight-on JPEG converted to PNG without cropping or geometric
alteration. The official map assigns the outer 16 mm bar and 37 mm pocket to
the upper and lower contact bands of the same long recessed footprint. Their
canonical hit regions therefore partition that visible recess vertically in
the map's stated order, rather than overlapping and making one contact
unselectable.

## Completion verification

All three packages are complete and visually reviewed. Their 40 regular pieces
use operator-selected constraints and pass the production `+1 px` resize
invariants. A zero-distance production save is byte-exact for four pieces and
only reserializes decimal precision for the other 36; the independent rendered
comparison found no visible snap. These constraints are therefore verified for
mathematical primitive consistency, not described as universally byte-exact.
