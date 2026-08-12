# Board Content Pipeline Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the evidence-backed board-content workflow, remove the unsuccessful programmatic image-generation workflow, and leave active documentation and automation aligned with the supported tools.

**Architecture:** `Hangboards/` remains the canonical board-content root, augmented by an evidence sidecar that the retained Python pipeline validates. The Python validator/exporter moves to `Tools/HangboardPipeline/`; the browser Workbench, macOS shell, and packaging move to `Tools/HangboardWorkbench/`. Retired image-catalog assets and tooling are deleted, while their plans and specifications move to `docs/history/tooling/experimental-image-catalog/`.

**Tech Stack:** Python 3.11, pytest, JavaScript node:test, SwiftPM/XCTest, shell scripts, GitHub Actions, JSON, Xcode.

## Global Constraints

- `Hangboards/catalog.json` and each `Hangboards/<board-id>/board.json` remain the sole canonical physical-board metadata source.
- Every canonical board package must contain a validated `evidence.json`; no evidence fact may be invented.
- The existing Compact II evidence must use only the three primary sources already recorded in `docs/ADDING_A_BOARD.md`, checked `2026-08-01`.
- Retain validation, catalog registration, generated board-library export, release checks, and human-reviewed Workbench operation.
- Retire `docs/hangboard-generative-catalog/`, its outline/flat/AI-v2 derivatives, `hangboard-catalog-flat`, `hangboard-catalog-outlines`, and `hangboard-to-svg --experimental-recess-detection`.
- Do not claim that a product photograph can programmatically generate faithful board artwork or authoritative hold geometry.
- Runtime app assets and Swift vector artwork remain under `HangTen/`; do not move them into `Hangboards/`.
- Retired plans/specifications remain accessible under `docs/history/tooling/` but must not be linked by active workflow guides.
- Use `git mv` for retained tools and historical documents; do not change Compact II hold facts, routine content, or Swift vector artwork.
- Keep `.context/` as the only workspace-owned transient output root.

---

## File structure after migration

```text
Hangboards/
  catalog.json
  metolius-wood-grips-compact-ii/
    board.json
    evidence.json

Tools/
  HangboardPipeline/                 # renamed from HangboardOnboarding
  HangboardWorkbench/                # renamed from hold-highlight-editor

docs/
  ADDING_A_BOARD.md
  history/tooling/experimental-image-catalog/
    plans/
    specs/
```

### Task 1: Require source evidence for every canonical board package

**Files:**
- Create: `Hangboards/metolius-wood-grips-compact-ii/evidence.json`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_catalog.py`
- Modify: `Tools/HangboardOnboarding/tests/test_board_catalog.py`
- Modify: `Tools/HangboardOnboarding/tests/test_board_catalog_cli.py`
- Modify: `Tools/HangboardOnboarding/tests/test_board_catalog_generation.py`

**Interfaces:**
- Consumes: `board.json` and a sibling `evidence.json` for every entry in `Hangboards/catalog.json`.
- Produces: `load_evidence(path: Path) -> BoardEvidenceDocument` and `validate_catalog(path: Path) -> CatalogDocument`, where validation rejects a missing, mismatched, malformed, or incompletely mapped evidence document.
- `evidence.json` schema version is `1` and contains `boardID`, `checkedAt`, `sources`, and `holdEvidence`.

- [ ] **Step 1: Write failing evidence-validation tests.**

  Add tests that copy the Compact II catalog fixture including `evidence.json`, then assert:

  ```python
  evidence_path = board_root / "evidence.json"
  evidence_path.unlink()
  with self.assertRaisesRegex(ValueError, r"evidence\.json does not exist"):
      module.validate_catalog(catalog_path)
  ```

  Add isolated mutations asserting failures for a mismatched `boardID`, a non-HTTPS source URL, a source ID referenced by `holdEvidence` but absent from `sources`, and one missing physical hold ID. Add one passing assertion that every Compact II hold ID has exactly `"hold-depth-diagram"` as its evidence mapping.

- [ ] **Step 2: Run the focused tests to verify the evidence contract is absent.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardOnboarding/tests/test_board_catalog.py Tools/HangboardOnboarding/tests/test_board_catalog_cli.py Tools/HangboardOnboarding/tests/test_board_catalog_generation.py -q
  ```

  Expected: the new evidence tests fail because `validate_catalog` does not load or validate `evidence.json`.

