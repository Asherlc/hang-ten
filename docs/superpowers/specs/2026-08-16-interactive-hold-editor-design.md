# Interactive Hold Editor Design

## Status

Implemented manual path editing for canonical hangboard geometry.

## Goal

Let an operator directly refine a selected geometry piece in Workbench without
editing path text. Workbench never discovers or proposes holds. The operator
creates the physical inventory and deliberately authors every path from primary
manufacturer evidence before and during visual review.

## Interaction model

- Selecting a freeform path shows its anchor and control-point handles.
- Dragging an anchor or control point updates only that selected path.
- Dragging the filled body translates every point together.
- Adding or deleting a vertex is an explicit operator action.
- Invalid or open paths cannot be saved.
- Choosing Custom/freeform preserves the current path and exposes its normal
  point controls.
- When the checked-out schema supports shape constraints, an operator may select
  a regular preset for a genuinely regular hold. Constraint handles remain
  aligned to the selected shape; constraints are never inferred from pixels.

## Canonical data contract

The geometry piece in `Hangboards/<slug>/board.json` remains authoritative.
Workbench may use a display-coordinate representation while editing, but save
must round-trip it to the same normalized closed path. The saved path—not the
presentation PNG or optional constraint metadata—drives normal rendering,
active highlighting, and hit testing in the app.

The editor must not create an alternate artwork document, hidden workspace
revision, or secondary geometry source. Existing pieces without constraint
metadata remain freeform.

## Validation and review

Each edit must preserve a finite closed path within the presentation canvas.
After saving, run the package validator and inspect the normal path in
Workbench. Active/highlight alignment is reviewed in the app on an owned
simulator. A package is not complete until every logical hold maps to its exact
physical contact and no geometry exists without a hold.

## Out of scope

- Pixel-derived shape classification or geometry creation.
- Automatic point reduction or boundary cleanup.
- Any hidden draft-to-published geometry lifecycle.
