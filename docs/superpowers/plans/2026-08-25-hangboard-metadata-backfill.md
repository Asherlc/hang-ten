# Catalog-wide Hangboard Metadata Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 44-package catalog’s optional hold metadata maximally complete without asserting any fact that primary manufacturer evidence does not map to an exact physical hold.

**Architecture:** A catalog-level source-audit JSON ledger declares the complete set of reviewed boards for each batch and records each exact value or deliberate blank. A new package-tool validator cross-checks that ledger against `board.json`, while the existing Workbench catalog capture gains a hold-ID overlay mode for manual source-position review. Six manufacturer-family batches extend the ledger and package data without changing the app schema or canonical hold geometry.

**Tech Stack:** Python 3.11 standard library, pytest, existing `hangboard_packages` package, existing Workbench Python capture utility, JSON, Markdown source audits, official manufacturer web/manual/diagram sources.

**Spec:** `docs/superpowers/specs/2026-08-25-hangboard-metadata-backfill-design.md`

## Global Constraints

- Use only primary manufacturer product pages, manuals, labelled diagrams, and official product views; do not use retailer, forum, or image-search facts.
- Keep unsupported values absent from `board.json`; capture the source-specific reason in the ledger and the batch source audit.
- Never infer a value from a photo, hold width, board-level measurement list, another model, or existing geometry.
- Never change or generate canonical geometry as part of this project. Hold-ID overlays render existing paths solely for human review.
- Keep all generated screenshots in `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/`; do not commit them.
- Use `rtk` for shell commands. Run package pytest through `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest`; run `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` for every batch.
- Commit and push every completed task. Each batch handoff and PR description must state evidence, fields added, before/after coverage, overlay root, and supported remaining blanks.

---

### Task 1: Add the auditable metadata-ledger domain and validator

**Files:**
- Create: `Tools/HangboardPackages/src/hangboard_packages/metadata_audit.py`
- Create: `Tools/HangboardPackages/tests/test_metadata_audit.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/__init__.py` only if it exists and exports package APIs

**Interfaces:**
- Consumes: `BoardInventory` and `BoardHold` from `hangboard_packages.board_catalog` plus a ledger JSON path.
- Produces: `load_metadata_ledger(path: Path) -> MetadataLedger`, `validate_metadata_ledger(ledger: MetadataLedger, inventory: BoardInventory) -> MetadataCoverageReport`, and `MetadataAuditError(ValueError)`.
- `MetadataCoverageReport.to_json()` returns `{ "reviewedBoardIDs": [...], "fields": {field: {"populated": int, "verified": int, "unavailable": int, "notApplicable": int}}, "boards": [...] }` with all IDs and keys sorted.

- [ ] **Step 1: Write failing parser and cross-check tests.**

  In `test_metadata_audit.py`, create temporary packages with `write_board_package`, load them with `discover_board_packages`, and write JSON fixtures. Cover one exact scalar mapping, one exact range mapping, an unavailable value, an unknown hold ID, a duplicate `(boardID, holdID, field)` entry, a verified value that differs from JSON, and an incomplete reviewed board.

  ```python
  def test_verified_scalar_must_equal_the_package_value(tmp_path: Path) -> None:
      package = write_board_package(tmp_path / "boards" / "fixture", board_id="fixture.board")
      document = json.loads((package / "board.json").read_text())
      document["holds"][0]["sizeMillimeters"] = 20
      (package / "board.json").write_text(json.dumps(document))
      ledger = _write_ledger(tmp_path, verified("fixture.board", "hold-left", "sizeMillimeters", 18))

      with pytest.raises(MetadataAuditError, match="sizeMillimeters does not match"):
          validate_metadata_ledger(load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards"))
  ```

- [ ] **Step 2: Run the focused test and verify RED.**

  Run: `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_metadata_audit.py`

  Expected: FAIL because `metadata_audit` does not exist.

