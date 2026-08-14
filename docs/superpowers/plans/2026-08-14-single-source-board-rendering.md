# Single-Source Board Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each registered package's `assets/primary.png` the only board visual rendered by iOS, while preserving generic frame-based highlight and tap interaction from `board.json`.

**Architecture:** `Hangboards/` remains the app-independent canonical data store for a board's facts, holds, semantics, evidence, and primary PNG. The Python pipeline and iOS loader will read only `board.json`, `semantics.json`, `evidence.json`, and declared assets; iOS will apply generic rectangular hit/highlight overlays over the primary PNG. No package or app source will carry vector artwork, board-specific rendering branches, or a fallback board illustration.

**Tech Stack:** SwiftUI/UIKit/XCTest, Python/pytest/Pillow, Xcode build resources, JSON package sidecars.

## Global Constraints

- `assets/primary.png` is the sole visual definition for every registered board package.
- `Hangboards/` owns all board information: identity, facts, hold IDs/frames, semantics, evidence, and canonical assets.
- The iOS app may implement generic rendering, highlighting, and taps, but may not contain board-specific geometry, artwork, asset names, or rendering branches.
- Preserve all existing board facts, hold IDs, normalized frames, semantic mappings, training plans, and Compact II `primary.png` bytes.
- A registered board without a readable declared primary PNG remains a launch-blocking package error; do not add an asset-catalog or generated-vector fallback.
- Generated output and test artifacts stay under `.context`; no worktree-cleaning or deletion outside exact task targets.

---

## File structure

- `Hangboards/metolius-wood-grips-compact-ii/`: retain the canonical facts, semantics, evidence, primary PNG, and optional original photo; remove the obsolete vector-artwork sidecar and evidence map.
- `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`: validate the three-data-sidecar package contract and construct a `BoardPackage` without vector artwork.
- `Tools/HangboardPipeline/src/hangboard_vectorizer/board_library.py`: materialize Workbench rectangles from `BoardHold.frame`, rather than package vector shapes.
- `HangTen/Models/BoardPackageStore.swift`: load board, semantics, and presentation URL only.
- `HangTen/Views/BoardMapView.swift`: render the package PNG plus generic frame overlays/tap targets.
- `HangTenTests/BoardPackageStoreTests.swift` and `HangTenTests/BoardSourceBoundaryTests.swift`: prove runtime package loading and the one-source boundary.
- `Tools/HangboardPipeline/tests/`: replace artwork-contract/parity expectations with package-contract and frame-derived Workbench expectations.
- `docs/ADDING_A_BOARD.md`, pipeline docs, audit templates, and scripts: describe and invoke the three-sidecar, primary-PNG contract without referencing removed artwork delivery code.

### Task 1: Remove vector artwork from the canonical package contract

