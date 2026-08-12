# Focused Hold Outline Editor Design

**Date:** 2026-08-12

## Goal

Make the Hangboard Workbench immediately understandable to its sole intended
operator: the person reviewing auto-detected holds and correcting their
outlines. The primary experience is a precise, expert outline editor—not a
general board pipeline dashboard.

## Problem

The current workbench combines unrelated concerns in the same surface:

- The persistent **Onboard**, **Inspect**, **Promote to iOS**, and **Validate**
  sidebar presents workflow choices before an operator can edit a hold.
- The top bar contains retry, upstream revision, compare, export, corrections,
  snapping, and save actions at the same visual level.
- The inspector exposes every geometry and metadata setting at once, even when
  direct point manipulation is the immediate task.

This forces the operator to infer the pipeline and tool meanings before doing
the work that matters: making an automatic hold outline accurate.

## Scope

### Included

- Make **Edit holds** the only persistent workbench surface.
- Remove the tool-suite sidebar and its Onboard / Inspect / Promote / Validate
  navigation from the editor.
- Center the UI on the board image, selected outline, direct vertex editing,
  the hold inventory, and one clear Save action.
- Keep all current precision and expert capabilities, but reveal them only in
  a selected-hold **Advanced tools** drawer.
- Keep board selection and a lightweight board-details entry point in the
  header.
- Retain autosave, revision binding, validation mechanics, and artifact
  contracts behind the simpler UI.

### Excluded

- Changing detection, canonical board data, geometry persistence, or the
  Stage 2 / Stage 3 artifact contract.
- Removing expert geometry capabilities.
- Redesigning the repository-opening screen or onboarding data model.
- Moving promotion/validation behavior into the editor; those remain available
  through separate developer-oriented entry points or commands.

## Design

### Primary editor

After board selection, the application opens directly into **Edit holds**.
The main workspace has two visible areas:

1. A hold inventory for filtering, selecting, and adding a missed hold.
2. The board canvas, where selection, point dragging, point insertion, point
   deletion, pan, zoom, and overlay visibility remain direct manipulations.

The header contains the active board selector, Undo, Redo, a concise save
state, and a primary **Save changes** action. It may offer a compact
**Board details** action. Retry, revise upstream, compare, export, export
corrections, and edge snapping do not occupy persistent header space.

The editor should use plain task-oriented feedback, such as “Saved outline
changes” and “Drag a point to reshape this hold,” never unexplained stage or
pipeline terminology.

### Selected-hold controls

Selecting a hold shows a compact inspector or drawer with only the direct,
frequent controls:

- Hold key and type.
- Point count and outline validation feedback.
- Delete hold.
- An **Advanced tools** disclosure.

The normal expectation is that outline editing happens on the canvas. Selected
freeform holds continue to show independently draggable vertices without a
separate mode. Adding a point, removing a targeted point, and undo/redo remain
available by their existing direct gesture and keyboard behavior.

No selection shows only a short instruction to choose a detected hold or add a
missed one.

### Advanced tools

The disclosure is contextual—it is available only with a selected hold—and
organizes every retained expert capability by intent:

- **Outline:** shape conversion, straight/smooth path style, curve tension,
  corner treatment, and simplify curve.
- **Transform:** move, resize, rotate, and bend controls where those apply to
  the selected shape.
- **Assists:** edge snapping, mirror copy, and mirror onto.
- **Details:** interaction mode and review notes.

Controls that cannot apply to the selected geometry remain omitted rather than
disabled. The Advanced drawer is closed by default and remembers its open
state only for the current editing session.

Comparison and export actions move to an explicit overflow menu labelled
**More**. This preserves recovery and review tooling without making it part of
the outlining task.

### Board lifecycle boundaries

Board metadata can be reviewed through **Board details**, separate from hold
correction. Promotion and validation are intentionally absent from this
surface; their existing backend workflows and local artifacts remain intact,
but they are accessed by developer-oriented commands or a separate utility.

The workbench must not imply that saving hold outlines commits, pushes, or
publishes a board. Save keeps its current local, revision-bound behavior.

## Acceptance criteria

- A selected board opens directly to the outline editor with no persistent
  tool-suite sidebar or pipeline-stage navigation.
- The visible primary actions are board selection, Undo, Redo, Save, and
  direct canvas/hold-list editing.
- A user can select an auto-detected hold and reshape it without opening any
  inspector section beyond the canvas itself.
- All current expert outline, transform, assist, and metadata controls remain
  available under clearly named selected-hold Advanced tools groups.
- Inapplicable advanced controls are not shown.
- Compare and export remain available from a labelled overflow menu; they no
  longer compete with Save or direct editing.
- Existing autosave, validation, undo/redo, geometry behavior, and persistence
  contracts continue to work unchanged.
- The interface contains no user-facing stage/checkpoint/promotion/validation
  wording on the main outline-editing surface.

## Verification

- Add markup and controller tests confirming the sidebar/tool views are absent
  from the editor shell, primary actions remain available, and Advanced tools
  render only for a selected hold.
- Add interaction tests for direct selected-hold vertex editing with Advanced
  tools closed.
- Test that each expert control appears in its applicable group and that
  inapplicable controls are omitted.
- Run the current workbench unit/browser tests and manually verify a real
  auto-detected board can be corrected, saved, reloaded, and exported.

## Risks and mitigations

Moving lifecycle controls out of the editor could make them harder to find for
development work. The explicit Board details and More entry points retain the
relevant access paths, while promotion and validation remain documented
developer workflows. Retaining the current backend and artifact boundaries
keeps this a UI/task-model change rather than a migration of board data.
