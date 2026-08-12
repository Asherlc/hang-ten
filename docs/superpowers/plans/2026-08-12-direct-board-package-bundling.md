# Direct Board Package Bundling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Hangboards/` the only editable board store, import the existing generated catalog as drafts, and have Hang Ten bundle and load approved JSON/PNG packages directly without generated board source or asset artifacts.

**Architecture:** `Hangboards/catalog.json` is a flat registry with per-board `draft` or `approved` status. A Python validator accepts incomplete draft packages and requires the complete audited contract for approved packages. An Xcode build phase invokes a byte-preserving staging script that copies only approved packages into the application bundle; generic Swift decoders and the generic SwiftUI renderer read those resources at runtime.

**Tech Stack:** Python 3.12, pytest, JSON, Swift 5, SwiftUI, XCTest, Xcode, shell scripts, GitHub Actions.

## Global Constraints

- `Hangboards/catalog.json` is the only lifecycle registry and permits exactly `draft` and `approved`; status is never encoded in a directory path.
- Every board directory is `Hangboards/<board-slug>/`; there is no `draft.json`, `onboarding`, or `shipped` lifecycle state.
- Draft packages are never bundled into the iOS application and never decoded as runtime boards.
- Approved packages contain `board.json`, `evidence.json`, `semantics.json`, `artwork.json`, and every referenced package asset; all evidence is source-backed and cross-file validated.
- The iOS app loads exact approved JSON/PNG bytes from `Bundle.main`; no generated Swift catalog, generated board JSON, generated artwork Swift, or generated Xcode imageset is created or read.
- The staging operation copies resources only into Xcode's build-product resources directory; it must not modify the checkout and must reject source/destination escapes and symlinks.
- Imported catalog images and approximate outlines are unreviewed draft material, never physical facts, evidence, semantic data, or runtime geometry.
- Retain existing Compact II and Rock Prodigy behavior, routines, hold IDs, and highlight behavior. The only intentional visual change is removal of screw holes from the Compact II presentation PNG.
- Do not invent evidence, board facts, semantic mappings, geometry, exercise content, or coaching claims.

---

## File structure after implementation

```text
Hangboards/
  catalog.json
  metolius-wood-grips-compact-ii/       # approved
    board.json
    evidence.json
    semantics.json
    artwork.json
    assets/
  trango-rock-prodigy-training-center/  # approved
    board.json
    evidence.json
    semantics.json
    artwork.json
  beastmaker-1000/                      # draft, imported review material
    README.md
    assets/
    review/

scripts/
  import-generated-board-catalog.py
  stage-approved-board-packages.py

HangTen/
  Models/BoardPackageStore.swift
  Views/BoardDesignLanguage.swift
```

The only `Hangboards` directory inside a built application is the exact output
of `stage-approved-board-packages.py`; it contains `catalog.json` plus the
complete directories for approved registry entries.

## Canonical interfaces

```python
@dataclass(frozen=True)
class CatalogEntry:
    id: str
    path: str
    status: Literal["draft", "approved"]

def validate_catalog(catalog_path: Path) -> CatalogDocument: ...
def load_approved_package(package_root: Path) -> BoardPackage: ...
def stage_approved_packages(repository_root: Path, destination: Path) -> tuple[Path, ...]: ...
def import_generated_catalog(source_root: Path, destination_root: Path) -> CatalogDocument: ...
```

```swift
struct BoardPackageStore {
    init(bundle: Bundle = .main) throws
    var boards: [TrainingBoard] { get }
    func board(id: String) -> TrainingBoard?
    func semantics(for boardID: String) -> [String: [String]]
    func design(for boardID: String) -> BoardDesign?
    func presentationImageURL(for board: TrainingBoard) -> URL?
}
```

### Task 1: Define the two-state registry and approved-package validator

