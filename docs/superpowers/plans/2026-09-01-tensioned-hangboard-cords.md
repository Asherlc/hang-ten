# Tensioned Hangboard Cords Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the evidence-complete, fail-closed tooling foundation required before any catalog-wide tensioned-cord raster correction can be promoted.

**Architecture:** Extend the existing Python hangboard-package audit boundary with a closed cord-presentation ledger, generic preservation/physics validation, and a three-asset method gate. Extend the existing Workbench capture and DEBUG app review seams so they address a concrete package/presentation pair; all product facts remain data in the ledger rather than branches in code.

**Tech Stack:** Python 3.12, Pillow, pytest, Swift/SwiftUI, XCTest/XCUITest, existing Hangboard Workbench browser capture tooling.

**Spec:** `docs/superpowers/specs/2026-09-01-tensioned-hangboard-cords-design.md`

## Global Constraints

- Baseline is `90b85ce2fd0e0328aa65756cbbbc0a3f3705750b`; rejected regression example is `0ae9fc84`; exact revert is `90b85ce2`.
- The ledger is closed at exactly 20 cord-bearing packages and 47 presentations, including aliases and rotated/inverted presentations.
- Preserve the five safe repairs named in the spec byte-for-byte.
- Port-A-Board option 4 and all five YY Baguette Evo presentations remain fail-closed blockers as described in the spec.
- No product-specific processing branches, masks, coordinates, templates, segmentation, vectorization, automatic registration/cropping, or per-board tuning.
- Every source behavior follows strict red-green-refactor TDD and tests real observable behavior.
- Generated review output belongs under a path containing owner `tensioned-cords-foundation`; owned processes/resources must be recorded, stopped, deleted, and verified absent.
- Do not update or merge PR #388.

---

### Task 1: Closed cord-presentation ledger and audit validator

**Files:**
- Create: `docs/source-audits/2026-09-01-tensioned-cord-presentations.json`
- Create: `Tools/HangboardPackages/src/hangboard_packages/tensioned_cord_audit.py`
- Create: `Tools/HangboardPackages/tests/test_tensioned_cord_audit.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/README.md`
- Include: the uncommitted design and plan documents that define this task.

**Interfaces:**
- Consumes: `BoardInventory` and decoded PNG/package helpers from `hangboard_packages`.
- Produces: `load_tensioned_cord_ledger(path)`, `validate_tensioned_cord_ledger(ledger, inventory, *, hangboards_root)`, a JSON-serializable report, and CLI command `audit-tensioned-cords --root Hangboards --ledger <path>`.

- [ ] **Step 1: Write failing parser and closed-inventory tests**

  Cover literal fixtures for all required fields, direct HTTPS evidence URLs,
  duplicate/missing/extra records, stale package/presentation/asset identity,
  exact 20/47 totals, blocker contracts, alias/source relationships, and
  presentation-specific orientation/gravity/tension values. Name the mutation
  each test catches.

- [ ] **Step 2: Run the focused tests and confirm expected RED failures**

  Run: `rtk python -m pytest Tools/HangboardPackages/tests/test_tensioned_cord_audit.py -q`

- [ ] **Step 3: Implement the minimal generic parser, validator, report, CLI, and ledger**

  Reuse existing package discovery and URL/source validation patterns. Product
  IDs and evidence facts belong only in the JSON ledger. Derive every ledger
  fact from the cited existing first-party audits or direct manufacturer
  evidence; use explicit unknown/blocker values instead of inference.

- [ ] **Step 4: Run focused and full package tests**

  Run the focused command, then `rtk python -m pytest Tools/HangboardPackages/tests -q`.

- [ ] **Step 5: Run the new CLI against the live catalog and commit**

  Run `rtk scripts/hangboard-packages.sh audit-tensioned-cords --root Hangboards --ledger docs/source-audits/2026-09-01-tensioned-cord-presentations.json`, confirm 20 packages/47 presentations and the expected blockers, then commit only Task 1 files.

### Task 2: Presentation-complete Workbench capture and generic DEBUG iOS route

**Files:**
- Modify: `Tools/HangboardWorkbench/capture_catalog.py`
- Modify: `Tools/HangboardWorkbench/tests/test_capture_catalog.py`
- Modify: `Tools/HangboardWorkbench/README.md`
- Modify: the smallest existing Swift root/debug routing and board-detail files needed after repository inspection.
- Test: the corresponding focused XCTest/XCUITest files following existing DEBUG review-route conventions.

**Interfaces:**
- Consumes: the live Workbench `/api/boards` and `/api/boards/{id}` documents and normal app `BoardPackageStore` presentation selection.
- Produces: one capture manifest entry and PNG per `(packageID, presentationID)`, and DEBUG launch environment `HANGTEN_REVIEW_BOARD_PRESENTATION=1`, `HANGTEN_REVIEW_BOARD_ID`, `HANGTEN_REVIEW_PRESENTATION_ID` that opens the normal renderer for exactly that pair.

