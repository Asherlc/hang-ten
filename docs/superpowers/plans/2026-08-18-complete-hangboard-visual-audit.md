# Complete Hangboard Visual Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a repeatable, source-backed visual audit and low-point-count redesign pass for every completed hangboard package.

**Architecture:** Drive the unchanged Workbench server and browser editor with one catalog-generic capture harness, preserving the editor as the rendering source of truth. Apply only source-backed metadata corrections and geometry changes accepted by generic error-bounded tooling, then recapture the complete catalog and publish labeled evidence.

**Tech Stack:** Python 3, Hangboard Workbench HTTP API, Google Chrome headless/DevTools, SVG, PNG, pytest, Node test runner, Swift/Xcode simulator tooling.

**Spec:** `docs/superpowers/specs/2026-08-18-complete-hangboard-visual-audit-design.md`

## Global Constraints

- Audit every direct child of `Hangboards/` containing `board.json` at the branch base; do not promote primary-only drafts.
- Use the exact Workbench API and SVG editor rendering path; no duplicate renderer.
- The capture and analysis workflow must contain no product IDs, product-specific coordinates, masks, templates, or tuning.
- Every changed metadata field must map to a cited authoritative source; omit unsupported optional facts.
- Normal, active, and hit-testing geometry remains the same canonical geometry from `board.json`.
- Retain labeled before and after contact sheets that visibly include every completed board, plus every full-resolution per-board before/after capture.
- Require strictly lower editable-point count for a geometry simplification and enforce at most 1 native pixel boundary deviation and 0.25% symmetric difference.
- Use `CONDUCTOR_WORKSPACE_NAME=audit-hangboard-fidelity` for owned simulator resources and clean up the exact owned UUID and workspace artifacts before completion.

---

### Task 1: Catalog-generic Workbench screenshot harness

**Files:**
- Create: `Tools/HangboardWorkbench/capture_catalog.py`
- Create: `Tools/HangboardWorkbench/tests/test_capture_catalog.py`
- Modify: `Tools/HangboardWorkbench/README.md`

**Interfaces:**
- Consumes: Workbench `GET /api/boards`, `GET /api/boards/<id>`, and the unchanged `#editor-svg` browser surface.
- Produces: `capture_catalog.capture_catalog(repository_root: Path, output_root: Path, chrome_path: Path, port: int) -> CaptureManifest`, one labeled PNG per completed board, `manifest.json`, and a labeled contact sheet.

- [ ] Write tests proving catalog order comes from `/api/boards`, capture readiness requires the primary image plus the manifest's exact SVG region count, filenames are derived from safe board IDs, and the contact sheet contains every manifest entry.
- [ ] Run `rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_capture_catalog.py -q` and confirm the new API is absent.
- [ ] Implement one headless-Chrome/DevTools capture workflow with bounded startup/readiness timeouts, deterministic viewport and canvas framing, structured failures, and exact child-process cleanup. Do not add a browser package dependency or a second hold renderer.
- [ ] Run the focused pytest and `rtk node --test Tools/HangboardWorkbench/tests/workbench*.test.js`; record exact totals.
- [ ] Document the command and output contract in the Workbench README.
- [ ] Commit the task with `Add catalog Workbench screenshot capture`.

### Task 2: Catalog-generic hold geometry derivation

**Files:**
- Create: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_geometry_derivation.py`
- Create: `Tools/HangboardPipeline/tests/test_board_geometry_derivation.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog_cli.py`
- Modify: `scripts/hangboard-tools.sh`
- Modify only if sharing existing helpers is necessary: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_presentation.py`, `Tools/HangboardPipeline/src/hangboard_vectorizer/board_path_simplification.py`

**Interfaces:**
- Consumes: any valid direct board package, its canonical `primary.png`, the Workbench `parse_closed_path` / `shape_for_path` codec, and the existing native-pixel error thresholds.
- Produces: `derive_geometry_candidates(package_root: Path) -> GeometryCandidateReport`; a deterministic, hash-bound dry-run manifest of unlabeled candidates; and `materialize_editor_document(package_root: Path, accepted_mapping: Mapping[str, object]) -> dict[str, object]` that fails unless every audited hold/piece is mapped and the mapping contains no coordinates, masks, product parameters, or thresholds.

