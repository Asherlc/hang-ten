# Board Content Pipeline Cleanup Implementation Plan

> **Superseded:** The generated-runtime-artifact architecture in this plan was
> replaced on 2026-08-12 by [Direct Board Package Bundling](2026-08-12-direct-board-package-bundling.md). Do not execute the remaining tasks here.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each evidence-backed `Hangboards/<board-slug>/` package the one editable source of truth for all board-owned metadata, evidence, semantic mappings, normalized vector geometry, and optional presentation assets; generate every Hang Ten board artifact from those packages; and retire unsuccessful image-automation experiments without removing the functioning pipeline or Workbench.

**Architecture:** `Hangboards/catalog.json` registers complete board packages containing `board.json`, `evidence.json`, `semantics.json`, and `artwork.json`. The retained Python pipeline validates those files as one referentially consistent unit and deterministically generates runtime JSON, Swift board/semantic/design code, and optional asset-catalog imagesets without reading prior outputs for defaults. Generic Swift rendering remains handwritten, while all board-specific facts, IDs, mappings, and coordinates move out of application code.

**Tech Stack:** Python 3.11, pytest, JSON, JavaScript node:test, Swift 5/SwiftUI, XCTest, SwiftPM, Xcode, shell scripts, GitHub Actions.

## Progress carried forward

- [x] **Task 1: Require source evidence for every canonical board package** — completed in `96e3473` with Compact II `evidence.json` and schema-version-1 validation. Task 3 evolves this contract; do not revert or repeat it.
- [x] **Task 2: Rename the supported pipeline and Workbench roots** — completed in `ea8a5ed`, moving active code to `Tools/HangboardPipeline/` and `Tools/HangboardWorkbench/`. All later paths use these names.

## Global constraints

- Every approved or shipped runtime board must be registered in `Hangboards/catalog.json` and derive from exactly one complete package.
- A complete package owns physical metadata, presentation metadata, evidence mappings, semantic mappings, normalized vector geometry, and optional board-specific source media.
- `HangTen/Resources/BoardLibrary.json`, `HangTen/Models/GeneratedBoardCatalog.swift`, `HangTen/Models/GeneratedBoardSemantics.swift`, `HangTen/Views/GeneratedBoardDesignCatalog.swift`, generated board imagesets, and board mappings in `PlanLibrary.json` are delivery artifacts; they must never supply defaults to their generator.
- Generic renderer code may remain under `HangTen/Views/BoardDesignLanguage.swift`, but it must contain no board ID, hold ID, board dimension, semantic mapping, or board-specific coordinate.
- Do not invent evidence, physical facts, semantic mappings, artwork paths, assets, exercise content, or coaching claims. Omit unsupported optional content. Stop a shipped-board migration if required existing content cannot be traced.
- The only allowed Rock Prodigy evidence is already recorded in `docs/TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md`: its Trango product page, manufacturer manual, depth guide, and product image. Do not use the retired generative catalog as evidence.
- Retain validation, catalog registration, deterministic export, release checks, and human-reviewed Workbench operation.
- Retire `docs/hangboard-generative-catalog/`, its outline/flat/AI-v2 derivatives, `hangboard-catalog-flat`, `hangboard-catalog-outlines`, and `hangboard-to-svg --experimental-recess-detection`.
- Do not claim that a product photograph can programmatically generate faithful board artwork or authoritative hold geometry.
- Preserve current Compact II and Rock Prodigy runtime values and vector rendering during migration. Do not change routine tasks, counts, durations, grips, targets, or coaching text.
- Retired plans/specifications remain under `docs/history/tooling/` and must not be linked from active workflow guides.
- Use `git mv` for retained tools, assets, and historical documents where history is meaningful.
- Keep `.context/` as the only workspace-owned transient output root.

---

## File structure after migration

```text
Hangboards/
  catalog.json
  metolius-wood-grips-compact-ii/
    board.json
    evidence.json
    semantics.json
    artwork.json
    assets/
      CompactBoardIllustration.png       # only if its audit mapping is retained
  trango-rock-prodigy-training-center/
    board.json
    evidence.json
    semantics.json
    artwork.json

Tools/
  HangboardPipeline/
    src/hangboard_vectorizer/
      board_catalog.py                   # package/registry models and validation
      board_artwork.py                   # normalized artwork schema and validation
      board_generation.py                # pure deterministic output rendering
    tests/
  HangboardWorkbench/                    # canonical package editor/reviewer

HangTen/
  Models/
    GeneratedBoardCatalog.swift
    GeneratedBoardSemantics.swift
  Resources/
    BoardLibrary.json
    PlanLibrary.json
    Assets.xcassets/                     # generated delivery copies only
  Views/
    BoardDesignLanguage.swift            # generic renderer
    GeneratedBoardDesignCatalog.swift

scripts/
  generate-board-content.py              # one generate/check coordinator
  export-board-catalog.py                # compatibility wrapper, delegates only
  export-board-library.py                # compatibility wrapper, delegates only
  export-board-catalog.sh                # compatibility wrapper, delegates only
  export-plan-library.sh                 # consumes generated semantics
```

