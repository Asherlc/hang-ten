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

The package remains one catalog product, `trango.rock-prodigy-pivot`; the four
manufacturer-numbered configurations are selectable presentations of that one
physical product, not four board records. The product page says the Quad Cleat
mounting system supports four directions. The official quick-start guide then
labels `ORIENTATION 1` through `ORIENTATION 4` and gives the physical transition
between them. Its separate `ORIENTATION 3 SWITCH` instruction is the required
left/right-half swap on the way to Orientation 4, not a fifth numbered
orientation.

| package presentation | exact manufacturer mapping | guide key-grip examples (non-exhaustive) |
| --- | --- | --- |
| `orientation-1` / `assets/primary.png` | Quick-start pp. 6–7; starting horizontal position. This is the formerly generic `primary` presentation, now explicitly named `Orientation 1`. | Jug, variable-depth sloper rail, horizontal pinch, medium supported crimp, large sloped crimp. |
| `orientation-2` / `assets/orientation-2.png` | Quick-start pp. 8–9; from Orientation 1, pivot both boards 90° outwards. | Small sloped crimp, steep gaston, shallow mono. |
| `orientation-3` / `assets/orientation-3.png` | Quick-start pp. 10–11; from Orientation 2, pivot both boards 90° inwards to the illustrated inverted horizontal position. | Two-finger pocket, three-finger pocket, large supported crimp, sloper. |
| `orientation-4` / `assets/orientation-4.png` | Quick-start pp. 12–15; switch the two physical boards left-to-right, then pivot both boards 90° outwards. | Compression pinch, deep mono, medium mono. |

The presentation evidence is the first-party [Pivot quick-start
guide](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/Rock_Prodigy_Pivot_Consumer_Quick_Start_FINAL_11.20.20.pdf?v=1612292507).
The four-direction product claim and source raster are the first-party [Pivot
product page](https://trango.com/products/rock-prodigy-pivot) and [Pivot main
image](https://trango.com/cdn/shop/products/22840_RockProdigyPivot_MainImage_TopDown.jpg?v=1755037446&width=1946).

The 2026-08-25 stable-ID review reconciled 18 physical contacts / 22 geometry
pieces in Orientation 1. Trango's “22 distinct grip positions” is an
orientation-dependent usage count, not a claim of 22 separately bounded
physical contacts. The guide also says its key-hold list is not comprehensive.
Accordingly, the package does not invent orientation-specific grip contacts:
each presentation contains exactly one transformed mapping of the same complete
18-contact inventory and no duplicate contact within that presentation.

| contact map | Orientation 1 IDs | Orientations 2–4 IDs |
| --- | --- | --- |
| edges | `upper-sloped-crimp-{left,right}`, `outer-sloped-crimp-{left,right}`, `variable-edge-{left,right}`, `medium-crimp-{left,right}`, `large-crimp-{left,right}` | The same base ID plus `-orientation-2`, `-orientation-3`, or `-orientation-4`. |
| pockets | `two-finger-pocket-{left,right}`, `three-finger-pocket-{left,right}` | The same base ID plus the presentation suffix. |
| pinches | `outer-wedge-pinch-{left,right}` | The same base ID plus the presentation suffix. |
| slopers | `lower-sloper-{left,right}` | The same base ID plus the presentation suffix. |

Orientation 1 retains the audited stable IDs unchanged. The package schema maps
one hold record to one `presentationID`, so Orientations 2–4 require suffixed
records for their distinct canonical frames. This yields 72 presentation-mapped
records and 88 pieces while still representing only 18 physical contacts per
presentation. Metadata is identical across copies of the same physical contact;
only ID, display name, presentation ID, frame, and path orientation differ.

Asset provenance is deterministic and contains no generated or inferred product
pixels. The existing 1774×887 PNG is two equal 887×887 manufacturer-image
halves and remains byte-for-byte unchanged as Orientation 1. Orientations 2 and
3 split on that exact half boundary, apply only the guide-prescribed cardinal
rotations to each complete half, and rejoin them on the same 1774×887 canvas.
Orientation 4 additionally swaps the complete halves before its prescribed
cardinal rotation, following pp. 12–15. No generative image editing, detection,
segmentation, masking, vectorization, registration, or path inference was used.
The canonical Orientation 2–4 paths apply the corresponding rigid transforms to
the directly reviewed Orientation 1 paths; right-side paths are exact mirrors of
their transformed left-side partners, as the symmetric product evidence allows.
All four rasters and all four path sets were visually reviewed against the
numbered guide diagrams.

The depth guide maps the stable pairs exactly: `upper-sloped-crimp-*` to
`12.5 mm`, `outer-sloped-crimp-*` to `11.5 mm`, `variable-edge-*` to
`16–31 mm`, `medium-crimp-*` to `9–10 mm`, `large-crimp-*` to `11–12 mm`,
`two-finger-pocket-*` to `28–32 mm`, and `three-finger-pocket-*` to
`17–28 mm`. The orientation guide explicitly draws four fingers on every
non-pocket contact represented in this presentation and two or three on the
corresponding pocket openings. Those capacities are retained; the two pocket
postures and lower-sloper posture are retained where the guide has an exact
schema representation. Supported/sloped crimp labels do not distinguish
the app's half- versus full-crimp postures, so those posture fields stay blank.
The source does not establish exact feature-tag arrays, so features stay blank.

## 2026-08-25 per-contact metadata ledger

The stable-ID captures were generated at
`.context/hangboard-metadata-backfill-icky-cow/trango/` with one label per
logical hold. All 52 Forge, Natural, and Pivot contacts were visually matched
to the first-party diagrams before the canonical ledger was written.

| board | exact verified mapping | retained blanks |
| --- | --- | --- |
| Forge | 20 kinds; rail/crimp/MR measurements; eight MR/IM two-finger capacities and pocket postures; four sloper postures; literal large-flat-edge and pocket features | IM lobe depths remain blank because `19–31 mm` is published only for the aggregate IMR area; no hand capacities; no unsupported crimper/rail postures |
| Natural | 14 kinds; jug/rail/upper-pocket measurements; 14 diagrammed finger capacities; six pocket postures/features; jug feature; closed-crimp schema adaptation | closed-crimp, center-lower-pocket, and supported-pocket measurements remain blank because the current official sources conflict; all hand capacities and unsupported rail/jug postures remain blank |
| Pivot | 18 kinds; all seven depth-guide measurement groups; all 18 diagrammed finger capacities; four pocket postures; two sloper postures | all hand capacities and features; generic supported/sloped crimp postures; measurements not published by the depth guide |

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
