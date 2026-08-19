# DeWoodstok and Escape board-package source audit

Checked 2026-08-12. This is a historical evidence audit, not current runtime
package or review state. Its source links remain useful, but current packages
are directly authored under `docs/ADDING_A_BOARD.md`. The former incomplete
draft assets were removed and are not future authoring inputs.

## Candidates and primary manufacturer sources

| slug | catalog id | official product URL | official front image URL | official oblique image URL | official hold guide or measurement URL |
| --- | --- | --- | --- | --- | --- |
| `dewoodstok-woodbord` | `dewoodstok.woodbord` | No public manufacturer product page located | No public manufacturer front image located | No public manufacturer oblique image located | No public manufacturer guide or measurement source located |
| `escape-beta` | `escape.beta` | https://escapeclimbing.com/products/ec72100 | https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_01-02.jpg?v=1700454580&width=1946 | https://escapeclimbing.com/cdn/shop/products/2020_Website_ProductImage_BetaBoardListing_02-02.jpg?v=1700454580&width=1946 | No official per-hold guide or measurement source located |
| `escape-unlimited` | `escape.unlimited` | https://escapeclimbing.com/products/ec72000 | https://escapeclimbing.com/cdn/shop/files/PDP_EC72000_UnlimitedBoard-01.png?v=1690380978&width=1946 | https://escapeclimbing.com/cdn/shop/products/2022_Website_ProductImage_UnlimtedBoardListing_Final-B.png?v=1690380978&width=1946 | No official per-hold guide or measurement source located |

The two Escape pages are manufacturer pages. The Beta page publishes only
overall dimensions (6 x 26 x 2 inches) and a dual-texture description. The
Unlimited page publishes overall height and width (6 and 23.5 inches) plus a
general ordered description of pad depths (2, 1.5, 1, and 0.5 pads). Neither
associates a complete, physical hold inventory with boundaries, millimetre
sizes or depths, finger capacities, or grip classifications.

No current official DeWoodstok product, image, manual, or hold guide was
located. Several retailer pages repeat a Woodbord product description and
dimensions, but they are not manufacturer evidence and are intentionally not
used for package facts. In particular, the repeated list of 4-finger and
2-finger pocket depths cannot establish which visible physical pocket has each
depth, nor supply official frame or semantics mappings.

## Evidence-key readiness matrix

No candidate reaches the package schema's evidence gate, so no exact evidence
keys are authored. Were a package ready, the following rows would each require
an exact key in its `evidence.json`.

| candidate | required evidence-key rows | authoritative coverage found | result |
| --- | --- | --- | --- |
| `dewoodstok.woodbord` | board facts; every `holds[].{id,name,shortLabel,detail,kind,frame,sizeMillimeters,depthRangeMillimeters,gripType,fingerCapacity,cueStyle,features}`; every semantic ID; `assets/primary.png` | No manufacturer source for product facts, hold inventory/frames, per-hold measurements, or semantics | blocked |
| `escape.beta` | board facts; every `holds[]` field above; every semantic ID; `assets/primary.png` | Product identity, overall dimensions, dual texture, and official gallery images only | blocked |
| `escape.unlimited` | board facts; every `holds[]` field above; every semantic ID; `assets/primary.png` | Product identity, overall dimensions, generic rung-depth ordering in finger pads, and official gallery images only | blocked |

## Exact blockers

### `dewoodstok-woodbord`

Missing official manufacturer evidence for the product URL, front and oblique
reference images, the physical hold inventory and boundaries, every per-hold
depth and size, finger capacity, grip type, semantic targets, and normalized
frames. The current Woodbord package was later authored directly and reviewed
under the newer flat-package contract.

### `escape-beta`

Missing official manufacturer evidence for the individual physical hold
inventory and boundaries, per-hold depth and size, finger capacity, grip type,
semantic targets, and the association of the gallery image areas to those
facts. Overall dimensions and an image cannot fill those gaps. The duplicate
historical candidate was removed; Escape Beta 22 is the active package.

### `escape-unlimited`

Missing official manufacturer evidence mapping each physical rung/hold to a
measured depth, its boundaries, size, finger capacity, grip type, semantic
targets, and normalized frames. The product copy's finger-pad sequence is not a
millimetre measurement or a per-hold map, and it explicitly leaves mono/crimp
placement to the climber. The old incomplete candidate was removed; a future
complete package must use directly authored and visually reviewed paths.
