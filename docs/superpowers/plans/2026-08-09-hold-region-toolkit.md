# Hold-region Review Toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a solo-friendly set of independent tools that inspect, compare, lint, preview, accept, promote, and release-check hold-region artifacts without coupling those responsibilities into the editor.

**Architecture:** Add a small Python review package beside the existing onboarding package. Its modules communicate through explicit run artifacts and expose thin CLI entry points; the existing hold editor remains responsible for geometry editing and local save. Generate comparison and preview outputs as local, self-contained browser artifacts, and make promotion profile-driven, hash-bound, dry-run by default, and handoff-only when runtime integration is not configured.

**Tech Stack:** Python 3.11; existing `hangboard-vectorizer` package; standard-library `argparse`, `hashlib`, `json`, `pathlib`, `subprocess`, and `tempfile`; existing Pillow/OpenCV image tooling; dependency-free HTML/CSS/JavaScript; pytest; Node's built-in test runner.

## Global Constraints

- Keep generated Stage 1 and Stage 2 artifacts immutable; write edited regions, correction deltas, acceptance records, reports, and promotion packages separately.
- Require explicit `--run <path>` input and confine all run reads/writes to that run or an explicitly configured repository destination.
- Use SHA-256 hashes for every promotion input and output; any hash mismatch invalidates acceptance and promotion.
- Make `promote` dry-run by default; `--apply` must use an explicit destination profile and atomic replacement.
- Do not infer physical hold semantics, invent missing metadata, or generate Swift runtime geometry from pixels.
- Do not add network calls, hosted review, accounts, automatic git commit, git push, or direct App Store Connect upload.
- Keep product-specific behavior in data profiles or runtime integration adapters, never in generic editor/review logic.
- Store generated output under the run's owned `.context` area or another explicit workspace-owned path.
- Preserve unrelated existing worktree changes and stage only files belonging to the task being implemented.

## File and module map

Create these focused modules under `Tools/HangboardOnboarding/src/hangboard_vectorizer/`:

- `review_artifacts.py`: run discovery, artifact paths, JSON loading, SHA-256 hashing, derived review state, and atomic JSON writes.
- `review_lint.py`: immutable lint issue/report types, edited-document validation, and correction reconciliation against the automatic baseline.
- `review_acceptance.py`: hash-bound acceptance and rejection records.
- `review_preview.py`: deterministic image overlays and static review gallery generation.
- `review_cli.py`: thin `inspect`, `lint`, `preview`, and `accept` argument parsing and process-style exit codes.
- `promotion_profile.py`: version-1 runtime integration profile parsing and destination confinement.
- `promotion.py`: promotion report generation, handoff-required/blocked/ready state calculation, and atomic `--apply`.
- `promotion_cli.py`: thin `promote` argument parsing and output handling.
- `release_check.py`: repository-facing promotion checks and machine-readable release checklist.
- `release_check_cli.py`: thin `release-check` argument parsing and process-style exit codes.

Create these tests:

- `Tools/HangboardOnboarding/tests/test_review_artifacts.py`
- `Tools/HangboardOnboarding/tests/test_review_lint.py`
- `Tools/HangboardOnboarding/tests/test_review_acceptance.py`
- `Tools/HangboardOnboarding/tests/test_review_preview.py`
- `Tools/HangboardOnboarding/tests/test_review_cli.py`
- `Tools/HangboardOnboarding/tests/test_promotion.py`
- `Tools/HangboardOnboarding/tests/test_release_check.py`
- `Tools/HangboardOnboarding/tests/review_fixtures.py`: shared test-only run, image, region, acceptance, and promotion-profile builders used by every new Python test module.

Create these dependency-free comparison assets:

- `Tools/hold-highlight-editor/compare-model.js`: pure browser model for correction summaries and layer selection.
- `Tools/hold-highlight-editor/compare.html`: read-only comparison view.
- `Tools/hold-highlight-editor/compare.css`: comparison-only styles.
- `Tools/hold-highlight-editor/tests/compare_model.test.js`: Node tests for the pure comparison model.

Modify these integration files:

- `Tools/HangboardOnboarding/pyproject.toml`: register the three new Python entry points.
- `scripts/hangboard-tools.sh`: expose `inspect`, `compare`, `lint`, `preview`, `accept`, `promote`, and `release-check` through the existing local environment wrapper.
- `README.md`, `Tools/hold-highlight-editor/README.md`, and `docs/ADDING_A_BOARD.md`: document the commands, artifact files, state transitions, and promotion safety rules.