- [ ] **Step 3: Implement a closed, explicit ledger schema.**

  Parse a root object with exactly `schemaVersion`, `reviewedBoardIDs`, and `records`. Require schema version `1`; nonempty unique identifier board IDs; and record objects with exactly `boardID`, `holdIDs`, `field`, `outcome`, `reviewedAt`, `source`, and either `value` (`verified`) or `reason` (blank outcomes). Require `source` to have `kind: "manufacturer"`, an HTTPS URL, and a nonempty source label. Permit only the six fields in the approved spec and only `verified`, `unavailable`, and `notApplicable` outcomes.

  Implement exact comparison against raw `BoardHold` values: scalars compare as JSON numbers, ranges compare both bounds, enums compare strings, and features compare ordered JSON arrays. Expand only explicit `holdIDs`; reject duplicate expanded keys. For every hold on every `reviewedBoardID`, require one record for each scoped field. Return sorted coverage counts instead of printing from the domain module.

- [ ] **Step 4: Run focused tests and verify GREEN.**

  Run: `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_metadata_audit.py`

  Expected: PASS, including the scalar/range exact-match and complete-coverage cases.

- [ ] **Step 5: Commit and push the validator domain.**

  ```sh
  git add Tools/HangboardPackages/src/hangboard_packages/metadata_audit.py Tools/HangboardPackages/tests/test_metadata_audit.py
  git commit -m "Add hangboard metadata audit validator"
  git push origin HEAD:add-hangboard-depth-capacity
  ```

