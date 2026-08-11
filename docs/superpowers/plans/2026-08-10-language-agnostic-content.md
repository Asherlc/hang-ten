# Language-Agnostic Plan and Board Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load factual board and hold content from versioned JSON while preserving existing plan resolution, custom routines, and SwiftUI board rendering behavior.

**Architecture:** Add a `BoardLibraryStore` that decodes a standalone `BoardLibrary.json` into runtime `TrainingBoard` values. Move shared semantic mapping definitions to a content-model boundary so board-owned mappings can feed the existing plan resolver, while retaining legacy plan `boardMappings` as a compatibility input. Keep `BoardDesign` and `BoardDesignCatalog` in Swift and continue selecting artwork by stable board ID.

**Tech Stack:** Swift 5, Foundation `Codable`, SwiftUI runtime models, XCTest, Xcode project resources, JSON fixtures, shell-based export/check scripts.

## Global Constraints

- Use stable board and hold IDs; do not rename existing Compact II IDs.
- Store durations as seconds, normalized geometry as finite `0...1` values, and enum values as language-neutral strings.
- Keep SwiftUI paths, gradients, shadows, palettes, and highlight treatments out of the JSON content schema.
- Preserve current plan IDs, step ordering, timing, targets, resolved hold IDs, custom-routine persistence, and board artwork.
- Validate schema version, required metadata, uniqueness, numeric ranges, and cross-references before exposing runtime content.
- Run the relevant XCTest subset after every task and the full iOS build before completion.
- Commit each independently testable task and push every new commit to the tracked remote branch.

---

### Task 1: Define the board JSON schema and store

**Files:**
- Create: `HangTen/Models/BoardStorage.swift`
- Create: `HangTen/Resources/BoardLibrary.json`
- Create: `HangTenTests/BoardStorageTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Produces `BoardLibraryMetadata`, `BoardHoldDefinition`, `BoardDefinition`, `BoardLibraryDefinition`, `BoardLibraryStoreError`, `BoardLibraryStore`, and `BoardLibraryValidator`.
- `BoardLibraryStore.init(data: Data, decoder: JSONDecoder = JSONDecoder()) throws` decodes and validates a document.
- `BoardLibraryStore.init(contentsOf: URL, decoder: JSONDecoder = JSONDecoder()) throws` loads a document from disk.
- `BoardLibraryStore.encodedData(prettyPrinted: Bool = false) throws -> Data` produces deterministic JSON.
- `BoardLibraryStore.boards: [TrainingBoard]` exposes resolved runtime boards.

- [ ] **Step 1: Write failing tests for board decoding and validation**

Add tests that decode a minimal board fixture, assert conversion of normalized numeric frames to `HoldFrame`, and assert that the store rejects duplicate board IDs, duplicate hold IDs, out-of-range frame values, non-positive aspect ratios, invalid finger capacities, and unknown hold IDs in `semanticHolds`.

```swift
func testBoardLibraryDecodesCompactBoardMetadataAndHoldFrame() throws {
    let store = try BoardLibraryStore(data: compactFixture)
    let board = try XCTUnwrap(store.boards.first)
    let hold = try XCTUnwrap(board.holds.first)

    XCTAssertEqual(board.id, "fixture.board")
    XCTAssertEqual(hold.id, "fixture.hold")
    XCTAssertEqual(hold.frame.rect, CGRect(x: 0.1, y: 0.2, width: 0.3, height: 0.4))
}
```

- [ ] **Step 2: Run the focused test and verify it fails for the missing store**

Run:

```sh
xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData test -only-testing:HangTenTests/BoardStorageTests
```

Expected: compilation failure because `BoardLibraryStore` and its definitions do not exist.

- [ ] **Step 3: Implement Codable definitions, conversion, and validation**

Use `Double` in JSON-facing frame definitions and convert to `CGFloat` only when constructing `HoldFrame`. Preserve the existing `BoardHold` initializer defaults for omitted optional fields. Define board-owned semantic mappings using the existing mapping shape (`holdIDs` or `kind`, never both), and produce actionable validation paths such as `boards[0].holds[1].frame.x`.

`BoardLibraryStore` must expose only validated boards. `encodedData` must use `.prettyPrinted` and `.sortedKeys` when requested, matching the plan-store export behavior.

- [ ] **Step 4: Add the canonical Compact II JSON fixture and Xcode resource entry**

Copy every current Compact II value from `BoardCatalog.compactII` into `BoardLibrary.json`, including all hold IDs, frames, sizes, features, product URL, and photo asset name. Add the resource to the HangTen target and test target resource handling as needed.

- [ ] **Step 5: Run the focused tests and verify they pass**

Run the focused `BoardStorageTests` command from Step 2. Expected: all board decoding, round-trip, and validation tests pass.

- [ ] **Step 6: Commit the task**

```sh
git add HangTen/Models/BoardStorage.swift HangTen/Resources/BoardLibrary.json HangTenTests/BoardStorageTests.swift HangTen.xcodeproj/project.pbxproj
git commit -m "feat: add versioned board content store"
git push
```

### Task 2: Make the runtime board catalog JSON-backed

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:276-811`
- Modify: `HangTen/Models/BoardStorage.swift`
- Modify: `HangTen/Models/BoardStorage.swift` tests or `HangTenTests/BoardStorageTests.swift`
- Modify: `HangTen/Views/MetoliusCompactIIDesign.swift`