## Canonical interfaces used by all remaining tasks

The four package files and registry follow the exact contracts in the amended
design. The Python interfaces introduced below are:

```python
@dataclass(frozen=True)
class BoardPackage:
    root: Path
    board: BoardDocument
    evidence: BoardEvidenceDocument
    semantics: BoardSemanticsDocument
    artwork: BoardArtworkDocument

def load_package(path: Path) -> BoardPackage: ...
def validate_catalog(path: Path) -> CatalogDocument: ...
def generate_board_content(
    repository_root: Path,
    catalog_path: Path,
    output_root: Path,
) -> GeneratedBoardContent: ...
def check_board_content(repository_root: Path, catalog_path: Path) -> list[str]: ...
```

`GeneratedBoardContent.files` is a mapping of repository-relative POSIX paths
to bytes. Its owned output set is explicit and contains the four generated
board/semantic/design/library files plus declared imageset contents. Plan
library generation consumes `GeneratedBoardSemantics.swift` and remains a
separate deterministic compiler step coordinated by the same top-level script.

### Task 3: Define and validate the complete board-package schemas

**Files:**
- Create: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_artwork.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Create: `Tools/HangboardPipeline/tests/test_board_artwork.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog_cli.py`

**Interfaces:**
- Consumes: the completed schema-version-1 `board.json`, `evidence.json`, and catalog parser.
- Produces: schema-version-2 `CatalogDocument`, `BoardDocument`, and `BoardEvidenceDocument`; schema-version-1 `BoardSemanticsDocument` and `BoardArtworkDocument`; `load_package(path: Path) -> BoardPackage`.
- `validate_catalog()` validates all four package files and returns catalog entries associated with validated packages; it performs no generation and reads no app output.

- [ ] **Step 1: Add failing registry and package-completeness tests.**

  Add fixtures with schema-version-2 registry metadata and package directory names. Assert rejection of duplicate/traversing package paths, duplicate package board IDs, a default board ID not in the package set, catalog metadata unknown keys, and missing `board.json`, `evidence.json`, `semantics.json`, or `artwork.json`. Assert that approved/shipped packages cannot omit any sidecar.

  ```python
  with pytest.raises(ValueError, match=r"package semantics\.json does not exist"):
      module.validate_catalog(catalog_path)
  with pytest.raises(ValueError, match="defaultBoardID must resolve"):
      module.validate_catalog(catalog_path)
  ```

- [ ] **Step 2: Add failing board presentation and semantic tests.**

  Assert `board.json` requires unique `presentation.generatedSymbol` values and validates an optional `photoAsset` name/path without path escape, symlinks, or a missing regular file. Assert every regular file below an optional package `assets/` directory has exactly one `assetEvidence` mapping; presentation assets must refer to one of those mapped assets, while evidence-only manufacturer source media is retained without being copied to Xcode. Assert `semantics.json.boardID` matches its board, semantic IDs and hold IDs are unique, mappings are non-empty, and all hold IDs exist in `board.json`.

  ```python
  semantics["semanticHolds"]["outer-jugs"]["holdIDs"] = ["missing"]
  with pytest.raises(ValueError, match="references unknown hold 'missing'"):
      module.load_package(package_root)
  ```

- [ ] **Step 3: Add failing artwork grammar and reference tests.**

  Cover finite normalized frames, finite points, non-empty closed silhouette
  paths, legal path command keys, corner-radius range `0...0.5`, supported
  roles (`topPlane`, `faceLight`, `separator`, `bottomPlane`, `topSeam`,
  `shelf`), treatments (`surface`, `shelf`, `recess`), recess depths (`deep`,
  `shallow`), unique layer/piece IDs, exact hold coverage, valid palette
  `sculptedWood`, and sibling `boardID` equality.

  ```python
  artwork["holdPieces"][0]["frame"]["x"] = float("nan")
  with pytest.raises(ValueError, match="must be finite"):
      load_artwork(path)

  artwork["holdPieces"][0]["holdID"] = "unknown"
  with pytest.raises(ValueError, match="unknown physical hold"):
      validate_package(package)
  ```

- [ ] **Step 4: Add failing evidence-coverage tests for all board-owned data.**

  Advance evidence to schema version 2 and assert `fieldEvidence` covers every
  factual field required by the validator, `holdEvidence` keys equal physical
  hold IDs, `semanticEvidence` keys equal semantic IDs, `artworkEvidence` keys
  equal `silhouette` plus `layers.<id>` and `holdPieces.<id>`, and
  `assetEvidence` keys equal every regular file beneath a package `assets/`
  directory. Every mapping contains
  non-empty declared `sourceIDs` and one allowed method. Assert
  `external-generative-adaptation` is rejected for factual `fieldEvidence` and
  `holdEvidence`.