The existing `Tools/hold-highlight-editor/server.py` and editor save contract remain compatible. Do not move the editor's browser model into the Python package; the review toolkit reads the same JSON artifact contract independently.

---

### Task 1: Add the review artifact contract and `inspect`

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_artifacts.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py`
- Create: `Tools/HangboardOnboarding/tests/review_fixtures.py`
- Create: `Tools/HangboardOnboarding/tests/test_review_artifacts.py`
- Create: `Tools/HangboardOnboarding/tests/test_review_cli.py`
- Modify: `Tools/HangboardOnboarding/pyproject.toml`
- Modify: `scripts/hangboard-tools.sh`

**Interfaces:**
- `ReviewRun` is a frozen dataclass containing `root`, `stage1_image`, `stage2_regions`, `edited_regions`, `corrections`, `lint_report`, `acceptance`, and `promotion_report` paths; optional paths are `None` when absent.
- `discover_review_run(root: Path) -> ReviewRun` requires exactly one `stage-1-auto-rgba.png` and one `stage-2-regions.json` under `root`, and rejects missing/ambiguous files.
- `sha256_file(path: Path) -> str` returns the lowercase 64-character SHA-256 digest of the exact file bytes.
- `load_json(path: Path, label: str) -> dict[str, object]` rejects missing, invalid, non-object JSON with a path-specific `ValueError`.
- `review_state(run: ReviewRun) -> str` returns one of `automatic`, `edited`, `lint-passed`, `accepted`, or `promoted` based on present artifacts; `lint-passed` requires a persisted report whose `passed` field is true, and hash validity is checked by later commands.
- `inspect_run(run: ReviewRun) -> dict[str, object]` returns JSON-safe paths relative to `run.root`, file hashes for present artifacts, the derived state, and the next action.
- `review_cli.main(argv: Sequence[str] | None = None) -> int` supports `inspect --run PATH --json` and prints a compact JSON object on success.
- `review_fixtures.make_review_run(root: Path) -> Path` creates a valid fixture with a real 32×16 RGBA PNG, one baseline region document, and no edited artifact.
- `review_fixtures.make_review_run_with_edit(root: Path, mutate_edited: Callable[[dict[str, object]], None] | None = None, mutate_corrections: bool = False) -> Path` creates the fixture plus edited and correction documents, applying the optional mutation before serialization.

- [ ] **Step 1: Write failing artifact-discovery and hashing tests.**

```python
def test_discover_review_run_requires_one_stage_image_and_region_document(tmp_path):
    run = make_review_run(tmp_path)
    discovered = discover_review_run(run)
    assert discovered.stage1_image.name == "stage-1-auto-rgba.png"
    assert discovered.stage2_regions.name == "stage-2-regions.json"
    assert discovered.edited_regions is None


def test_discover_review_run_rejects_ambiguous_stage_two_documents(tmp_path):
    run = make_review_run(tmp_path)
    duplicate = run / "stages/02/attempt-0002/stage-2-regions.json"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one stage-2-regions.json"):
        discover_review_run(run)


