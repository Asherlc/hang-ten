# Strict Sloper Metadata Migration Design

## Goal

Make the subtype and inclination of every flat sloper explicit, source-backed
board-package data. This lets the app distinguish flat and round slopers
without inferring their properties from names, images, or geometry.

## Scope

The migration covers every existing hold whose `kind` is `sloper` (currently
96 holds across 28 packages), the canonical board-package schema, its Python
validator, the Swift package decoder and writer, and the iOS Hold inspector.

## Canonical schema

Every sloper hold must declare a `sloper` object:

```json
{
  "kind": "sloper",
  "sloper": {
    "type": "flat",
    "angleDegrees": 20
  }
}
```

`type` is exactly one of `flat` or `round`.

`angleDegrees` is required only for `flat`. It is a finite number from 0
through 90, inclusive, measured from the board face: 0 degrees is parallel
to the board face and larger angles slope farther away. A `round` sloper must
not include `angleDegrees`. Holds of any other kind must not include
`sloper`.

The package validator, the Swift decoder, and the editor writer all reject
the same invalid combinations. The decoded `BoardHold` retains this metadata
so callers do not need to reinterpret JSON.

## Evidence and migration

Each migrated hold must be mapped to a primary manufacturer URL that supports
the chosen subtype and, for flat slopers, the exact angle. The migration will
record this mapping in a checked-in audit document with the board package,
hold IDs, source URL, source fact, and resulting schema value.

Names, rendered geometry, imagery, and the existing `shapeConstraint` are
not evidence. When primary manufacturer material does not establish a required
value, that hold remains a migration blocker; the schema is not weakened and
no value is fabricated.

## Editor behavior

The Hold inspector displays a Sloper section only when the selected hold has
`kind: sloper`. It offers a subtype control for `flat` and `round`. When the
subtype is flat, it exposes an angle control in degrees. When it becomes
round, it clears the angle before saving. The editor may choose a valid
initial angle for a newly selected flat subtype, but the canonical package
remains subject to the same strict validation rules.

## Testing and verification

Tests will be written before implementation and demonstrate the red-green
cycle for:

- strict conditional schema validation in Python and Swift;
- lossless store/editor/writer round trips;
- editor state transitions between flat and round;
- validation of all board packages after data migration.

The final check will run the focused Python and Xcode tests, the complete
package validator, and the relevant iOS build/test target. The audit document
will be checked against every migrated sloper ID before completion.

## Out of scope

This change does not infer sloper data automatically, alter training-plan
wording or mappings, add other sloper shapes, or change hold geometry.
