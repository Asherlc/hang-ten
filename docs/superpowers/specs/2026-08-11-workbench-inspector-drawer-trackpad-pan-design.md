# Workbench Drawer, Direct Editing, and Trackpad Navigation Design

**Date:** 2026-08-11

## Goal

Keep the hold inspector available at ordinary desktop widths without horizontal
overflow, make board editing read as one user-facing step named **Edit holds**,
and make a two-finger trackpad gesture pan the board while pinch-to-zoom keeps
zooming at the cursor.

## Problem

At a roughly 1,280px-wide window, the permanent 284px suite sidebar, 250px
region panel, 400px canvas minimum, and 238px inspector require more width than
the window. The inspector consequently extends past the right edge. The current
980px fallback removes it entirely, which prevents continuous access to the
selected hold's details.

The canvas consumes every wheel event as zoom. A normal two-finger trackpad
scroll therefore zooms rather than moves across a large board.

The editor also exposes internal pipeline stages (including hold-contour
refinement, smoothing, and vector refinement) in the editing surface. Those
implementation stages are not a useful task model for the person editing
holds. Freeform holds further require a separate Edit points mode before their
vertices appear, and their generic object controls imply proportional resize.

## Scope

### Included

- At viewport widths of 1,250px and below, retain the region panel and canvas
  as the workspace grid and present the existing inspector as an off-canvas
  right drawer.
- Give the drawer a persistent, fixed open control, a close control, modal
  dialog semantics, Escape close, focus trapping, and focus restoration to the
  opener. The existing inspector DOM remains the single rendered inspector;
  it is moved visually, never duplicated.
- Keep the current three-column inspector layout above 1,250px.
- Pan the canvas for ordinary wheel events by `deltaX` and `deltaY`; zoom around
  the pointer only when `event.ctrlKey` is true, which covers trackpad pinch.
  Both paths call `preventDefault()`.
- Replace visible pipeline and checkpoint copy in the Onboard editor with the
  single label **Edit holds**. A selected board opens its existing editable
  geometry view directly. Preserve internal stage, approval, autosave, and
  validation mechanics without surfacing stage names or manual progression in
  this editor.
- Make freeform selected holds show their vertices without a separate mode;
  dragging a vertex changes only that contour coordinate. Keep object resize
  handles for non-freeform primitive shapes.
- Delete or Backspace removes a targeted freeform vertex only when the contour
  will retain at least three points. With no eligible targeted vertex, the
  existing selected-hold delete action applies.
- Escape cancels the highest-priority active operation; with no active
  draw/pan/drag/handle/edge/transform operation, it deselects the hold and
  refreshes inspector and overlay state.
- Move manufacturer, display name, subtitle/product context, dimensions,
  aspect ratio, and product/source URL out of the Promote to iOS surface into
  reusable Board info. Promotion consumes that information and the board's
  canonical ID rather than presenting a redundant editable iOS board ID.

### Excluded

- Changes to the board API, artifact persistence, geometry data format, or
  internal pipeline execution.
- A duplicate/mobile-only inspector form, arbitrary responsive breakpoints,
  touch-gesture redesign, or a browser scroll fallback over the canvas.
- Changing vector-path editing behavior beyond removing user-facing stage
  terminology.

## Design

### Responsive inspector

`index.html` gains an `inspector-drawer-toggle` button adjacent to editor
actions, a labelled drawer backdrop, and a close button inside the existing
`.inspector-panel`. The inspector has `role="dialog"`, `aria-modal="true"`, and
an accessible title relationship to `inspector-title` only while the narrow
drawer presentation is active. `app.js` records `state.inspectorDrawerOpen`
and the element that opened it.

At `max-width: 1250px`, `.workspace-grid` has exactly two columns:
`250px minmax(0, 1fr)`. `.inspector-panel` becomes a fixed right drawer with a
238px content width, transform-based closed/open state, its own scrolling, and
a backdrop that blocks workspace interaction. The toggle remains visible and
reports its state with `aria-expanded`; clicking it opens the drawer and moves
focus to the close button. Close button, backdrop click, and Escape close the
drawer and return focus to the toggle. Tab and Shift+Tab cycle within the
drawer while open. The drawer itself remains in the DOM, so every ordinary
`renderInspector()` update continues to update the one form.

At widths above 1,250px, the normal three-column grid remains, the toggle and
drawer-only close button are hidden, and the inspector has no modal behavior.
The 980px rule must no longer use `display: none` for the inspector.

### Canvas wheel navigation

Extract the wheel decision into a small pure function in
`editor-interaction-model.js`, exposed as `globalThis.HoldEditorInteractionModel`:

```js
function viewportWheelAction({ ctrlKey, deltaX, deltaY }) {
  if (ctrlKey) return { kind: "zoom", scale: Math.exp(-deltaY * 0.0012) };
  return { kind: "pan", deltaX, deltaY };
}
```