def test_sha256_file_hashes_exact_bytes(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_bytes(b"artifact")
    assert sha256_file(path) == hashlib.sha256(b"artifact").hexdigest()
```

- [ ] **Step 2: Run the focused tests and verify they fail for missing symbols.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_review_artifacts.py -q`

Expected: FAIL because `review_artifacts.py` and the fixture builders do not exist yet.

- [ ] **Step 3: Add the shared test fixture builders and implement confined discovery and derived state.**

In `review_fixtures.py`, implement only `make_review_run` and `make_review_run_with_edit` in this task. Use Pillow to write the 32×16 RGBA PNG and use these exact region documents: canvas `{width: 32, height: 16}`; baseline region ID `1`, key `left`, type `edge`, mode `surface`, and contour `[[3, 3], [12, 3], [12, 8], [3, 8]]`; edited region ID `1` with contour `[[3, 3], [13, 3], [12, 8], [3, 8]]`; added region ID `2`, key `right`, type `pocket`, mode `aperture`, and contour `[[18, 3], [27, 3], [27, 8], [18, 8]]`. Serialize corrections with `schemaVersion: 1`, a one-item `modified` list, and empty `added`/`deleted` lists. Each helper must return the run root rather than a mutable global.

In `review_artifacts.py`, use `Path.rglob`, require exactly one generated image/document, resolve every discovered path, and only accept optional review files in the same Stage 2 artifact directory. Recognize these exact optional names: `stage-2-regions.edited.json`, `stage-2-human-corrections.json`, `lint-report.json`, `stage-2-review-acceptance.json`, and `board-promotion-report.json`. Reject a run root that is not a directory.

- [ ] **Step 4: Add the inspect CLI and wrapper entry point.**

Register:

```toml
hangboard-review = "hangboard_vectorizer.review_cli:main"
```

Make `review_cli.main(["inspect", "--run", str(run)])` return `0` and print an object containing `state`, `nextAction`, relative artifact paths, and hashes. Add only the `inspect` dispatch to `scripts/hangboard-tools.sh` in this task; later tasks add their own commands. Return `2` for invalid arguments and `3` for filesystem or artifact errors, matching `onboard_cli.py`.

- [ ] **Step 5: Run the focused tests and commit the task.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_review_artifacts.py tests/test_review_cli.py -q`

Expected: PASS.

Commit only the task files:

```bash
git add Tools/HangboardOnboarding/src/hangboard_vectorizer/review_artifacts.py Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py Tools/HangboardOnboarding/tests/test_review_artifacts.py Tools/HangboardOnboarding/tests/test_review_cli.py Tools/HangboardOnboarding/pyproject.toml scripts/hangboard-tools.sh
git commit -m "feat: inspect hold-region review artifacts"
```

### Task 2: Implement linting and hash-bound acceptance

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_lint.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_acceptance.py`
- Create: `Tools/HangboardOnboarding/tests/test_review_lint.py`
- Create: `Tools/HangboardOnboarding/tests/test_review_acceptance.py`
- Modify: `Tools/HangboardOnboarding/tests/review_fixtures.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py`

**Interfaces:**
- `LintIssue` is a frozen dataclass with `severity: Literal["error", "warning"]`, `code: str`, `path: str`, and `message: str`.
- `LintReport` is a frozen dataclass with `passed: bool`, `issues: tuple[LintIssue, ...]`, `baseline_sha256: str`, and `edited_sha256: str`.
- `lint_review(run: ReviewRun, profile: Mapping[str, object] | None = None) -> LintReport` validates the edited document and correction delta against the generated baseline.
- `write_lint_report(run: ReviewRun, report: LintReport) -> Path` atomically writes `lint-report.json` beside the edited artifact and returns its path.
- `AcceptanceRecord` is a frozen dataclass serializing `schemaVersion`, `decision`, `reviewer`, `reviewedAt`, `source`, `toolVersion`, and `notes`.
- `write_acceptance(run: ReviewRun, decision: Literal["accepted", "rejected"], reviewer: str, notes: str, now: datetime | None = None) -> Path` requires a current lint pass for acceptance and atomically writes `stage-2-review-acceptance.json` beside the edited artifact.
- `validate_acceptance(run: ReviewRun) -> AcceptanceRecord` verifies every recorded source hash before returning the record.
- `review_fixtures.make_review_run_with_edit_and_acceptance(root: Path) -> Path` creates the edited fixture and writes a current accepted record through `write_acceptance`.

- [ ] **Step 1: Write failing geometry and correction-reconciliation tests.**

Cover these exact cases:

```python
def test_lint_accepts_valid_edited_regions_and_matching_delta(tmp_path):
    run = make_review_run_with_edit(tmp_path)
    report = lint_review(discover_review_run(run))
    assert report.passed is True
    assert report.issues == ()


@pytest.mark.parametrize("mutation, code", [
    (lambda doc: doc["canvas"].update(width=0), "canvas.width-positive"),
    (lambda doc: doc["regions"][0].update(contour=[[1, 2], [3, 4]]), "contour.min-points"),
    (lambda doc: doc["regions"][0]["contour"][0].__setitem__(0, -1), "contour.out-of-bounds"),
])
def test_lint_reports_specific_geometry_failures(tmp_path, mutation, code):
    run = make_review_run_with_edit(tmp_path, mutate_edited=mutation)
    report = lint_review(discover_review_run(run))
    assert report.passed is False
    assert any(issue.code == code for issue in report.issues)


def test_lint_rejects_modified_delta_that_does_not_match_baseline(tmp_path):
    run = make_review_run_with_edit(tmp_path, mutate_corrections=True)
    report = lint_review(discover_review_run(run))
    assert any(issue.code == "corrections.modified-mismatch" for issue in report.issues)
```

- [ ] **Step 2: Run the focused lint tests and verify failure.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_review_lint.py -q`

Expected: FAIL because the lint report and validator are not implemented.

- [ ] **Step 3: Implement the lint contract.**

Validate positive finite canvas dimensions; each region must have an integer ID unique within the document, a non-empty key, a recognized type from `pocket`, `edge`, `sloper`, or `jug`, a recognized mode from `aperture` or `surface`, at least three finite points, positive shoelace area, and every point inside the canvas. Compare added/modified/deleted correction entries by region ID and canonical JSON bytes against the baseline and edited documents. Emit all independent issues in stable `(severity, code, path)` order.

- [ ] **Step 4: Write failing acceptance and invalidation tests.**

```python
def test_acceptance_records_hashes_and_is_atomic(tmp_path):
    run = make_review_run_with_edit(tmp_path)
    path = write_acceptance(discover_review_run(run), "accepted", "asher", "Reviewed all regions")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["decision"] == "accepted"
    assert document["source"]["editedSha256"] == sha256_file(run / "stages/02/attempt-0001/stage-2-regions.edited.json")


def test_validate_acceptance_rejects_changed_edited_artifact(tmp_path):
    run = make_review_run_with_edit(tmp_path)
    write_acceptance(discover_review_run(run), "accepted", "asher", "Reviewed")
    edited = run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="edited artifact hash changed"):
        validate_acceptance(discover_review_run(run))
