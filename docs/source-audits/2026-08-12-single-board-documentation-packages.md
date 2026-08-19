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
| Product identity, overall dimensions, aggregate hold inventory, and selected central hold depths | [Moon Armstrong Fingerboard Beech](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) | Moon identifies the Armstrong model; publishes 65 x 16.5 x 5.5 cm, an aggregate hold inventory, central 22 mm and 18 mm one-arm edges, and a jug for one-arm pull-ups. |
| Visible layout | [Moon Armstrong Fingerboard Beech](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) | The manufacturer gallery shows a visible layout only. |
| Per-hold guide/measurements | No manufacturer-issued numbered hold guide or complete per-hold measurement source located | No complete physical inventory or semantic map. |

### `moon-armstrong`

**Authoring note:** Reconcile Moon's aggregate inventory with each visible
contact in the official gallery. Retain the explicitly identified 22 mm and
18 mm central edges and jug; omit unassigned measurements, capacity, and
posture. Author the remaining visible paths directly.

## Nature Climbing Stoak Board III (`nature.stoak-board-iii`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, overall dimensions, material, 22 mm edge, top jug, and configurable inserts | [Nature Climbing Stoak Board III Oak](https://natureclimbing.com/products/stoak-board-iii) | Nature lists 57 x 12 x 5.5 cm, oak/granite construction, a 22 mm edge, a top jug, and 5 mm magnetic insert adjustments. |
| Product gallery and surface appearance | [Nature Climbing Stoak Board III Oak](https://natureclimbing.com/products/stoak-board-iii) | Gallery establishes visible silhouette and materials only. |
| Per-hold guide/measurements for the selected configuration | No manufacturer-issued numbered guide or fixed-configuration hold map located | No one-to-one inventory, boundaries, capacities, classifications, or adjustment-state map. |

### `nature-stoak-board-iii`

**Authoring note:** The magnetic inserts change available depth. Document the
configuration shown by the selected presentation and retain only the explicit
22 mm edge, top jug, dimensions, and material facts. Author visible contacts
directly and omit unsupported configuration-specific values.

## target10a Linebreaker Base (`target10a.linebreaker-base`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity and high-level beginner positioning | [Linebreaker BASE product article](https://www.target10a.com/magazin/2017/01/01/linebreaker-base/) | target10a identifies the Linebreaker BASE and describes its grip selection and depths as intended for beginners. |
| Safety and mounting information | [Linebreaker BASE safety information](https://m.media-amazon.com/images/I/418jCjplLXL.pdf) | A manufacturer-branded document hosted on Amazon's CDN; it supplies safety, mounting, and use information, but no hold map. Its hosting does not establish target10a.com provenance. |
| Per-hold guide, dimensions, and measurements | No official numbered hold guide, front/oblique measurement set, or per-hold depth source located | No complete physical inventory, boundaries, capacities, or classifications. |

### `target10a-linebreaker-base`

**Authoring note:** Use the exact official product views to freeze the visible
inventory and the article only for its high-level product claims. The CDN
document supports safety/mounting, not hold measurements. Omit unsupported
depth, capacity, and posture values and directly author the visible paths.

## Required follow-up

For each unfinished model, reconcile the product copy with official front and
oblique views, document conflicts (including the Stoak insert configuration),
directly author and review the complete package, and omit anything the sources
do not establish.