- [ ] **Step 3: Add the Compact II evidence document with recorded facts only.**

  Create `Hangboards/metolius-wood-grips-compact-ii/evidence.json` with this schema shape and exact sources:

  ```json
  {
    "schemaVersion": 1,
    "boardID": "metolius.wood-grips-compact-ii",
    "checkedAt": "2026-08-01",
    "sources": [
      {
        "id": "product-page",
        "title": "Metolius Wood Grips II Training Boards",
        "url": "https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards",
        "supports": ["identity", "dimensions", "front-geometry"]
      },
      {
        "id": "hold-depth-diagram",
        "title": "Metolius Wood Grips board depths",
        "url": "https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428",
        "supports": ["hold-depths", "hold-types", "hold-finger-capacity"]
      },
      {
        "id": "training-board-manual",
        "title": "Metolius Training Board Instructions",
        "url": "https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826",
        "supports": ["installation", "training-guidance"]
      }
    ],
    "holdEvidence": {
      "jug-left": ["hold-depth-diagram"],
      "jug-right": ["hold-depth-diagram"],
      "sloper-flat-left": ["hold-depth-diagram"],
      "sloper-round-center": ["hold-depth-diagram"],
      "sloper-flat-right": ["hold-depth-diagram"],
      "edge-29-left": ["hold-depth-diagram"],
      "pocket-29-three-left": ["hold-depth-diagram"],
      "pocket-29-two-left": ["hold-depth-diagram"],
      "pocket-29-four-center": ["hold-depth-diagram"],
      "pocket-29-two-right": ["hold-depth-diagram"],
      "pocket-29-three-right": ["hold-depth-diagram"],
      "edge-29-right": ["hold-depth-diagram"],
      "edge-19-left": ["hold-depth-diagram"],
      "pocket-19-three-left": ["hold-depth-diagram"],
      "pocket-19-two-left": ["hold-depth-diagram"],
      "pocket-19-four-center": ["hold-depth-diagram"],
      "pocket-19-two-right": ["hold-depth-diagram"],
      "pocket-19-three-right": ["hold-depth-diagram"],
      "edge-19-right": ["hold-depth-diagram"]
    }
  }
  ```

  Do not add inferred dimensions, hold claims, or synthetic source links.

- [ ] **Step 4: Implement strict sidecar validation.**

  In `board_catalog.py`, add immutable `EvidenceSource` and `BoardEvidenceDocument` dataclasses. Implement `load_evidence(path: Path) -> BoardEvidenceDocument` and validate these exact invariants:

  - `schemaVersion` is integer `1`.
  - `boardID` equals the sibling board’s `id`.
  - `checkedAt` is an ISO calendar date parsed by `datetime.date.fromisoformat`.
  - `sources` is a non-empty list with unique identifier-shaped IDs, non-empty titles, HTTPS URLs, and non-empty unique `supports` strings.
  - `holdEvidence` is an object whose keys equal the board hold-ID set exactly; every value is a non-empty list of unique source IDs defined in `sources`.

  Call `load_evidence(board_path.parent / "evidence.json")` from `validate_catalog` immediately after `load_board(board_path)`. Keep `BoardDocument.to_json()` unchanged: evidence is a sidecar, not app-runtime metadata.

- [ ] **Step 5: Update temporary catalog fixtures.**

  In each affected test helper that copies a `board.json` package, copy its sibling `evidence.json` into the same fixture root. Update expected diagnostics only where a missing evidence document is now the intentional subject of the test.

