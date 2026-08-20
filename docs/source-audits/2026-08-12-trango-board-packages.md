# Trango Forge, Natural, and Pivot board-package source audit

Checked 2026-08-12; Forge and Natural re-audited and directly authored
2026-08-19. This audit preserves the manufacturer material reviewed for Forge,
Natural, and Pivot. The old incomplete art was removed and was not used as an
authoring input. Pivot was completed through direct path authoring and is the
structural/style precedent described in
`docs/ADDING_A_BOARD.md`; it is not a geometry template for other products.

## Candidates and official manufacturer sources

| slug | board ID | product page | official front image | hold documentation |
| --- | --- | --- | --- | --- |
| `trango-rock-prodigy-forge` | `trango.rock-prodigy-forge` | [Forge product page](https://trango.com/products/rock-prodigy-forge) | [Forge main image](https://trango.com/cdn/shop/products/22820_Rock_Prodigy_Forge_Main_Image.jpg?v=1582662057&width=1946) | [Forge manual](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/2018_update_forge_instructions_booklet.pdf?v=1588609204), [Forge depth guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Forge_Depth_Guide.pdf?v=1634672887), [Forge grip-identification chart](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/forge-grip-identification-chart.pdf?v=1588609203) |
| `trango-rock-prodigy-natural` | `trango.rock-prodigy-natural` | [Natural product page](https://trango.com/products/rock-prodigy-natural) | [Natural main image](https://trango.com/cdn/shop/products/22850_RockProdigyNatural_MainImage_TopDownMarkings.jpg?v=1755037315&width=1946) | [Natural quick-start guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Natural_Consumer_Quick_Start_Final_Digital_9.21.21.pdf?v=1656514361), [official rail detail](https://trango.com/cdn/shop/products/22850_RockProdigyNatural_AltImage2_Rails.jpg?v=1724692982&width=1946) |
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

## Completed authoring interpretation

### `trango-rock-prodigy-forge`

The official grip-identification chart names ten distinct regions on each
physical half: 30-degree sloper, 40-degree sloper, large flat edge, slopey
crimper, variable-depth rail, closed crimp, MR deep pocket, MR shallow pocket,
IM deep pocket, and IM shallow pocket. The three pinch widths are alternate
grip positions on the same outer sloper block rather than three additional
physical contacts. That yields 20 logical holds and 20 pieces across the
mirrored pair.

The depth guide maps the variable rail to `7–20 mm`, MR deep to `25 mm`, and MR
shallow to `15 mm`; those values are retained. The guide maps the closed crimp
to `7.5 mm`, which the integer-only `sizeMillimeters` field cannot represent, so
the sourced value appears only in its name. It assigns an aggregate `19–31 mm`
range to the IMR area rather than separately mapping the visible deep and
shallow lobes; those two holds therefore omit measurements. `MR` and `IM` names
are retained only where Trango's chart explicitly labels them. No grip posture,
feature tags, or app routing metadata is added.

The official square JPEG was converted to PNG without cropping, registration,
or geometric alteration. Every left-side path was deliberately authored from
the main image and its official diagrams; the right-side frames and path
directions are exact mirrors. Oval constraints were operator-selected only for
the visibly regular MR and IM pocket openings. All sculpted rails and surfaces
remain freeform.

### `trango-rock-prodigy-natural`

The front view establishes six recessed logical contacts per half: top and
bottom variable rails, one closed crimp, one upper pocket, one center lower
pocket, and one outer supported pocket. The supported pocket is a single
physical contact interrupted by the mounting/relief feature, so it has two
geometry pieces. The quick-start guide separately corroborates a top jug on
each half. This yields 14 logical holds and 16 pieces across the mirrored pair.

The product page and marked front view agree on `20–33 mm` and `10–24 mm` for
the two rails and `38 mm` for the upper pocket; those values are retained. The
product page calls the crimp `10 mm`, while the quick-start guide calls it
`7.5 mm`. The quick-start guide distinguishes a `29 mm` two-finger pocket from
a `36–26 mm` supported pocket, while the marked front image labels those
contacts `27 mm` and `30/27 mm`, respectively. Those conflicted measurements
and exact finger-combination labels are omitted. The guide's wide and medium
pinches are ways to combine already-modeled contact surfaces, not additional
physical openings, so they are not duplicated as holds.

The official square JPEG was converted to PNG without cropping, registration,
or geometric alteration. The right half is an exact mirror of the authored
left half. Only the genuinely regular upper and center-lower pocket openings
use operator-selected oval constraints; variable rails, the crimp, jug, and
compound supported pocket remain freeform.

- Pivot: the completed package is the structural and path-style precedent. Its
  paths were directly authored and visually reviewed; its product-specific
  coordinates must not be reused.

Trango says Forge differs from Training Center, so no Training Center source or
geometry was substituted into Forge. Forge and Natural were authored from
their own current manufacturer evidence and remain gated on current package and
visual validation.

All 12 constrained Forge and Natural pieces pass the production `+1 px` resize
invariants. A zero-distance save can reserialize decimal precision, so these
pieces are verified for mathematical oval consistency and no visible snap
rather than claimed as byte-exact.
