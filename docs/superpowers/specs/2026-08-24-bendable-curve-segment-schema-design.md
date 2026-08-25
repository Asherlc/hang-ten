# Persisted Bendable Curve Segments

## Purpose

Allow an author to mark a straight hold-outline edge as bendable and then pull
that edge into a smooth curve without introducing an anchor point. The mark
must survive saving and reopening a board, while imported and constrained
cubic geometry retains ordinary whole-path dragging.

## Canonical schema

`board.json` path commands gain one optional property:

```json
{
  "command": "curve",
  "control1": [0.25, 0.2],
  "control2": [0.75, 0.2],
  "to": [1, 0.5],
  "bendable": true
}
```

`bendable` is valid only on a cubic `curve` command and may only be `true`.
Its absence means false. It is authoring metadata: it never changes geometry,
rendering, hit testing, or the iOS training-app model. Existing packages stay
valid and preserve their current behavior.

The canonical flag lives on the segment command, not in a persisted command
index list. Command order can change during editing; the flag must move with
the command object and be explicitly derived for replacement commands.

## Package and client boundaries

The Python package schema and Workbench package validation accept and retain
the property. The Workbench editor-document API exposes a transient command
index projection only to associate the canonical command flags with the SVG
display path; saving maps that projection back to the corresponding canonical
commands. Indices are never written to `board.json`.

The strict Swift package decoder accepts `bendable` on cubic commands and
otherwise ignores it. This keeps the package loadable on iOS without making a
runtime training behavior depend on editor metadata.

## Editor behavior

The existing **Make bendable** command replaces an `L` command with a cubic
curve and marks that new command `bendable: true`. A direct drag on only that
marked, unconstrained cubic changes its controls so that the curve midpoint
passes through the pointer. Its endpoint anchors remain unchanged.

An unmarked cubic—including imported geometry—continues to drag the whole
outline. Constrained shapes never expose or honor bendability. Existing
control-handle dragging remains unchanged.

Structural path operations preserve intent deliberately:

- Splitting a marked cubic creates marked replacement curve commands.
- Straightening a marked curve removes the marker.
- Deleting or replacing a marked command removes the marker unless the
  operation explicitly creates marked descendant curve commands.
- Moving anchors or controls retains the marker on the same command.

## Validation and tests

Validation rejects `bendable` on move, line, quadratic, and close commands,
and rejects false or non-boolean values. Tests cover package parsing and
round-tripping, strict Swift decoding, Workbench load/save behavior, reload,
structural edits, direct bending, and the unchanged behavior of unmarked and
constrained cubics.
