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

**2026-08-25 corrected mapping:** Eighteen source-labelled contacts are
represented: one full-width jug; separate left/right 8, 10, and 12 mm top
shelves; separate left/right 30 and 40 mm middle shelves (each 40 mm shelf
retains its integrated two-finger pocket); one 25 mm centre edge; separate
left/right 15 and 20 mm bottom shelves; and two isolated mono pockets. The
engraved front identifies the individual planar shelves by depth, so their
shared cavity walls do not merge them into one logical hold. Each labelled edge
keeps its exact scalar `sizeMillimeters`; the centre edge retains 25 mm and the
isolated monos retain source-backed one-finger capacity. The official front JPEG
is converted to PNG only for package compatibility, without cropping or
geometry changes. The center edge uses a manually selected rounded-rectangle
constraint, and the circular monos use circle constraints. The jug and the
remaining shelf paths stay freeform. Each retained constraint was materialized
from the current Workbench primitive and passes an exact zero-delta constrained
resize.

## Required follow-up

For each unfinished model, confirm the physical inventory from the product copy
and official views, document any ambiguity, omit unsupported optional facts,
and directly author and visually review the complete flat package.

## 2026-08-25 source-audited metadata

The current manufacturer pages and images below were re-opened on 2026-08-25.
Fresh stable-ID captures were manually reviewed under
`.context/hangboard-metadata-backfill-icky-cow/escape-frictitious-evolv-dewoodstok/`.
The captures are review aids only; no path or geometry changed.

### Frictitious DoorMount Pro 7

The controlling sources are the current
[DoorMount Pro product page](https://frictitiousclimbing.com/products/doormount-pro),
[official engraved Pro 7 front](https://frictitiousclimbing.com/cdn/shop/files/DMP-7-Front_d597f381-f23b-4d16-a5b2-d9d201171fa5.jpg?v=1784063035&width=3840),
and [official pocket-use image](https://frictitiousclimbing.com/cdn/shop/files/DMP-Pockets.jpg?v=1779384260&width=3840).
The reviewed overlay is
`frictitious.doormount-pro-7--1afc3c4fb553.png`.

This current review supersedes the 2026-08-19 seven-contact interpretation
above. The product page's seven-hold wording counts source families: five edge
depths, pockets, and the pull-up jug. The current engraved front resolves those
families to one full-width jug and six mirrored contact pairs, exactly matching
the package's 13 stable records.

| Official position | Stable hold ID(s) | Verified kind | Verified metadata |
| --- | --- | --- | --- |
| Full-width pull-up jug | `top-jug` | `jug` | `features: [jug]` |
| Outer upper surfaces engraved `35` | `edge-35-left`, `edge-35-right` | `edge` | 35 mm |
| Inner upper surfaces engraved `25` | `mixed-25-pocket-left`, `mixed-25-pocket-right` | `edge` | 25 mm |
| Circular pockets below the 25 mm edges | `hold-7`, `hold-6` | `pocket` | `features: [pocket]`; fixed capacity blank |
| Outer lower surfaces engraved `20` | `hold-12`, `hold-13` | `edge` | 20 mm |
| Middle lower surfaces engraved `15` | `hold-11`, `hold-8` | `edge` | 15 mm |
| Inner lower surfaces engraved `10` | `hold-10`, `hold-9` | `edge` | 10 mm |

The package gained the exact 25/20/15/10 mm scalar mappings and exact jug and
pocket feature tags. The old `fingerCapacity: 2` values on `hold-6` and
`hold-7` were removed: the use image shows a two-finger use, not a fixed
maximum capacity. Display names and the subtitle were corrected to reflect the
source positions; stable IDs and geometry were preserved. The ledger accounts
for all 91 seven-field outcomes: 26 verified, 54 unavailable, and 11 not
applicable.

All depth ranges, simultaneous-hand capacities, and exact grip postures remain
blank because Frictitious publishes none for these exact contacts. Finger
capacity is not applicable to the source-identified jug and edges; the two
pockets retain an unavailable capacity. Edge feature tags remain blank because
the official labels establish no additional exact supported taxonomy.

### Evolv Basic Training Board (Long)

The controlling source is Evolv's current
[Basic Training Board (Long) product page](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105),
supported by its
[official straight-on image](https://oberalp.imgix.net/ef857c73-13f1-4205-ac47-706cd101e1bb.jpg?auto=format&cs=srgb&fit=clip&type=still&w=628).
The reviewed overlay is
`evolv-kilter-basic-long--ac4049aa3a2d.png`.

| Official hold-list label | Stable hold ID | Verified kind | Verified metadata |
| --- | --- | --- | --- |
| `Jug Rounded` | `jug-rounded` | `jug` | `features: [jug]` |
| `20 mm rounded edge` | `edge-20` | `edge` | 20 mm |
| `15 mm rounded edge` | `edge-15` | `edge` | 15 mm |
| `10 mm rounded edge` | `edge-10` | `edge` | 10 mm |

The three scalar depths were already present. This pass added only the exact
jug feature tag. All four `kind` values are directly verified by Evolv's hold
list. The ledger accounts for all 28 seven-field outcomes: 8 verified, 16
unavailable, and 4 not applicable.

Depth ranges, simultaneous-hand capacities, and exact grip postures remain
blank. Finger capacity is not applicable to the source-identified jug and
edges. `rounded edge` has no exact `roundedEdge` schema tag, so the three edge
feature lists remain blank rather than receiving inferred qualitative tags.

### Frictitious Megalith inventory reconciliation

The controlling sources are the current
[Megalith product page](https://frictitiousclimbing.com/products/megalith) and
[official engraved front](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front.jpg?v=1780436232&width=3840).
The product page specifies seven shoulder-width edge depths, the integrated
two-finger pocket on the 40 mm edge, mono pockets, a 25 mm single-hand centre
hold, and the full-width jug. The engraved front establishes separate planar
8/10/12, 30/40, and 15/20 shelves on each side. They receive one scalar-depth
record per labelled shelf, not a combined range record.

The unnamed overlapping `hold-11` through `hold-14` paths remain removed: they
were nested overlays rather than labelled shelves. The correction replaces the
six range records with fourteen source-labelled scalar edge records, taking the
package from ten to eighteen logical holds without restoring those duplicates.

A fresh stable-ID capture was manually reviewed at
`.context/hangboard-metadata-backfill-icky-cow/frictitious-megalith-reconciliation/frictitious.megalith--3f1c176e6ccc.png`.
It reports eighteen regions: separate IDs align with every engraved 8/10/12,
30/40, and 15/20 shelf, while no unnamed nested overlay remains.
