# Hangboard Canonical Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a repository-owned Compact II board package authoritative for board facts and hold IDs, register in-progress onboarding runs there, and generate the iOS board catalog from it.

**Architecture:** `Hangboards/catalog.json` indexes board packages. Each package has a validated `board.json` containing lifecycle, provenance, and stable hold metadata, plus registered onboarding runs. Python tooling validates/packages these artifacts and generates Swift source. iOS keeps `BoardDesign` for exact rendering but consumes the generated metadata catalog.

**Tech Stack:** Python 3.11 standard library plus the existing onboarding package; Swift/XCTest; shell scripts; JSON.

## Global Constraints

- The first migration covers only Metolius Wood Grips Compact II.
- Lifecycle states are exactly `draft`, `onboarding`, `approved`, and `shipped`.
- Stable hold IDs use the existing iOS IDs such as `jug-left` and `pocket-29-two-left`.
- Onboarding numeric region IDs are provenance mappings and do not replace stable hold IDs.
- Temporary onboarding output remains under `.context`; registration copies runs into the board package.
- Exact Swift `BoardDesign` path commands remain renderer implementation details.
- Existing user changes in `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outline_sources.json` and `Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py` must not be modified.
- Every production behavior change gets a test written and observed failing before implementation.

---

### Task 1: Canonical board package and catalog tooling

**Files:**
- Create: `Hangboards/catalog.json`
- Create: `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_catalog.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_catalog_cli.py`
- Modify: `Tools/HangboardOnboarding/pyproject.toml`
- Modify: `scripts/hangboard-tools.sh`
- Test: `Tools/HangboardOnboarding/tests/test_board_catalog.py`

**Interfaces:**
- `load_catalog(path: Path) -> CatalogDocument`
- `load_board(path: Path) -> BoardDocument`
- `validate_catalog(path: Path) -> CatalogDocument`
- `register_run(catalog_path: Path, board_id: str, run_path: Path, run_id: str | None = None) -> BoardDocument`
- CLI commands: `hangboard-catalog validate --catalog <path>`, `hangboard-catalog register --catalog <path> --board <id> --run <path>`, and `hangboard-catalog status --catalog <path>`.

- [ ] **Step 1: Write failing validation and registration tests.**
- [ ] **Step 2: Run `rtk python3 -m unittest ...` and verify the new tests fail because the catalog module and files do not exist.**
- [ ] **Step 3: Add the JSON documents, typed Python loaders, validation, confined run registration, CLI entry point, and shell dispatch.**
- [ ] **Step 4: Run the focused tests and verify valid Compact II data, rejected duplicate/escaping data, correct lifecycle derivation, and copied run artifacts.**
- [ ] **Step 5: Commit the task with `feat: add canonical hangboard package`.**

### Task 2: Generate the iOS board catalog from JSON

**Files:**
- Create: `scripts/export-board-catalog.py`
- Create: `scripts/export-board-catalog.sh`
- Create: `HangTen/Models/GeneratedBoardCatalog.swift`
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Test: `Tools/HangboardOnboarding/tests/test_board_catalog_generation.py`

**Interfaces:**
- `render_swift_catalog(board: BoardDocument) -> str`
- `export_swift_catalog(catalog_path: Path, output_path: Path, check: bool = False) -> None`
- Shell usage: `scripts/export-board-catalog.sh` regenerates; `scripts/export-board-catalog.sh --check` fails on drift.

- [ ] **Step 1: Write failing tests asserting generated Swift contains the Compact II ID, all 19 stable hold IDs, and `--check` detects drift.**
- [ ] **Step 2: Run the focused tests and verify they fail before the generator exists.**
- [ ] **Step 3: Implement deterministic Swift rendering and generate `GeneratedBoardCatalog.swift`.**
- [ ] **Step 4: Remove the hand-authored `BoardCatalog` inventory from `TrainingModels.swift`, add the generated source to the Xcode project, and preserve the existing `BoardCatalog.all`/`board(for:)` API.**
- [ ] **Step 5: Run generator tests, `scripts/export-board-catalog.sh --check`, and the iOS test/build commands.**
- [ ] **Step 6: Commit the task with `feat: generate iOS board catalog from manifests`.**

### Task 3: Document and verify the end-to-end workflow

**Files:**
- Modify: `docs/ADDING_A_BOARD.md`
- Modify: `Tools/HangboardOnboarding/README.md`
- Modify: `README.md`
- Test: `Tools/HangboardOnboarding/tests/test_board_catalog_cli.py`

**Interfaces:**
- Document the canonical package path, lifecycle states, temporary `.context` runs, registration command, and generated iOS catalog command.
- The CLI test exercises `validate`, `status`, and `register` through the public command entry point.

- [ ] **Step 1: Write failing CLI workflow tests for validate/status/register output.**
- [ ] **Step 2: Run them and verify the public command is missing or incomplete.**
- [ ] **Step 3: Implement the smallest CLI output and error behavior needed by the tests.**
- [ ] **Step 4: Update the guides with the Compact II package layout and draft-to-shipped workflow.**
- [ ] **Step 5: Run the full onboarding test suite and the generated-catalog check.**
- [ ] **Step 6: Commit the task with `docs: document canonical hangboard workflow`.**