- [ ] **Step 6: Run focused validation and generated-library checks.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardOnboarding/tests/test_board_catalog.py Tools/HangboardOnboarding/tests/test_board_catalog_cli.py Tools/HangboardOnboarding/tests/test_board_catalog_generation.py -q
  python3 scripts/export-board-library.py --check
  ```

  Expected: all selected tests pass and the generated app board library is unchanged.

- [ ] **Step 7: Commit the evidence contract.**

  ```sh
  git add Hangboards/metolius-wood-grips-compact-ii/evidence.json Tools/HangboardOnboarding/src/hangboard_vectorizer/board_catalog.py Tools/HangboardOnboarding/tests/test_board_catalog.py Tools/HangboardOnboarding/tests/test_board_catalog_cli.py Tools/HangboardOnboarding/tests/test_board_catalog_generation.py
  git commit -m "feat: require board evidence sidecars"
  ```

### Task 2: Rename the supported pipeline and Workbench roots

**Files:**
- Move: `Tools/HangboardOnboarding/` to `Tools/HangboardPipeline/`
- Move: `Tools/hold-highlight-editor/` to `Tools/HangboardWorkbench/`
- Modify: `scripts/hangboard-tools.sh`
- Modify: `scripts/export-board-library.py`
- Modify: `.github/dependabot.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/codeql.yml`
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: the retained Python package at `Tools/HangboardPipeline/src/hangboard_vectorizer` and Workbench runtime at `Tools/HangboardWorkbench/`.
- Produces: the existing `scripts/hangboard-tools.sh` command surface except `convert`; all CI, CodeQL, Dependabot, release packaging, and generated-board export paths resolve the new roots.
- The temporary fixture remains `Tools/HangboardPipeline/boards/metolius-wood-grips-compact-ii/` until a later board-fixture separation is explicitly designed.

- [ ] **Step 1: Write path-contract tests before moving files.**

  In the existing shell/export and Workbench checkout-selection tests, add assertions that the active source layout is exactly:

  ```python
  root / "Tools" / "HangboardPipeline" / "src" / "hangboard_vectorizer"
  root / "Tools" / "HangboardWorkbench" / "server.py"
  root / "Tools" / "HangboardPipeline" / "boards"
  ```

  Assert that the legacy root names are not accepted by `validate_hang_ten_checkout` or `CheckoutSelection.validatedURL`.

- [ ] **Step 2: Run the new path-contract tests and verify the expected failure.**

  Run:

  ```sh
  python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py -q
  swift test --package-path Tools/hold-highlight-editor/macos
  ```

  Expected: tests fail because the old directories are still the active checkout markers.

- [ ] **Step 3: Move both supported tool roots with Git history.**

  ```sh
  git mv Tools/HangboardOnboarding Tools/HangboardPipeline
  git mv Tools/hold-highlight-editor Tools/HangboardWorkbench
  ```

  Do not rename the `hangboard_vectorizer` Python import package, `hangboard-workbench` executable, or `HangboardWorkbench` SwiftPM product; they are published internal interfaces.

- [ ] **Step 4: Update stable script and exporter paths.**

  In `scripts/hangboard-tools.sh`, set:

  ```bash
  tool_root="$repository_root/Tools/HangboardPipeline"
  ```

  Remove the `convert` command from `usage()` and its `hangboard-to-svg` case. In `scripts/export-board-library.py`, update `module_path` to `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`.

- [ ] **Step 5: Update automation and packaging paths atomically.**

  Replace all `Tools/HangboardOnboarding` references with `Tools/HangboardPipeline` and all `Tools/hold-highlight-editor` references with `Tools/HangboardWorkbench` in `.github/dependabot.yml`, CI, CodeQL, the Workbench release workflow, and `.gitignore`. Update packaging helpers, Workbench backend source discovery, macOS checkout selection, their Python/Swift tests, and test fixtures to use the same paths.

- [ ] **Step 6: Run supported-tool verification after the move.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_catalog_generation.py Tools/HangboardWorkbench/tests/test_server.py Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q
  node --test Tools/HangboardWorkbench/tests/workbench*.test.js
  swift test --package-path Tools/HangboardWorkbench/macos
  python3 scripts/export-board-library.py --check
  ```

  Expected: all commands pass with no reference to either legacy tool root.

- [ ] **Step 7: Commit the supported-tool relocation.**

  ```sh
  git add -A Tools scripts .github .gitignore
  git commit -m "refactor: consolidate board tools"
  ```

### Task 3: Remove unsupported programmatic image workflows