**Interfaces:**
- `BoardCatalog.all` remains `[TrainingBoard]` for compatibility.
- `BoardCatalog.board(for:)` keeps its current fallback behavior.
- `BoardLibraryStore.builtIn` loads `BoardLibrary.json` from `Bundle.main` or the model test bundle, with a narrowly scoped legacy fallback for resource-less command-line tools until Task 5 removes it.

- [ ] **Step 1: Write failing tests proving the production catalog comes from the JSON document**

Add a test that loads the checked-in board document and compares `BoardCatalog.all` against it by board ID, hold ID, frame, size, features, and metadata. Add a test that the Compact II design's rendered hold IDs equal the loaded board's hold IDs.

- [ ] **Step 2: Run the focused tests and verify the current hard-coded catalog is detected**

Run `BoardStorageTests` and the existing design/catalog tests. Expected: the new source-of-truth assertion fails until `BoardCatalog` delegates to `BoardLibraryStore`.

- [ ] **Step 3: Replace the Compact II production literals with a JSON-backed facade**

Make `BoardCatalog.all` resolve `BoardLibraryStore.builtIn.boards`. Preserve `compactII` as a computed/static compatibility value and preserve `compactIIFlatSloperHoldIDs` as a derived list from the loaded board. Keep test-only fixture construction possible through explicit `TrainingBoard` initializers.

- [ ] **Step 4: Preserve artwork registration by stable board ID**

Keep `BoardDesignCatalog` unchanged except where needed to remove references to deleted literal catalog constants. Its DEBUG assertion must compare loaded factual hold IDs with `BoardDesign` hold IDs and continue to pass.

- [ ] **Step 5: Run focused tests and the app build**

Run the board tests, existing plan-storage tests, and:

```sh
xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -derivedDataPath .context/DerivedData build
```

Expected: the loaded catalog and artwork remain behaviorally identical.

- [ ] **Step 6: Commit the task**

```sh
git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardStorage.swift HangTen/Views/MetoliusCompactIIDesign.swift HangTenTests
git commit -m "refactor: load board catalog from JSON"
git push
```

