# DeWoodstok and Escape board-package source audit

Checked 2026-08-12. This is an evidence audit, not a runtime package or
review-state record. The existing `assets/primary.png` files are generated
presentation images; they were not used to establish hold facts.

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
depth, nor supply an official artwork/semantics mapping.

## Evidence-key readiness matrix

No candidate reaches the package schema's evidence gate, so no exact evidence
keys are authored. Were a package ready, the following rows would each require
an exact key in its `evidence.json`.

| candidate | required evidence-key rows | authoritative coverage found | result |
| --- | --- | --- | --- |
| `dewoodstok.woodbord` | board facts; every `holds[].{id,name,shortLabel,detail,kind,frame,sizeMillimeters,depthRangeMillimeters,gripType,fingerCapacity,cueStyle,features}`; every semantic ID; every artwork element and hold piece; `assets/primary.png` | No manufacturer source for product facts, hold inventory/boundaries, per-hold measurements, semantics, or artwork | blocked |
| `escape.beta` | board facts; every `holds[]` field above; every semantic ID; every artwork element and hold piece; `assets/primary.png` | Product identity, overall dimensions, dual texture, and official gallery images only | blocked |
| `escape.unlimited` | board facts; every `holds[]` field above; every semantic ID; every artwork element and hold piece; `assets/primary.png` | Product identity, overall dimensions, generic rung-depth ordering in finger pads, and official gallery images only | blocked |

## Retained assets

| candidate | retained path | SHA-256 | source role | package evidence key |
| --- | --- | --- | --- | --- |
| `dewoodstok.woodbord` | `assets/primary.png` | `5e21480090569510c2f51dfba9311b6e5c144a9565c5c821d6ade2a9a94ef1fc` | generated presentation candidate, not factual evidence | not authored: candidate is unregistered |
| `escape.beta` | `assets/primary.png` | `fca647122a0fc2474843fb9b39a24e6a7000ded35e9f009e0265afb2ec927506` | generated presentation candidate, not factual evidence | not authored: candidate is unregistered |
| `escape.unlimited` | `assets/primary.png` | `162cd0bfc010ad33ed68790663a58ede59124aab046de1153f973539fac01466` | generated presentation candidate, not factual evidence | not authored: candidate is unregistered |

## Exact blockers

### `dewoodstok-woodbord`

Missing official manufacturer evidence for the product URL, front and oblique
reference images, the physical hold inventory and boundaries, every per-hold
depth and size, finger capacity, grip type, semantic targets, and artwork
elements. The candidate remains primary-only and unregistered; no sidecars or
catalog entry are permitted.

### `escape-beta`

Missing official manufacturer evidence for the individual physical hold
inventory and boundaries, per-hold depth and size, finger capacity, grip type,
semantic targets, and the association of the gallery image areas to those
facts. Overall dimensions and an image cannot fill those gaps. The candidate
remains primary-only and unregistered.

### `escape-unlimited`

Missing official manufacturer evidence mapping each physical rung/hold to a
measured depth, its boundaries, size, finger capacity, grip type, semantic
targets, and artwork elements. The product copy's finger-pad sequence is not a
millimetre measurement or a per-hold map, and it explicitly leaves mono/crimp
placement to the climber. The candidate remains primary-only and unregistered.
