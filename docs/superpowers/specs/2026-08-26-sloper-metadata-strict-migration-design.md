# Strict Sloper Metadata Migration Design

## Goal

Make known sloper subtypes and inclinations explicit, source-backed
board-package data. This lets the app distinguish flat and round slopers
where manufacturers publish the fact, without inferring unknown properties
from names, images, or geometry.

## Scope

The migration covers every existing hold whose `kind` is `sloper` (currently
96 holds across 28 packages), the canonical board-package schema, its Python
validator, the Swift package decoder and writer, and the iOS Hold inspector.

## Canonical schema

When a manufacturer establishes a sloper subtype, the hold declares a
`sloper` object:

```json
{
  "kind": "sloper",
  "sloper": {
    "type": "flat",
    "angleDegrees": 20
  }
}
```

`sloper` is optional for `kind: "sloper"` holds and prohibited on every other
kind. When present, `type` is required and exactly one of `flat` or `round`.

`angleDegrees` is available only for `flat`; it is optional because many
manufacturer sources do not publish a value. When present, it is a finite
number from 0 through 90, inclusive, measured from the board face: 0 degrees
is parallel to the board face and larger angles slope farther away. A `round`
sloper must not include `angleDegrees`. Holds of any other kind must not
include `sloper`.

The package validator, the Swift decoder, and the editor writer all reject
the same invalid combinations. The decoded `BoardHold` retains optional
metadata so callers do not need to reinterpret JSON.

## Evidence and migration

Each migrated hold must be mapped to a primary manufacturer URL. A verified
subtype is stored only when that source publishes the fact; a flat angle is
stored only when that source publishes the exact value. The migration will
record either the verified result or an unavailable-subtype outcome in a
checked-in audit document with the board package, hold IDs, source URL, source
fact, and resulting schema value.

Names, rendered geometry, imagery, and the existing `shapeConstraint` are
not evidence. When primary manufacturer material does not establish a
subtype, the hold omits `sloper`; no value is fabricated. A missing
manufacturer angle is represented by an omitted `angleDegrees` field, rather
than an invented value.

## Editor behavior

The Hold inspector displays a Sloper section only when the selected hold has
`kind: sloper`. Its subtype control includes `Unspecified`, `Flat`, and
`Round`. When the subtype is flat, it exposes an optional angle control in
degrees. Selecting `Unspecified` or `Round` clears the angle before saving.
Selecting flat leaves an absent angle absent; the editor never invents one.
The canonical package remains subject to the same validation rules.

## Testing and verification

Tests will be written before implementation and demonstrate the red-green
cycle for:

- optional conditional schema validation in Python and Swift;
- lossless store/editor/writer round trips;
- editor state transitions between flat and round;
- validation of all board packages and audit outcomes after data migration.

The final check will run the focused Python and Xcode tests, the complete
package validator, and the relevant iOS build/test target. The audit document
will be checked against every migrated sloper ID before completion.

## Out of scope

This change does not infer sloper data automatically, alter training-plan
wording or mappings, add other sloper shapes, or change hold geometry.