**Files:**
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`
- Create: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_artwork.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Create: `Tools/HangboardPipeline/tests/test_board_artwork.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog_cli.py`

**Interfaces:**
- Consumes: the current schema-v1 Compact II catalog and evidence sidecar.
- Produces: the `CatalogEntry`, `CatalogDocument`, `BoardPackage`, and validator interfaces above.

- [ ] **Step 1: Write failing lifecycle and draft-contract tests.**

  Add fixture registries and assert that entries require a unique identifier,
  a confined relative package path, and exactly one of `draft` / `approved`.
  Assert a draft directory without package JSON validates and an approved
  directory with the same content fails.

  ```python
  catalog["boards"][0]["status"] = "shipped"
  with pytest.raises(ValueError, match="status must be one of"):
      validate_catalog(catalog_path)

  with pytest.raises(ValueError, match=r"approved package .*board\.json"):
      validate_catalog(approved_missing_package_path)
  ```

- [ ] **Step 2: Run the new tests to establish RED.**

  Run: `.context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py -q`

  Expected: FAIL because the current parser requires legacy lifecycle fields
  and does not distinguish draft from approved content.

- [ ] **Step 3: Write failing approved-package completeness/evidence tests.**

  Cover the exact approved sidecar set, matching board IDs, unique semantic
  mappings, exact physical-hold coverage by artwork, asset path confinement,
  symlink rejection, and evidence key coverage for every factual, semantic,
  artwork, and asset field.

  ```python
  package["evidence"]["assetEvidence"].pop("assets/presentation.png")
  with pytest.raises(ValueError, match="assetEvidence keys must equal package assets"):
      load_approved_package(package_root)
  ```

- [ ] **Step 4: Implement immutable schema models and closed validation.**

  Implement `CatalogEntry(status: str)` and `CatalogDocument(entries: tuple[CatalogEntry, ...])` in `board_catalog.py`. Implement the normalized frame/path/layer/hold-piece models in `board_artwork.py`; expose `load_approved_package()` only after all sidecars and evidence validate. Reject unknown schema keys, non-finite numbers, duplicate IDs, path traversal, and symlinks. Do not inspect `HangTen/` files.

- [ ] **Step 5: Run focused GREEN and the pipeline suite.**

  Run:

  ```sh
  .context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog_cli.py -q
  .context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests -q
  ```

  Expected: both commands pass without treating any application artifact as input.

- [ ] **Step 6: Commit and push the validator contract.**

  ```sh
  git add Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py Tools/HangboardPipeline/src/hangboard_vectorizer/board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog_cli.py
  git commit -m "feat: validate draft and approved board packages"
  git push origin HEAD
  ```

### Task 2: Import the generated catalog as labeled draft packages

**Files:**
- Create: `scripts/import-generated-board-catalog.py`
- Create: `Tools/HangboardPipeline/tests/test_generated_catalog_import.py`
- Modify: `Hangboards/catalog.json`
- Move: `docs/hangboard-generative-catalog/` material into flat board package directories

**Interfaces:**
- Consumes: primary PNGs, optional `flat-illustrations/*.png`, optional `ai-illustrations-v2/*.png`, and `outlines/*.json` from the existing catalog.
- Produces: one `CatalogEntry(status="draft")` and package `README.md`, `assets/`, and `review/` material for each imported board; preserves sources byte-for-byte. If a later approved board has the same slug, its imported material stays in `review/unreviewed-generated-catalog/` and remains excluded from runtime/package-evidence content.

- [ ] **Step 1: Write a failing inventory and classification test.**

  Derive expected slugs from primary PNG basenames, excluding contact sheets.
  Assert every slug has exactly one draft registry entry, one copied primary
  image, an outline in `review/` when one existed, and any matching visual
  variants in `assets/`. Assert no draft package contains `board.json`,
  `evidence.json`, `semantics.json`, or `artwork.json`.

  ```python
  assert imported_entry.status == "draft"
  assert (package_root / "assets" / "primary.png").read_bytes() == source.read_bytes()
  assert "unreviewed-generated-catalog" in (package_root / "README.md").read_text()
  ```

- [ ] **Step 2: Run the test to establish RED.**

  Run: `.context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_generated_catalog_import.py -q`

  Expected: FAIL because no draft package importer exists.

- [ ] **Step 3: Implement the idempotent importer.**

  Implement `import_generated_catalog(source_root, destination_root)` with a
  fixed mapping: primary to `assets/primary.png`, flat to `assets/flat.png`,
  AI-v2 to `assets/ai-v2.png`, outline to `review/outline.approx.json`.
  Generate a short README that names all retained material as unreviewed
  generated-catalog review material and forbids use as factual or runtime
  geometry. Rewrite registry entries deterministically, preserving approved
  entries and replacing only imported draft entries. For a target slug that is
  already approved, copy imported material below
  `review/unreviewed-generated-catalog/` without replacing the registry entry.
  Fail if an expected source has duplicate basenames.

- [ ] **Step 4: Import the full catalog and run GREEN.**

  Run:

  ```sh
  .context/impolite-wombat-canonical-board-artwork-venv/bin/python scripts/import-generated-board-catalog.py --source docs/hangboard-generative-catalog --destination Hangboards
  .context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_generated_catalog_import.py Tools/HangboardPipeline/tests/test_board_catalog.py -q
  ```

  Expected: every primary image has one draft package; no draft is eligible as an approved package.

- [ ] **Step 5: Commit and push draft import.**

  ```sh
  git add Hangboards scripts/import-generated-board-catalog.py Tools/HangboardPipeline/tests/test_generated_catalog_import.py
  git commit -m "feat: import generated board catalog as drafts"
  git push origin HEAD
  ```

### Task 3: Migrate the two runtime boards and create the screwless Compact II asset

**Files:**
- Modify: `Hangboards/catalog.json`
- Modify: `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Modify: `Hangboards/metolius-wood-grips-compact-ii/evidence.json`
- Create: `Hangboards/metolius-wood-grips-compact-ii/semantics.json`
- Create: `Hangboards/metolius-wood-grips-compact-ii/artwork.json`
- Create: `Hangboards/metolius-wood-grips-compact-ii/assets/CompactBoardIllustration.png`
- Create: `Hangboards/trango-rock-prodigy-training-center/{board,evidence,semantics,artwork}.json`
- Create: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`
- Create: `docs/source-audits/2026-08-12-rock-prodigy-board-package.md`

**Interfaces:**
- Consumes: current Compact II and Rock Prodigy runtime metadata/designs plus only their already-approved manufacturer sources.
- Produces: two complete `approved` packages whose metadata, IDs, semantics, and normalized vector paths preserve current runtime behavior.

- [ ] **Step 1: Write preservation tests before migration.**

  Record the exact Compact II 19-hold inventory and Rock Prodigy 26-hold
  inventory, their semantic mappings, canvas frames, layers, hold-piece IDs,
  path commands, treatments, and package presentation paths. Assert both
  registry entries have `status: "approved"`.

  ```python
  compact = load_approved_package(compact_root)
  assert len(compact.board.holds) == 19
  assert set(compact.artwork.hold_ids) == {hold.id for hold in compact.board.holds}
  ```

- [ ] **Step 2: Run the preservation tests to establish RED.**

  Run: `.context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py -q`

  Expected: FAIL because the package sidecars and Rock Prodigy package do not exist.

- [ ] **Step 3: Create audited canonical packages.**

  Transcribe existing reviewed metadata, semantics, and expanded normalized
  geometry exactly. Assign Compact II and Rock Prodigy registry status
  `approved`. Preserve the Compact II manufacturer JPG as a package-owned
  source asset. If Task 2 has already imported the Rock Prodigy catalog entry,
  retain its unreviewed PNGs/outlines only below
  `review/unreviewed-generated-catalog/`; they are not `assets/`, are not
  evidence-covered, and are never read by runtime/package validation. Map every
  factual/semantic/artwork/asset item to an existing evidence source; the Rock
  Prodigy audit may use only the four sources named in
  `docs/TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md`.

- [ ] **Step 4: Create and review the screwless Compact II presentation PNG.**

  Use the image-editing workflow on the existing `CompactBoardIllustration.png`.
  Remove visible screw/mounting holes only, preserving dimensions, crop,
  background, silhouette, color, scale, every hold boundary, and every other
  non-fastener detail. Place only the accepted output at the package-relative
  presentation path and record it in `assetEvidence` as
  `external-generative-adaptation`. Inspect source/output at full resolution;
  reject residual holes or changes outside the removed holes.

- [ ] **Step 5: Run package GREEN and visually inspect the presentation image.**

  Run:

  ```sh
  .context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py -q
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  ```

  Expected: both approved packages validate; test fixtures prove the original
  board inventory/geometry survives; visual inspection confirms no Compact II
  screw holes remain.

- [ ] **Step 6: Commit and push approved packages.**

  ```sh
  git add Hangboards Tools/HangboardPipeline/tests/test_approved_board_packages.py docs/source-audits/2026-08-12-rock-prodigy-board-package.md
  git commit -m "refactor: centralize approved board packages"
  git push origin HEAD
  ```

### Task 4: Stage approved packages as byte-preserving app resources

**Files:**
- Create: `scripts/stage-approved-board-packages.py`
- Create: `Tools/HangboardPipeline/tests/test_board_package_staging.py`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: `Hangboards/catalog.json` and package directories validated by Task 1.
- Produces: `stage_approved_packages(repository_root, destination) -> tuple[Path, ...]` and an app-bundle `Hangboards/` resource tree containing catalog plus approved packages only.

- [ ] **Step 1: Write failing staging tests.**

  Build a temporary repository with one draft and one approved package. Assert
  the destination contains the original catalog plus every approved file with
  byte equality, excludes every draft path, and removes stale files only below
  the explicit destination directory.

  ```python
  staged = stage_approved_packages(repository_root, destination)
  assert destination.joinpath("catalog.json").read_bytes() == catalog.read_bytes()
  assert not destination.joinpath("draft-board").exists()
  assert destination.joinpath("approved-board", "assets", "presentation.png").read_bytes() == image_bytes
  ```

- [ ] **Step 2: Run the tests to establish RED.**

  Run: `.context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_board_package_staging.py -q`

  Expected: FAIL because no staging script exists.

- [ ] **Step 3: Implement safe package staging.**

  Load the registry with `validate_catalog()`, copy `catalog.json` and only
  approved directories to a sibling temporary destination, verify every copied
  path is regular and non-symlinked, then atomically replace the exact Xcode
  build-product destination. Reject a destination outside the Xcode resource
  directory supplied by the build phase. Never write inside `Hangboards/` or
  `HangTen/`.

- [ ] **Step 4: Add the Xcode resource build phase.**

  Add a target build phase before resource use that runs:

  ```sh
  "${SRCROOT}/scripts/stage-approved-board-packages.py" \
    --repository-root "${SRCROOT}" \
    --destination "${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}/Hangboards"
  ```

  Declare the script input as `${SRCROOT}/Hangboards` and output as
  `${TARGET_BUILD_DIR}/${UNLOCALIZED_RESOURCES_FOLDER_PATH}/Hangboards/catalog.json`.
  Do not add a copied `Hangboards` directory to source control or Xcode's Copy
  Bundle Resources phase.

- [ ] **Step 5: Run GREEN and inspect a built bundle.**

  Run:

  ```sh
  .context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_board_package_staging.py -q
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  ```

  Expected: staging tests pass and the application build succeeds with an
  `Hangboards/catalog.json` resource in its product bundle and no draft package resources.

- [ ] **Step 6: Commit and push direct resource staging.**

  ```sh
  git add scripts/stage-approved-board-packages.py Tools/HangboardPipeline/tests/test_board_package_staging.py HangTen.xcodeproj/project.pbxproj
  git commit -m "feat: bundle approved board packages directly"
  git push origin HEAD
  ```

### Task 5: Decode and render bundled approved board packages generically

**Files:**
- Create: `HangTen/Models/BoardPackageStore.swift`
- Create: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Views/BoardDesignLanguage.swift`
- Modify: `HangTen/Views/BoardMapView.swift`

**Interfaces:**
- Consumes: the app-bundle resource tree produced by Task 4.
- Produces: `BoardPackageStore` and the generic `BoardCatalog` façade backed solely by decoded approved package data.

- [ ] **Step 1: Write failing package-store tests.**

  Create a test bundle fixture with one approved and one draft registry entry.
  Assert the store returns only the approved `TrainingBoard`, semantic mapping,
  vector `BoardDesign`, and package-relative image URL. Assert malformed JSON,
  missing approved sidecars, unknown artwork hold IDs, and a presentation asset
  path escape produce the precise `BoardPackageStoreError` case.

  ```swift
  let store = try BoardPackageStore(bundle: fixtureBundle)
  XCTAssertEqual(store.boards.map(\.id), ["approved-board"])
  XCTAssertNil(store.board(id: "draft-board"))
  XCTAssertEqual(store.semantics(for: "approved-board")["outer-jugs"], ["jug-left", "jug-right"])
  ```

- [ ] **Step 2: Run tests to establish RED.**

  Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardPackageStoreTests`

  Expected: FAIL because the resource decoder and generic artwork decoder do not exist.

- [ ] **Step 3: Implement Codable package decoding and generic artwork adaptation.**

  Decode catalog entries from `Bundle.url(forResource: "catalog", withExtension: "json", subdirectory: "Hangboards")`. Enumerate only `approved` entries, resolve every subpath below that package URL, decode `board.json`, `semantics.json`, and `artwork.json`, then adapt decoded paths/treatments into the existing generic `BoardDesign` primitives. `BoardDesignLanguage.swift` remains generic and contains no board-specific coordinate/ID. Create the `BoardCatalog` façade from one shared store and retain only generic APIs (`all`, `defaultBoard`, `board(for:)`).

- [ ] **Step 4: Make presentation images package-relative.**

  Replace `photoAssetName`-based `Image(name:)` use with the package store's
  `presentationImageURL(for:)` and a `UIImage(contentsOfFile:)`/SwiftUI image
  adapter. Return `nil` when a board does not declare a presentation asset; do
  not fall back to an Xcode imageset.

- [ ] **Step 5: Run focused GREEN.**

  Run:

  ```sh
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardStorageTests
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  ```

  Expected: tests pass and every current board map resolves from approved
  bundled JSON without a generated board definition.

- [ ] **Step 6: Commit and push runtime package loading.**

  ```sh
  git add HangTen/Models/BoardPackageStore.swift HangTen/Models/TrainingModels.swift HangTen/Views/BoardDesignLanguage.swift HangTen/Views/BoardMapView.swift HangTenTests/BoardPackageStoreTests.swift
  git commit -m "feat: load approved board packages at runtime"
  git push origin HEAD
  ```

### Task 6: Remove all duplicate board delivery artifacts and route plans through package semantics

**Files:**
- Modify: `HangTen/Models/PlanStorage.swift`
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTen/Views/CustomRoutineEditorView.swift`
- Delete: `HangTen/Models/GeneratedBoardCatalog.swift`
- Delete: `HangTen/Resources/BoardLibrary.json`
- Delete: `HangTen/Views/MetoliusCompactIIDesign.swift`
- Delete: `HangTen/Views/RockProdigyTrainingCenterDesign.swift`
- Delete: `HangTen/Resources/Assets.xcassets/CompactBoard.imageset/`
- Delete: `HangTen/Resources/Assets.xcassets/CompactBoardIllustration.imageset/`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/PlanStorageTests.swift`
- Create: `HangTenTests/BoardSourceBoundaryTests.swift`

**Interfaces:**
- Consumes: `BoardCatalog`, `BoardPackageStore.semantics(for:)`, and runtime designs from Task 5.
- Produces: generic plan resolution and no checked-in secondary board metadata, geometry, or image asset copies.

- [ ] **Step 1: Write failing semantic-resolution and boundary tests.**

  Assert every plan target resolves through `BoardPackageStore` semantic data
  and that the app has exactly the approved package board IDs. Add a tracked-
  source scan that rejects `GeneratedBoardCatalog`, `BoardLibrary.json`, the
  old design-file names, `CompactBoardIllustration`, and package hold IDs in
  handwritten app source, excluding tests and `Hangboards/`.

  ```swift
  XCTAssertEqual(BoardCatalog.all.map(\.id).sorted(), ["metolius.wood-grips-compact-ii", "trango.rock-prodigy-training-center"])
  XCTAssertFalse(BoardTargetResolver.resolveHoldIDs(for: target, on: board).isEmpty)
  ```

- [ ] **Step 2: Run tests to establish RED.**

  Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardSourceBoundaryTests -only-testing:HangTenTests/PlanStorageTests`

  Expected: FAIL because app code still contains generated and handwritten board sources.

- [ ] **Step 3: Replace handwritten aliases/mappings with generic APIs.**

  Initialize `AppStore.selectedBoard` from `BoardCatalog.defaultBoard`.
  Replace all `compactII` and `rockProdigyTrainingCenter` convenience
  references with runtime lookups/validated IDs. Build plan board mappings from
  `BoardPackageStore.semantics(for:)`; preserve `PlanLibrary.json` bytes except
  where changing the data source requires deterministic metadata-only changes.

- [ ] **Step 4: Remove duplicate sources and Xcode references.**

  Remove generated catalog/library resources, bespoke design source files, and
  both old board imagesets only after Task 5's bundle path is active. Remove
  their PBX file/build references. Do not remove generic `Assets.xcassets` or
  unrelated images.

- [ ] **Step 5: Run GREEN and full iOS unit coverage.**

  Run:

  ```sh
  scripts/export-plan-library.sh --check
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardSourceBoundaryTests -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/BoardStorageTests
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  ```

  Expected: the plan compiler and selected tests/build pass; no duplicate board definition survives.

- [ ] **Step 6: Commit and push app cleanup.**

  ```sh
  git add -A HangTen HangTenTests HangTen.xcodeproj scripts/export-plan-library.sh
  git commit -m "refactor: consume bundled board packages directly"
  git push origin HEAD
  ```

### Task 7: Align Workbench, CI, and documentation with direct packages

**Files:**
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/workbench_promotion.py`
- Modify: `Tools/HangboardWorkbench/server.py`
- Modify: `Tools/HangboardPipeline/tests/test_workbench_end_to_end.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/ADDING_A_BOARD.md`
- Create: `Tools/HangboardPipeline/tests/test_documentation_paths.py`

**Interfaces:**
- Consumes: Task 1 validator and Task 4 staging script.
- Produces: canonical-package Workbench editing, CI validation/staging checks, and accurate draft/approved docs.

- [ ] **Step 1: Write failing Workbench and CI/doc contract tests.**

  Assert Workbench edits package files and registry status rather than any
  generated app artifact. Assert CI validates catalog, runs draft-import
  inventory checks, stages approved resources into a temporary destination,
  and runs the iOS package-store tests. Assert active docs name two statuses,
  direct app bundling, and the rule that drafts never ship.

  ```python
  assert "stage-approved-board-packages.py" in ci_workflow
  assert "status: draft" in adding_a_board
  assert "GeneratedBoardCatalog" not in active_docs
  ```

- [ ] **Step 2: Run tests to establish RED.**

  Run: `.context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests/test_workbench_end_to_end.py Tools/HangboardPipeline/tests/test_documentation_paths.py -q`

  Expected: FAIL because active tooling/docs still target generated outputs and old lifecycle terminology.

- [ ] **Step 3: Implement canonical Workbench/CI/documentation behavior.**

  Make Workbench publish only package/registry candidates validated by Task 1;
  it must not write Swift, Xcode assets, or board-library JSON. Add CI commands
  for validation, imported-draft inventory, temporary approved-resource
  staging, and runtime tests. Rewrite active guidance to describe flat package
  paths, registry status, draft import, approval requirements, direct bundling,
  and source-backed review. Preserve historical experimental-catalog rationale
  under `docs/history/` after the importer has retained all material.

- [ ] **Step 4: Run repository verification and visual validation.**

  Run:

  ```sh
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  .context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  git diff --check
  ```

  Then use the dedicated iOS simulator validation workflow to inspect both
  approved boards in portrait and landscape with normal and active hold states.
  Store screenshots below `.context/`; compare them with pre-migration runtime
  rendering and confirm the Compact II presentation image has no screw holes.

- [ ] **Step 5: Commit and push final integration.**

  ```sh
  git add .github Tools/HangboardPipeline Tools/HangboardWorkbench README.md docs/ADDING_A_BOARD.md docs/history
  git commit -m "ci: enforce direct approved board packages"
  git push origin HEAD
  ```

## Final acceptance audit

Run these checks after Task 7:

```sh
scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
.context/impolite-wombat-canonical-board-artwork-venv/bin/python -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
rg -n '"status": "(draft|approved)"' Hangboards/catalog.json
rg -n 'GeneratedBoardCatalog|GeneratedBoardSemantics|GeneratedBoardDesignCatalog|BoardLibrary\.json|CompactBoardIllustration' HangTen HangTen.xcodeproj -g '!**/Tests/**'
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
git diff --check
```

Expected: the first five validation/build commands pass; the source scan finds
no retired delivery artifact outside deliberate historical documentation; all
registry entries use one of the two statuses; only approved package bytes are
present in the built app bundle.