### Task 3: Feed board-owned semantic mappings into plan resolution

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/PlanStorage.swift`
- Modify: `HangTen/Models/BoardStorage.swift`
- Modify: `HangTenTests/PlanStorageTests.swift`
- Modify: `HangTenTests/BoardStorageTests.swift`

**Interfaces:**
- `TrainingBoard` gains a defaulted runtime semantic mapping property so existing test initializers remain source-compatible.
- `PlanLibraryStore.init(definition:availableBoards:)` remains source-compatible.
- `PlanLibraryStore` merges board-owned mappings when a plan document lacks a mapping for a selected board, while explicit legacy `boardMappings` retain precedence during migration.

- [ ] **Step 1: Write failing tests for board-owned semantic resolution**

Create a board fixture whose JSON defines `semanticHolds["fixture-edge"]`, create a plan targeting `{ "semantic": "fixture-edge" }` without a plan-level `boardMappings` entry, and assert that the resolved `WorkoutStep.targets` contains the expected physical hold IDs. Add a precedence test showing an explicit legacy plan mapping wins over a board-owned mapping.

- [ ] **Step 2: Run the focused tests and verify missing mapping failures**

Run `PlanStorageTests` and `BoardStorageTests`. Expected: the new board-owned semantic test fails with the existing missing-semantic-target error.

- [ ] **Step 3: Move shared semantic mapping types to the content-model boundary**

Avoid duplicate Codable shapes. Reuse one definition for board JSON and plan-library compatibility mappings, preserving the existing encoded keys `holdIDs`, `kind`, `boardID`, and `semanticHolds`. Add the mapping to resolved `TrainingBoard` values with an empty default for hand-built fixtures.

- [ ] **Step 4: Update plan validation and resolution**

When validating a plan library, use explicit `library.boardMappings` first and board-owned mappings second. Validate board-owned mappings against the loaded board's hold IDs. When resolving `.semantic` or `.semantics`, query the selected board's effective mapping before throwing `missingSemanticTarget`.

- [ ] **Step 5: Run focused regression tests**

Run all plan-storage and board-storage tests. Expected: old JSON with plan-level mappings still passes, new JSON with board-owned mappings resolves correctly, and all existing resolved plan snapshots remain unchanged.

- [ ] **Step 6: Commit the task**

```sh
git add HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift HangTen/Models/BoardStorage.swift HangTenTests/PlanStorageTests.swift HangTenTests/BoardStorageTests.swift
git commit -m "feat: resolve plan targets from board semantics"
git push
```

### Task 4: Migrate built-in plan content and custom-routine dependencies

**Files:**
- Modify: `HangTen/Models/PlanStorage.swift`
- Modify: `HangTen/Models/CustomRoutineStore.swift`
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTenTests/PlanStorageTests.swift`
- Modify: `HangTenTests/CustomRoutineStoreTests.swift`
- Modify: `HangTenTests/CustomRoutineAppStoreTests.swift`

**Interfaces:**
- `PlanLibraryStore` receives explicit loaded boards internally while preserving its public initializer defaults.
- `CustomRoutineStore` validates and resolves against the same board instances used by the app.
- `AppStore` continues to expose `plans`, `board(for:)`, `holdIDs(for:on:)`, and custom routine behavior without UI changes.

- [ ] **Step 1: Write failing integration tests for explicit board injection**

Add a test that constructs a `BoardLibraryStore` from fixture JSON, passes its boards into a `PlanLibraryStore`, and confirms a generic plan is compatible only when its semantic targets resolve. Add a custom-routine test that uses a non-singleton board fixture and confirms validation and resolution use that board.

- [ ] **Step 2: Run the focused tests and verify current implicit-catalog behavior**

Run `PlanStorageTests`, `CustomRoutineStoreTests`, and `CustomRoutineAppStoreTests`. Expected: the explicit-injection tests fail until stores use the supplied board collection consistently.

- [ ] **Step 3: Thread the loaded board collection through built-in and custom stores**

Keep the default arguments for existing callers, but have the default resolve once from `BoardLibraryStore.builtIn`. Ensure plan validation, target resolution, compatibility filtering, custom routine validation, and custom routine plan generation all use the same board collection rather than independently reading a catalog singleton.

