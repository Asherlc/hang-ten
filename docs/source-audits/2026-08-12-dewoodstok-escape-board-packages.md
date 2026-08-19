# DeWoodstok and Escape board-package source audit

Checked 2026-08-12. This is a historical evidence audit, not current runtime
package or review state. Its source links remain useful, but current packages
are directly authored under `docs/ADDING_A_BOARD.md`. The former incomplete
draft assets were removed and are not future authoring inputs.

## Candidates and primary manufacturer sources

| slug | board id | official product URL | official front image URL | official oblique image URL | official hold guide or measurement URL |
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
depth, nor supply an official per-hold measurement mapping.

## Current authoring interpretation

| model | required package decision | optional facts to omit |
| --- | --- | --- |
| `dewoodstok-woodbord` | The current completed Woodbord package uses the later manufacturer source and reviewed physical inventory. | Do not restore retailer-only measurements or certification language. |
| `escape-beta` | This was a duplicate historical candidate; Escape Beta 22 is the active product package. | Do not create a second package or reuse the removed candidate art. |
| `escape-unlimited` | Freeze the visible rung inventory from the exact product imagery, then author and review its paths directly. | Treat finger-pad wording as descriptive; omit unsupported millimetre depths, capacities, and posture. |

Official imagery supports visible boundaries and symmetry for direct authoring.
It does not turn marketing copy into measurements or training prescriptions.
