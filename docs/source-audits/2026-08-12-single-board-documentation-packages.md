# Single-board documentation package source audit

Checked 2026-08-12. This historical audit preserves the primary sources reviewed
for four models. The incomplete draft directories and their art were removed;
they are not retained inputs. Future geometry is directly authored from primary
manufacturer evidence under `docs/ADDING_A_BOARD.md`. A product page or gallery
image still cannot establish non-visible capacity, grip posture, or measurement
facts unless the manufacturer labels them.

## Evidence-key readiness

Every ready package would need exact evidence for the board facts; every
`holds[].{id,name,shortLabel,detail,kind,frame,sizeMillimeters,`
`depthRangeMillimeters,gripType,fingerCapacity,cueStyle,features}` field;
every semantic target; and `assets/primary.png`. The source rows below state
which of those requirements the manufacturer material actually covers.

## Lattice Triple Rung (`lattice.triple-rung`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, dimensions, material, three named edge depths, and continuous extruded design | [Lattice Triple Rung product page](https://latticetraining.com/product/triple-rung-wooden-hangboard/) | Lattice lists 55 x 13 x 5 cm, wood construction, and 45 mm flat, 20 mm, and 10 mm edges. It says the board is continuous and has no pockets. |
| Front presentation and visible ordering | [Lattice Triple Rung product gallery](https://latticetraining.com/product/triple-rung-wooden-hangboard/) | Product-gallery imagery establishes visible silhouette and rung layout only. |
| Usage/test protocol | [Triple Rung instructions](https://latticetraining.com/app/uploads/2020/07/Triple-Run-Instructions-130x500mm-Folded-Print-Ready-PDF.pdf) | Installation and general training instructions; not a physical hold map. |

### `lattice-triple-rung`

**Blocker:** Lattice's materials identify the three edge *sizes*, but do not
publish a numbered physical-hold diagram or map each edge to all package
fields: a discrete boundary/frame, finger capacity, grip type, cue style, and
feature classification. The product description's statement that a climber
can choose hand width does not define the schema's `fingerCapacity` value.
It also does not define semantic target IDs. Those facts cannot be inferred
from the continuous profile alone, so no complete package was authored then.

## Moon Armstrong Fingerboard (`moon.armstrong`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, overall dimensions, aggregate hold inventory, and selected central hold depths | [Moon Armstrong Fingerboard Beech](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) | Moon identifies the Armstrong model; publishes 65 x 16.5 x 5.5 cm, an aggregate hold inventory, central 22 mm and 18 mm one-arm edges, and a jug for one-arm pull-ups. |
| Visible layout | [Moon Armstrong Fingerboard Beech](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html) | The manufacturer gallery shows a visible layout only. |
| Per-hold guide/measurements | No manufacturer-issued numbered hold guide or complete per-hold measurement source located | No complete physical inventory or semantic map. |

### `moon-armstrong`

**Blocker:** Moon's aggregate inventory does not assign each individual
physical hold an identity, boundary/frame, depth, capacity, or grip
classification. It also does not map physical holds to semantic targets or to
the normalized frames required by the package. A gallery cannot supply those
unpublished one-to-one mappings. No `board.json`, `semantics.json`, or
`evidence.json` is permitted.

## Nature Climbing Stoak Board III (`nature.stoak-board-iii`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, overall dimensions, material, 22 mm edge, top jug, and configurable inserts | [Nature Climbing Stoak Board III Oak](https://natureclimbing.com/products/stoak-board-iii) | Nature lists 57 x 12 x 5.5 cm, oak/granite construction, a 22 mm edge, a top jug, and 5 mm magnetic insert adjustments. |
| Product gallery and surface appearance | [Nature Climbing Stoak Board III Oak](https://natureclimbing.com/products/stoak-board-iii) | Gallery establishes visible silhouette and materials only. |
| Per-hold guide/measurements for the selected configuration | No manufacturer-issued numbered guide or fixed-configuration hold map located | No one-to-one inventory, boundaries, capacities, classifications, or adjustment-state map. |

### `nature-stoak-board-iii`

**Blocker:** The configurable insert system means the available edge depth can
change. Nature does not publish a source assigning every configuration's
physical hold boundary, final depth, finger capacity, grip type, or semantic
target. A package cannot choose one configuration or label visible recesses
without unsupported facts. The incomplete candidate was later removed.

## target10a Linebreaker Base (`target10a.linebreaker-base`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity and high-level beginner positioning | [Linebreaker BASE product article](https://www.target10a.com/magazin/2017/01/01/linebreaker-base/) | target10a identifies the Linebreaker BASE and describes its grip selection and depths as intended for beginners. |
| Safety and mounting information | [Linebreaker BASE safety information](https://m.media-amazon.com/images/I/418jCjplLXL.pdf) | A manufacturer-branded document hosted on Amazon's CDN; it supplies safety, mounting, and use information, but no hold map. Its hosting does not establish target10a.com provenance. |
| Per-hold guide, dimensions, and measurements | No official numbered hold guide, front/oblique measurement set, or per-hold depth source located | No complete physical inventory, boundaries, capacities, or classifications. |

### `target10a-linebreaker-base`

**Blocker:** The official target10a.com article is high-level copy, and the
manufacturer-branded CDN document does not enumerate holds. Neither supports
a discrete physical-hold inventory, per-hold dimensions/depths, finger
capacities, grip types, semantics, or normalized hold frames. A future complete
package must omit unsupported optional facts and directly author visible paths.

## Required follow-up

Obtain manufacturer-published hold diagrams, manuals, or measurement tables
that clarify the discrete hold inventory and any optional facts to be claimed.
The source set must also select and document one Stoak Board III insert
configuration. Then directly author and review a complete flat package, omitting
anything the sources do not establish.