```

- [ ] **Step 5: Implement acceptance, wire CLI commands, test, and commit.**

Use UTC ISO-8601 timestamps, default the CLI reviewer to `local-user`, require `accept` to run lint first, and write through a temporary file in the Stage 2 directory followed by `Path.replace`. Every `lint` invocation writes `lint-report.json` before returning, including failing reports. `reject` may record a rejected decision without a lint pass but still records all present artifact hashes. Extend `review_fixtures.py` with `make_review_run_with_edit_and_acceptance` and route it through `write_acceptance`; do not hand-write acceptance JSON in a fixture. Add `lint --run PATH --json` and `accept --run PATH --decision accepted|rejected --reviewer NAME --notes TEXT` to `review_cli.py`.

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_review_lint.py tests/test_review_acceptance.py tests/test_review_cli.py -q`

Expected: PASS.

Commit:

```bash
git add Tools/HangboardOnboarding/src/hangboard_vectorizer/review_lint.py Tools/HangboardOnboarding/src/hangboard_vectorizer/review_acceptance.py Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py Tools/HangboardOnboarding/tests/test_review_lint.py Tools/HangboardOnboarding/tests/test_review_acceptance.py Tools/HangboardOnboarding/tests/test_review_cli.py
git commit -m "feat: lint and accept hold-region reviews"
```

### Task 3: Add deterministic previews and a read-only comparison viewer

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_preview.py`
- Create: `Tools/HangboardOnboarding/tests/test_review_preview.py`
- Create: `Tools/hold-highlight-editor/compare-model.js`
- Create: `Tools/hold-highlight-editor/compare.html`
- Create: `Tools/hold-highlight-editor/compare.css`
- Create: `Tools/hold-highlight-editor/tests/compare_model.test.js`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py`

**Interfaces:**
- `render_preview_bundle(run: ReviewRun, output: Path) -> dict[str, object]` writes a deterministic `review-preview/` directory containing `normal.png`, `automatic.png`, `edited.png`, `all-highlighted.png`, one PNG per grip type present, and `review-gallery.html`.
- `build_comparison_document(run: ReviewRun) -> str` returns a self-contained HTML document with the Stage 1 image encoded as a data URL, automatic/edited region JSON embedded as inert data, and the SHA-256 values displayed in the metadata panel.
- Browser `HoldComparisonModel.buildSummary(baseline, edited, corrections)` returns `{added, modified, deleted, unchanged}` arrays sorted by numeric region ID.
- Browser `HoldComparisonModel.visibleLayers(mode)` returns the exact layer names for `image`, `automatic`, `edited`, and `difference` modes.

