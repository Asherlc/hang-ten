# Interactive Hold Editor Design

## Status

Approved. Adds interactive SVG path editing to the Hangboard Workbench so users
can visually refine AI-generated hold outlines instead of editing raw path data
in a textarea.

## Problem

The Workbench hold editor currently only supports textual SVG path editing via
a textarea. Users generating holds with AI need to visually refine contours —
dragging vertices, adjusting bezier curves, repositioning holds — without
understanding SVG path syntax.

## Goal

Add an interactive SVG path editor overlay to the existing canvas, enabling:

- **Select → edit**: Click a hold to select it; vertex and control point handles appear
- **Drag vertex**: Move individual anchor points to reshape the contour
- **Drag control point**: Adjust bezier curve shape via control handles
- **Drag body**: Reposition the entire hold by dragging its filled area
- **Add vertex**: Double-click a path segment to insert a new vertex
- **Delete vertex**: Right-click a vertex to remove it (adjacent curves become lines)

## Interaction model

### Selection

Clicking a hold overlay selects it. Only one hold is selected at a time.
Deselecting (clicking empty canvas) hides all handles.

### Handles

When a hold is selected, its contour path renders handles at every anchor point:

- **Vertex handles**: 6px filled circles with white stroke, colored by hold type.
  Positioned at each M, L, Q-to, and C-to coordinate.
- **Control point handles**: 3px filled gray circles, connected to their parent
  anchor by a thin dashed gray line. Only visible for Q and C commands.
- Dragged handle scales to 1.2x for visual feedback.

### Dragging

All dragging operates in **display path coordinates** (absolute pixels within
the canvas SVG). The existing `displayPath` → `shape_for_path` round-trip
handles converting back to normalized frame-local coordinates on save.

**Vertex drag**: Moves the anchor point. For Q commands, the control point
shifts by the same delta. For C commands, both control points shift by the
same delta. This preserves the curve shape during translation.

**Control point drag**: Moves only the control point. The anchor and other
control point remain fixed.

**Body drag**: Translates all vertices and control points by the same delta.
Uses a hit-test on the filled path element (not the stroke) to initiate.

### Adding vertices

Double-clicking a path segment (between two vertices) inserts a new vertex
at the click position:

- **L segment**: Insert an L at the closest point on the line
- **Q segment**: Subdivide the quadratic bezier at t=0.5 using De Casteljau,
  producing two Q segments with the new vertex at the split point
- **C segment**: Subdivide the cubic bezier at t=0.5 using De Casteljau,
  producing two C segments with the new vertex at the split point

The new vertex inherits the hold's type color.

### Deleting vertices

Right-clicking a vertex removes it:

- If the adjacent segments are Q or C, they are replaced by a single L
  (straight line) to the next remaining vertex
- The M vertex cannot be deleted (it is the path origin); right-click is
  ignored
- After deletion, re-validate the path

### Validation

On every edit (vertex move, body move, add, delete):

1. Reconstruct the `displayPath` string from the edited command array
2. Run client-side validation: path must be one closed contour, no
   self-intersection, coordinates within canvas bounds
3. If invalid, show the validation panel with the error (existing UI)
4. If valid, update `state.document` and mark `state.dirty = true`

Validation uses the existing `validateEditorDocument()` from
`workbench-controller.js`.

## Data model

No changes to `board.json`, `artwork.json`, or the server-side save flow.
All editing happens on the `displayPath` string within the editor document
regions. The save path (`saveEditorDocument` → `shape_for_path`) already
converts display coordinates back to normalized frame-local coordinates.

### Path command representation

The editor maintains an in-memory array of parsed commands alongside the
`displayPath` string:

```javascript
// Each command in the array:
{
  type: "M" | "L" | "Q" | "C" | "Z",
  points: [{x, y}, ...],       // anchor/endpoints
  controls: [{x, y}, ...],     // control points (Q: 1, C: 2)
}
```

On edit, the array is mutated and serialized back to a `displayPath` string
using the existing `_render` format: `M x y L x y Q cpx cpy x y C c1x c1y
c2x c2y x y Z`.

## Architecture

### Module boundary

The path parsing/mutation logic lives in a standalone module,
`Tools/HangboardWorkbench/path-editor.js`, separate from `app.js`. It exports
plain helper functions operating on a parsed command array:

- `parsePath(pathString)` — parses a `displayPath` string into a command array
- `serializePath(commands)` — serializes a command array back to a path string
- `moveVertex(commands, index, dx, dy)` — translates an anchor and its
  dependent control points
- `addVertex(commands, afterIndex, x, y)` — inserts a vertex on the segment
  after `afterIndex`, subdividing Q/C curves via De Casteljau
- `deleteVertex(commands, index)` — removes a vertex, converting an adjacent
  curve to a line where its start point shifted

The module supports both Node (`module.exports`, used by its test suite) and
the browser (`globalThis.HoldPathEditor`, since it's loaded via a plain
`<script>` tag before `app.js`). `app.js` itself owns SVG handle rendering
and pointer-event wiring, calling into these helpers on each edit.

### SVG structure

Handles render in a new `<g id="path-editor-overlay">` group inside the
existing `#editor-svg`, layered above the hold overlays. The overlay group
contains:

- Vertex handle circles (one per anchor point)
- Control point handle circles (one per control point)
- Dashed lines connecting control points to anchors
- A transparent hit-test path for body drag initiation

### Event handling

All mouse/touch events are captured on the SVG element using
`addEventListener` with `{ passive: false }` for drag prevention. Events:

- `pointerdown` on vertex handle → start vertex drag
- `pointerdown` on control handle → start control drag
- `pointerdown` on hit-test path → start body drag
- `pointerdown` on empty canvas → deselect
- `pointermove` → update drag position
- `pointerup` → commit edit, re-validate
- `dblclick` on path segment → add vertex
- `contextmenu` on vertex → delete vertex (with `preventDefault`)

Pointer events are used (not mouse events) for touch support.

### Performance

Handles re-render only when the path changes or selection changes, not on
every frame. During drag, only the dragged handle and the path `d` attribute
update (no full re-render). The hold overlay `<path>` element gets its `d`
attribute updated live during drag for immediate visual feedback.

## Files changed

| File | Change |
|------|--------|
| `Tools/HangboardWorkbench/app.js` | Add path editor module: command parsing, handle rendering, drag handlers, add/delete, validation integration. Modify `renderEditor()` to create/destroy editor on selection change. |
| `Tools/HangboardWorkbench/styles.css` | Add styles for `.path-editor-vertex`, `.path-editor-control`, `.path-editor-line`, drag feedback |
| `Tools/HangboardWorkbench/index.html` | No structural changes — overlay renders inside existing SVG |

## Testing

- Manual: Load a board, select a hold, drag a vertex, verify contour changes
- Manual: Drag body, verify hold repositions
- Manual: Double-click segment, verify vertex added
- Manual: Right-click vertex, verify vertex removed
- Manual: Edit, save, reload, verify persistence
- Automated: Unit tests for command parsing, De Casteljau subdivision, vertex add/delete logic
- Regression: Existing `validateEditorDocument` tests must still pass