### Task 2: Expose deterministic audit validation through the package CLI

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cli.py`
- Modify: `scripts/hangboard-packages.sh`
- Modify: `Tools/HangboardPackages/tests/test_cli.py`
- Modify: `Tools/HangboardPackages/README.md`

**Interfaces:**
- Consumes: `audit-metadata --root Hangboards --ledger docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`.
- Produces: sorted JSON from `MetadataCoverageReport.to_json()` on stdout and a single-line `error:` diagnostic on stderr on an invalid ledger.

- [ ] **Step 1: Write failing CLI tests.**

  Add a fixture ledger matching a temporary board and require the new command to return its coverage JSON. Add an invalid-record case requiring return code `1` and a concise unknown-hold diagnostic.

  ```python
  result = _run_cli("audit-metadata", "--root", str(packages), "--ledger", str(ledger))

  assert result.returncode == 0, result.stderr
  assert _json_output(result.stdout)["reviewedBoardIDs"] == ["fixture.board"]
  ```

- [ ] **Step 2: Run the focused CLI test and verify RED.**

  Run: `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_cli.py -k audit_metadata`

  Expected: FAIL because `audit-metadata` is not an accepted command.

- [ ] **Step 3: Add the command without changing `validate` or `status`.**

  Add an `audit-metadata` subparser requiring both `--root` and `--ledger`; discover the final inventory, load and validate the ledger, then print `report.to_json()` with the existing sorted JSON formatter. Add `audit-metadata` to the shell wrapper’s allowed commands. Document the command and its source-only, read-only behavior in the package README.

- [ ] **Step 4: Run focused and package tests.**

  Run: `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_cli.py Tools/HangboardPackages/tests/test_metadata_audit.py`

  Expected: PASS.

- [ ] **Step 5: Commit and push the CLI.**

  ```sh
  git add Tools/HangboardPackages/src/hangboard_packages/cli.py scripts/hangboard-packages.sh Tools/HangboardPackages/tests/test_cli.py Tools/HangboardPackages/README.md
  git commit -m "Expose hangboard metadata audit command"
  git push origin HEAD:add-hangboard-depth-capacity
  ```

### Task 3: Capture visible stable hold IDs for manual mapping review

**Files:**
- Modify: `Tools/HangboardWorkbench/capture_catalog.py`
- Modify: `Tools/HangboardWorkbench/tests/test_capture_catalog.py`
- Modify: `Tools/HangboardWorkbench/README.md`

**Interfaces:**
- Consumes: the existing capture command plus `--hold-id-labels`.
- Produces: screenshots in a caller-owned `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/<batch>/` directory, with one SVG text label per logical `metadata.holdID`; each label is positioned at the union of that hold’s rendered path bounds.

- [ ] **Step 1: Write failing capture-helper tests.**

  Add pure tests for a helper that converts API regions with `metadata.holdID` and DOM path bounds into one label per hold, uses the union center for multi-piece holds, and rejects a region missing a hold ID. Add an argument-parser test for `--hold-id-labels`.

  ```python
  assert hold_id_label_positions((
      RegionBounds("two-piece-0", "two-piece", 0, 0, 10, 10),
      RegionBounds("two-piece-1", "two-piece", 20, 10, 10, 10),
  )) == (HoldIDLabel("two-piece", 15, 10),)
  ```

- [ ] **Step 2: Run the focused capture test and verify RED.**

  Run: `rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_capture_catalog.py -k 'hold_id or labels'`

  Expected: FAIL because the label helper and flag do not exist.

- [ ] **Step 3: Inject review-only SVG labels immediately before capture.**

  When `--hold-id-labels` is selected, fetch the selected board’s editor document, group rendered `.region-shape` paths by `metadata.holdID`, call `getBBox()` for each piece, calculate the union center, and append non-interactive SVG `<text data-audit-hold-id>` labels. Use a high-contrast halo/stroke so IDs are legible without hiding paths. Remove only these injected labels after each screenshot. The default capture mode must remain byte-for-byte behaviorally unchanged.

- [ ] **Step 4: Run capture tests and a Metolius smoke capture.**

  Run: `rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_capture_catalog.py`

  Then run the command with `--hold-id-labels` into `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/metolius/` and visually confirm every Metolius logical hold has one visible stable ID. Stop the local server/Chrome process through the capture tool’s existing managed-process cleanup and verify it exited before continuing.

- [ ] **Step 5: Commit and push capture support.**

  ```sh
  git add Tools/HangboardWorkbench/capture_catalog.py Tools/HangboardWorkbench/tests/test_capture_catalog.py Tools/HangboardWorkbench/README.md
  git commit -m "Capture stable hold IDs for metadata review"
  git push origin HEAD:add-hangboard-depth-capacity
  ```

### Task 4: Complete the Metolius pilot batch

**Files:**
- Create: `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`
- Modify: `docs/source-audits/2026-08-12-metolius-board-packages.md`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`
- Modify: `Hangboards/metolius-climbers-edge/board.json`
- Modify: `Hangboards/metolius-contact/board.json`
- Modify: `Hangboards/metolius-foundry/board.json`
- Modify: `Hangboards/metolius-light-rail-2/board.json`
- Modify: `Hangboards/metolius-prime-rib/board.json`
- Modify: `Hangboards/metolius-project/board.json`
- Modify: `Hangboards/metolius-rock-rings-3d/board.json`
- Modify: `Hangboards/metolius-simulator-3d/board.json`
- Modify: `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Modify: `Hangboards/metolius-wood-grips-deluxe-ii/board.json`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

**Interfaces:**
- Consumes: official Metolius product pages and numbered depth diagrams already linked by the two Metolius source audits; review-only labelled captures.
- Produces: the first ledger with all ten Metolius IDs in `reviewedBoardIDs` and complete six-field outcomes for every Metolius hold.

- [ ] **Step 1: Produce and review labelled screenshots before assigning data.**

  Capture the ten boards into `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/metolius/`. For every manufacturer-labelled position, manually record its stable hold ID, source label, and presentation in the Markdown audit. Do not use the labels to redraw, crop, or otherwise alter a path.

- [ ] **Step 2: Research only the official evidence and write a failing coverage assertion.**

  Re-open every Metolius primary product page and current official numbered diagram linked in the audit. Add a test requiring the ledger report’s sorted `reviewedBoardIDs` to equal the ten Metolius board IDs and requiring zero unaccounted fields for each board.

  ```python
  assert report.reviewed_board_ids == (
      "metolius.climbers-edge", "metolius.contact", "metolius.foundry", "metolius.light-rail-2",
      "metolius.prime-rib", "metolius.project", "metolius.rock-rings-3d", "metolius.simulator-3d",
      "metolius.wood-grips-compact-ii", "metolius.wood-grips-deluxe-ii",
  )
  assert all(board.unaccounted_fields == 0 for board in report.boards)
  ```

- [ ] **Step 3: Run the assertion and verify RED.**

  Run: `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_metadata_audit.py -k metolius`

  Expected: FAIL because no catalog ledger exists.

- [ ] **Step 4: Enter evidence, then only the matching package values.**

  Add one ledger record for every Metolius hold/field outcome, using explicit stable IDs and exact official source labels. For `verified`, write the value to its corresponding `board.json`; for `unavailable` or `notApplicable`, leave it absent. Preserve existing values only when the refreshed ledger source proves the exact mapping; remove any value that cannot be retained. Extend both Markdown audits with the URLs, review date, ID-to-position mapping, values added/removed, and blank rationale.

- [ ] **Step 5: Verify, report, commit, and push.**

  Run:

  ```sh
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_metadata_audit.py
  rtk scripts/hangboard-packages.sh audit-metadata --root Hangboards --ledger docs/source-audits/2026-08-25-hangboard-metadata-ledger.json
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  ```

  Record the JSON coverage before/after in the PR description and chat handoff, including the `.context` overlay root and every verified remaining blank. Commit the ledger, audits, tests, and only changed Metolius packages; push the commit.

### Task 5: Complete the Tension and So iLL batch

**Files:**
- Modify: `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`
- Modify: `docs/source-audits/2026-08-12-soill-tension-board-packages.md`
- Modify: `docs/source-audits/2026-08-25-hold-metadata-completeness-appendendum.md`
- Modify: `Hangboards/tension-flash-board/board.json`, `Hangboards/tension-grindstone/board.json`, `Hangboards/tension-honestone/board.json`, `Hangboards/tension-whetstone/board.json`
- Modify: `Hangboards/soill-iron-palm-2/board.json`, `Hangboards/soill-split-palm/board.json`, `Hangboards/soill-training-tiles/board.json`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

- [ ] **Step 1: Capture and manually reconcile all seven boards.**

  Render labelled screenshots in `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/tension-soill/`; compare every mapped source label with the existing stable ID before modifying data.

- [ ] **Step 2: Add a failing seven-board ledger-scope assertion.**

  Require the sorted reviewed IDs to add `tension.flash-board`, `tension.grindstone`, `tension.honestone`, `tension.whetstone`, `soill.iron-palm-2`, `soill.split-palm`, and `soill.training-tiles`, with no unaccounted fields.

- [ ] **Step 3: Verify RED, then add exact evidence records and matching JSON values.**

  Run the focused metadata-audit test and confirm it fails before changing the ledger. Refresh the official sources in the existing audit, add explicit values or blank rules, update only source-mapped package fields, and document all retained variable-depth mappings without converting them to scalar depths.

- [ ] **Step 4: Run validation, publish the coverage delta, commit, and push.**

  Run the focused test, `audit-metadata`, and final-inventory validation. Put field totals, the overlay root, and unsupported evidence gaps in the PR description/chat handoff; commit and push the batch.

### Task 6: Complete the Beastmaker, Lattice, Moon, Nature, Target10a, and The Hangboard batch

**Files:**
- Modify: `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`
- Modify: `docs/source-audits/2026-08-12-beastmaker-board-packages.md`
- Modify: `docs/source-audits/2026-08-12-single-board-documentation-packages.md`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`
- Modify: `Hangboards/beastmaker-1000/board.json`, `Hangboards/beastmaker-2000/board.json`, `Hangboards/lattice-triple-rung/board.json`, `Hangboards/moon-armstrong/board.json`, `Hangboards/nature-stoak-board-iii/board.json`, `Hangboards/target10a-linebreaker-base/board.json`, `Hangboards/the-hangboard/board.json`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