- [ ] **Step 1: Write failing preview and browser-model tests.**

```python
def test_preview_bundle_is_deterministic_and_records_edited_hash(tmp_path):
    run = make_review_run_with_edit(tmp_path)
    first = render_preview_bundle(discover_review_run(run), tmp_path / "first")
    second = render_preview_bundle(discover_review_run(run), tmp_path / "second")
    assert first["editedSha256"] == second["editedSha256"]
    assert (tmp_path / "first/review-preview/edited.png").read_bytes() == (tmp_path / "second/review-preview/edited.png").read_bytes()
    assert (tmp_path / "first/review-preview/review-gallery.html").is_file()
```

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { buildSummary } from "../compare-model.js";

test("comparison summary separates added, modified, deleted, and unchanged regions", () => {
  const baseline = [{ id: 1, key: "left", contour: [[0, 0], [5, 0], [5, 5]] }];
  const edited = [
    { id: 1, key: "left", contour: [[0, 0], [6, 0], [5, 5]] },
    { id: 2, key: "right", contour: [[8, 0], [9, 0], [9, 1]] },
  ];
  assert.deepEqual(buildSummary(baseline, edited), {
    added: [2], modified: [1], deleted: [], unchanged: [],
  });
});
```

- [ ] **Step 2: Run both focused tests and verify failure.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_review_preview.py -q`

Run: `node --test Tools/hold-highlight-editor/tests/compare_model.test.js`

Expected: FAIL because the preview renderer and comparison model do not exist.

- [ ] **Step 3: Implement deterministic Pillow previews.**

Load the Stage 1 RGBA image, draw baseline and edited contours with stable type colors, and save the exact named PNGs. Use the same colors as `app.js`: jug `#ff754f`, sloper `#32bbc1`, edge `#9a6cf2`, pocket `#ee4d97`. Render the gallery with relative image paths, run hashes, and a summary table. Write through a temporary output directory and replace only after all files are complete.

- [ ] **Step 4: Implement the self-contained comparison document and browser model.**

The generated HTML must render without a server by embedding the image data URL and JSON payload. Provide image-only, automatic-only, edited-only, and difference modes; opacity control; side-by-side toggle; fit/zoom controls; selected-region focus; and a correction summary. Do not include Save, Add, Delete, or any mutating editor control.

- [ ] **Step 5: Wire `preview` and `compare`, test, and commit.**

Add `preview --run PATH --output PATH` and `compare --run PATH --output PATH` to `review_cli.py`. `compare` prints the absolute generated HTML path and returns `2` when no edited artifact exists. `preview` returns `3` for invalid image or region data.

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_review_preview.py tests/test_review_cli.py -q`

Run: `node --test Tools/hold-highlight-editor/tests/compare_model.test.js`

Expected: PASS.

Commit:

```bash
git add Tools/HangboardOnboarding/src/hangboard_vectorizer/review_preview.py Tools/HangboardOnboarding/tests/test_review_preview.py Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py Tools/hold-highlight-editor/compare-model.js Tools/hold-highlight-editor/compare.html Tools/hold-highlight-editor/compare.css Tools/hold-highlight-editor/tests/compare_model.test.js
git commit -m "feat: add hold-region previews and comparison viewer"
```

### Task 4: Add profile-driven promotion and safe apply

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion_profile.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion_cli.py`
- Create: `Tools/HangboardOnboarding/tests/test_promotion.py`
- Modify: `Tools/HangboardOnboarding/tests/review_fixtures.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_artifacts.py`

