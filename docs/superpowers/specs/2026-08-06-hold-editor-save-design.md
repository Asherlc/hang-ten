# Hold Editor Local Save Design

## Goal

Let the visual hold-region editor persist reviewed geometry directly into an onboarding run without making the browser capable of writing arbitrary local files.

## Architecture

Add a dependency-free Python server beside the static editor. The operator launches it with an explicit onboarding run directory. It binds to loopback, serves the editor, discovers the run's Stage 1 image and Stage 2 region proposal, and exposes a narrow JSON API for loading and saving that session.

Static hosting remains supported. In static mode, the existing download exports continue to work and the Save button explains that a local editing session is required.

## Data flow

1. The server resolves and validates the supplied run directory.
2. `GET /api/session` returns browser-safe URLs for the Stage 1 image and Stage 2 regions document.
3. The browser loads those artifacts through the existing editor model and keeps the original regions as its correction baseline.
4. Save sends the complete edited document and calculated added/modified/deleted correction delta to `PUT /api/save`.
5. The server validates both documents and atomically writes `stage-2-regions.edited.json` and `stage-2-human-corrections.json` beside the discovered Stage 2 proposal.
6. The response reports the saved paths and timestamp; the editor marks the current state saved.

The generated `stage-2-regions.json` remains unchanged so automatic output and human review remain distinguishable and reproducible.

## Safety and errors

- Bind only to `127.0.0.1` by default.
- Serve artifacts only from the configured run directory.
- Reject path traversal, malformed JSON, missing canvas data, invalid region contours, and oversized requests.
- Write temporary files in the destination directory, flush them, then replace the destination atomically.
- Return structured errors without exposing files outside the configured run.
- Keep Export Regions and Export Corrections available as recovery paths.

## Interface

Add a primary **Save** button to the toolbar. It is active when `/api/session` identifies a writable run. Save status distinguishes unsaved changes, saving, saved, and failed states. Undo, redo, geometry editing, and metadata changes all mark the document dirty.

Run the editor with:

```bash
rtk python3 Tools/hold-highlight-editor/server.py --run-dir /absolute/path/to/onboarding-run
```

## Verification

- Unit-test run discovery, payload validation, atomic output paths, path confinement, and malformed requests.
- Exercise the HTTP session and save endpoints against a temporary onboarding run.
- Run JavaScript syntax validation and load the editor through the local server.