**Files:**
- Delete: `docs/hangboard-generative-catalog/`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_flat_illustrations.py`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_outline_cli.py`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_outlines.py`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_outline_sources.json`
- Delete: `Tools/HangboardPipeline/tests/test_catalog_flat_illustrations.py`
- Delete: `Tools/HangboardPipeline/tests/test_catalog_outline_catalog.py`
- Delete: `Tools/HangboardPipeline/tests/test_catalog_outlines.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/cli.py`
- Modify: `Tools/HangboardPipeline/tests/test_cli.py`
- Modify: `Tools/HangboardPipeline/pyproject.toml`
- Modify: `Tools/HangboardPipeline/README.md`
- Modify: `Tools/HangboardPipeline/TESTING.md`
- Modify: `Tools/HangboardPipeline/docs/validation/beastmaker-1000.md`
- Modify: `Tools/HangboardWorkbench/server.py`
- Modify: `Tools/HangboardWorkbench/README.md`
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`

**Interfaces:**
- Consumes: the supported `hangboard-catalog`, onboarding/review/promotion/release-check, and benchmark commands only.
- Produces: no source-tree catalog image mode, catalog-outline API routes, or photo-to-SVG command; Workbench startup supports repository-board workspaces and explicitly supplied reviewed run directories only.

- [ ] **Step 1: Write failing tests that forbid retired command registration and catalog mode.**

  Add tests asserting `Tools/HangboardPipeline/pyproject.toml` has no `hangboard-catalog-flat`, `hangboard-catalog-outlines`, or `hangboard-to-svg` entry point. Add Workbench CLI tests asserting these argument pairs are rejected by `argparse`:

  ```python
  ["--catalog-source-dir", "fixtures/images", "--catalog-outline-dir", "fixtures/outlines"]
  ["--catalog-source-dir", "fixtures/images"]
  ["--catalog-outline-dir", "fixtures/outlines"]
  ```

  Add a repository scan test that fails if a tracked supported file under `.github/`, `Tools/`, `scripts/`, `Hangboards/`, `README.md`, `AGENTS.md`, or `docs/ADDING_A_BOARD.md` contains `hangboard-generative-catalog`, `hangboard-catalog-flat`, `hangboard-catalog-outlines`, `hangboard-to-svg`, or `experimental-recess-detection`.

- [ ] **Step 2: Run the retirement tests to verify they fail against the current command surface.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_catalog_outlines.py Tools/HangboardWorkbench/tests/test_server.py -q
  ```

  Expected: the new assertions fail because the package and Workbench still expose the retired workflow.

- [ ] **Step 3: Remove the catalog assets, renderers, vectorizer, and experimental converter.**

  Delete the listed catalog directory, files, and tests. In `pyproject.toml`, retain only these console scripts:

  ```toml
  hangboard-catalog = "hangboard_vectorizer.board_catalog_cli:main"
  hangboard-onboard = "hangboard_vectorizer.onboard_cli:main"
  hangboard-release-check = "hangboard_vectorizer.release_check_cli:main"
  hangboard-promote = "hangboard_vectorizer.promotion_cli:main"
  hangboard-review = "hangboard_vectorizer.review_cli:main"
  hangboard-semantic-benchmark = "hangboard_vectorizer.semantic_benchmark:main"
  ```

  In `cli.py`, remove the `--experimental-recess-detection` flag, all detector thresholds, and every branch that accepts an unknown product. Make `--product` required, keep only the packaged known-product conversion path used by the accepted replay fixture, and change the parser program name from `hangboard-to-svg` to `known-product-replay`. Delete only the corresponding experimental test cases from `test_cli.py`; retain the known-product fixture tests. `product_render.py`, `export.py`, `templates.py`, and `beastmaker_replay.py` remain internal fixture support and have no console-script entry point.

- [ ] **Step 4: Remove catalog-outline mode from the Workbench server.**

  Remove `catalog_outline_path`, `catalog_source_dir`, and `catalog_outline_dir` from `EditorSession`; delete `CatalogSession`, `load_catalog`, `discover_catalog_outline_sessions`, `catalog_from_inputs`, catalog outline load/save helpers, catalog-region serialization, revision-token handling, the `--catalog` argument, and both catalog-source CLI arguments. The retained Workbench must start only from a repository root and an optional workspace root; it must not open an arbitrary historical artifact catalog.

- [ ] **Step 5: Rewrite operator documentation around evidence and human review.**

  In both tool READMEs, `TESTING.md`, and `docs/validation/beastmaker-1000.md`, remove product-photo conversion, catalog-outline, flat-preview, and automatic-detection instructions. State that the pipeline validates canonical metadata and supports review of source-backed runs; it does not generate trustworthy board images or runtime hold geometry from a photograph. Describe the remaining known-product render invocation only as an internal replay fixture, never as an onboarding command.