**Interfaces:**
- `PromotionProfile` is a frozen dataclass with `schema_version: int`, `profile_id: str`, `board_id: str`, `required_region_keys: tuple[str, ...]`, `runtime_mappings: tuple[RuntimeMapping, ...]`, and `destinations: tuple[Destination, ...]`.
- `RuntimeMapping` contains `region_key: str`, `runtime_hold_id: str`, `grip_type: str`, `interaction_mode: str`, and optional `notes: str`.
- `Destination` contains `source_relative: str` and `destination_relative: str`; destination paths are resolved under the configured repository root and may not escape it.
- `load_promotion_profile(path: Path) -> PromotionProfile` requires JSON `schemaVersion: 1`, non-empty IDs, unique region/runtime IDs, and normalized relative destination paths.
- `PromotionReport` serializes `schemaVersion`, `status`, `profileId`, `boardId`, `inputHashes`, `outputHashes`, `plannedWrites`, `warnings`, and `errors`.
- `promote_run(run: ReviewRun, profile: PromotionProfile | None, repository_root: Path, *, apply: bool = False) -> PromotionReport` requires current acceptance, reruns lint, creates `promotion/` outputs under the run, and returns `handoff-required` when `profile is None`.
- `review_fixtures.make_profile(root: Path, destination_relative: str = "canonical/board.json") -> Path` writes a valid version-1 profile fixture with one required region mapping and one confined destination.
- `review_fixtures.make_review_run_with_blocked_promotion(root: Path) -> Path` creates an accepted fixture and then changes its edited JSON so promotion is blocked.
- `review_fixtures.make_review_run_with_ready_promotion(root: Path) -> Path` creates an accepted fixture, writes a valid profile, and applies a ready dry-run report for release-check tests.

- [ ] **Step 1: Write failing profile and promotion-state tests.**

```python
def test_promote_without_runtime_profile_returns_handoff_required(tmp_path):
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    report = promote_run(discover_review_run(run), None, tmp_path / "repo")
    assert report.status == "handoff-required"
    assert (run / "stages/02/attempt-0001/promotion/board-promotion-report.json").is_file()


def test_promote_blocks_changed_artifact_after_acceptance(tmp_path):
    run = make_review_run_with_edit_and_acceptance(tmp_path / "run")
    edited = run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report = promote_run(discover_review_run(run), None, tmp_path / "repo")
    assert report.status == "blocked"
    assert any("hash" in error for error in report.errors)


def test_apply_rejects_destination_outside_repository_root(tmp_path):
    profile = make_profile(tmp_path, destination_relative="../../outside.json")
    with pytest.raises(ValueError, match="outside repository root"):
        load_promotion_profile(profile)
```

- [ ] **Step 2: Run focused promotion tests and verify failure.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_promotion.py -q`

Expected: FAIL because profile and promotion types are not implemented.

- [ ] **Step 3: Implement profile parsing and destination confinement.**

Parse only version 1. Require every `required_region_keys` value to be unique and every runtime mapping to name an existing required key. Resolve destination paths with `Path.resolve(strict=False)` and require `relative_to(repository_root.resolve())` before any write. Do not accept absolute destination paths.

- [ ] **Step 4: Implement hash-bound promotion reports and handoff packages.**

Call `validate_acceptance` and `lint_review` before writing outputs. Always write a machine-readable report and a copied `promotion/edited-regions.json` with its hash. If no profile is supplied, include `handoffRequired: true` and return `handoff-required`; if a profile is supplied but a required region mapping is missing, return `blocked`; if all mappings pass, return `ready` in dry-run mode. Include `plannedWrites` without touching repository destinations during dry run.

- [ ] **Step 5: Implement atomic `--apply`, wire CLI, test, and commit.**

For `--apply`, require a profile, create each destination parent, copy only the explicitly listed package files through a temporary sibling file and `Path.replace`, and include the final output hashes in the report. Never delete destination files and never modify Stage 1/Stage 2 generated files. Add `promote --run PATH --profile PATH --repository-root PATH [--apply]` to `promotion_cli.py`.

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_promotion.py tests/test_review_acceptance.py -q`

Expected: PASS.

Register `hangboard-promote = "hangboard_vectorizer.promotion_cli:main"` in `pyproject.toml` and add only the `promote` dispatch to `scripts/hangboard-tools.sh` in this task. The wrapper must not advertise `release-check` until Task 5 creates that entry point.

Commit:

```bash
git add Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion_profile.py Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion.py Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion_cli.py Tools/HangboardOnboarding/src/hangboard_vectorizer/review_artifacts.py Tools/HangboardOnboarding/tests/test_promotion.py
git commit -m "feat: add safe hold-region promotion"
```

### Task 5: Add repository-facing `release-check`

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/release_check.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/release_check_cli.py`
- Create: `Tools/HangboardOnboarding/tests/test_release_check.py`
- Modify: `Tools/HangboardOnboarding/pyproject.toml`
- Modify: `scripts/hangboard-tools.sh`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion.py`

