# Trango Forge, Natural, and Pivot board-package source audit

Checked 2026-08-12. This document records the manufacturer material reviewed
for the three generated-image candidates below. It is documentation, not
runtime content or package state. Each candidate remains unregistered with
only its existing `assets/primary.png`; that generated presentation image was
not used to supply unsupported hold facts.

## Candidates and official manufacturer sources

| slug | catalog ID | product page | official front image | hold documentation |
| --- | --- | --- | --- | --- |
| `trango-rock-prodigy-forge` | `trango.rock-prodigy-forge` | [Forge product page](https://trango.com/products/rock-prodigy-forge) | [Forge main image](https://trango.com/cdn/shop/products/22820_Rock_Prodigy_Forge_Main_Image.jpg?v=1582662057&width=1946) | [Forge manual](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/2018_update_forge_instructions_booklet.pdf?v=1588609204), [Forge depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Forge_Depth_Guide.pdf?v=1634672887), [Forge grip-identification chart](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/forge-grip-identification-chart.pdf?v=1588609203) |
| `trango-rock-prodigy-natural` | `trango.rock-prodigy-natural` | [Natural product page](https://trango.com/products/rock-prodigy-natural) | [Natural main image](https://trango.com/cdn/shop/products/22850_RockProdigyNatural_MainImage_TopDownMarkings.jpg?v=1755037315&width=1946) | [Natural quick-start guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Natural_Consumer_Quick_Start_Final_Digital_9.21.21.pdf?v=1656514361) |
| `trango-rock-prodigy-pivot` | `trango.rock-prodigy-pivot` | [Pivot product page](https://trango.com/products/rock-prodigy-pivot) | [Pivot main image](https://trango.com/cdn/shop/products/22840_RockProdigyPivot_MainImage_TopDown.jpg?v=1755037446&width=1946) | [Pivot quick-start guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507), [Pivot depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Depth_Guide.pdf?v=1634672905) |

The pages and linked documents are first-party Trango material. The existing
Rock Prodigy Training Center package and its sources were intentionally not
used as evidence for a Forge, Natural, or Pivot hold: Trango says Forge has
different hold dimensions from the Training Center, and shared brand naming is
not evidence of a cross-model hold map.

## What the sources establish

| candidate | supported facts | source limitation relevant to a package |
| --- | --- | --- |
| Forge | Identity, two-piece dimensions, a closed crimp with thumb support, drafted pockets, pinches, slopers, and the depth-guide values for selected MR, IMR, rail, crimp, and pinch grips. | The depth guide and grip chart label selected grip positions, not a complete one-to-one inventory of every physical contact region and its boundaries. The manual describes usage but does not complete that inventory. |
| Natural | Identity, material, each-board dimensions, variable rails, pockets, closed crimp, pinches, and the quick-start guide's named key grips and depth ranges. | The quick-start guide expressly says its grip guide is *not a comprehensive list of all holds*. Its key-grip illustrations cannot establish every physical boundary or all package hold records. |
| Pivot | Identity, four orientations, 22 distinct grip positions, and named key grips including pockets, rails, pinches, gastons, slopers, crimps, and monos. | The quick-start guide expressly says its orientation guide is *not a comprehensive list of all possible holds*. The product page provides no board dimensions, while the depth guide does not turn the non-exhaustive selection into a complete physical inventory. |

## Evidence-key readiness matrix

A registered board must have evidence for every `board.json` fact, every
physical `holds[]` field, each semantic target, every artwork element and hold
piece, and `assets/primary.png`. The table below identifies why none of these
candidates can honestly populate those maps.

| candidate | source-backed portions | missing required package evidence | result |
| --- | --- | --- | --- |
| `trango.rock-prodigy-forge` | Product identity/dimensions; selected named grips and several measurements; official front image | Complete individual physical-hold inventory and boundaries; source-backed `gripType`, `fingerCapacity`, `cueStyle`, and `features` for every contact region; exhaustive semantic and artwork mappings | Do not add sidecars or a catalog entry. |
| `trango.rock-prodigy-natural` | Product identity/material/dimensions; named key grips, capacities, and depth ranges; official front image | Complete inventory and individual boundaries, because the manufacturer calls the guide non-comprehensive; all required app-specific field mappings and exhaustive semantic/artwork mappings | Do not add sidecars or a catalog entry. |
| `trango.rock-prodigy-pivot` | Product identity; officially named key grips across orientations; official front image | Published board dimensions; complete inventory/boundaries across all 22 positions; source-backed field mappings and exhaustive semantic/artwork mappings | Do not add sidecars or a catalog entry. |

## Exact blockers

### `trango-rock-prodigy-forge`

The official depth guide documents selected measurement labels but does not
publish the complete, individual physical-hold inventory needed to distinguish
all board contact regions. The product page's claim that Forge dimensions
differ from the Training Center expressly prevents filling that gap from the
Training Center package. No source establishes every required hold boundary,
capacity, grip classification, UI cue, feature, semantic target, or artwork
piece. The candidate must remain primary-only and unregistered.

### `trango-rock-prodigy-natural`

The Natural quick-start guide provides valuable named-grip measurements, but
states that the grip guide is not comprehensive. It therefore cannot prove the
complete physical inventory/boundaries required by the package schema. Neither
the product page nor the image supplies the omitted records or the evidence for
every required per-hold field. The candidate must remain primary-only and
unregistered.

### `trango-rock-prodigy-pivot`

Trango documents orientations and selected key grips but explicitly does not
claim a comprehensive list of possible holds. It publishes neither an
exhaustive physical boundary map nor overall board dimensions. The source set
cannot support all per-hold records, semantic targets, and artwork mappings
without inference. The candidate must remain primary-only and unregistered.

## Required follow-up

Obtain a manufacturer-issued exhaustive, model-specific hold diagram or data
sheet for each board. It must map every physical contact region and its
boundary to measured depth/size, finger capacity, grip classification, and
the documented targets intended for training. Then author all four canonical
sidecars and register that model in one change. Do not treat Training Center
evidence as a substitute.
