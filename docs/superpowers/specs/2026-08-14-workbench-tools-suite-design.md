# Workbench Tools Suite Design

## Status

Approved direction: replace the board-content pipeline with a standalone
Workbench tool suite. This supersedes the runtime architecture in the
2026-08-13 direct-board-editor design. Historical design records remain as
history; they do not define the current product.

## Goal

The Workbench is the direct authoring surface for repository board packages.
It lists boards, creates boards, loads an image, edits holds, validates the
result, and saves the package. It has no runs, stages, checkpoints, approval
states, promotion, retry, or hidden pipeline workspace.

`Tools/HangboardPipeline/` is removed from the repository. The Workbench must
not import, package, document, test, or require that directory.

## Product model

### Boards, not runs

The opening screen contains one board library. Registered packages appear in
the library, and a new board is created directly under `Hangboards/` when the
user explicitly saves it. Browser-local unsaved edits may be discarded, but
they are not persisted as a run, a draft directory, or an in-progress item.

Opening a board always loads its primary image and saved hold geometry. The
editor always permits editing and saving a board the selected checkout owns.

### A suite of direct tools

The standalone Workbench has these internal tools, each operating on the same
package data:

1. **Board library** — reads `Hangboards/catalog.json`, lists packages, and
   creates or replaces a package transactionally.
2. **Image tool** — imports or changes the package primary image with its
   path confined to that package.
3. **Hold editor** — reads and writes exact hold outlines against the primary
   image.
4. **Validator** — checks package identity, assets, metadata, and hold
   geometry before any write is committed.
5. **Save tool** — atomically writes the changed package and catalog under a
   per-library lock.

These are direct tools, not sequential lifecycle stages. Their APIs and UI
copy use board, image, hold, validation, and save language only.

## Canonical package contract

The package remains the source of truth:

```text
Hangboards/
  catalog.json
  <board-slug>/
    board.json
    artwork.json
    evidence.json
    semantics.json
    assets/primary.png
```

`board.json` owns stable board and hold metadata. `artwork.json` owns the
primary-board artwork and the exact editable hold outlines. Saving an edited
hold updates its path in `artwork.json` and its derived normalized frame in
`board.json` in one package transaction. Other documented artwork layers,
evidence, and semantics remain untouched unless the user changes their
respective tool.

### Hold invariant

One physical hold has exactly one hold ID and exactly one closed, contiguous
outline. A saved outline has one contour; duplicate `holdID` entries,
disconnected subpaths, self-intersection, and paths outside the normalized
canvas are validation failures. Decorative seams, shading, and board layers
are artwork only and cannot represent or extend a hold.

The editor presents a hold as one selectable object. It never exposes an
artwork-piece concept or silently approximates a hold with a convex hull,
largest component, or another lossy conversion.

## Direct request flow

1. The native shell verifies the selected checkout contains the standalone
   Workbench and `Hangboards/`, then starts the matching backend.
2. The browser requests the direct board library.
3. Selecting a board receives the package primary image and a direct hold
   document derived from `board.json` and `artwork.json`.
4. The editor loads image and holds atomically, preserving the prior editor
   state if either resource fails.
5. Save validates the proposed package, replaces only the relevant canonical
   files atomically, then reloads the saved board.

There are no artifact URLs, revision IDs, runtime workspaces, status polling,
or stage-derived editor documents in this flow.

## Migration and deletion

Reusable, package-specific parsing, geometry, validation, and atomic-write
code is moved into `Tools/HangboardWorkbench/` under direct names. Legacy
pipeline code is not kept as an internal compatibility module.

The migration deletes `Tools/HangboardPipeline/` and removes its command
wrappers, build hooks, native checkout requirements, tests, documentation,
and CI references. Repository package validation and Workbench packaging are
updated to use the standalone Workbench modules. No previously generated run
directories are read or migrated.

## Error handling

The UI reports the failing board and operation (for example, “Could not load
Metolius Wood Grips Compact II holds” or a specific validation error). A failed
load does not clear already visible holds. A failed save does not alter the
current package or catalog. Errors never expose filesystem paths.

## Verification

- Unit tests prove package read/write and validation are owned solely by the
  Workbench and do not import `hangboard_vectorizer`.
- Package tests prove a valid board opens with all holds and saves edited
  contours and derived frames atomically.
- Geometry tests reject duplicate IDs, more than one contour per hold,
  non-contiguous/self-intersecting paths, and out-of-canvas coordinates.
- Browser tests prove the library/editor contains no run, stage, approval,
  checkpoint, pipeline, or promotion product language; failed loads retain
  prior state.
- Native and packaging tests prove the app starts from a checkout without
  `Tools/HangboardPipeline/`.
- Repository checks confirm no live source, script, build, CI, or user guide
  references the deleted pipeline path or CLI commands.
