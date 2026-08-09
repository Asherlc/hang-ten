# Hold Editor UI Design

## Goal

Turn the existing hangboard onboarding editor into a single-purpose, full-feature
hold editor. The user should work directly on hold highlights in one screen:
choose a board/run, edit existing highlights, add missing highlights with a
chosen hold type, delete incorrect highlights, and save the reviewed result.

The editor remains a complete hold-level authoring tool. Simplifying the product
means removing the staged onboarding workflow from the UI, not removing hold
metadata or geometry capabilities.

## Scope

### In scope

- A single **Hold Editor** workspace centered on the board image and highlight
  regions.
- Board/run selection in server mode, with the selected run loaded directly.
- Existing hold inventory and search.
- Existing highlight selection, movement, point editing, resize, rotation,
  bending, curve simplification, mirroring, and undo/redo.
- Adding a new highlight, including choosing its hold type: jug, sloper, edge,
  or pocket.
- Deleting an existing highlight.
- Editing hold-level details already supported by the editor: key, type, shape,
  path style, interaction mode, and review notes.
- Saving to the selected onboarding run and exporting edited regions or human
  corrections as recovery paths.
- Copy and status text that describes hold-highlight editing rather than
  onboarding stages.

### Out of scope

- Replacing the existing region document schema or save API.
- Changing the generated Stage 1 image or automatic Stage 2 proposal.
- Adding product-specific board logic to the browser editor.
- Removing static file-loading support as a fallback for offline/manual use,
  unless the implementation needs to hide those controls in server mode.
- Adding automated segmentation or automatic hold classification.

## User experience

The primary workflow is:

1. Start the local editor server with one or more board/run inputs.
2. Choose a board when multiple runs are available; the selected image and
   highlights load as one editable document.
3. Select a hold from the inventory or canvas.
4. Adjust its highlight shape and hold details, add a missing highlight, or
   delete an incorrect one.
5. Save the complete edited region document and correction delta.

The interface should not ask the user to think in terms of stages, approvals,
or a sequence of image/region-loading steps. The generated document is the
starting point for a hold-editing session, not a visible wizard step.

The three-pane layout remains the foundation:

- Left: searchable **Hold inventory** with count and add-highlight controls.
- Center: board image, highlight overlay, overlay visibility, opacity, zoom,
  fit, and pan controls.
- Right: full **Hold inspector** for geometry and hold metadata.

The header should identify the tool as **Hold Editor** and explain that it edits
hold highlights. Server mode should make the board/run selector and Save action
the primary entry points. Existing undo, redo, export, and static fallback
actions may remain available, but stage-oriented labels and instructional copy
must be removed or rewritten.

## Interaction details

### Add highlight

The Add control starts the existing draw workflow. On completion, the new hold
is selected and its inspector is shown. The user must be able to choose its hold
type from the existing four-type vocabulary before saving. The new region uses
the existing shape/drawing controls and participates in the same history and
correction-delta logic as an edited region.

### Delete highlight

Delete remains available for the selected hold. It removes the hold from the
current document, records the deletion in undo/redo history, and reports the
change in the status bar. Saving emits the existing deleted correction entry.

### Edit highlight

Existing geometry controls and hold inspector fields remain supported. Changes
continue to update the current document and mark it dirty. No new geometry
algorithm is required for this UI refactor.

### Board switching

When multiple server runs are configured, the board selector changes the active
editing document. If there are unsaved changes, the editor asks for confirmation
before discarding them. A failed switch keeps the current document intact. A
successful switch resets selection, history, transient draw/edit modes, and
viewport state as the existing server-session flow does.

## Architecture and data flow

Keep the existing dependency-free browser architecture:

- `index.html` defines the single workspace and accessible controls.
- `app.js` owns interaction state, rendering, server-session loading, save/export
  actions, and event wiring.
- `editor-model.js` remains the pure document/history geometry and export layer.
- `server.py` remains the constrained run catalog, artifact, and atomic-save
  boundary.

The implementation should prefer targeted UI/state changes over a model rewrite.
The existing normalized region document remains the canonical in-browser
editing state. The server continues to receive the complete edited document and
the calculated human-correction delta; generated source artifacts remain
read-only.

## Failure handling

- A missing or invalid server session leaves the editor in its existing static
  fallback state and reports that the user can load compatible files manually.
- A failed board switch does not replace the current image or regions.
- Save remains disabled while loading, saving, or when there are no edits.
- Save failures remain visible in the existing save-state indicator and status
  bar without losing the current edits.
- Deleting, adding, and editing remain recoverable through undo/redo.

## Verification

Add or update tests at the narrowest useful boundary:

- DOM/source checks confirm the editor is branded and described as a Hold Editor,
  retains type selection for new/editable holds, and retains add/delete actions.
- Existing editor-model tests continue to cover added and deleted correction
  entries and metadata-preserving exports.
- Browser-level checks verify the server-loaded single-screen flow, board
  switching, add-with-type, delete, undo/redo, dirty state, and save routing.
- Run the focused JavaScript and Python editor tests, then inspect the diff for
  whitespace/errors and manually review the rendered editor if the local
  browser tooling is available.

## Acceptance criteria

- A reviewer can open a configured run and begin editing highlights immediately
  without navigating a multi-step onboarding UI.
- The reviewer can edit existing highlights, add a new highlight and choose its
  type, and delete an existing highlight.
- Full hold geometry and metadata editing remain available.
- Board selection, save, export, undo, redo, dirty-state protection, and error
  handling continue to work.
- The UI and documentation consistently describe a hold editor, not a staged
  onboarding workflow.
- Existing artifact schemas and generated source files remain unchanged.
