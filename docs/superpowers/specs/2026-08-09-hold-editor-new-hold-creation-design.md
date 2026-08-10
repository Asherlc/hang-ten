# Hold Editor New Hold Creation Design

## Goal

Make newly added hold highlights finishable with Enter regardless of which editor control currently has focus, and preserve the selected non-freeform shape when a new hold is created.

## Scope

The change applies to `Tools/hold-highlight-editor`, the dependency-free browser editor. Existing shape choices remain the source of truth: freeform and curved freeform use point tracing, while rectangle, rounded rectangle, arced rectangle, ellipse, and capsule use drag-to-create geometry.

## Behavior

- While drawing, Enter finishes a valid freeform or curved-freeform draft even if the shape picker or another form control still has focus.
- While drawing, Escape cancels the draft under the same focus conditions.
- A newly created primitive hold stores its selected shape in `metadata.shapeKind`.
- Curved freeform continues to store `shapeKind: "freeform"` with smooth path styling, matching the existing inspector model.
- Existing editing, text-entry, and global shortcuts keep their current behavior when no drawing session is active.

## Implementation

Update the global keyboard handler so drawing-specific Enter/Escape handling runs before the early return for text controls. Update `finishDraw()` to derive `shapeKind` from the selected draw mode, mapping only curved freeform back to `freeform`. Add source-level UI regression tests that lock both keyboard ordering and metadata mapping behavior.

## Verification

Run the editor’s Node test suite with `node --test Tools/hold-highlight-editor/tests/*.test.js`. The regression tests must fail against the current implementation before the production change and pass afterward.
