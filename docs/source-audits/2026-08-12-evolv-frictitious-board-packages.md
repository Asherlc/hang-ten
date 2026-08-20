# Evolv and Frictitious package-source audit

Checked 2026-08-12. This historical audit records sources that can be reused
under the current direct-authoring contract in `docs/ADDING_A_BOARD.md`. A
product page and manufacturer-hosted imagery support identity, visible contact
boundaries, and presentation. They do not establish non-visible measurements,
capacity, or grip posture unless the manufacturer labels those facts.

The former incomplete candidate directories were removed. Evolv Kilter Basic
Long was later completed independently; future Frictitious packages must be
created complete with directly authored paths rather than restoring old art.

## Evolv Kilter Basic Long (`evolv.kilter-basic-long`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, manufacturer, material, dimensions, and listed hold depths | [Evolv Basic Training Board (Long)](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105) | Evolv identifies the Kilter collaboration; lists 79 cm × 16 cm × 6 cm and a rounded jug plus 20, 15, and 10 mm rounded edges. |
| Straight-on visible layout | [Evolv manufacturer-hosted still image](https://oberalp.imgix.net/ef857c73-13f1-4205-ac47-706cd101e1bb.jpg?auto=format&cs=srgb&fit=clip&type=still&w=628) | Visible silhouette and layout only. |
| Oblique visible surfaces | [Evolv manufacturer-hosted technical image](https://oberalp.imgix.net/f8a564c9-b501-445f-bd43-af630730abfd.jpg?auto=format&cs=srgb&fit=clip&type=tech_detail&w=628) and [second technical image](https://oberalp.imgix.net/e3b05632-02ce-467f-9226-d2a2862c482a.jpg?auto=format&cs=srgb&fit=clip&type=tech_detail&w=628) | Visible surface shape only. |

### `evolv-kilter-basic-long`

**Authoring note:** Evolv identifies the rounded jug and the 20, 15, and 10 mm
rows. The four visible continuous contacts may be directly authored; omit
unsupported capacities and posture. This package was later completed.

## Frictitious DoorMount Pro 7 (`frictitious.doormount-pro-7`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, board dimensions, material, and overall load rating | [Frictitious DoorMount Pro product page](https://frictitiousclimbing.com/en-ca/products/doormount-pro) | Lists Pro 7 dimensions (25.5 in × 4.5 in × 2.25 in), poplar wood hangboard, and system rating. |
| Manufacturer front image | [DoorMount Pro 7 front image](https://cdn.shopify.com/s/files/1/0093/8783/5451/files/DMP-7-Front_d597f381-f23b-4d16-a5b2-d9d201171fa5.jpg?v=1784063035) | Visible silhouette, engraved depth labels, symmetry, and continuous physical boundaries. |
| Manufacturer pocket image | [DoorMount Pro pocket image](https://cdn.shopify.com/s/files/1/0093/8783/5451/files/DMP-Pockets.jpg?v=1779384260) | Corroborates that the pocket is integrated into the 25 mm continuous contact rather than a separately isolated cavity. |
| Manufacturer installation imagery | [DoorMount Pro Quick Start Guide](https://frictitiousclimbing.com/en-ca/pages/doormount-pro-quick-start-guide) | Mount and orientation instructions, not a hold map. |

The product page says Pro 7 has seven holds and names a pull-up jug, pockets,
and 35, 25, 20, 15, and 10 mm edges.

### `frictitious-doormount-pro-7`

**Authoring note:** The published seven-hold total and named jug/edge families
must reconcile with the seven visible logical contacts. The official images may
support those boundaries; omit capacity or posture not explicitly stated.

**2026-08-19 frozen mapping:** Seven logical physical contacts are represented:
one full-width top jug; mirrored 35 mm cavities; mirrored continuous contacts
combining each 25 mm edge with its integrated pocket; and mirrored lower
continuous contacts spanning the engraved 20, 15, and 10 mm steps. Engraved
depth transitions do not create physical gaps, so the mixed and lower contacts
must not be split into extra holds. `kind: edge` is the conservative dominant
classification for the mixed continuous contact; no capacity is asserted. The
official front JPEG is converted to PNG solely to satisfy the package asset
contract, with its square canvas and presentation content otherwise unchanged.
Only the regular 35 mm outlines receive manually selected rounded-rectangle
constraints. The lower contacts have full-height rounded ends and use pill
constraints. The continuous top jug and mixed contacts remain freeform. Each
retained constraint was materialized from the current Workbench primitive and
passes an exact zero-delta constrained resize.

## Frictitious Megalith (`frictitious.megalith`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, dimensions, material, and published edge sizes | [Frictitious Megalith product page](https://frictitiousclimbing.com/products/megalith) | Lists 26.75 in × 6.5 in × 2.25 in, poplar wood, seven shoulder-width edge sizes (8–40 mm), full-width jug, a 25 mm center hold, a two-finger pocket on the 40 mm edge, and “mono pockets.” |
| Manufacturer front imagery | [Megalith front image](https://cdn.shopify.com/s/files/1/0093/8783/5451/files/Megalith-Front.jpg?v=1780436232) and [alternate official front image](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front-1.jpg?v=1780436232&width=3840) | Visible silhouette, engraved sizes, paired layout, continuous boundaries, and isolated mono cavities. |

### `frictitious-megalith`

**Authoring note:** Reconcile the seven edge sizes, full-width jug, center hold,
two-finger pocket, and visible mono pockets into one physical inventory. The
official images support visible boundaries, including whether the integrated
pocket shares a logical contact; omit any unsupported capacity or posture.

**2026-08-19 frozen mapping:** Ten logical physical contacts are represented:
one full-width jug; mirrored continuous top contacts spanning the engraved 8,
10, and 12 mm steps; mirrored middle contacts spanning 30 and 40 mm with the
source-described two-finger pocket integrated into the same physical cavity;
one isolated 25 mm centre edge; mirrored continuous bottom contacts spanning 15
and 20 mm; and two isolated mono pockets. The composite stepped contacts omit a
single `sizeMillimeters` because more than one manufacturer-labelled depth is
part of the same physical region. The centre edge retains 25 mm and the isolated
monos retain source-backed one-finger capacity. The official front JPEG is
converted to PNG only for package compatibility, without cropping or geometry
changes. The center edge uses a manually selected rounded-rectangle constraint,
and the circular monos use circle constraints. The paired 8/10/12 and 15/20
cavity outlines retain their reviewed bespoke freeform curvature rather than
forcing the Workbench's fixed preset radii. The jug and integrated 30/40/pocket
contacts also remain freeform. Each retained constraint was materialized from
the current Workbench primitive and passes an exact zero-delta constrained
resize.

## Required follow-up

For each unfinished model, confirm the physical inventory from the product copy
and official views, document any ambiguity, omit unsupported optional facts,
and directly author and visually review the complete flat package.
