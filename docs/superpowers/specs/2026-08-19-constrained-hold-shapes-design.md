# Constrained Hold Shapes Design

## Goal

Make Workbench shape choices durable and keep oval, circle, pill, rounded-rectangle, and rectangle outlines geometrically constrained while users resize, move, rotate, save, and reopen them.

## Canonical representation

Each geometry piece may contain this optional object alongside `frame`, `shape`, and `treatment`:

```json
"shapeConstraint": {
  "shape": "oval",
  "rotationDegrees": 15
}
```

`shape` is exactly one of `oval`, `circle`, `pill`, `roundedRectangle`, or `rectangle`. `rotationDegrees` is finite and normalized to the half-open range `[-180, 180)`. Absence means Custom/freeform.

The existing `frame` and `shape` remain the sole rendering, highlighting, and hit-testing geometry. They also retain position and size. `shapeConstraint` records only the invariant and orientation needed to reconstruct shape-aligned editing behavior. It does not mention or depend on a particular editor.

All strict package consumers accept and validate the optional object. Workbench exposes it on the corresponding editor region and round-trips additions, updates, and removals. Swift and the package validator do not use it to render. Existing packages require no migration.

## Inspector and handles

The Outline shape picker becomes stateful and contains Custom, Oval, Circle, Pill, Rounded rectangle, and Rectangle. Selecting a primitive regenerates the selected piece inside its current axis-aligned bounds and sets rotation to zero. Selecting Custom preserves the path exactly and removes the constraint.

Constrained pieces hide individual anchors and Bézier controls. They render a shape-aligned bounding box with eight resize handles. Edge handles change one intrinsic dimension and corner handles change both, keeping the opposite edge or corner fixed. Handles clamp at two canvas pixels rather than crossing or flipping.

Circles stay circular in image-space pixels. Corner drags preserve aspect ratio with the opposite corner fixed. Edge drags change the diameter with the opposite parallel edge fixed and the perpendicular center unchanged. Pills choose horizontal or vertical semicircular ends from the shorter intrinsic dimension. Rounded rectangles retain the existing corner radius of twenty percent of the shorter intrinsic dimension.

Rotation handles and rotation buttons preserve the constraint and update `rotationDegrees`. The bounding box rotates with the shape. Whole-shape dragging and keyboard nudging preserve the constraint without changing its angle. Existing physical-hold rotation continues to rotate every sibling piece around the shared centroid and updates every constrained sibling's angle.

## Geometry derivation

For constrained paths, Workbench obtains the tight path center, inverse-rotates commands by `rotationDegrees`, and calculates the intrinsic unrotated bounds using real line, quadratic, and cubic extrema. The resize calculation transforms the pointer into that local coordinate system, changes the appropriate bounds, regenerates the exact primitive, and rotates it back. No unrotated frame is persisted.

The path stays the rendering source of truth. If malformed constraint metadata or invalid geometry reaches Workbench, the operation is rejected and the prior path, constraint, dirty state, and status are restored.

## Persistence and compatibility

The Workbench editor document carries an optional `shapeConstraint` on each region. Backend validation rejects unknown keys, unknown shape values, booleans/non-finite angles, and angles outside `[-180, 180)`. Save dirty detection includes constraint changes even when a path is unchanged. Adding or changing a constraint stores it on the matching geometry piece; choosing Custom removes it. Unrelated `treatment` data and sibling pieces remain unchanged.

The iOS package decoder and package validator accept and strictly validate `shapeConstraint`; the iOS adapter ignores it when creating runtime board shapes. This preserves current rendering exactly.

## Failure behavior

The picker and handles are disabled during board or Git operations. A resize that becomes invalid or leaves the canvas is reverted on pointer completion using the existing transactional drag behavior. Cancellation and lost pointer capture restore both path and constraint state. Save failures keep all in-memory edits.

## Testing

- Python package tests cover valid and invalid constraint schema, editor exposure, save/reopen persistence, Custom removal, dirty detection, and preservation of unrelated geometry data.
- Pipeline tests cover strict parsing and retention of the optional constraint value.
- Swift package tests cover acceptance, rejection, and unchanged runtime `BoardShape` adaptation.
- Path-editor tests cover inverse-rotated bounds, all eight handles, minimum-size clamping, circle aspect locking, vertical/horizontal pills, and rotated primitives.
- Browser tests cover stateful picker behavior, Custom unlock, constrained handle rendering, drag/rotate/move metadata updates, sibling isolation, cancellation rollback, busy-state protection, save, and reload.

## Scope

Directly authored board-specific paths and coordinates are expected package data. Board-specific runtime code and pixel-derived automatic classification or generation are not permitted. Existing freeform editing remains unchanged, and no existing board is automatically labeled as a primitive.
