# Workbench Board Selection Startup Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for every implementation task, with a fresh subagent and a review checkpoint before commit. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every JavaScript module referenced by Hangboard Workbench's page available through the shared static manifest so the application reaches board loading and selection.

**Architecture:** Keep `STATIC_ASSET_ROUTES` as the explicit route and packaged-resource allow-list. Add the four omitted suite modules to that tuple, and use a Python regression test to compare local `index.html` script sources to the manifest's asset values. The server's existing manifest-based routing and the packaging build's existing `STATIC_ASSETS` derivation then consume the same corrected source of truth.

**Tech Stack:** Python 3.11+, pytest, standard-library `re`, vanilla HTML and JavaScript.

## Global Constraints

- Preserve explicit static-file allow-listing; do not add wildcard routes or filesystem discovery.
- Add exactly `workbench-suite-model.js`, `workbench-suite-controller.js`, `promotion-view.js`, and `validation-view.js` to the manifest.
- Keep the four additions in the same order as their `<script>` tags in `index.html`.
- Do not change board APIs, board persistence, browser application logic, or the macOS shell.
- Do not add third-party dependencies.

---

### Task 1: Cover the page-to-manifest contract and restore the missing assets

**Files:**

- Modify: `Tools/hold-highlight-editor/workbench_assets.py`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`

**Interfaces:**

- Consumes: `STATIC_ASSET_ROUTES: tuple[tuple[str, str], ...]` from `workbench_assets.py` and `Tools/hold-highlight-editor/index.html`.
- Produces: route entries for all page scripts and `test_static_manifest_routes_every_local_script_referenced_by_index()`.

- [ ] **Step 1: Write the failing page-to-manifest regression test**

In `Tools/hold-highlight-editor/tests/test_server.py`, add `import re` with the
standard-library imports and replace the existing asset import with:

```python
from workbench_assets import STATIC_ASSETS, STATIC_ASSET_ROUTES  # noqa: E402
```

Add this test after `test_server_routes_static_files_from_the_shared_manifest`:

```python
def test_static_manifest_routes_every_local_script_referenced_by_index():
    index = (EDITOR_ROOT / "index.html").read_text(encoding="utf-8")
    local_script_sources = set(
        re.findall(r'<script\\s+src="([^"?#]+)"', index)
    )
    manifest_assets = {asset for _route, asset in STATIC_ASSET_ROUTES}

    assert local_script_sources == manifest_assets - {"index.html", "styles.css"}
```

- [ ] **Step 2: Run the focused test and verify it fails for the missing suite modules**

Run:

```bash
pytest Tools/hold-highlight-editor/tests/test_server.py::test_static_manifest_routes_every_local_script_referenced_by_index -q
```

Expected: FAIL. The assertion's left side contains
`workbench-suite-model.js`, `workbench-suite-controller.js`,
`promotion-view.js`, and `validation-view.js`; the manifest side does not.

- [ ] **Step 3: Add the four ordered, explicit manifest routes**

In `Tools/hold-highlight-editor/workbench_assets.py`, insert these entries
immediately after `("/workbench-model.js", "workbench-model.js"),` and before
the existing `vector-path-model.js` entry:

```python
    ("/workbench-suite-model.js", "workbench-suite-model.js"),
    ("/workbench-suite-controller.js", "workbench-suite-controller.js"),
    ("/promotion-view.js", "promotion-view.js"),
    ("/validation-view.js", "validation-view.js"),
```

Do not change the `STATIC_ASSETS = tuple(...)` expression. Its existing
derivation must include the four files for server validation and PyInstaller.

- [ ] **Step 4: Run the focused regression test and verify it passes**

Run:

```bash
pytest Tools/hold-highlight-editor/tests/test_server.py::test_static_manifest_routes_every_local_script_referenced_by_index -q
```

Expected: PASS. The eleven script sources in `index.html` exactly match the
manifest's JavaScript asset values.

- [ ] **Step 5: Run the affected server and packaging suites**

Run:

```bash
pytest Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_workbench_packaging.py -q
```

Expected: PASS. The server continues to validate and route only manifest
assets, while PyInstaller arguments include every asset derived from the
corrected manifest.

- [ ] **Step 6: Commit the implementation**

```bash
git add Tools/hold-highlight-editor/workbench_assets.py Tools/hold-highlight-editor/tests/test_server.py
git commit -m "fix: serve workbench suite assets"
git push
```

## Self-Review

- Spec coverage: Task 1 adds all four required routes, preserves the explicit
  allow-list, and adds the required page-script manifest regression test.
- Placeholder scan: no deferred work, unbound names, or unspecified commands
  remain.
- Type consistency: the test consumes the exact tuple exported by
  `workbench_assets.py`; `STATIC_ASSETS` remains the production derivation used
  by the server and packaging build.
