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
to `7.5 mm`, which is recorded exactly in `sizeMillimeters`. It assigns an
aggregate `19–31 mm` range to the IMR area rather than separately mapping the visible deep and
shallow lobes; those two holds therefore omit measurements. `MR` and `IM` names
are retained only where Trango's chart explicitly labels them. The chart and
depth-guide abbreviation key establish two-finger MR/IM use, so all eight
stable MR/IM pocket IDs use `fingerCapacity: 2`, `twoFingerPocket`, and the
literal `pocket` feature. The four angle-labelled surfaces use the exact
`sloper` posture, and the two large flat edges use the literal `largeEdge` and
`flatEdge` features. The manufacturer term “closed crimp” is recorded as the
explicit app-schema adaptation `fullCrimp`; no other posture or feature is
filled from appearance.

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
remain omitted. The guide's position diagrams nevertheless establish maximum
finger capacity independently of those depth conflicts: four on each jug,
rail, and closed crimp; three on each upper and supported pocket; and two on
each center-lower pocket. The pocket postures and `pocket` features are mapped
to those exact stable IDs. “Closed crimp” is explicitly adapted to the app
schema's `fullCrimp`; the source terminology remains recorded here. The
guide's wide and medium pinches are ways to combine already-modeled contact
surfaces, not additional physical openings, so they are not duplicated as
holds.

The official square JPEG was converted to PNG without cropping, registration,
or geometric alteration. The right half is an exact mirror of the authored
left half. Only the genuinely regular upper and center-lower pocket openings
use operator-selected oval constraints; variable rails, the crimp, jug, and
compound supported pocket remain freeform.

### `trango-rock-prodigy-pivot`

The completed package remains the structural and path-style precedent; its
product-specific coordinates must not be reused. The 2026-08-25 stable-ID
review reconciled 18 physical contacts / 22 geometry pieces. Trango's “22
distinct grip positions” is an orientation-dependent usage count, not a claim
of 22 separately bounded physical contacts, so it does not require geometry or
ID changes.

The depth guide maps the stable pairs exactly: `upper-sloped-crimp-*` to
`12.5 mm`, `outer-sloped-crimp-*` to `11.5 mm`, `variable-edge-*` to
`16–31 mm`, `medium-crimp-*` to `9–10 mm`, `large-crimp-*` to `11–12 mm`,
`two-finger-pocket-*` to `28–32 mm`, and `three-finger-pocket-*` to
`17–28 mm`. The orientation guide explicitly draws four fingers on every
non-pocket contact represented in this presentation and two or three on the
corresponding pocket openings. Those capacities are retained; the two pocket
postures/features and lower-sloper posture are retained where the guide has an
exact schema representation. Supported/sloped crimp labels do not distinguish
the app's half- versus full-crimp postures, so those posture fields stay blank.
The pinch changes role across orientations, so no width feature is selected.

## 2026-08-25 per-contact metadata ledger

The stable-ID captures were generated at
`.context/hangboard-metadata-backfill-icky-cow/trango/` with one label per
logical hold. All 52 Forge, Natural, and Pivot contacts were visually matched
to the first-party diagrams before the canonical ledger was written.

| board | exact verified mapping | retained blanks |
| --- | --- | --- |
| Forge | 20 kinds; rail/crimp/MR measurements; eight MR/IM two-finger capacities and pocket postures; four sloper postures; literal large-flat-edge and pocket features | IM lobe depths remain blank because `19–31 mm` is published only for the aggregate IMR area; no hand capacities; no unsupported crimper/rail postures |
| Natural | 14 kinds; jug/rail/upper-pocket measurements; 14 diagrammed finger capacities; six pocket postures/features; jug feature; closed-crimp schema adaptation | closed-crimp, center-lower-pocket, and supported-pocket measurements remain blank because the current official sources conflict; all hand capacities and unsupported rail/jug postures remain blank |
| Pivot | 18 kinds; all seven depth-guide measurement groups; all 18 diagrammed finger capacities; four pocket postures/features; two sloper postures | all hand capacities; generic supported/sloped crimp postures; orientation-dependent pinch features; measurements not published by the depth guide |

Every omitted field has a hold-level reason and primary source in
`2026-08-25-hangboard-metadata-ledger.json`. No geometry, hold identity, or
presentation raster changed in this metadata pass.

Trango says Forge differs from Training Center, so no Training Center source or
geometry was substituted into Forge. Forge and Natural were authored from
their own current manufacturer evidence and remain gated on current package and
visual validation.

All 12 constrained Forge and Natural pieces pass the production `+1 px` resize
invariants. A zero-distance save can reserialize decimal precision, so these
pieces are verified for mathematical oval consistency and no visible snap
rather than claimed as byte-exact.

## 2026-08-26 Pivot configuration-variation audit