- [ ] **Step 5: Run the schema tests and verify they fail before implementation.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog_cli.py -q
  ```

  Expected: failures identify absent v2 registry/package, semantic, artwork,
  presentation, and extended evidence behavior.

- [ ] **Step 6: Implement immutable parsers and cross-file validation.**

  In `board_artwork.py`, implement frozen dataclasses for `NormalizedFrame`,
  `PathCommand`, `BoardShapeDocument`, `BoardLayerDocument`,
  `BoardHoldPieceDocument`, and `BoardArtworkDocument`. In `board_catalog.py`,
  add presentation, semantics, v2 evidence, `BoardPackage`, and v2 registry
  models. Reject unknown JSON keys at every schema level so typos never become
  ignored canonical content. Keep the v1 evidence parser only long enough for
  a clear migration diagnostic; v2 catalogs require v2 packages.

- [ ] **Step 7: Run focused and complete pipeline tests.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog_cli.py -q
  python3 -m pytest Tools/HangboardPipeline/tests -q
  ```

  Expected: all tests pass without reading `HangTen/` as canonical input.

- [ ] **Step 8: Commit the complete schema contract.**

  ```sh
  git add Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py Tools/HangboardPipeline/src/hangboard_vectorizer/board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py Tools/HangboardPipeline/tests/test_board_catalog_cli.py
  git commit -m "feat: define canonical board packages"
  git push
  ```

### Task 4: Migrate Compact II into one complete canonical package

**Files:**
- Modify: `Hangboards/catalog.json`
- Modify: `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Modify: `Hangboards/metolius-wood-grips-compact-ii/evidence.json`
- Create: `Hangboards/metolius-wood-grips-compact-ii/semantics.json`
- Create: `Hangboards/metolius-wood-grips-compact-ii/artwork.json`
- Move: `HangTen/Resources/Assets.xcassets/CompactBoard.imageset/WoodGripsCompactII.jpg` to `Hangboards/metolius-wood-grips-compact-ii/assets/WoodGripsCompactII.jpg`
- Create: `Hangboards/metolius-wood-grips-compact-ii/assets/CompactBoardIllustration.png`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_artwork.py`

**Interfaces:**
- Consumes: existing Compact II facts from `board.json`, semantic mappings from `BoardLibrary.json`/`PlanStorage.swift`, geometry from `MetoliusCompactIIDesign.swift`, and only the sources already recorded in its evidence document.
- Produces: one v2 Compact II package whose semantic IDs, hold IDs, frames, layers, shapes, treatments, and presentation values preserve current runtime behavior exactly.

- [ ] **Step 1: Record pre-migration Compact II invariants in tests.**

  Assert 19 physical holds; exact semantic mapping keys and values; stable
  generated symbol `compactII`; subtitle and optional photo asset name; exact
  canvas frame; exact silhouette command count; layer IDs/count; piece IDs,
  hold IDs, frames, treatment parameters, and path-command coordinates. Derive
  expected values by transcribing the current reviewed Swift and generated JSON
  into test literals before deleting either source.

- [ ] **Step 2: Retain the manufacturer reference and create the required screwless presentation asset.**

  Use `git mv` to place `WoodGripsCompactII.jpg` in the Compact II package as
  a byte-identical manufacturer-source reference. Inspect the current
  `CompactBoardIllustration.png`, then use the image-generation editing
  workflow with that local image as the reference to create the package-owned
  `assets/CompactBoardIllustration.png`. The edit prompt must require removal
  of all visible screw or mounting holes only; it must preserve the existing
  front-on crop, transparent/background treatment, canvas dimensions, board
  silhouette, proportions, wood color, every hold opening, and all other
  non-fastener details. Do not add branding, bolts, texture, shadows, holds,
  or other hardware.

  Visually compare the source and output at full resolution. Reject and
  regenerate any output with residual holes, changed hold boundaries, changed
  silhouette, altered board scale/crop, or invented details. Do not retain the
  old fastener-bearing illustration as a second package asset or runtime
  source. The new presentation PNG is an explicitly labeled visual adaptation,
  never evidence for physical facts or vector geometry.

- [ ] **Step 3: Create `semantics.json` from the currently shipped mapping.**

  Move the 11 Compact II mappings (`outer-jugs`, both edge sizes, both sloper
  groups, and all six pocket groups) byte-for-value from current app mappings.
  Add `semanticEvidence` mappings only to sources that identify the relevant
  physical contacts.

- [ ] **Step 4: Serialize the reviewed Swift design into fully expanded JSON.**

  Transcribe `canvasFrame`, `silhouette`, all layers, and all hold pieces from
  `MetoliusCompactIIDesign.swift`. Assign stable descriptive IDs to every layer
  that previously lacked one. Expand the local `addPair` mirroring into
  explicit right-side frames and mirrored path commands; do not store a helper
  expression or infer coordinates from the product photo.