`index.html` loads it after `curve-gesture-model.js` and before `app.js`.
`app.js` calls it from the non-passive viewport wheel listener. It always calls
`event.preventDefault()`: `zoom` delegates to the existing cursor-anchored
`setZoom(...)`; `pan` subtracts the deltas from `state.panX` and `state.panY`,
then calls `renderTransform()`. This preserves ordinary scrolling direction
and all current Fit, mouse, Space-pan, and zoom-button behavior.

### Board info and promotion boundary

Add **Board info** as a reusable board-level section in the Inspect tool. It
owns the metadata fields `manufacturer`, `name`, `subtitle`, `dimensions`,
`aspectRatio`, and `productURL`; each label retains its evidence-oriented help
text. The active board's canonical `boardId` is displayed read-only as Board
ID. Board info is loaded from and saved to the active board's canonical metadata
record, revision-bound with the board, rather than being a transient promotion
form. Empty values remain empty; the UI must not populate manufacturer, copy,
dimensions, ratio, URL, or source claims from the image or model inference.

The Promote to iOS view contains no editable identity/metadata fields. Its
controller receives `board` and Board info, builds the existing required
promotion payload internally, and sets `boardID` to `board.boardId`. The
server-side profile decoder accepts this canonical derivation and rejects any
distinct client-supplied platform ID until a proven separate identifier and
schema are explicitly introduced. Promotion stays blocked with an actionable
message when required Board info is absent, and its preview signature covers
the derived canonical ID plus Board info.

### Single-step editing and freeform vertices

Replace the pipeline block with a compact editor identity whose only visible
step is **Edit holds**. Remove `STAGE_LABELS`, `PIPELINE_TO_TIMELINE_STAGE`,
`timelineView`, stage-timeline rendering, and stage/checkpoint copy from the
Onboard editor. The active board card may retain board revision identity but
must not publish internal stage names. Replace user-facing approval progression
copy with save/complete language; the existing backend calls continue to drive
the internal workflow.

For a selected contour region whose `metadata.shapeKind` is `freeform`, always
render the existing `.vertex-handle` circles and bind each to `startHandleDrag`.
Do not render its `renderObjectControls` bounding frame or resize handles.
Dragging the handle continues to set only `region.contour[index]`, preserving
the rest of the contour. The Edit points control can be removed from the
inspector because it is no longer required for this behavior. Non-freeform
primitive regions keep the current object controls and proportional resize
implementation; vector rendering stays unchanged.

`selectedCornerIndex` identifies a targeted freeform vertex after click or
drag. Delete and Backspace first call `deleteSelectedFreeformVertex()`. It runs
only for a selected freeform with a valid selected index and more than three
contour points; it removes exactly that coordinate, clears the targeted-corner
state, commits `Deleted control point`, and rerenders. With no targeted
freeform vertex (including a three-point contour), selected-hold deletion
remains the result. Vector regions and primitives retain their existing
selected-hold behavior.

The keydown handler handles an active drawing cancellation first, then any
active gesture cancellation/release, then drawer close, then selection clear.
Only the final no-active-gesture branch calls `selectRegion(null)`, which
causes the inspector's existing no-selection render and overlay refresh.

## Acceptance Criteria

- At 1,250px or narrower, no horizontal workspace overflow occurs; the region
  panel and canvas remain visible and the inspector opens as an accessible
  right drawer.
- Drawer open/close control state, focus movement, focus restoration, backdrop
  close, Escape close, and Tab trapping work without duplicating inspector DOM.
- Above 1,250px, the inspector is a normal third column.
- A normal wheel event pans by both supplied deltas and never zooms; a
  `ctrlKey` wheel event zooms around the event cursor. Both prevent page scroll.
- The Onboard editing surface says **Edit holds** and does not display
  hold-contour refinement, smoothing, vector refinement, checkpoint, or stage
  labels; internal pipeline behavior remains intact.
- Board info is editable and reusable outside Promote to iOS; the canonical
  board ID is read-only, no metadata is inferred, and promotion consumes the
  saved Board info without showing redundant inputs.
- A selected freeform hold always exposes independently draggable vertices,
  does not show bounding-box resize controls, and a vertex drag changes only
  the dragged coordinate. Targeted vertices can be deleted down to, but not
  below, three points; otherwise Delete/Backspace deletes the selected hold.
  Primitive shapes retain resize controls.
- Escape cancels active editing first; otherwise it deselects the current hold
  and restores the inspector's no-selection state.

## Risks and Mitigations

The breakpoint must not leave the inspector `display: none`, because that
would make it inaccessible and prevent focus behavior. A single DOM inspector
avoids divergent form state. Wheel classification is isolated in a pure module
so the semantics can be tested without a browser. Freeform rendering is
conditioned on `shapeKind`, preserving established primitive resizing and
vector constraints.