- [ ] **Step 1: Capture labels and refresh each official source set.**

  Use `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/independent-makers/` and record every actual source-position mapping. Treat Beastmaker family values as unsupported unless the refreshed manufacturer material maps them to the exact pocket IDs.

- [ ] **Step 2: Write and run the failing scope assertion.**

  Require exactly these seven additional IDs in the ledger and zero unaccounted fields; confirm RED before changing package JSON.

- [ ] **Step 3: Add evidence-backed ledger outcomes and package metadata.**

  Add only exact source values, retain blank rules for grouped/unmapped size claims, and extend the named audits with field-by-field rationale. Do not turn board-level depth lists into per-hold values.

- [ ] **Step 4: Validate, report, commit, and push.**

  Run metadata-audit tests, `audit-metadata`, and final inventory. Include before/after field totals, overlay location, and explicit remaining gaps in the handoff; commit and push.

### Task 7: Complete the Escape, Frictitious, Evolv, and DeWoodstok batch

**Files:**
- Modify: `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`
- Modify: `docs/source-audits/2026-08-12-dewoodstok-escape-board-packages.md`
- Modify: `docs/source-audits/2026-08-12-evolv-frictitious-board-packages.md`
- Modify: `Hangboards/escape-beta-22/board.json`, `Hangboards/escape-unlimited/board.json`, `Hangboards/frictitious-doormount-pro-7/board.json`, `Hangboards/frictitious-megalith/board.json`, `Hangboards/evolv-kilter-basic-long/board.json`, `Hangboards/dewoodstok-woodbord/board.json`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