- [ ] **Step 5: Move presentation fields into `board.json` and complete evidence.**

  Move subtitle, generated symbol, and optional photo asset declaration from
  Python/runtime overrides into `presentation`. Declare the screwless PNG as
  its `photoAsset` and retain the source JPG as a package asset. Add exact
  field, semantic, artwork, and asset evidence coverage: map the JPG to the
  official product page with its truthful source-media method and map the PNG
  to the same source using `external-generative-adaptation`. Do not change any
  physical hold fact.

- [ ] **Step 6: Advance the registry and validate the package.**

  Convert `Hangboards/catalog.json` to schema version 2 with global library
  metadata currently in `BoardLibrary.json` and a single Compact II package
  path. Run:

  ```sh
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py -q
  ```

  Expected: the v2 package passes, the package owns both image roles, and all
  pre-migration metadata/artwork invariants match. Complete a visual review of
  the package presentation PNG before proceeding: it has no screw holes and
  retains the reviewed board silhouette and every hold boundary.

- [ ] **Step 7: Commit the Compact II canonical package.**

  ```sh
  git add Hangboards Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py
  git commit -m "refactor: consolidate Compact II board source"
  git push
  ```

### Task 5: Gate and migrate the existing Rock Prodigy runtime board

**Files:**
- Create after audit passes: `Hangboards/trango-rock-prodigy-training-center/board.json`
- Create after audit passes: `Hangboards/trango-rock-prodigy-training-center/evidence.json`
- Create after audit passes: `Hangboards/trango-rock-prodigy-training-center/semantics.json`
- Create after audit passes: `Hangboards/trango-rock-prodigy-training-center/artwork.json`
- Modify after audit passes: `Hangboards/catalog.json`
- Create: `docs/source-audits/2026-08-11-rock-prodigy-board-package.md`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_artwork.py`

**Interfaces:**
- Consumes: the one other existing runtime board, `BoardCatalog.rockProdigyTrainingCenter`, its design in `RockProdigyTrainingCenterDesign.swift`, its plan semantics, and the four real sources named in `docs/TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md`.
- Produces only after audit approval: a complete evidence-backed package registered beside Compact II. A failed audit produces no package and no deletion; it blocks completion of the global single-source objective.

- [ ] **Step 1: Create a field-by-field audit before writing canonical JSON.**

  In the audit document, enumerate every board identity/dimension/presentation
  field, every physical hold fact, every semantic mapping, `silhouette`, every
  layer, and every hold piece. Map each item to the product page, manufacturer
  manual, depth guide, and/or product image already listed in the 2026-08-10
  audit. Mark normalized coordinates as
  `reviewed-human-authored-normalization` of the product image, not measured
  manufacturer geometry.

- [ ] **Step 2: Apply the truthfulness gate.**

  If any required shipped-board fact, semantic mapping, or artwork item lacks
  a real source, stop this task: do not add Rock Prodigy to `catalog.json`, do
  not delete its Swift implementation, and report the exact unsupported items
  for user review. Do not use generative-catalog outlines. The remaining plan
  cannot be declared complete while a shipped runtime board remains outside a
  package.

- [ ] **Step 3: Write failing preservation tests after the audit passes.**

  Assert the exact current board ID, 26 hold IDs and metadata values, semantic
  groups used by the intermediate routine, canvas frame, all expanded mirrored
  path commands, layer/piece IDs, frames, roles, and treatments. Assert that
  the two-piece board's overlapping pinch/sloper logical contacts remain
  explicit and evidence-mapped rather than collapsed.

- [ ] **Step 4: Create the four package files from audited current values.**

  Set `presentation.generatedSymbol` to
  `rockProdigyTrainingCenter`, omit `photoAsset` because the current runtime has
  none, and fully expand all mirrored geometry. Use no URL beyond the approved
  four-source set. Add field, hold, semantic, and artwork evidence mappings
  that reproduce the audit document.

- [ ] **Step 5: Register and validate Rock Prodigy.**

  Add `trango-rock-prodigy-training-center` to registry packages. Run:

  ```sh
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py -q
  ```

  Expected: both existing runtime boards are now complete validated packages
  and all preservation assertions pass.

- [ ] **Step 6: Commit the audited Rock Prodigy package.**

  ```sh
  git add Hangboards/trango-rock-prodigy-training-center Hangboards/catalog.json docs/source-audits/2026-08-11-rock-prodigy-board-package.md Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_board_artwork.py
  git commit -m "refactor: add audited Rock Prodigy board package"
  git push
  ```

### Task 6: Generate every runtime board artifact from packages

**Files:**
- Create: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_generation.py`
- Create: `Tools/HangboardPipeline/tests/test_board_generation.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`
- Delete after replacement: `_SWIFT_BOARD_OVERRIDES` in `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`
- Create: `scripts/generate-board-content.py`
- Modify: `scripts/export-board-catalog.py`
- Modify: `scripts/export-board-library.py`
- Modify: `scripts/export-board-catalog.sh`
- Regenerate: `HangTen/Models/GeneratedBoardCatalog.swift`
- Create: `HangTen/Models/GeneratedBoardSemantics.swift`
- Create: `HangTen/Views/GeneratedBoardDesignCatalog.swift`
- Regenerate: `HangTen/Resources/BoardLibrary.json`
- Generate/update: `HangTen/Resources/Assets.xcassets/<owned-board-imageset>/`