- [ ] **Step 6: Run the retired-workflow absence and retained-workflow tests.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
  node --test Tools/HangboardWorkbench/tests/workbench*.test.js
  python3 scripts/export-board-library.py --check
  rg -n 'hangboard-generative-catalog|hangboard-catalog-flat|hangboard-catalog-outlines|hangboard-to-svg|experimental-recess-detection' .github Tools scripts Hangboards README.md AGENTS.md docs/ADDING_A_BOARD.md
  ```

  Expected: both test suites and export check pass; `rg` returns exit status `1` with no matches.

- [ ] **Step 7: Commit the retirement.**

  ```sh
  git add -A docs/hangboard-generative-catalog Tools/HangboardPipeline Tools/HangboardWorkbench
  git commit -m "chore: retire unsupported board image tooling"
  ```

### Task 4: Move retired rationale and rewrite active repository guides

**Files:**
- Move: `docs/superpowers/plans/2026-08-08-hangboard-hold-outlines.md` to `docs/history/tooling/experimental-image-catalog/plans/2026-08-08-hangboard-hold-outlines.md`
- Move: `docs/superpowers/plans/2026-08-08-hardboard-hold-outlines.md` to `docs/history/tooling/experimental-image-catalog/plans/2026-08-08-hardboard-hold-outlines.md`
- Move: `docs/superpowers/plans/2026-08-09-ai-hangboard-illustrations-v2.md` to `docs/history/tooling/experimental-image-catalog/plans/2026-08-09-ai-hangboard-illustrations-v2.md`
- Move: `docs/superpowers/plans/2026-08-09-deterministic-flat-hangboard-previews.md` to `docs/history/tooling/experimental-image-catalog/plans/2026-08-09-deterministic-flat-hangboard-previews.md`
- Move: `docs/superpowers/plans/2026-08-09-flat-hangboard-illustrations.md` to `docs/history/tooling/experimental-image-catalog/plans/2026-08-09-flat-hangboard-illustrations.md`
- Move: `docs/superpowers/specs/2026-08-08-hardboard-hold-outlines-design.md` to `docs/history/tooling/experimental-image-catalog/specs/2026-08-08-hardboard-hold-outlines-design.md`
- Move: `docs/superpowers/specs/2026-08-09-ai-hangboard-illustrations-v2-design.md` to `docs/history/tooling/experimental-image-catalog/specs/2026-08-09-ai-hangboard-illustrations-v2-design.md`
- Move: `docs/superpowers/specs/2026-08-09-flat-hangboard-illustrations-design.md` to `docs/history/tooling/experimental-image-catalog/specs/2026-08-09-flat-hangboard-illustrations-design.md`
- Create: `docs/history/tooling/experimental-image-catalog/README.md`
- Modify: `README.md`
- Modify: `docs/ADDING_A_BOARD.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: the retained `scripts/hangboard-tools.sh` commands, `Hangboards/` package schema, evidence sidecar, and app export scripts.
- Produces: active documentation that gives only the supported workflow and a self-contained historical index explaining why the retired experiment exists in Git history rather than active tooling.

- [ ] **Step 1: Write documentation assertions before moving historical files.**

  Add a lightweight Python test in `Tools/HangboardPipeline/tests/test_documentation_paths.py` that reads `README.md` and `docs/ADDING_A_BOARD.md` and asserts:

  ```python
  assert "Tools/HangboardPipeline" in text
  assert "Tools/HangboardWorkbench" in text
  assert "evidence.json" in text
  assert "programmatically generate faithful board artwork" in text
  assert "hangboard-generative-catalog" not in text
  assert "hangboard-to-svg" not in text
  ```

