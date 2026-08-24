# Stable Editor Geometry Design

## Goal

Make freeform-hold editing operate on a typed, session-local geometry model whose
anchors, Bézier controls, and segments have stable identities throughout an edit.
The persisted Hangboard package contract remains unchanged.

## Context

The Workbench already parses `HoldRegion.displayPath` into typed `PathCommand`
values before every edit, has constraint editing, guide snapping, horizontal and
vertical segment commands, mirrored duplication, document undo/redo, and
fail-closed validation. The missing boundary is a stable, editor-owned identity
model: UI selection, React keys, and drag state currently address vertices and
controls by command and control indices.

## Architecture

Introduce an `EditablePath` projection in the Workbench browser layer. It owns a
mutable typed command list and assigns opaque, editor-local IDs to each segment,
anchor, and control. IDs are seeded from the hold-region key and generated in
document order when a path is first projected or rebuilt; they are never written
to `board.json`.

During an editing session, mutation helpers preserve unaffected IDs. Inserting a
vertex allocates IDs only for the inserted anchor and segments affected by the
split; converting a segment, moving an anchor/control, or snapping a segment
retains the existing IDs. A path is serialized through the existing canonical
`PathEditor.serializePath` only when the document needs an updated
`displayPath`. An externally loaded, undone, redone, or otherwise replaced
document rebuilds the local projection from its canonical path.

`board.json`, the Python package validator, the iOS consumer, and the
Workbench’s save contract remain exactly as they are. SVG path strings are
therefore still a browser/editor boundary, not a package-schema migration.

## Components

### `editable-path.ts`

This new pure module defines the editor-only model and operations:

- `EditablePath`, `EditableSegment`, `EditableAnchor`, and `EditableControl`
  have opaque `id` fields plus command-compatible coordinates.
- `createEditablePath(regionKey, pathString, pathEditor)` parses the canonical
  path and assigns deterministic IDs for a fresh projection.
- `serializeEditablePath(editablePath, pathEditor)` writes canonical SVG path
  data without IDs.
- Mutation helpers expose anchors and controls by ID, preserving unrelated IDs
  as they translate, move, snap, convert, or split segments.
- Invalid or non-closed input continues to fail through the existing parser and
  document validator; this module does not widen accepted path syntax.

### `useHoldEditor.ts`

Replace index-based selection and drag targets with editor-local IDs. A ref owns
the selected hold’s `EditablePath` during an active edit and is discarded or
rebuilt when the selected region/path changes. Existing document history still
stores `EditorDocument` snapshots only; it never stores local IDs.

### `HoldCanvas.tsx`

Render anchor and control targets with their stable IDs as React keys and data
attributes. Keyboard focus, context-menu actions, and pointer drags pass IDs to
the hook rather than array indexes.

## Existing Capabilities

No new snapping implementation is needed. The existing guide-edge snapping and
horizontal/vertical segment operations remain in place and are called through
the typed projection. Shape constraints, duplicate-and-mirror, and undo/redo
also retain their existing behavior.

## Error Handling

The local editable projection is disposable. Any parse, mutation, or final
validation failure follows the existing rollback path: restore the original
`EditorDocument`, release pointer capture, discard the projection, and report
the current invalid-contour message. No local-ID error can alter a saved package.

## Testing

Pure-module tests prove deterministic fresh IDs, identity preservation for
non-destructive edits, ID allocation on insertion, canonical serialization, and
no ID leakage into serialized output. React editor tests prove an anchor remains
selected through a drag, an unrelated anchor retains its DOM identity after
insertion, and undo/redo rebuilds valid editable projections without changing
saved path data. The established Workbench typecheck, module, React, and bundle
checks verify integration.

## Non-goals

- Persisting anchor, control, or segment IDs in `board.json`.
- Changing JSON geometry, its schema version, or package validation.
- Adding a general SVG import/export feature.
- Introducing automatic/image-derived geometry generation.
- Reimplementing existing snapping, shape constraints, mirroring, or history.