**Interfaces:**
- Consumes: only validated `CatalogDocument` and `BoardPackage` values plus package asset bytes.
- Produces: `GeneratedBoardContent.files: Mapping[str, bytes]`; atomic `write_generated_content()` and read-only `check_board_content()`.
- Compatibility export scripts delegate to the same pure renderer and select its output; they no longer merge current app JSON.

- [ ] **Step 1: Write failing pure-generation tests.**

  In a temporary repository containing only `Hangboards/` package fixtures,
  assert the generator renders all four primary outputs and optional imageset
  files. Do not copy any `HangTen/` input into the fixture. Assert stable output
  across two runs and insertion-order changes in input JSON.

  ```python
  first = generate_board_content(repo, catalog, tmp_path / "first").files
  second = generate_board_content(repo, catalog, tmp_path / "second").files
  assert first == second
  assert "HangTen/Views/GeneratedBoardDesignCatalog.swift" in first
  ```

- [ ] **Step 2: Write failing drift and ownership tests.**

  Assert `--check` reports a modified generated Swift file, missing JSON file,
  stale generator-owned imageset, or changed asset byte. Store owned imageset
  paths in a generated manifest rather than deleting arbitrary user assets.
  Assert generated headers name `Hangboards/catalog.json` and warn against hand
  editing.

- [ ] **Step 3: Write failing no-output-input regression tests.**

  Delete `BoardLibrary.json` and all generated Swift from a temporary checkout;
  generation must still succeed. Seed those files with conflicting subtitle,
  semantic mapping, hold frame, and design coordinates; rendered output must be
  unchanged. This test specifically prevents reintroducing
  `existing_boards_by_id()`/preserved-output defaults.

- [ ] **Step 4: Implement pure board, semantic, design, JSON, and asset rendering.**

  Render Swift literals for every supported enum, shape, expanded path command,
  frame, layer, hold piece, and treatment. `GeneratedBoardDesignCatalog` owns
  the board-ID lookup. Render `GeneratedBoardSemantics` as a board-ID keyed
  mapping using package semantic values. Copy optional package assets and
  generate deterministic `Contents.json` files. Sort packages only where order
  is semantically irrelevant; preserve canonical hold, layer, piece, and path
  order.

- [ ] **Step 5: Implement transactional write and read-only check modes.**

  Render into a `.context` temporary tree, validate all bytes, then replace the
  exact owned file set. On failure, leave current outputs untouched. In check
  mode, compare bytes and list every missing, stale, or unexpected owned output
  without writing.

- [ ] **Step 6: Replace old exporter merging and Python overrides.**

  Make all three compatibility wrappers invoke `board_generation.py`; remove
  `_SWIFT_BOARD_OVERRIDES`, `existing_boards_by_id`, `existing_holds_by_id`,
  and any code that copies `cueStyle`, `subtitle`, `photoAssetName`, or
  `semanticHolds` from current outputs.

- [ ] **Step 7: Generate and check outputs.**

  Run:

  ```sh
  python3 scripts/generate-board-content.py
  python3 scripts/generate-board-content.py --check
  python3 scripts/export-board-library.py --check
  scripts/export-board-catalog.sh --check
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_generation.py Tools/HangboardPipeline/tests/test_board_catalog_generation.py Tools/HangboardPipeline/tests/test_board_library_generation.py -q
  ```

  Expected: generation is idempotent and every compatibility check passes from
  canonical input alone.

- [ ] **Step 8: Commit deterministic generation.**

  ```sh
  git add Tools/HangboardPipeline scripts HangTen/Models/GeneratedBoardCatalog.swift HangTen/Models/GeneratedBoardSemantics.swift HangTen/Views/GeneratedBoardDesignCatalog.swift HangTen/Resources/BoardLibrary.json HangTen/Resources/Assets.xcassets
  git commit -m "feat: generate runtime boards from packages"
  git push
  ```