**Files:**
- Delete: `Hangboards/metolius-wood-grips-compact-ii/artwork.json`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_artwork.py`
- Modify: `Hangboards/metolius-wood-grips-compact-ii/evidence.json`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py:1-500`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/semantic_benchmark.py:1-100`
- Modify: `Tools/HangboardPipeline/tests/test_board_artwork.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`
- Modify: `Tools/HangboardPipeline/tests/test_semantic_benchmark.py`

**Interfaces:**
- Consumes: the existing `BoardDocument`, `BoardSemanticsDocument`, and `BoardEvidenceDocument` value types.
- Produces: `BoardPackage(root, board, evidence, semantics)` with no `artwork` property; `_SIDECARS == ("board.json", "evidence.json", "semantics.json")`; exact evidence validation for field, hold, semantic, and asset maps only.

- [ ] **Step 1: Write failing package-contract tests**

  Replace artwork fixtures in `test_board_artwork.py` with three-sidecar fixtures and add assertions that a package containing `artwork.json` is rejected as an unknown root file. Update `test_approved_board_packages.py` so the registered Compact II JSON set is exactly:

  ```python
  CANONICAL_PACKAGE_SIDECARS = {"board.json", "evidence.json", "semantics.json"}

  def test_registered_package_rejects_obsolete_artwork_sidecar(tmp_path: Path) -> None:
      module = load_board_catalog_module()
      root = _write_approved_package(tmp_path / "package")
      root.joinpath("artwork.json").write_text("{}", encoding="utf-8")

      with pytest.raises(ValueError, match="unknown package file: artwork.json"):
          module.load_board_package(root)
  ```

  Change the Compact II invariant test to assert its facts, holds, semantic mappings, primary PNG hash, and absence of `artwork.json`; remove every assertion accessing `package.artwork`. Change the benchmark test to assert only semantic parity and eliminate its `parity.artwork` assertion.

- [ ] **Step 2: Run the focused tests and verify they fail for the old contract**

  Run:

  ```bash
  cd Tools/HangboardPipeline && python -m pytest \
    tests/test_board_artwork.py tests/test_board_catalog.py \
    tests/test_approved_board_packages.py tests/test_semantic_benchmark.py -q
  ```

  Expected: failure because the current validator still requires `artwork.json`, exposes `package.artwork`, and requires `artworkEvidence`.

- [ ] **Step 3: Implement the minimal three-sidecar validator**

  In `board_catalog.py`, remove the `board_artwork` imports/fallback loader, remove `artwork_evidence` from `BoardEvidenceDocument`, remove `artwork` from `BoardPackage`, and change the contract to:

  ```python
  _SIDECARS = ("board.json", "evidence.json", "semantics.json")
  _PACKAGE_ROOT_FILES = frozenset((*_SIDECARS, "assets"))

  @dataclass(frozen=True)
  class BoardPackage:
      root: Path
      board: BoardDocument
      evidence: BoardEvidenceDocument
      semantics: BoardSemanticsDocument
  ```

  Make `_load_evidence` accept exactly `schemaVersion`, `boardID`, `checkedAt`, `sources`, `fieldEvidence`, `holdEvidence`, `semanticEvidence`, and `assetEvidence`. In `load_board_package`, require matching IDs only across the three sidecars, retain semantic-to-hold and exact evidence checks, and remove artwork loading/evidence validation. Delete `board_artwork.py`, remove artwork parity from `semantic_benchmark.py`, and retain its deterministic package hash and semantic report.

  Delete `Hangboards/metolius-wood-grips-compact-ii/artwork.json`; remove only the `artworkEvidence` object from its `evidence.json`. Do not alter `board.json`, `semantics.json`, or any asset byte.

- [ ] **Step 4: Run focused package and benchmark tests**

  Run the Step 2 command again.

  Expected: PASS; the registered Compact II package validates without artwork, rejects a reintroduced artwork sidecar, and the benchmark reports semantic parity.

- [ ] **Step 5: Commit and push the contract change**

  ```bash
  git add Hangboards/metolius-wood-grips-compact-ii Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py Tools/HangboardPipeline/src/hangboard_vectorizer/semantic_benchmark.py Tools/HangboardPipeline/src/hangboard_vectorizer/board_artwork.py Tools/HangboardPipeline/tests/test_board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_semantic_benchmark.py
  git commit -m "refactor: remove board artwork package contract"
  git push
  ```

### Task 2: Derive Workbench regions from canonical hold frames

**Files:**
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_library.py:1-335`
- Modify: `Tools/HangboardPipeline/tests/test_board_library.py:1-340`
- Modify: `Tools/HangboardPipeline/tests/test_workbench_end_to_end.py`
- Modify: `Tools/HangboardPipeline/tests/test_workbench_promotion.py`

**Interfaces:**
- Consumes: `BoardPackage.board.holds`, where every `BoardHold` has an ID, kind, and normalized `frame`.
- Produces: one Workbench region per `BoardHold`, with `key == hold.id`, bounds/anchor calculated from `hold.frame`, and a rectangular SVG `displayPath`; `silhouettePaths` is an empty array because no canonical vector silhouette exists.

- [ ] **Step 1: Write failing frame-derived Workbench tests**

  Replace the current test that compares Stage 3 output to `artwork.json` with a test asserting a single region per physical hold and a frame rectangle path:

  ```python
  def test_copy_current_run_uses_board_hold_frames_for_regions(tmp_path: Path) -> None:
      library = RepositoryBoardLibrary(_repository(tmp_path))
      destination = tmp_path / ".context" / "runtime" / "run"
      library.copy_current_run("metolius.wood-grips-compact-ii", destination)

      document = json.loads(next(destination.glob("stages/03/*/stage-3-vector-regions.json")).read_text())
      package = load_board_package(FIXTURE)
      assert [region["key"] for region in document["regions"]] == [hold.id for hold in package.board.holds]
      assert document["silhouettePaths"] == []
      assert all(region["displayPath"].startswith("M ") and region["displayPath"].endswith(" Z") for region in document["regions"])
  ```

  Update any Workbench fixtures to omit `artwork.json` and assert the primary PNG remains the copied review/base asset.

- [ ] **Step 2: Run the focused Workbench tests and verify they fail**

  Run:

  ```bash
  cd Tools/HangboardPipeline && python -m pytest \
    tests/test_board_library.py tests/test_workbench_end_to_end.py \
    tests/test_workbench_promotion.py -q
  ```

  Expected: failure from imports/accesses of `package.artwork` and tests requiring its shape paths.