Reviewed 2026-08-26 against Trango's [Pivot product
page](https://trango.com/products/rock-prodigy-pivot), [Quick Start
Guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507),
and [Depth
Guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Depth_Guide.pdf?v=1634672905).
The product page says the Pivot has four usage orientations and 22 distinct
grip positions. The Quick Start's orientation material is explicitly a guide
to *key* holds, not a comprehensive list of all possible holds. These five
packages therefore model only the named key grip positions below. They do not
claim a complete physical-contact inventory, add alternate grips, derive
measurements, or carry optional capacity, posture, feature, or coaching
metadata.

Neither the Pivot product page nor either cited Pivot guide provides board
dimensions. The orientation packages consequently omit `dimensions`; the
previous dimension string was unsupported and is not retained as a package
fact.

Each package is a direct child under `Hangboards/` with the same unmodified
official Pivot front presentation used by the completed base package. The
image is the presentation of the same physical product, not evidence for an
unlisted contact. During review, every configuration path was deliberately
matched to the named contact in the Quick Start orientation plate and the
corresponding canonical physical-contact boundary in the already-reviewed base
presentation. When Trango's plate depicts a named grip on both mirrored
halves, each component is a separate logical hold because it is a separate
physical contact. Every
documented key grip therefore has one `-left` record mapped to the reviewed
left contact and one `-right` record mapped to the reviewed right contact.
Orientation 1's Jug and Horizontal Pinch usages remain combined once per side
because the Quick Start applies both usage names to the same wedge contact;
there is no overlapping duplicate jug/pinch record.

| package / mounting state | documented key grip | schema kind | reviewed canonical physical-contact mapping |
| --- | --- | --- | --- |
| `trango-rock-prodigy-pivot-orientation-1` / Orientation 1 | Jug / Horizontal Pinch | `jug` | `jug-horizontal-pinch-left` → `outer-wedge-pinch-left`; `jug-horizontal-pinch-right` → `outer-wedge-pinch-right`. The Quick Start separately names Jug and Horizontal Pinch usage on this reviewed wedge contact. The combined per-side name preserves both source names without overlapping records. `jug` is the conservative allowed schema kind selected for the record; this source-to-schema adaptation does not claim a separate pinch contact. |
| same | Variable Depth Sloper Rail | `sloper` | `variable-depth-sloper-rail-left/right` → `variable-edge-left/right`, side for side |
| same | Medium Supported Crimp | `edge` | `medium-supported-crimp-left/right` → `medium-crimp-left/right`, side for side |
| same | Large Sloped Crimp | `edge` | `large-sloped-crimp-left/right` → `upper-sloped-crimp-left/right`, side for side |
| `trango-rock-prodigy-pivot-orientation-2-90-outwards` / Orientation 2, 90° Outwards | Shallow Mono | `pocket` | `shallow-mono-left/right` → `variable-edge-left/right`, side for side; the guide identifies a one-finger use at the rail's reviewed contact, so each complete continuous rail boundary is retained instead of inventing a raster-derived sub-contour. |
| same | Steep Gaston | `edge` | `steep-gaston-left/right` → `outer-wedge-pinch-left/right`, side for side |
| same | Small Sloped Crimp | `edge` | `small-sloped-crimp-left/right` → `outer-sloped-crimp-left/right`, side for side |
| `trango-rock-prodigy-pivot-orientation-3-90-inwards` / Orientation 3, 90° Inwards | 2 Finger Pocket | `pocket` | `two-finger-pocket-left/right` → base `two-finger-pocket-left/right`, side for side |
| same | 3 Finger Pocket | `pocket` | `three-finger-pocket-left/right` → base `three-finger-pocket-left/right`, side for side |
| same | Large Supported Crimp | `edge` | `large-supported-crimp-left/right` → `medium-crimp-left/right`, side for side |
| same | Sloper | `sloper` | `sloper-left/right` → `lower-sloper-left/right`, side for side |
| `trango-rock-prodigy-pivot-orientation-3-switch-left-to-right` / Orientation 3 Switch, L-to-R | Variable Depth Incut Rail | `edge` | `variable-depth-incut-rail-left/right` → `variable-edge-left/right`, side for side |
| same | Shallow Gaston | `edge` | `shallow-gaston-left/right` → `outer-wedge-pinch-left/right`, side for side |
| `trango-rock-prodigy-pivot-orientation-4-90-outwards` / Orientation 4, 90° Outwards | Compression Pinch | `pinch` | `compression-pinch-left/right` → `outer-wedge-pinch-left/right`, side for side |
| same | Deep Mono | `pocket` | `deep-mono-left/right` → `variable-edge-left/right`, side for side; each complete reviewed rail contact is kept for the documented mono use. |
| same | Medium Mono | `pocket` | `medium-mono-left/right` → `three-finger-pocket-left/right`, side for side |

“Orientation 3 Switch” is counted separately from Orientation 3 for package
selection because the Quick Start directs an L-to-R board switch and names a
different key-grip set. It is not a fifth physical rotation: the product page's
four-orientation statement remains the product identity claim. Conversely,
the 22-position statement does not justify filling the orientation packages
with undocumented entries because the manufacturer guide says the shown key
holds are non-comprehensive.
