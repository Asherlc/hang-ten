# Per-Segment Hold Curves Design

## Goal

Let operators curve individual hold-highlight edges in the Stage 2 contour
editor, including quarter-circle-like edges, without changing the existing
move, point-edit, export, or undo workflows. Keep the stored curve model
generic enough for a future Stage 3 vector editor.

## Current context

The current `main` branch has one geometry representation:

- Stage 2 stores `contour` points and optional metadata for global smooth paths
  and per-corner treatments. Its renderer can smooth the whole closed outline,
  but it cannot edit one edge independently.

The Stage 3 vector editor is not present on `main`; adding or porting that
separate workflow is outside this focused change. The edge-curve model uses
quadratic command semantics so a future vector editor can map it directly to
`Q` commands.

The implementation is based on the current `main` branch and remains
dependency-free browser JavaScript.

## Interaction design

The existing **Edit points** toggle becomes the entry point for both vertex and
edge editing. When enabled:

1. Stage 2 renders the existing vertex handles plus one curve handle at the
   midpoint of every edge. A straight edge has a small neutral handle; dragging
   it normal to the edge creates a bowed quadratic curve. The handle is clamped
   to the canvas and remains associated with its edge when neighboring vertices
   move.
2. The selected corner behavior remains unchanged. Clicking or dragging a
   vertex edits the vertex; clicking or dragging a curve handle edits only its
   segment. Object-level drag, resize, rotate, and bend remain available when
   edit mode is off.
3. A segment handle uses pointer capture and commits one history entry on
   pointer release. Invalid or degenerate geometry is rejected without mutating
   the current region.

The curve handle is deliberately explicit rather than changing ordinary shape
dragging. This preserves the editor's existing gesture contract.

## Shared geometry and persistence

Stage 2 adds normalized per-edge curve metadata under `region.metadata`, keyed
by the starting contour point index:

```json
{
  "edgeCurves": {
    "0": { "kind": "quadratic", "control": [120, 64] }
  }
}
```

Missing entries mean straight segments. The control point is stored in canvas
coordinates so it can be transformed with the contour. The model validates
finite coordinates, valid edge indexes, and supported kinds. Existing files
without `edgeCurves` load unchanged.

The Stage 2 renderer and authoritative export path use the same command builder:
`M`, one command per closed edge (`L` or `Q`), and `Z`. For compatibility with
the existing Stage 2 artifact contract, the exported `contour` is a deterministic
flattening of the curved path. The editable `edgeCurves` metadata is preserved
in the edited artifact and correction comparison so reopening the editor does
not lose the curve. A future Stage 3 vector editor can map each quadratic edge
directly to a `Q` command or promote it to a cubic segment.

Transforms apply to endpoints and all curve controls. Mirroring reflects control
points and reverses edge associations so the visible curve remains identical on
the opposite side.

## UI and accessibility

Curve controls use the existing SVG overlay styling and are sized in inverse
zoom units. Each handle receives an accessible label such as `Curve edge 1` and
the canvas status text identifies the active operation. The inspector keeps the
existing point count and area metrics; Stage 2 area uses the flattened contour
for validation and export.

The inspector adds no new persistent form field. The existing Edit points button
continues to toggle the mode, with updated status text and shortcut hint. A
future explicit arc preset can be added without changing the stored model; the
initial feature provides free dragging with a quadratic control that can make a
quarter-circle-like edge.

## Testing

- Add model tests for straight-to-quadratic promotion, per-edge curve path
  serialization, deterministic flattening, malformed metadata rejection, and
  mirror/transform preservation.
- Extend UI contract tests for edge handles, pointer-drag updates, one history
  entry per gesture, and unchanged whole-object dragging outside edit mode.
- Run the focused Node test suites, JavaScript syntax checks, Python editor
  tests, and `git diff --check` before handoff.

## Out of scope

- Replacing the existing SVG path grammar with a general path editor.
- Porting or creating the Stage 3 vector editor on the `main` branch.
- Automatic curve fitting or image segmentation.
- New product-specific board geometry or changes to the iOS app's runtime
  catalog.
