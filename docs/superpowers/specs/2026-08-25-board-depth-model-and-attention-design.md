# Board depth model and editor attention

## Goal

Make the Workbench identify packages whose depth-bearing holds still need
attention, let an operator edit both supported depth forms, and represent
manufacturer-defined discrete steps as individual fixed-depth holds.

## Data model

`sizeMillimeters` remains the scalar measurement for one fixed-depth hold.
`depthRangeMillimeters` remains the lower/upper bound only for a genuinely
continuous variable-depth contact. A hold may have neither measurement, but it
must never have both. Depth is required for editor-attention purposes only for
`edge` and `pocket` holds. `jug`, `sloper`, and `pinch` are never attention
items solely because they lack a depth.

## Editor behavior

The Hold Inspector exposes a `Depth measurement` select with `Unset`, `Fixed`,
and `Variable` choices. Fixed reveals a single positive finite `Depth (mm)`
input. Variable reveals the existing lower and upper positive finite inputs.
Changing mode clears the other representation on every selected piece of the
logical hold; switching to Unset clears both. Existing saved scalar and range
metadata selects the corresponding mode when a hold is opened.

## Board-list behavior

The board-list API includes a required `needsAttention` boolean. It is true
when a package contains an `edge` or `pocket` without either a scalar depth or
a continuous range. The typed browser client validates that field and the
library renders an accessible `Needs attention` status only when it is true.

## Catalog migration

Manufacturer-labelled discrete step depths become separate logical holds with
one scalar `sizeMillimeters` each and separately authored canonical geometry.
Continuous variable rails remain one logical hold with a range. No geometry is
generated, inferred, copied between products, or split mechanically: the
operator traces and reviews every resulting physical contact in Workbench,
mirroring only where the product evidence establishes symmetry.

The current Tension Grindstone, Honestone, and Whetstone mappings and the
Frictitious Megalith mappings must be re-evaluated against their official
product pages and direct package images. The current source audit calls the
Tension stepped surfaces continuous; the user-approved policy changes their
logical inventory only after distinct contact boundaries have been directly
authored and reviewed. The Rock Prodigy Forge and Pivot variable rails stay
ranges unless their manufacturer evidence identifies discrete contacts.

## Compatibility and verification

Both the Workbench and iOS package readers/writers enforce the mutually
exclusive fields and preserve fractional values. Tests cover payload validation,
attention classification, inspector mode transitions, save/load round trips,
and rejection of conflicting measurements. Package validation, the Workbench
test suite, and simulator review validate the final catalog changes.