- [ ] **Step 2: Run the documentation test and verify it fails before the rewrite.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_documentation_paths.py -q
  ```

  Expected: failure because the active guides still point to the old tool path and conversion workflow.

- [ ] **Step 3: Move the retired plans and specifications with history.**

  Create the destination directories, then use `git mv` for each of the eight listed files. Do not move `2026-08-11-board-content-pipeline-cleanup-design.md` or this implementation plan: they describe the active cleanup decision.

- [ ] **Step 4: Add a historical index.**

  Create `docs/history/tooling/experimental-image-catalog/README.md` with these three sections:

  ```markdown
  # Retired experimental image catalog

  ## Why it was retired
  The images were generated externally; local scripts only derived approximate outlines or simplified pixels and did not create faithful board artwork from manufacturer evidence.

  ## What remains supported
  Canonical board metadata, evidence validation, app export, and human-reviewed Workbench operations remain active. See ../../ADDING_A_BOARD.md.

  ## Records
  The plans and specifications here are historical rationale. The deleted generated PNGs remain recoverable from Git history.
  ```

- [ ] **Step 5: Rewrite active documentation and agent instructions.**

  Replace the old tool paths in `README.md` and `docs/ADDING_A_BOARD.md`. Add `evidence.json` to the board-package contract and direct contributors to the three Compact II sources only as evidence examples. Remove all generated-catalog, outline, flat-preview, and experimental-conversion text. State plainly: “The pipeline validates and exports source-backed board content; it does not programmatically generate faithful board artwork or authoritative hold geometry from a photograph.” Update `AGENTS.md` to point to `Tools/HangboardPipeline/` and require evidence sidecars for new board packages.

- [ ] **Step 6: Verify active documentation and moved history.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_documentation_paths.py -q
  test -f docs/history/tooling/experimental-image-catalog/README.md
  test -f docs/history/tooling/experimental-image-catalog/specs/2026-08-09-ai-hangboard-illustrations-v2-design.md
  test -f docs/history/tooling/experimental-image-catalog/plans/2026-08-09-flat-hangboard-illustrations.md
  rg -n 'hangboard-generative-catalog|hangboard-to-svg|experimental-recess-detection' README.md docs/ADDING_A_BOARD.md AGENTS.md
  ```

  Expected: the pytest and file checks pass; the final `rg` returns exit status `1` with no matches.

- [ ] **Step 7: Commit documentation and history cleanup.**

  ```sh
  git add README.md docs/ADDING_A_BOARD.md AGENTS.md docs/history docs/superpowers
  git commit -m "docs: clarify supported board content workflow"
  ```

### Task 5: Validate the consolidated repository and release paths

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `Tools/HangboardPipeline/tests/test_ci_workflow.py`
- Modify: `Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py`

**Interfaces:**
- Consumes: the consolidated tool paths, evidence sidecar contract, retained command surface, and active documentation.
- Produces: CI and release workflows that install, test, package, and validate only supported board tooling.

- [ ] **Step 1: Add workflow assertions for the final supported command/path surface.**

  Update the workflow tests to assert Python CI installs `Tools/HangboardPipeline[dev]`, Workbench release installs `Tools/HangboardPipeline` plus packages `Tools/HangboardWorkbench`, and neither workflow contains `HangboardOnboarding`, `hold-highlight-editor`, `hangboard-catalog-flat`, `hangboard-catalog-outlines`, or `hangboard-to-svg`.

- [ ] **Step 2: Run workflow tests to verify they catch stale paths.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_ci_workflow.py Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q
  ```

  Expected: failure until any remaining workflow path or assertion has been corrected.

- [ ] **Step 3: Correct the stale workflow paths and command assertions.**

  Replace every `Tools/HangboardOnboarding` path with `Tools/HangboardPipeline` and every `Tools/hold-highlight-editor` path with `Tools/HangboardWorkbench`. Remove any assertion or workflow step naming `hangboard-catalog-flat`, `hangboard-catalog-outlines`, or `hangboard-to-svg`. Do not add a compatibility alias for either retired root or command.

- [ ] **Step 4: Run the full repository validation set.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
  node --test Tools/HangboardWorkbench/tests/*.test.js
  swift test --package-path Tools/HangboardWorkbench/macos
  python3 scripts/export-board-library.py --check
  scripts/export-board-catalog.sh --check
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  git diff --check
  git status --short
  ```

  Expected: all test/build/export/catalog commands pass, `git diff --check` is silent, and `git status --short` contains only the intended cleanup changes before committing.

- [ ] **Step 5: Commit final integration fixes.**

  ```sh
  git add .github Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests
  git commit -m "ci: validate consolidated board tooling"
  ```

- [ ] **Step 6: Push the completed commit series.**

  ```sh
  git push
  ```

  Expected: the branch’s commits are accepted by its configured remote tracking branch.