- [ ] **Step 1: Capture and reconcile six boards by stable ID.**

  Write screenshots to `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/escape-frictitious-evolv-dewoodstok/` and require manual comparison to official product/diagram evidence.

- [ ] **Step 2: Write and verify the failing ledger-scope test.**

  Extend the expected reviewed IDs with the six named board IDs and require no unaccounted fields; run the focused test to observe RED.

- [ ] **Step 3: Backfill only per-contact evidence.**

  Refresh official material, map every source position to the reviewed hold IDs, create verified or blank ledger records, update matching JSON fields, and extend both source audits. Keep the documented DoorMount inventory mismatch blank until a primary source resolves it.

- [ ] **Step 4: Validate, report, commit, and push.**

  Run metadata-audit tests, CLI audit, and final-inventory validation. Publish the coverage delta and unsupported evidence gaps in the PR/chat handoff; commit and push.

### Task 8: Complete the Trango batch

**Files:**
- Modify: `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`
- Modify: `docs/source-audits/2026-08-12-trango-board-packages.md`
- Modify: `docs/source-audits/2026-08-12-rock-prodigy-board-package.md`
- Modify: `Hangboards/trango-rock-prodigy-forge/board.json`, `Hangboards/trango-rock-prodigy-natural/board.json`, `Hangboards/trango-rock-prodigy-pivot/board.json`, `Hangboards/trango-rock-prodigy-training-center/board.json`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

- [ ] **Step 1: Capture four labelled boards and reconcile source conflicts.**

  Create `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/trango/` captures. Compare all current manuals/product markings and explicitly preserve blanks wherever the Natural guide conflicts or IMR values are aggregate-only.

- [ ] **Step 2: Write and observe the failing Trango scope test.**

  Require the four Trango IDs as reviewed and zero unaccounted fields; run focused pytest and verify RED.

- [ ] **Step 3: Update records, JSON, and source audits.**

  Add exact verified mappings and blank outcomes; keep geometry unchanged; document the conflict resolution and every retained blank in the two source audits.

- [ ] **Step 4: Validate, report, commit, and push.**

  Run metadata-audit tests, the CLI report, final-inventory validation, then commit and push the coverage summary with the overlay root.

### Task 9: Complete the YY Vertical and Zlagboard batch