### Task 7: Remove handwritten app board definitions and consume generated data

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/PlanStorage.swift`
- Modify: `HangTen/Views/BoardDesignLanguage.swift`
- Modify: `HangTen/Views/BoardMapView.swift`
- Delete: `HangTen/Views/MetoliusCompactIIDesign.swift`
- Delete: `HangTen/Views/RockProdigyTrainingCenterDesign.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/PlanStorageTests.swift`
- Modify: `HangTenTests/BoardStorageTests.swift`
- Create: `HangTenTests/GeneratedBoardSourceTests.swift`
- Modify: `scripts/export-plan-library.sh`

**Interfaces:**
- Consumes: `GeneratedBoardCatalog.all`, `GeneratedBoardSemantics.byBoardID`, and `GeneratedBoardDesignCatalog.design(for:)`.
- Produces: generic app code with no duplicated physical board or semantic definitions; plan export obtains board mappings from generated semantics.

- [ ] **Step 1: Add failing runtime inventory and referential tests.**

  Assert `Set(BoardCatalog.all.map(\.id))` equals the board-library and generated
  design/semantics ID sets; every semantic hold resolves; every design's
  physical hold-ID set equals the model set; and the default board resolves.
  Preserve existing Compact II and Rock Prodigy plan resolution assertions.

- [ ] **Step 2: Add a failing source-boundary test.**

  Have `GeneratedBoardSourceTests` scan tracked handwritten Swift/Python source
  outside generated files and fail on the two board IDs, current hold IDs,
  `_SWIFT_BOARD_OVERRIDES`, `static let metoliusCompactII`, or
  `static let trangoRockProdigyTrainingCenter`. Exempt canonical JSON, generated
  files, tests, and historical docs.

- [ ] **Step 3: Point app aliases and lookups at generated definitions.**

  Keep `BoardCatalog.compactII` and `rockProdigyTrainingCenter` only if callers
  need source-compatible aliases, and define them solely as generated-symbol
  references. Define `BoardCatalog.all = GeneratedBoardCatalog.all`. Make
  `BoardMapView` use `GeneratedBoardDesignCatalog` directly or a generic alias
  with no handwritten dictionary.

- [ ] **Step 4: Replace built-in semantic dictionaries.**

  Remove `semanticHoldIDs` and `rockProdigySemanticHoldIDs` from
  `PlanStorage.swift`. Build `BoardMappingDefinition` values from
  `GeneratedBoardSemantics.byBoardID`, preserving plan JSON output. Include
  `GeneratedBoardSemantics.swift` in `export-plan-library.sh` compilation.

- [ ] **Step 5: Remove bespoke design files and update Xcode membership.**

  Delete both design files only after the generated design catalog compiles.
  Remove their file/build references and add the generated semantics/design
  source files to the app and test target as appropriate. Leave palette,
  rendering, highlight, and normalized-shape primitives in
  `BoardDesignLanguage.swift`.

- [ ] **Step 6: Verify model, design, plan, and build behavior.**

  Run:

  ```sh
  scripts/export-plan-library.sh --check
  python3 scripts/generate-board-content.py --check
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/GeneratedBoardSourceTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/BoardStorageTests
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  ```

  Expected: tests and build pass; `PlanLibrary.json` is byte-identical unless
  deterministic formatting changes were explicitly reviewed; source-boundary
  scan finds no second board definition.

- [ ] **Step 7: Commit generated-only app consumption.**

  ```sh
  git add -A HangTen HangTenTests HangTen.xcodeproj scripts/export-plan-library.sh
  git commit -m "refactor: consume generated board definitions"
  git push
  ```

### Task 8: Make Workbench edit and validate canonical package files

**Files:**
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_library.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/workbench_promotion.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/ios_promotion.py`
- Modify: `Tools/HangboardWorkbench/server.py`
- Modify: `Tools/HangboardWorkbench/workbench.js`
- Modify: `Tools/HangboardWorkbench/README.md`
- Modify: `Tools/HangboardPipeline/tests/test_board_library.py`
- Modify: `Tools/HangboardPipeline/tests/test_workbench_end_to_end.py`
- Modify: `Tools/HangboardPipeline/tests/test_workbench_promotion.py`
- Modify: `Tools/HangboardPipeline/tests/test_ios_promotion.py`
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`
- Modify: `Tools/HangboardWorkbench/tests/workbench*.test.js`

**Interfaces:**
- Consumes: validated `BoardPackage` values and the same generator/check interfaces as CI.
- Produces: human-reviewed edits to canonical package candidates followed by atomic package publication; it no longer proposes direct edits to generated Swift, JSON, or plan mappings.

- [ ] **Step 1: Write failing package-round-trip and promotion tests.**

  Open a fixture package, edit metadata, one semantic mapping, and one artwork
  piece, save, reload, and assert exact values and evidence coverage. Assert a
  promotion preview lists the four canonical package files plus an optional
  asset, never `GeneratedBoardCatalog.swift`, `BoardLibrary.json`,
  `PlanLibrary.json`, or bespoke design Swift.

- [ ] **Step 2: Write failing validation UI tests.**

  Assert missing evidence, unknown hold references, invalid normalized points,
  and generated drift appear as separate actionable Workbench diagnostics.
  Assert the UI labels geometry as human-reviewed normalization and contains no
  claim that photo conversion is authoritative.

- [ ] **Step 3: Refactor repository board publication.**

  Make `RepositoryBoardLibrary.publish()` stage and validate the complete
  package directory, then atomically replace that package and registry entry.
  Generate delivery artifacts only after canonical publication succeeds; if
  generation fails, roll back both package and owned output files.

- [ ] **Step 4: Replace direct iOS promotion targets.**

  Change `ios_promotion.py` from rendering app Swift/plan files to rendering a
  canonical package candidate with explicit evidence. Remove its hard-coded
  `_TARGET_PATHS` app file list and board-specific PlanLibrary rewrite. Keep
  preview tokens, conflict checks, rollback, and human approval behavior.

- [ ] **Step 5: Run Workbench verification.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_library.py Tools/HangboardPipeline/tests/test_workbench_end_to_end.py Tools/HangboardPipeline/tests/test_workbench_promotion.py Tools/HangboardPipeline/tests/test_ios_promotion.py Tools/HangboardWorkbench/tests/test_server.py -q
  node --test Tools/HangboardWorkbench/tests/workbench*.test.js
  swift test --package-path Tools/HangboardWorkbench/macos
  python3 scripts/generate-board-content.py --check
  ```

  Expected: publication and UI tests pass, and Workbench-generated packages
  reproduce checked-in runtime outputs.