- [ ] Write product-neutral synthetic tests for transparent and light-neutral backgrounds, textured illumination, dark and light recesses, disconnected pieces, nested holes, touching regions, mirrored/asymmetric candidates, clipped candidates, threshold instability, deterministic repeated output, and fail-closed incomplete/duplicate mappings.
- [ ] Run the focused pytest and confirm the derivation API/CLI are absent.
- [ ] Implement one fixed multiscale candidate pipeline whose scales derive only from canvas dimensions and whose thresholds derive only from reproducible image statistics. Candidate generation must not read board ID, existing hold coordinates, or product metadata.
- [ ] Round-trip accepted contours through the Workbench codec and select `roundedRect` only when it passes the same native-mask gates; otherwise emit a reducible simple path.
- [ ] Add a dry-run `derive-hold-geometry` CLI. Any write/materialization path must require a complete hash-bound accepted mapping and atomically validate the whole candidate package.
- [ ] Run focused derivation, simplification, presentation, Workbench geometry, and package tests; run two catalog dry runs and require byte-for-byte deterministic manifests.
- [ ] Commit the task with `Add generic hold geometry derivation`.

### Task 3: Complete source, metadata, and geometry audit

**Files:**
- Modify: `Hangboards/*/board.json` only where authoritative evidence or generic simplification supports a change
- Create or modify: `docs/source-audits/2026-08-18-complete-hangboard-visual-audit.md`
- Create: `docs/source-audits/assets/2026-08-18-complete-hangboard-visual-audit/before-contact-sheet.png`
- Create: `docs/source-audits/assets/2026-08-18-complete-hangboard-visual-audit/before/*.png`

**Interfaces:**
- Consumes: Task 1 capture command and manifest; Task 2 candidate reports; the three `.context/all-board-audit/research-*.md` evidence reports; existing source audits; generic `simplify-hold-paths` and `normalize-presentations` commands.
- Produces: one authoritative audit row per completed board; a baseline editor contact sheet; evidence-backed package corrections; exact before/after point and inventory metrics.

- [ ] Capture the branch-base package state and assert the manifest board IDs equal package discovery IDs before saving the labeled before contact sheet and all full-resolution per-board captures.
- [ ] For every completed board, compare the editor render, primary image, hold metadata, and inventory to the cited manufacturer evidence; record one audit row even when unchanged.
- [ ] Add failing package/data assertions before any metadata correction, then make the smallest source-backed correction and run the focused package test.
- [ ] Materialize candidate geometry only where source inventory, candidate topology, symmetry/multi-piece rules, and a complete coordinate-free mapping all agree; leave every ambiguous board unchanged with an explicit blocker.
- [ ] Run the generic simplifier with `--write`; accept only changes satisfying the global native-pixel error and strict point-reduction gates. Do not hand-edit contours merely to reduce points.
- [ ] Run the generic presentation normalizer with `--write` only if its dry run finds a catalog-generic crop; preserve exact pixel content and reprojection.
- [ ] Record all inventory preservation checks, changed fields, point counts, error metrics, and source mappings in the audit document.
- [ ] Run `rtk scripts/hangboard-tools.sh packages validate --root Hangboards` and both generic dry runs; require all changed packages to validate and both dry runs to be idempotent.
- [ ] Commit the task with `Audit and refine complete hangboard catalog`.

### Task 4: After captures, visual verification, and PR-ready evidence

**Files:**
- Create: `docs/source-audits/assets/2026-08-18-complete-hangboard-visual-audit/after-contact-sheet.png`
- Create: `docs/source-audits/assets/2026-08-18-complete-hangboard-visual-audit/after/*.png`
- Modify: `docs/source-audits/2026-08-18-complete-hangboard-visual-audit.md`

**Interfaces:**
- Consumes: Task 3 final packages and audit metrics; Task 1 capture command; isolated simulator validation contract.
- Produces: complete after contact sheet, per-board visual verdicts, fresh validation evidence, and PR description image links.

- [ ] Recapture every completed package through the Workbench, retain every full-resolution per-board after capture, and assert before/after manifests have identical ordered board-ID inventories.
- [ ] Inspect both contact sheets at readable scale and record a per-board verdict covering hold completeness, outline alignment, clipping, symmetry, and visible source agreement.
- [ ] Run focused Python and Node Workbench suites, package validation, simplifier/presentation idempotence, and `xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'`.
- [ ] Create an owned iOS simulator named `Hang Ten Conductor audit-hangboard-fidelity Review`, build/install/launch using its exact UUID, capture representative inactive and highlighted states, inspect them, then verify exact simulator deletion and cleanup.
- [ ] Finalize the audit with exact commands, test totals, simulator identity, visual findings, remaining physical-device limits, and relative Markdown links for both catalog contact sheets and both per-board capture directories.
- [ ] Commit the task with `Add complete hangboard visual evidence`.