**Interfaces:**
- `ReleaseCheckResult` is a frozen dataclass with `name: str`, `passed: bool`, `command: tuple[str, ...]`, `output: str`, and `error: str | None`.
- `run_release_check(run: ReviewRun, repository_root: Path, *, run_xcode: bool = False) -> tuple[ReleaseCheckResult, ...]` checks promotion report status, configured destination files, `scripts/export-plan-library.sh --check`, and optionally the shared `HangTen` XCTest command.
- `release_check_report(results: tuple[ReleaseCheckResult, ...]) -> dict[str, object]` returns `passed`, `checks`, and UTC `generatedAt` fields.
- `release_check_cli.main(argv: Sequence[str] | None = None) -> int` supports `release-check --run PATH --repository-root PATH [--xcode] --json`.

- [ ] **Step 1: Write failing release-check tests.**

```python
def test_release_check_fails_when_promotion_is_blocked(tmp_path):
    run = make_review_run_with_blocked_promotion(tmp_path / "run")
    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)
    assert results[0].name == "promotion-status"
    assert results[0].passed is False


def test_release_check_runs_export_check_with_repository_root(tmp_path, monkeypatch):
    run = make_review_run_with_ready_promotion(tmp_path / "run")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append(command) or subprocess.CompletedProcess(command, 0, "ok", ""))
    results = run_release_check(discover_review_run(run), tmp_path, run_xcode=False)
    assert any(command[-2:] == ("export-plan-library.sh", "--check") for command in calls)
    assert all(result.passed for result in results)
```

- [ ] **Step 2: Run the focused tests and verify failure.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_release_check.py -q`

Expected: FAIL because the release-check module is not implemented.

- [ ] **Step 3: Implement deterministic repository checks.**

Run the export check with `cwd=repository_root`, `check=True` behavior represented in the result, and captured text output. When `--xcode` is present, run the exact existing simulator test command with `CODE_SIGNING_ALLOWED=NO`, `CODE_SIGNING_REQUIRED=NO`, a run-local `.context/release-check-derived-data` path, and a unique simulator destination chosen by the existing isolated validation guide. Do not create or delete a simulator unless `--xcode` is requested.

- [ ] **Step 4: Wire the CLI, wrapper, test, and commit.**

Register `hangboard-release-check = "hangboard_vectorizer.release_check_cli:main"` in `pyproject.toml` and add the `release-check` dispatch to `scripts/hangboard-tools.sh`. Return `0` only when every check passes; return `3` when a check fails; return `2` for invalid arguments. Write `release-check.json` under the run's `promotion/` directory only after all checks have been collected.

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_release_check.py tests/test_promotion.py -q`

Expected: PASS.

Commit:

```bash
git add Tools/HangboardOnboarding/src/hangboard_vectorizer/release_check.py Tools/HangboardOnboarding/src/hangboard_vectorizer/release_check_cli.py Tools/HangboardOnboarding/tests/test_release_check.py Tools/HangboardOnboarding/src/hangboard_vectorizer/promotion.py
git commit -m "feat: add board release checks"
```

### Task 6: Complete wrapper integration, documentation, and end-to-end verification

**Files:**
- Modify: `Tools/HangboardOnboarding/pyproject.toml`
- Modify: `scripts/hangboard-tools.sh`
- Modify: `README.md`
- Modify: `Tools/hold-highlight-editor/README.md`
- Modify: `docs/ADDING_A_BOARD.md`
- Create: `Tools/HangboardOnboarding/tests/test_review_workflow.py`

- [ ] **Step 1: Write the fixture-based end-to-end test.**

```python
def test_complete_solo_review_workflow(tmp_path):
    run = make_review_run_with_edit(tmp_path / "run")
    discovered = discover_review_run(run)
    assert review_cli.main(["inspect", "--run", str(run)]) == 0
    assert review_cli.main(["lint", "--run", str(run)]) == 0
    assert review_cli.main(["preview", "--run", str(run), "--output", str(tmp_path / "preview")]) == 0
    assert review_cli.main(["accept", "--run", str(run), "--decision", "accepted", "--reviewer", "local-user", "--notes", "Reviewed fixture"]) == 0
    report = promote_run(discovered, None, tmp_path / "repo")
    assert report.status == "handoff-required"
    assert validate_acceptance(discover_review_run(run)).decision == "accepted"
```