- [ ] **Step 3: Replace artwork geometry with generic rectangular paths**

  In `_CanonicalPackageRunner`, remove `_pieces`, `BoardHoldPieceDocument`, `BoardShapeDocument`, `_piece_path`, and `_shape_path`. Build `regions` by enumerating `self._holds`; calculate `anchor` and `bounds` from each `hold.frame`; set `displayPath` with this helper:

  ```python
  @staticmethod
  def _frame_path(hold: BoardHold, width: int = 1, height: int = 1) -> str:
      x, y = hold.frame.x * width, hold.frame.y * height
      w, h = hold.frame.width * width, hold.frame.height * height
      return f"M {x} {y} H {x + w} V {y + h} H {x} Z"
  ```

  Set each region's `pieceIndex` to `0`, use `_frame_path(hold, width, height)`, and return `"silhouettePaths": []`. Build Stage 4 `highlights` with exactly one `displayPath` per hold from `_frame_path(hold)`. Preserve stage files, stage counts, metadata, package safety checks, and primary-image copying.

- [ ] **Step 4: Run focused Workbench tests**

  Run the Step 2 command again.

  Expected: PASS; the Workbench can materialize and replay a package using only its primary image and `board.json` frames.

- [ ] **Step 5: Commit and push the Workbench migration**

  ```bash
  git add Tools/HangboardPipeline/src/hangboard_vectorizer/board_library.py Tools/HangboardPipeline/tests/test_board_library.py Tools/HangboardPipeline/tests/test_workbench_end_to_end.py Tools/HangboardPipeline/tests/test_workbench_promotion.py
  git commit -m "refactor: derive workbench regions from board frames"
  git push
  ```

### Task 3: Render the package PNG and generic overlays in iOS