- [ ] **Step 4: Preserve the existing built-in plan output**

Keep `PlanLibrary.json` as the bundled plan resource and retain the current `scripts/export-plan-library.sh --check` drift check. Remove only the board-specific Swift literals that are now redundant; do not change the plan schema or workout timing.

- [ ] **Step 5: Run integration tests and export validation**

Run the focused test suites and:

```sh
scripts/export-plan-library.sh --check
```

Expected: the checked-in plan JSON remains deterministic and all custom routine behavior remains green.

- [ ] **Step 6: Commit the task**

```sh
git add HangTen/Models/PlanStorage.swift HangTen/Models/CustomRoutineStore.swift HangTen/Models/AppStore.swift HangTenTests
git commit -m "refactor: share JSON-backed boards across routine stores"
git push
```

### Task 5: Remove the legacy board source and finalize documentation

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/BoardStorage.swift`
- Modify: `scripts/`
- Modify: `docs/ADDING_A_BOARD.md`
- Modify: `README.md`
- Modify: `HangTenTests/BoardStorageTests.swift`
- Modify: `HangTenTests/PlanStorageTests.swift`

**Interfaces:**
- Add a deterministic board export/check command parallel to `scripts/export-plan-library.sh` if needed to verify `BoardLibrary.json` against the source-audited migration fixture.
- Document JSON board authoring, schema validation, stable IDs, semantic mappings, and the continued SwiftUI artwork boundary.

- [ ] **Step 1: Write failing tests that forbid production dependence on the legacy board literal**

Add a test or source-level check that the bundled board document is the source used for `BoardCatalog.all`, and that its board/hold inventory matches the artwork registry. Keep only an explicitly named resource-less tooling fallback if the plan export command still requires one.

- [ ] **Step 2: Run the focused tests and identify remaining legacy references**

Run the board and plan-storage tests, then:

```sh
rtk rg -n "BoardCatalog\.compactII|BoardCatalog\.all|BuiltInBoard|BoardLibrary" HangTen scripts docs
```

Use the results to distinguish compatibility API references from production data literals.

- [ ] **Step 3: Delete the production Compact II data literals and keep compatibility APIs**

Remove the hard-coded hold array and metadata construction from `TrainingModels.swift`. Keep lightweight API compatibility only where callers still need `BoardCatalog.compactII` or `BoardCatalog.board(for:)`; those APIs must delegate to `BoardLibraryStore.builtIn`.

- [ ] **Step 4: Add deterministic board export/check support**

Make the checked-in JSON reproducible from the migration fixture or store encoder, use sorted keys and stable array ordering, and fail `--check` when the committed `BoardLibrary.json` differs from the generated document. The check must not overwrite the working tree.

- [ ] **Step 5: Update authoring documentation**

Update `README.md` and `docs/ADDING_A_BOARD.md` to identify `BoardLibrary.json` as the factual source of truth, explain semantic mappings and stable IDs, and state that bespoke SwiftUI `BoardDesign` artwork remains separate and must cover every loaded hold ID.

- [ ] **Step 6: Run the complete verification suite**

Run:

```sh
xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -derivedDataPath .context/DerivedData test
xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -derivedDataPath .context/DerivedData build
scripts/export-plan-library.sh --check
```

Expected: zero test failures, a successful simulator build, deterministic plan export validation, and no changed files from check-only commands.

- [ ] **Step 7: Commit the task**

```sh
git add HangTen README.md docs/ADDING_A_BOARD.md scripts HangTenTests
git commit -m "chore: finalize portable plan and board content"
git push
```

## Final Review Checklist

- [ ] Review the complete diff for schema drift, accidental UI changes, and duplicate sources of truth.
- [ ] Confirm every new production commit is pushed to the tracked remote branch.
- [ ] Verify `git status --short` is clean after tests and check-only commands.
