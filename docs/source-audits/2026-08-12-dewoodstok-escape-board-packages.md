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
| `escape-unlimited` | `escape.unlimited` | https://escapeclimbing.com/products/ec72000 | https://cdn.shopify.com/s/files/1/0051/0374/7160/files/PDP_EC72000_UnlimitedBoard-01.png?v=1690380978 | https://escapeclimbing.com/cdn/shop/products/2022_Website_ProductImage_UnlimtedBoardListing_Final-B.png?v=1690380978&width=1946 | https://cdn.shopify.com/s/files/1/0051/0374/7160/products/2022_Website_ProductImage_UnlimtedBoardListing_Final-E.png and https://cdn.shopify.com/s/files/1/0051/0374/7160/products/2022_Website_Editorial_EscapeClimbing_UnlimitedBoard_Progression-02.png |

The two Escape pages are manufacturer pages. The Beta page publishes only
overall dimensions (6 x 26 x 2 inches) and a dual-texture description. The
Unlimited page publishes overall height and width (6 and 23.5 inches), Premium
Baltic Birch, and a general ordered description of pad depths. The official
depth and progression graphics label the same four contact tiers as 60, 45,
20, and 15 mm. The straight-on view establishes that the 60 mm sloper is one
continuous full-width contact while each of the other three tiers is divided
into an actual left and right cavity. It therefore supports seven physical
regions, not the earlier six-record interpretation.

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
| `escape-unlimited` | Freeze seven physical regions: one continuous 60 mm top sloper plus mirrored 45, 20, and 15 mm cavities. Author all paths directly and mirror each cavity pair about the board centre. | Omit finger capacity, posture, feature tags, and any overall thickness; the manufacturer does not publish them. |

Official imagery supports visible boundaries and symmetry for direct authoring.
It does not turn marketing copy into measurements or training prescriptions.

## 2026-08-19 direct-authoring mapping: `escape-unlimited`

| Package field | Primary evidence and decision |
| --- | --- |
| Identity and URL | Current Escape product page: `Unlimited Board`, `escape.unlimited`, and `https://escapeclimbing.com/products/ec72000`. |
| Dimensions | Product page publishes 23.5 in wide and 6 in tall. Overall thickness remains omitted. |
| Presentation | The exact official 1500 × 1500 straight-on PNG linked above is stored as `assets/primary.png` without cropping or geometric transformation. |
| Material subtitle | Product page says Premium Baltic Birch. |
| Hold inventory | The straight-on view shows one continuous top sloper plus three physically separated mirrored cavity pairs: seven regions total. |
| Millimetres | The official depth graphic and progression graphic label the tiers 60, 45, 20, and 15 mm. These replace the earlier generic pad-only interpretation. |
| Kinds | The progression graphic explicitly calls the top surface a sloper. The three recessed tiers are conservatively encoded as edges. |
| Geometry | Every canonical path was deliberately drawn against the official straight-on image. The six genuinely regular cavity outlines have full-height rounded ends and use manually selected pill constraints; the sloper remains freeform. Each retained constraint was materialized from the current Workbench primitive and passes an exact zero-delta constrained resize. |

The product-page pad wording and the millimetre graphics describe the same
ordered tiers but are not identical unit conversions. The package records the
graphic's explicit millimetre labels and does not derive new conversions. No
capacity, posture, grip prescription, or training claim is inferred.