- [ ] **Step 6: Commit canonical Workbench operation.**

  ```sh
  git add Tools/HangboardPipeline Tools/HangboardWorkbench
  git commit -m "refactor: edit canonical boards in Workbench"
  git push
  ```

### Task 9: Remove unsupported programmatic image workflows

**Files:**
- Delete: `docs/hangboard-generative-catalog/`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_flat_illustrations.py`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_outline_cli.py`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_outlines.py`
- Delete: `Tools/HangboardPipeline/src/hangboard_vectorizer/catalog_outline_sources.json`
- Delete: corresponding `test_catalog_flat_illustrations.py`, `test_catalog_outline_catalog.py`, and `test_catalog_outlines.py`
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
- Consumes: supported catalog/package validation, generation, review, promotion, release-check, benchmark, and Workbench operations.
- Produces: no catalog-outline API, flat renderer, source-tree generated catalog, or unknown-photo conversion path.

- [ ] **Step 1: Add failing command/route absence tests.**

  Assert `pyproject.toml` has no `hangboard-catalog-flat`,
  `hangboard-catalog-outlines`, or `hangboard-to-svg` entry point. Assert
  Workbench rejects catalog-source/outline arguments. Add a tracked active-file
  scan forbidding `hangboard-generative-catalog`, `hangboard-catalog-flat`,
  `hangboard-catalog-outlines`, `hangboard-to-svg`, and
  `experimental-recess-detection` outside history.

- [ ] **Step 2: Run tests and verify the retired surface is detected.**

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_catalog_outlines.py Tools/HangboardWorkbench/tests/test_server.py -q
  ```

  Expected: new assertions fail against current commands/routes.

- [ ] **Step 3: Remove the experimental assets, commands, implementations, and tests.**

  Delete only the listed retired workflow. Keep canonical package generation,
  known source-backed replay fixtures that support current tests, review,
  promotion, release checks, and Workbench operation. Do not delete a package
  asset moved and audited in Task 4.

- [ ] **Step 4: Remove catalog-outline mode from Workbench.**

  Remove catalog-specific session fields, discovery, load/save helpers, routes,
  and CLI arguments. Retain repository package and explicitly supplied reviewed
  run operation.

- [ ] **Step 5: Rewrite tool documentation around factual limits.**

  State: “The pipeline validates and exports source-backed board packages; it
  does not programmatically generate faithful board artwork or authoritative
  hold geometry from a photograph.” Describe any retained known-product replay
  only as an internal fixture.