- [ ] **Step 2: Run the end-to-end test and verify failure before wrapper/docs work is complete.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest tests/test_review_workflow.py -q`

Expected: PASS after the command interfaces from Tasks 1–5 are present; any wrapper or documentation omissions remain visible in the subsequent shell checks.

- [ ] **Step 3: Add all wrapper subcommands with explicit usage text.**

The wrapper dispatches as follows:

```text
inspect         hangboard-review inspect
compare         hangboard-review compare
lint            hangboard-review lint
preview         hangboard-review preview
accept          hangboard-review accept
promote         hangboard-promote
release-check   hangboard-release-check
```

Keep the existing `onboard`, `benchmark`, and `convert` behavior unchanged. The wrapper must continue using the workspace-local virtual environment and must not install a global package.

- [ ] **Step 4: Document the exact solo workflow and safety boundaries.**

Add a README section with these commands:

```sh
scripts/hangboard-tools.sh inspect --run .context/hangboard-onboarding/example
scripts/hangboard-tools.sh compare --run .context/hangboard-onboarding/example --output .context/compare.html
scripts/hangboard-tools.sh lint --run .context/hangboard-onboarding/example
scripts/hangboard-tools.sh preview --run .context/hangboard-onboarding/example --output .context/preview
scripts/hangboard-tools.sh accept --run .context/hangboard-onboarding/example --decision accepted --reviewer local-user --notes "Reviewed all holds"
scripts/hangboard-tools.sh promote --run .context/hangboard-onboarding/example --repository-root "$PWD"
scripts/hangboard-tools.sh release-check --run .context/hangboard-onboarding/example --repository-root "$PWD"
```

Explain that `promote` is dry-run by default, `--apply` requires an explicit profile, and `handoff-required` is an intentional result when runtime Swift integration has not been configured.

- [ ] **Step 5: Run all verification commands and commit the integration task.**

Run: `cd Tools/HangboardOnboarding && python3 -m pytest -q`

Run: `node --test Tools/hold-highlight-editor/tests/editor_model.test.js Tools/hold-highlight-editor/tests/compare_model.test.js`

Run: `scripts/hangboard-tools.sh --help`

Run: `scripts/hangboard-tools.sh inspect --run .context/hangboard-onboarding/fixture-run` and confirm the output includes `state`, `nextAction`, and SHA-256 hashes.

Run: `rtk git diff --check`

Expected: all Python and Node tests pass, wrapper help lists every command, fixture inspect succeeds, and the diff check is clean.

Commit only the integration files:

```bash
git add Tools/HangboardOnboarding/pyproject.toml scripts/hangboard-tools.sh README.md Tools/hold-highlight-editor/README.md docs/ADDING_A_BOARD.md Tools/HangboardOnboarding/tests/test_review_workflow.py
git commit -m "docs: document hold-region promotion workflow"
```

## Execution order and review checkpoints

Implement Tasks 1–6 in order. Each task has its own tests and commit. After
Task 3, review the generated comparison/preview artifacts visually. After
Task 4, verify that a dry-run cannot modify the repository and that a missing
runtime profile returns `handoff-required`. After Task 6, run the full test
suite and the isolated simulator validation before calling the toolkit ready.

## Plan self-review

- Spec coverage: artifact discovery and inspect are Task 1; lint and acceptance are Task 2; comparison and previews are Task 3; profile-driven promotion and safe apply are Task 4; repository release checks are Task 5; wrapper, docs, and end-to-end verification are Task 6.
- Vagueness scan: no step depends on an unnamed future component, an unspecified destination, or an unbounded validation. The runtime profile is an explicit version-1 JSON input, and absence of that input has the defined `handoff-required` result.
- Type consistency: `ReviewRun` is produced by `discover_review_run` and consumed by lint, acceptance, preview, promotion, and release-check; `PromotionProfile` is produced by `load_promotion_profile` and consumed by `promote_run`; `PromotionReport` is the status input for release-check.
- Scope: the editor remains unchanged except for a read-only comparison viewer, and App Store Connect automation remains outside this plan because the current GitHub Actions release workflow already owns it.