**Files:**
- Delete: `HangTen/Views/BoardDesignLanguage.swift`
- Modify: `HangTen/Models/BoardPackageStore.swift:60-550`
- Modify: `HangTen/Views/BoardMapView.swift:1-220`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `scripts/export-plan-library.sh:18-27`
- Modify: `HangTenTests/BoardPackageStoreTests.swift:1-500`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift:1-380`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:**
- Consumes: `TrainingBoard.holds` and `BoardCatalog.packageStore.presentationImageURL(for:) -> URL?`.
- Produces: `BoardMapView` with the canonical `UIImage(contentsOfFile:)` base and generic `HoldFrame` overlays; `BoardPackageStore` exposes boards, semantics, and presentation URLs, but no `BoardDesign` or `design(for:)` API.

- [ ] **Step 1: Write failing iOS boundary and loader tests**

  In `BoardPackageStoreTests`, change fixture creation to write only `board.json`, `semantics.json`, and `primary.png`; remove artwork mutation cases. Add an exact source assertion:

  ```swift
  func testStoreLoadsPackageWithoutArtworkDocument() throws {
      let fixture = try makeFixtureBundle()
      let store = try BoardPackageStore(bundle: fixture.bundle)
      XCTAssertEqual(store.boards.map(\.id), ["package-board"])
      XCTAssertEqual(
          try XCTUnwrap(store.presentationImageURL(for: try XCTUnwrap(store.boards.first))).lastPathComponent,
          "primary.png"
      )
  }
  ```

  In `BoardSourceBoundaryTests`, add `HangTen/Views/BoardDesignLanguage.swift` and `Hangboards/metolius-wood-grips-compact-ii/artwork.json` to forbidden paths/tokens, remove its artwork JSON scan, and assert `BoardMapView.swift` contains `BoardPresentationImage` usage but neither `Canvas(` nor `BoardDesign`.

- [ ] **Step 2: Run focused iOS tests and verify they fail**

  Run:

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
    -only-testing:HangTenTests/BoardPackageStoreTests \
    -only-testing:HangTenTests/BoardSourceBoundaryTests
  ```

  Expected: failure because `BoardPackageStore` requires `artwork.json` and `BoardMapView` still chooses `DesignedBoardMap`.

- [ ] **Step 3: Implement the generic raster map**

  Remove `BoardArtworkDocument`, `designsByBoardID`, artwork error cases, artwork sidecar decoding/validation, and `design(for:)` from `BoardPackageStore`. Delete `BoardDesignLanguage.swift` and remove its file reference/build entry from `project.pbxproj` plus the exporter compile list.

  Replace `BoardMapView`'s `DesignedBoardMap`/`GenericVectorBoardMap` branch with `BoardPresentationImage(board: board)` as the base. In the same `GeometryReader`, iterate `board.holds` and derive each overlay frame from `hold.frame.rect`. Place a transparent `contentShape(Rectangle())` tap target for every hold. For highlighted holds, add an app-generic rounded rectangle fill/stroke inside the same frame; map `.active` and `.preview` through the existing `BoardHighlightMode` colors. Do not add board-ID checks, image-name literals, Canvas drawing, or any image fallback.

- [ ] **Step 4: Run focused iOS tests and build**

  Run the Step 2 test command, then:

  ```bash
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro'
  ```

  Expected: PASS; package loading requires only the three sidecars, and the application compiles without vector-artwork types.

- [ ] **Step 5: Commit and push the iOS renderer migration**

  ```bash
  git add HangTen HangTen.xcodeproj/project.pbxproj HangTenTests scripts/export-plan-library.sh
  git commit -m "refactor: render boards from canonical primary images"
  git push
  ```

### Task 4: Align documentation, source audits, and complete verification

**Files:**
- Modify: `docs/ADDING_A_BOARD.md`
- Modify: `README.md`
- Modify: `Tools/HangboardPipeline/README.md`
- Modify: `Tools/HangboardPipeline/TESTING.md`
- Modify: `scripts/hangboard-tools.sh`
- Modify: `docs/source-audits/2026-08-12-*.md` files that define the registered-package sidecar/evidence contract
- Test: `Tools/HangboardPipeline/tests/`
- Test: `HangTenTests/`

**Interfaces:**
- Consumes: the Task 1 three-sidecar validator, Task 2 frame-derived Workbench output, and Task 3 raster renderer.
- Produces: documentation and scripts that describe only canonical board facts/frames/semantics/evidence/assets; no user-facing package contract names `artwork.json`, artwork evidence, or artwork parity.

- [ ] **Step 1: Write failing documentation-contract assertions**

  Extend the existing documentation-path test (or add `test_single_source_rendering_docs.py`) to require the canonical sidecar list in `docs/ADDING_A_BOARD.md` to be exactly `board.json`, `evidence.json`, and `semantics.json`, and to reject the phrase `` `artwork.json` `` from active package-contract documentation. Keep historical migration plans/specs exempt by limiting the assertion to `README.md`, `docs/ADDING_A_BOARD.md`, `Tools/HangboardPipeline/README.md`, `Tools/HangboardPipeline/TESTING.md`, and `scripts/hangboard-tools.sh`.

- [ ] **Step 2: Run the documentation test and verify it fails**

  Run:

  ```bash
  cd Tools/HangboardPipeline && python -m pytest tests/test_documentation_paths.py -q
  ```

  Expected: failure because active guidance still describes artwork sidecars/evidence/parity.

- [ ] **Step 3: Update active guidance and remove the artwork benchmark command**

  Describe `primary.png` as the only board visual. Describe `board.json` frames as factual normalized hold regions used by generic consumers for taps/highlights. Remove `artwork.json`, `artworkEvidence`, artwork parity, and the `benchmark` subcommand/help text from active documentation/scripts. Update audit templates and active audit prose so a registered package requires evidence for board facts, hold fields, semantic mappings, and assets only. Preserve historical documents as historical records rather than rewriting their recorded past architecture.

- [ ] **Step 4: Run the complete relevant verification set**

  Run:

  ```bash
  cd Tools/HangboardPipeline && python -m pytest -q
  ```

  Then run:

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro'
  ```

  Finally use the repository's `validate-hang-ten-ios` workflow to launch an isolated simulator and verify the Compact II home/workout map is the exact primary PNG with visible generic active/preview overlays and working tap selection.

- [ ] **Step 5: Commit and push documentation and final tests**

  ```bash
  git add README.md docs/ADDING_A_BOARD.md docs/source-audits Tools/HangboardPipeline/README.md Tools/HangboardPipeline/TESTING.md Tools/HangboardPipeline/tests/test_documentation_paths.py scripts/hangboard-tools.sh
  git commit -m "docs: document canonical board rendering"
  git push
  ```

## Plan self-review

- Spec coverage: Task 1 eliminates the duplicate package visual contract; Task 2 eliminates its tooling dependency; Task 3 removes iOS vector rendering and preserves generic interaction; Task 4 aligns documentation and validates the package PNG on a simulator.
- Scope: no task changes a board fact, hold ID, semantics, plan content, or primary PNG byte.
- Type consistency: all downstream consumers use `BoardPackage.board.holds`, `BoardHold.frame`, and `presentationImageURL(for:)`; no task retains `BoardPackage.artwork`, `BoardDesign`, or `design(for:)`.
