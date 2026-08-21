# iOS Hangboard Editor Design

Port the Hangboard Workbench geometry editor into the Hang Ten iOS app as a
native SwiftUI, phone-first editor. The editor edits copies of bundled board
packages stored in the app sandbox, validates every save against the same
fail-closed package contract the app loader enforces, and exports finished
packages for review back into the repository.

## Goals

- Native Swift port of the Workbench editing model: no WebView, no server.
- Phone-first interaction: touch-sized targets, two-finger navigation, tool
  dock and bottom-sheet inspector instead of right-click menus and sidebars.
- Saved custom boards are indistinguishable from bundled packages: same
  schema, same validation, same rendering path (`BoardHoldPathShape`).
- Reuse existing Swift validation (`BoardHoldGeometryValidator`, contour
  checks in `BoardPackageStore.swift`) so an edited package can never drift
  from what the app and staging script accept.

## Non-goals (v1)

- GitHub branch/commit/PR workflow (stays desktop/hosted Workbench).
- Creating a brand-new board from scratch (image import + metadata authoring).
- Multi-select batch editing; treatment (surface/shelf/recess) editing.
- Autosave. Saves are explicit with an unsaved-changes guard.

## Storage model

`CustomBoardStore` manages `Documents/CustomBoards/<slug>/board.json` plus
`assets/primary.png`, using the exact package contract of bundled boards:

- **Duplicate to edit.** The only way to create an editable board is
  duplicating a bundled package ("Edit copy" on a board). The copy gets slug
  `<original>-custom` (uniquified), keeps all metadata, and is marked custom.
- **Catalog merge.** Custom boards load through the same validation as
  bundled ones and appear in `BoardPickerView` with a "Custom" badge. They
  never shadow a bundled ID: duplicate IDs fail closed at save time.
- **Atomic validated save.** Write to a temp package, validate fully, then
  replace. A failed validation leaves the previous package untouched.
- **Export.** Share sheet hands out a zipped package (`<slug>.zip`) so edits
  travel back to a Mac checkout through AirDrop/Files.
- **Delete** removes the custom package after confirmation.

## Editing core (Swift port of `path-editor.ts`)

Geometry operates on canvas-space piece paths — structured
`[EditorPathCommand]` (move/line/quad/curve/close) over the presentation
image's normalized canvas, not SVG strings:

- Bounds including Bezier extrema; flattened contours (32 samples per curve,
  matching the Swift validator and `board_geometry.py`).
- Vertex move, control move, whole-path translate with centerline guide
  snapping, rotation about a pivot.
- Add point on segment (split line/quad/cubic), add inflection point on a
  curve (nearest-parameter search + De Casteljau split), delete vertex with
  inflection-pair merging, round corner.
- Segment bendable/straight conversion, snap segment horizontal/vertical.
- Shape constraints (`oval`, `circle`, `pill`, `roundedRectangle`,
  `rectangle`): primitive command generation, rotated outline model with
  eight handles, constrained resize with circle aspect lock. The constraint
  is editing metadata only; the saved canonical path stays the sole
  rendering/hit-test source of truth.
- Undo/redo via document snapshots taken before each committed gesture or
  command.

### Save conversion

On save each piece converts from canvas space to the canonical frame-local
form exactly like `board_package.py`: frame = tight bounds of the flattened
contour (never control points), commands re-expressed in `[0, 1]` frame
coordinates, oversized controls clamped, coordinates rounded to 12 decimals.
The result must pass the full package validation before replacing the stored
package.

## UI (phone-first)

Entry point: "Edit copy" action on a board in `BoardPickerView`, plus a
custom-boards section listing editable boards with delete/export.

`BoardEditorScreen` layout, top to bottom:

1. **Navigation bar**: back (dirty-state confirmation), undo/redo, Save.
2. **Canvas** (full remaining height): presentation image, all hold outlines
   in muted stroke, selected hold emphasized with fill + vertices + Bezier
   controls; constrained holds show the eight-handle box instead.
   - One finger acts by current tool; two fingers always pan/zoom
     (pinch-zoom around gesture centroid, double-tap to fit).
   - Tools: **Select** (tap hold to select, drag hold to move, drag a
     vertex or Bezier control to reshape) and **Pan**.
   - Long-press opens native context menus mapped from Workbench's
     right-click menus: on a vertex (delete, round corner), on a segment
     (add inflection point here, bend/straighten, snap horizontal/vertical),
     and on a hold (duplicate-free delete, mirror).
3. **Tool dock** (bottom): Select, Pan, Add Hold, Mirror L↔R, Inspect.
4. **Inspector sheet** (from Inspect): name,
   kind picker, finger capacity stepper, outline shape picker (Custom +
   five constraints), rotate ±15°/±45° buttons and numeric field, piece list
   for multi-piece holds, delete hold.
5. **Save flow**: validate first; failures open a validation sheet listing
   per-hold issues with jump-to-hold; success writes atomically.

Mirror L↔R mirrors selected pieces across the canvas vertical centerline
(exact coordinate mirroring, constraint rotation negated). It supports the
documented exact-mirroring authoring practice; it is an explicit operator
action, not generated geometry.

Visual language uses the existing design system (`hangCard`, rounded fonts,
hang palette); canvas overlays use high-contrast strokes that stay legible
over any board photo. All touch targets are ≥44 pt; vertices get generous
hit slop scaled by zoom.

## Architecture units

| Unit | Responsibility |
| --- | --- |
| `Models/BoardEditorDocument.swift` | Codable write-side mirror of `board.json` incl. optional `shapeConstraint`; unknown-key strictness matching the loader |
| `Models/HoldPathEditor.swift` | Pure geometry operations listed above |
| `Models/PieceGeometryConverter.swift` | Canvas ↔ frame-local conversion, frame fitting, control clamping |
| `Models/CustomBoardStore.swift` | Discovery, duplicate, atomic validated save, delete, zip export |
| `Models/BoardEditorViewModel.swift` | Selection, tools, drag sessions, undo stack, dirty/validation state |
| `Views/BoardEditorView.swift` (+ small child views) | Canvas, gestures, tool dock, inspector, validation sheet |

`AppStore`/catalog integration exposes merged `[TrainingBoard]` and reloads
after saves. New files register in `project.pbxproj` following its explicit
build-file pattern.

## Error handling

- Every mutation that could invalidate a contour runs validation on commit;
  invalid results revert to the pre-gesture snapshot with a status message
  (same behavior as Workbench).
- Save-time validation reuses loader rules: closed non-self-intersecting
  contour with ≥3 unique points enclosing area, identifier-shaped unique
  hold IDs, finger capacity range, aspect ratio match within 0.1%, PNG
  decodability, no unknown keys.
- Store errors surface as localized alerts; nothing silently drops edits.

## Testing

- `HoldPathEditorTests`: port behavioral cases from `path-editor.test.ts`
  (parse-free equivalents): subdivision, inflection add/delete/merge, round
  corner, bend/straighten, snapping, rotation, constrained resize incl.
  circle lock, bounds/extrema.
- `PieceGeometryConverterTests`: canvas→frame round-trip against real
  bundled packages (every `Hangboards/*/board.json` decodes, converts, and
  revalidates byte-stably modulo rounding).
- `CustomBoardStoreTests`: duplicate/save/delete/export lifecycle, atomicity
  under invalid documents, catalog merge and ID-collision failure.
- ViewModel tests: selection, undo/redo boundaries, dirty tracking,
  validation gating.
