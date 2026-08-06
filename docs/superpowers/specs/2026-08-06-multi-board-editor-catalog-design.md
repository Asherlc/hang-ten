# Multi-board hold editor catalog

## Goal

Let a reviewer choose any automatically generated hangboard run in the hold-region editor, edit that run's generated regions, and save corrections back beside that run's Stage 2 artifacts. Adding another board must require data only, never editor code or product-specific logic.

## Run catalog

The editor server accepts a JSON catalog whose `runs` array contains:

- `label`: human-readable selector text.
- `runDir`: the root that confines all readable and writable artifacts.
- `image`: an optional path relative to `runDir` for the generated Stage 1 image.
- `regions`: an optional path relative to `runDir` for the generated Stage 2 proposal.

When `image` and `regions` are omitted, the server discovers the standard pipeline filenames within `runDir`. Explicit relative paths support historical pipeline layouts, such as Stage 1 and Stage 2 living in sibling directories, without encoding any product identity in the editor. Absolute artifact paths and paths that escape `runDir` are rejected.

Repeated `--run-dir` arguments remain available for standard runs and the existing single-run invocation remains compatible. Catalog entries and discovered runs are normalized to the same internal session type.

## HTTP boundary

`GET /api/sessions` returns only opaque run IDs, labels, and display metadata. It does not expose filesystem roots. Existing artifact endpoints accept `?run=<id>` and resolve the requested run independently on every request. `PUT /api/save?run=<id>` writes only to the selected session. A missing run parameter selects the first configured run for compatibility; an unknown ID returns 404.

Each session continues to expose only its configured image and regions document. Saves remain atomic and produce `stage-2-regions.edited.json` and `stage-2-human-corrections.json` beside that session's proposal. Auto-generated source artifacts are never overwritten.

## Editor behavior

A board selector appears in server mode and is populated from `/api/sessions`. Switching boards reloads its image and regions, resets selection/history/viewport state, and updates the save destination. If the current board has unsaved changes, the editor asks before discarding them. Static file-loading mode hides the selector.

Every image, regions fetch, and save request carries the selected opaque run ID. The server remains stateless about which board is active, preventing multiple tabs from changing one another's destination.

## Failure handling

Catalog validation happens at startup. Labels must be non-empty, paths must remain inside their run roots, artifacts must exist, and generated run IDs must be unique. A failed board switch leaves the current document intact and reports the error. Saves remain disabled during loading or when there are no edits.

## Verification

Server tests cover catalog parsing, confinement, discovery compatibility, run selection, unknown IDs, and per-run save routing. Browser verification loads Beastmaker, Metolius Wood Grips Compact II, and Metolius Simulator 3D from their pipeline artifacts, switches among them, and confirms their distinct images and region inventories appear in the same editor.