- [ ] **Step 6: Verify retirement and retained operation.**

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
  node --test Tools/HangboardWorkbench/tests/workbench*.test.js
  python3 scripts/generate-board-content.py --check
  rg -n 'hangboard-generative-catalog|hangboard-catalog-flat|hangboard-catalog-outlines|hangboard-to-svg|experimental-recess-detection' .github Tools scripts Hangboards README.md AGENTS.md docs/ADDING_A_BOARD.md
  ```

  Expected: tests/check pass; `rg` exits `1` with no active matches.

- [ ] **Step 7: Commit retired tooling removal.**

  ```sh
  git add -A docs/hangboard-generative-catalog Tools/HangboardPipeline Tools/HangboardWorkbench
  git commit -m "chore: retire unsupported board image tooling"
  git push
  ```

### Task 10: Archive retired rationale and document the single-source workflow

**Files:**
- Move: the five 2026-08-08/09 experimental image plans listed in the prior plan to `docs/history/tooling/experimental-image-catalog/plans/`
- Move: the three 2026-08-08/09 experimental image specs listed in the prior plan to `docs/history/tooling/experimental-image-catalog/specs/`
- Create: `docs/history/tooling/experimental-image-catalog/README.md`
- Modify: `README.md`
- Modify: `docs/ADDING_A_BOARD.md`
- Modify: `AGENTS.md`
- Create: `Tools/HangboardPipeline/tests/test_documentation_paths.py`

**Interfaces:**
- Consumes: complete package schemas, generation/check commands, and retired-workflow decision.
- Produces: active docs that name `Hangboards/` as the only editable board source and history docs isolated from supported navigation.

- [ ] **Step 1: Add failing documentation assertions.**

  Assert active guides name all four package files, both supported tool roots,
  `python3 scripts/generate-board-content.py --check`, evidence coverage, and
  human-reviewed normalized artwork. Assert they say generated HangTen files
  are not edited manually and do not contain retired commands/catalog paths.

- [ ] **Step 2: Move historical plans/specifications with `git mv`.**

  Move only the eight image-experiment records identified in the original plan.
  Keep this amended design and plan active.

- [ ] **Step 3: Add the historical index.**

  Explain that original images were externally generated, local scripts only
  produced approximate derivatives, deleted binaries remain in Git history,
  and current board packages use reviewed normalized geometry with explicit
  evidence rather than automatic conversion.

- [ ] **Step 4: Rewrite active repository guidance.**

  Document the exact create/edit flow: collect sources; author field/hold,
  semantic, artwork, and optional asset mappings; validate the complete
  package; generate; review app rendering; run drift checks. Explicitly state
  that `BoardLibrary.json` and generated Swift are outputs, not templates.

- [ ] **Step 5: Verify documentation.**

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_documentation_paths.py -q
  test -f docs/history/tooling/experimental-image-catalog/README.md
  rg -n 'hangboard-generative-catalog|hangboard-to-svg|experimental-recess-detection' README.md docs/ADDING_A_BOARD.md AGENTS.md
  ```

  Expected: pytest/file check pass; `rg` exits `1` with no active matches.

- [ ] **Step 6: Commit documentation and history.**

  ```sh
  git add README.md docs/ADDING_A_BOARD.md AGENTS.md docs/history docs/superpowers Tools/HangboardPipeline/tests/test_documentation_paths.py
  git commit -m "docs: define single-source board workflow"
  git push
  ```

### Task 11: Enforce generated drift and validate release paths

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `.github/dependabot.yml` only if a stale path remains
- Modify: `Tools/HangboardPipeline/tests/test_ci_workflow.py`
- Modify: `Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_generation.py`

**Interfaces:**
- Consumes: consolidated tool roots, complete package validator, generated-content check, Workbench tests, and iOS build.
- Produces: CI/release automation that fails on canonical/package invalidity, output drift, handwritten board definitions, retired tooling, or stale paths.

- [ ] **Step 1: Add failing workflow assertions.**

  Assert CI installs `Tools/HangboardPipeline[dev]`, runs package validation and
  `generate-board-content.py --check` before Xcode tests, and scans for second
  definitions. Assert Workbench release installs the pipeline and packages
  `Tools/HangboardWorkbench`. Forbid both legacy tool roots and all retired
  command names.

- [ ] **Step 2: Update workflows to the final validation surface.**

  Add the canonical validation/generation check without compatibility aliases.
  Preserve the existing Workbench release build and current iOS CI behavior.

- [ ] **Step 3: Run the full repository validation set.**

  ```sh
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  python3 scripts/generate-board-content.py --check
  python3 -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
  node --test Tools/HangboardWorkbench/tests/*.test.js
  swift test --package-path Tools/HangboardWorkbench/macos
  scripts/export-plan-library.sh --check
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  git diff --check
  git status --short
  ```

  Expected: all commands pass; generated checks are silent; status contains
  only intended final workflow/test changes before commit.

- [ ] **Step 4: Manually verify both board renderings.**

  Launch an isolated iOS Simulator, display Compact II and Rock Prodigy board
  maps, and compare silhouettes, layers, hold hit regions, and active/preview
  highlighting with pre-migration screenshots. Store temporary captures under
  `.context/`, not in the repository. Any visual difference requires correcting
  canonical `artwork.json` or generator logic and rerunning all checks.

- [ ] **Step 5: Commit and push final integration.**

  ```sh
  git add .github Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests
  git commit -m "ci: enforce canonical board generation"
  git push
  ```

## Final acceptance audit

Before declaring the branch complete, run these read-only scans in addition to
Task 11:

```sh
rg -n 'metolius\.wood-grips-compact-ii|trango\.rock-prodigy-training-center|jug-left|trango\.rptc\.' HangTen Tools scripts \
  -g '!HangTen/Models/GeneratedBoardCatalog.swift' \
  -g '!HangTen/Models/GeneratedBoardSemantics.swift' \
  -g '!HangTen/Views/GeneratedBoardDesignCatalog.swift' \
  -g '!HangTen/Resources/BoardLibrary.json' \
  -g '!HangTen/Resources/PlanLibrary.json' \
  -g '!**/tests/**'
python3 scripts/generate-board-content.py --check
git diff --check
```

The `rg` scan must have no board-definition matches in active handwritten
application/pipeline code. Intentional routine source labels or documentation
references must be inspected individually; they are not board definitions, but
they may not repeat physical mappings or geometry. The generation check must
prove every runtime board artifact is reproducible from package input alone.
