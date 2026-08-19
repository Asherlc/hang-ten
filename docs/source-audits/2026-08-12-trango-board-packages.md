# Trango Forge, Natural, and Pivot board-package source audit

Checked 2026-08-12. This historical audit preserves the manufacturer material
reviewed for Forge, Natural, and Pivot. The old incomplete art was removed and
is not an input to future work. Pivot was later completed through direct path
authoring and is the structural/style precedent described in
`docs/ADDING_A_BOARD.md`; it is not a geometry template for other products.

## Candidates and official manufacturer sources

| slug | board ID | product page | official front image | hold documentation |
| --- | --- | --- | --- | --- |
| `trango-rock-prodigy-forge` | `trango.rock-prodigy-forge` | [Forge product page](https://trango.com/products/rock-prodigy-forge) | [Forge main image](https://trango.com/cdn/shop/products/22820_Rock_Prodigy_Forge_Main_Image.jpg?v=1582662057&width=1946) | [Forge manual](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/2018_update_forge_instructions_booklet.pdf?v=1588609204), [Forge depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Forge_Depth_Guide.pdf?v=1634672887), [Forge grip-identification chart](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/forge-grip-identification-chart.pdf?v=1588609203) |
| `trango-rock-prodigy-natural` | `trango.rock-prodigy-natural` | [Natural product page](https://trango.com/products/rock-prodigy-natural) | [Natural main image](https://trango.com/cdn/shop/products/22850_RockProdigyNatural_MainImage_TopDownMarkings.jpg?v=1755037315&width=1946) | [Natural quick-start guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Natural_Consumer_Quick_Start_Final_Digital_9.21.21.pdf?v=1656514361) |
| `trango-rock-prodigy-pivot` | `trango.rock-prodigy-pivot` | [Pivot product page](https://trango.com/products/rock-prodigy-pivot) | [Pivot main image](https://trango.com/cdn/shop/products/22840_RockProdigyPivot_MainImage_TopDown.jpg?v=1755037446&width=1946) | [Pivot quick-start guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507), [Pivot depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Depth_Guide.pdf?v=1634672905) |

The pages and linked documents are first-party Trango material. The Rock
Prodigy Training Center sources were intentionally not used as evidence for a
Forge, Natural, or Pivot hold: Trango says Forge has
different hold dimensions from the Training Center, and shared brand naming is
not evidence of a cross-model hold map.

## What the sources establish

| candidate | supported facts | source limitation relevant to a package |
| --- | --- | --- |
| Forge | Identity, two-piece dimensions, a closed crimp with thumb support, drafted pockets, pinches, slopers, and the depth-guide values for selected MR, IMR, rail, crimp, and pinch grips. | The depth guide and grip chart label selected grip positions, not a complete one-to-one inventory of every physical contact region and its boundaries. The manual describes usage but does not complete that inventory. |
| Natural | Identity, material, each-board dimensions, variable rails, pockets, closed crimp, pinches, and the quick-start guide's named key grips and depth ranges. | The quick-start guide expressly says its grip guide is *not a comprehensive list of all holds*. Its key-grip illustrations cannot establish every physical boundary or all package hold records. |
| Pivot | Identity, four orientations, 22 distinct grip positions, and named key grips including pockets, rails, pinches, gastons, slopers, crimps, and monos. | The quick-start guide expressly says its orientation guide is *not a comprehensive list of all possible holds*. The product page provides no board dimensions, while the depth guide does not turn the non-exhaustive selection into a complete physical inventory. |

## Current authoring interpretation

- Forge: use its depth and grip guides for the measurements they explicitly map;
  freeze the remaining visible contacts from Forge imagery and omit unassigned
  capacity or posture.
- Natural: the guide is expressly non-comprehensive, so use it for named key
  grips and measurements only. Reconcile the rest against the exact Natural
  product views and omit unresolved values.
- Pivot: the completed package is the structural and path-style precedent. Its
  paths were directly authored and visually reviewed; its product-specific
  coordinates must not be reused.

Trango says Forge differs from Training Center, so never substitute sources
across those models. Each unfinished package requires a complete physical
inventory, directly authored paths, current validation, and visual review.
