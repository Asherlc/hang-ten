# Workbench Board Selection Startup Repair Design

**Date:** 2026-08-11

## Goal

Restore board selection in Hangboard Workbench by making every JavaScript file
referenced by the editor page available through the explicit static-asset
manifest used by both the local server and the packaged macOS runtime.

## Problem

`Tools/hold-highlight-editor/index.html` loads the suite modules
`workbench-suite-model.js`, `workbench-suite-controller.js`,
`promotion-view.js`, and `validation-view.js`. They are absent from
`STATIC_ASSET_ROUTES` in `Tools/hold-highlight-editor/workbench_assets.py`.

The server serves only routes declared in that manifest, and the packaging
build embeds only the manifest's assets. Each missing module therefore returns
404 in both the development server and packaged app. The browser stops
evaluating `app.js` before `loadInitialSession()` runs, so no board library is
loaded and the UI remains at “No board selected.”

## Scope

### Included

- Add routes for exactly the four missing suite scripts to
  `STATIC_ASSET_ROUTES`.
- Add a regression test that reads `index.html` and verifies that every local
  `<script src="…">` file has an asset entry in the shared route manifest.
- Preserve the current explicit allow-list model for server routes and bundled
  static resources.

### Excluded

- Changes to board discovery, `/api/boards`, `loadInitialSession()`, or board
  persistence.
- Dynamic static-file serving, wildcard routes, or a directory scan at runtime.
- UI, workflow, native-shell, and package-format changes.

## Design

`STATIC_ASSET_ROUTES` stays the single, ordered source of truth. Add these
route-to-file entries in the same order that `index.html` loads them, between
`workbench-model.js` and `vector-path-model.js`:

| Route | Asset |
| --- | --- |
| `/workbench-suite-model.js` | `workbench-suite-model.js` |
| `/workbench-suite-controller.js` | `workbench-suite-controller.js` |
| `/promotion-view.js` | `promotion-view.js` |
| `/validation-view.js` | `validation-view.js` |

`STATIC_ASSETS` continues to be derived from the routes. Consequently the
existing server validation and PyInstaller resource collection include the new
files without another production-code change.

The regression test belongs in `Tools/hold-highlight-editor/tests/test_server.py`
alongside route-manifest coverage. It reads the real `index.html`, extracts
each local script source, and compares the resulting set with the asset names
in `STATIC_ASSET_ROUTES`. This detects future page scripts that would otherwise
be missing from both the server and packaged application.

## Acceptance Criteria

- All eleven local script sources in `index.html` are included in the static
  asset-route manifest.
- Requests for the four suite scripts resolve through the same explicit server
  manifest as the existing editor scripts.
- The packaging build includes the four suite scripts through `STATIC_ASSETS`.
- `pytest Tools/hold-highlight-editor/tests/test_server.py::test_static_manifest_routes_every_local_script_referenced_by_index -q`
  passes.
- `pytest Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_workbench_packaging.py -q`
  passes.

## Risks and Mitigations

The change intentionally expands only the existing allow-list by four known
files. It does not permit arbitrary paths. The page-to-manifest regression test
prevents an independently added local script from becoming a startup-only 404
in the future.