**Files:**
- Modify: `docs/source-audits/2026-08-25-hangboard-metadata-ledger.json`
- Modify: `docs/source-audits/2026-08-12-yy-vertical-board-packages.md`
- Modify: `docs/source-audits/2026-08-12-zlagboard-board-packages.md`
- Modify: `Hangboards/yy-baguette/board.json`, `Hangboards/yy-baguette-evo/board.json`, `Hangboards/yy-penta-evo/board.json`, `Hangboards/yy-travelboard/board.json`, `Hangboards/yy-verticalboard-evo/board.json`, `Hangboards/yy-verticalboard-first/board.json`, `Hangboards/yy-verticalboard-light/board.json`, `Hangboards/yy-verticalboard-one/board.json`, `Hangboards/zlagboard-evo/board.json`, `Hangboards/zlagboard-pro/board.json`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

- [ ] **Step 1: Create and review ten labelled board captures.**

  Use `.context/hangboard-metadata-backfill-${CONDUCTOR_WORKSPACE_NAME}/yy-zlagboard/`. Match stable IDs to official labels and never derive an angle, finger count, or depth from the screenshot.

- [ ] **Step 2: Write and verify the final batch RED assertion.**

  Extend expected reviewed IDs with the ten YY/Zlag IDs and require zero unaccounted fields; run focused pytest and observe RED.

- [ ] **Step 3: Fill only proven values and document blank outcomes.**

  Refresh official sources, write ledger records per exact contact, change matching JSON fields only, and add the field-level mapping and omission reasons to the two audits.

- [ ] **Step 4: Validate, report, commit, and push.**

  Run metadata-audit tests, CLI audit, and final-inventory validation. Put the final batch’s before/after totals, overlay root, and explicit unresolved evidence gaps in the PR/chat handoff; commit and push.

### Task 10: Certify the complete catalog and hand off the evidence gaps

**Files:**
- Modify: `docs/source-audits/2026-08-25-all-board-hold-audit.md`
- Modify: `docs/source-audits/2026-08-25-hold-metadata-completeness-appendendum.md`
- Modify: `Tools/HangboardPackages/tests/test_metadata_audit.py`

**Interfaces:**
- Consumes: the final ledger and full discovered inventory.
- Produces: one final report whose reviewed IDs equal all 44 package IDs, with no unaccounted field and a human-readable catalog coverage ledger.

- [ ] **Step 1: Write the final failing inventory-completeness test.**

  ```python
  inventory_ids = tuple(package.board.id for package in discover_board_packages(HANGBOARDS_ROOT).packages)
  report = validate_metadata_ledger(load_metadata_ledger(LEDGER_PATH), discover_board_packages(HANGBOARDS_ROOT))

  assert report.reviewed_board_ids == inventory_ids
  assert sum(board.unaccounted_fields for board in report.boards) == 0
  ```

- [ ] **Step 2: Run it and verify RED if any package escaped a batch.**

  Run: `rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests/test_metadata_audit.py -k complete_catalog`

  Expected: FAIL until all six batches have populated the ledger.

- [ ] **Step 3: Complete final audit narratives without fabricating data.**

  Update both Markdown audits with final per-field totals, a table of verified remaining blanks and source-specific reasons, and the reviewed overlay roots. Do not add package metadata merely to make a count look better.

- [ ] **Step 4: Run the full verification suite.**

  Run:

  ```sh
  rtk uv run --with pytest --with Pillow --with PyYAML python -m pytest -q Tools/HangboardPackages/tests
  rtk scripts/hangboard-packages.sh audit-metadata --root Hangboards --ledger docs/source-audits/2026-08-25-hangboard-metadata-ledger.json
  rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  rtk git diff --check
  rtk git status --short
  ```

  Expected: all tests and both commands pass, the report covers 44 boards, and only intended tracked changes remain.

- [ ] **Step 5: Commit, push, and prepare the final PR description.**

  Commit the final source-audit narrative and completeness test, push it, then write a PR description with: all six batch links/commits; full before/after field totals; official-source policy; review-only overlay locations; and every remaining blank grouped by manufacturer evidence gap.