- [ ] **Step 1: Write failing Workbench tests**

  Assert multi-presentation enumeration, presentation-safe distinct filenames,
  selected asset/region readiness, manifest completeness, and contact-sheet
  coverage. Existing one-presentation behavior remains compatible.

- [ ] **Step 2: Run the focused Workbench tests and confirm expected RED failures**

  Run `rtk python -m pytest Tools/HangboardWorkbench/tests/test_capture_catalog.py -q`.

- [ ] **Step 3: Implement the minimal presentation-aware capture flow**

  Select presentations through the existing Workbench UI/API boundary and wait
  for the exact selected asset plus its complete presentation-scoped geometry.

- [ ] **Step 4: Write failing Swift tests for generic DEBUG routing**

  Cover valid package/presentation resolution, invalid package, invalid
  presentation, absence outside the opt-in environment, and the selected
  presentation rendered through the normal board-detail/map path.

- [ ] **Step 5: Run the focused Swift tests and confirm expected RED failures**

  Use the repository's bounded `xcodebuild test` form for the exact test class.

- [ ] **Step 6: Implement the smallest DEBUG-only route and rerun focused tests**

  Keep environment parsing testable and product-agnostic; surface invalid input
  in the UI instead of silently falling back.

- [ ] **Step 7: Run Workbench capture tests, Swift tests, and build-for-testing; commit**

  Include a workspace-owned capture smoke run that proves more entries than
  packages when multi-presentation packages exist. Stop and delete its exact
  server, Chrome profile, simulator, and output directory after recording
  acceptance evidence.

### Task 3: Generic preservation/physics validator and three-asset feasibility gate

**Files:**
- Create: `Tools/HangboardPackages/src/hangboard_packages/cord_image_validation.py`
- Create: `Tools/HangboardPackages/tests/test_cord_image_validation.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `Tools/HangboardPackages/README.md`
- Create or modify only generic run-contract fixtures under `Tools/HangboardPackages/tests/fixtures/` when required.

**Interfaces:**
- Consumes: baseline/candidate PNGs, one validated ledger record, and a method-run JSON contract.
- Produces: `validate_cord_candidate(...)`, `validate_cord_method_cohort(...)`, machine-readable violations, CLI command `gate-tensioned-cord-method`, and a cohort report for Aelith, Captain Dual, and MXEdge Large.

- [ ] **Step 1: Write failing preservation regression tests**

  Create controlled literal PNG fixtures and mutations that independently drop
  alpha, change dimensions/background/framing, shift or rescale the board,
  alter board/hold/color/material pixels, change unrelated pixels, misalign
  canonical overlays, or claim unsupported topology. Include a regression
  fixture derived from the observable `0ae9fc84` failure classes without
  checking out or promoting its assets.

- [ ] **Step 2: Write failing cord-physics and cohort tests**

  Cover taut versus slack paths, load direction inconsistent with canvas-down
  gravity, mechanically rotated/inverted proof reuse, blocker refusal, missing
  cohort members, and different method/config fingerprints across the three
  required assets. The gate must fail unless all three pass the same method.

- [ ] **Step 3: Run focused tests and confirm expected RED failures**

  Run `rtk python -m pytest Tools/HangboardPackages/tests/test_cord_image_validation.py -q`.

- [ ] **Step 4: Implement the minimal generic validation and gate**

  Use canvas-coordinate pixel comparison and explicit method-run evidence; do
  not infer product regions or create masks/registration/cropping. If an exact
  invariant cannot be proven from the contract, return an explicit blocker.

- [ ] **Step 5: Replay one unchanged method/config on the three required live assets**

  Store run output only below `.context/tensioned-cords-foundation-*`, record
  ownership immediately, and produce a report with per-asset pass/blocker
  status. No method is promoted when any exact invariant is unprovable.

- [ ] **Step 6: Run focused/full tests and catalog validators; commit**

  Run both Python suites, `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, and `rtk scripts/hangboard-packages.sh status --root Hangboards`.

### Task 4: Integrated acceptance and coherent checkpoint

**Files:**
- Modify only files needed to fix findings from integrated review.
- Create: workspace-owned acceptance records under `.context/` only; do not commit generated captures.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: a clean whole-branch review, one accepted foundation checkpoint, and the cohort handoff notes for Crimptonite, Flash, Port-A-Board, and MXEdge.

- [ ] **Step 1: Run all focused and full verification fresh**

  Run the package and Workbench suites, live ledger CLI, feasibility cohort
  gate, final package validation/status, relevant XCTest/XCUITest, and bounded
  simulator build.

- [ ] **Step 2: Confirm preservation of the five safe repairs**

  Compare their tracked asset hashes byte-for-byte with safe baseline
  `90b85ce2`; any change is a failure.

- [ ] **Step 3: Run independent whole-branch review and address findings**

  Review against this plan and spec. Do not accept Critical or Important
  findings or unverified 20/47 inventory coverage.

- [ ] **Step 4: Squash or create one coherent accepted checkpoint without touching PR #388**

  Push the named workspace branch, then notify the other three Paseo workspaces
  with the exact accepted hash, explicit merge permission, and the requested
  cohort blocker/ledger notes. Do not publish a provisional hash.

