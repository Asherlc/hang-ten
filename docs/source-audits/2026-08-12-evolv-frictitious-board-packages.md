# Evolv and Frictitious package-source audit

Checked 2026-08-12. This audit evaluates the unregistered image candidates
against the source-backed package contract in `docs/ADDING_A_BOARD.md`. A
product page and a manufacturer-hosted image establish product identity and
visible artwork only. They do not establish a physical hold's capacity, grip
classification, or a distinct physical boundary unless the manufacturer
explicitly documents it.

None of these candidates is registered. Each remains exactly
`assets/primary.png`, with no JSON sidecars, review-state files, or alternate
generated images.

## Evolv Kilter Basic Long (`evolv.kilter-basic-long`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, manufacturer, material, dimensions, and listed hold depths | [Evolv Basic Training Board (Long)](https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105) | Evolv identifies the Kilter collaboration; lists 79 cm × 16 cm × 6 cm and a rounded jug plus 20, 15, and 10 mm rounded edges. |
| Straight-on visible layout | [Evolv manufacturer-hosted still image](https://oberalp.imgix.net/ef857c73-13f1-4205-ac47-706cd101e1bb.jpg?auto=format&cs=srgb&fit=clip&type=still&w=628) | Visible silhouette and layout only. |
| Oblique visible surfaces | [Evolv manufacturer-hosted technical image](https://oberalp.imgix.net/f8a564c9-b501-445f-bd43-af630730abfd.jpg?auto=format&cs=srgb&fit=clip&type=tech_detail&w=628) and [second technical image](https://oberalp.imgix.net/e3b05632-02ce-467f-9226-d2a2862c482a.jpg?auto=format&cs=srgb&fit=clip&type=tech_detail&w=628) | Visible surface shape only. |

**Blocker:** Evolv's page enumerates hold *types* but does not publish an
official numbered hold guide, per-hold count/boundaries, finger capacities, or
grip classifications. The images cannot supply those non-visible facts. It
therefore cannot support `board.json` hold records, hold evidence, or semantic
targets without inference.

## Frictitious DoorMount Pro 7 (`frictitious.doormount-pro-7`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, board dimensions, material, and overall load rating | [Frictitious DoorMount Pro product page](https://frictitiousclimbing.com/en-ca/products/doormount-pro) | Lists Pro 7 dimensions (25.5 in × 4.5 in × 2.25 in), poplar wood hangboard, and system rating. |
| Manufacturer front image | [DoorMount Pro 7 front image](https://frictitiousclimbing.com/cdn/shop/files/DMP-7-Front_d597f381-f23b-4d16-a5b2-d9d201171fa5.jpg?v=1784063035&width=640) | Visible silhouette and layout only. |
| Manufacturer pocket image | [DoorMount Pro pocket image](https://frictitiousclimbing.com/cdn/shop/files/DMP-Pockets.jpg?v=1779384260&width=640) | Visible pocket surface only. |
| Manufacturer installation imagery | [DoorMount Pro Quick Start Guide](https://frictitiousclimbing.com/en-ca/pages/doormount-pro-quick-start-guide) | Mount and orientation instructions, not a hold map. |

The product page says Pro 7 has seven holds and names a pull-up jug, pockets,
and 35, 25, 20, 15, and 10 mm edges.

**Blocker:** Frictitious does not identify the physical boundary/count of the
pocket hold(s), their finger capacities, or a grip classification for the
edges and pockets. Its images cannot convert the generic word “pockets” into
capacity or physical-hold metadata. The published seven-hold total is
insufficient to map all seven individual records and their factual fields.

## Frictitious Megalith (`frictitious.megalith`)

| Required evidence | Official source | Coverage |
| --- | --- | --- |
| Product identity, dimensions, material, and published edge sizes | [Frictitious Megalith product page](https://frictitiousclimbing.com/products/megalith) | Lists 26.75 in × 6.5 in × 2.25 in, poplar wood, seven shoulder-width edge sizes (8–40 mm), full-width jug, a 25 mm center hold, a two-finger pocket on the 40 mm edge, and “mono pockets.” |
| Manufacturer front imagery | [Megalith front image](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front.jpg?v=1780436232&width=1280) and [alternate official front image](https://frictitiousclimbing.com/cdn/shop/files/Megalith-Front-1.jpg?v=1780436232&width=3840) | Visible silhouette and layout only. |

**Blocker:** The product page never gives the count, location, or individual
boundaries of the plural mono pockets, nor a complete per-hold classification
and capacity map. It also does not say how the 40 mm edge's two-finger pocket
is bounded relative to the edge as a separate physical hold. The official
images may be normalized into artwork once the factual hold inventory exists,
but cannot establish it. No source-backed `board.json`, `semantics.json`, or
evidence map can be authored without inventing that inventory.

## Required follow-up

Request manufacturer-issued numbered hold diagrams or manuals for all three
models. The material must name every physical hold and establish its boundary,
depth/size, finger capacity, and grip classification. Once available, update
this audit with exact source rows and author the four package sidecars in one
change; do not infer missing fields from the retained `primary.png` files.
