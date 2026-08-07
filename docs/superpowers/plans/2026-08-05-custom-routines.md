# Custom Routines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local custom-routine creation, duplication, editing, ordering, deletion, and board/generic targeting while sending every routine through the shared literal-step workout interfaces.

**Architecture:** Keep the bundled `PlanLibrary.json` catalog immutable and add a versioned `CustomRoutineStore` for user definitions. Normalize all built-in and duplicated multi-part steps into literal single-segment `WorkoutStep` values, resolve custom definitions into the same `TrainingPlan` type, and let `AppStore` compose the two collections. Add a pure draft model for testable editor mutations, then wire it into SwiftUI Plans/detail/editor views.

**Tech Stack:** Swift 6-compatible SwiftUI, Foundation, Codable, XCTest, Xcode 26, iOS 17.0+, `xcodebuild`, and the repository’s isolated-simulator workflow.

## Global Constraints

- Custom routines are local-only in v1. No export, import, sync, or sharing.
- Users can create from scratch or duplicate a built-in or custom routine.
- Custom routines can be edited, reordered, and deleted. Built-in routines remain read-only.
- A routine has a required name, an optional description, optional difficulty, optional category, and optional comma-separated tags.
- Difficulty and category use the existing picker vocabularies. Tags are free text, normalized by trimming, removing empty entries, and de-duplicating.
- A routine has a fixed target mode chosen at creation: board-specific exact hold IDs or generic hold kinds/features.
- The target mode cannot change after creation. A duplicate inherits its source mode.
- Every runtime `WorkoutStep` contains at most one timing segment after normalization.
- Fixed work/rest segments become literal rows in order; maximum-effort stopwatch behavior remains a single stopwatch step with its source duration cap.
- `AppStore.plans`, board compatibility, hold resolution, filters, favorites, detail, workout, audio, activity recording, HealthKit, and session logging remain shared interfaces for built-in and custom plans.
- A generic routine is compatible only when every target resolves on the selected board and must resolve on at least one registered board before saving.
- Invalid custom data must never prevent built-in plans from loading.
- Keep the minimum deployment target at iOS 17.0 and do not add third-party dependencies.
- Use `rtk` for every repository shell command and run a failing focused test before each production behavior implementation.
- Use a workspace-owned simulator only: its name must begin with `Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME`, its UUID must be recorded in `.context/conductor-owned-simulators`, and every simulator command must use that explicit UUID rather than `booted`.
- Put build output, test results, logs, screenshots, and temporary review files under `.context`.
- Install an exit cleanup trap for any simulator created by a task, invoke `scripts/conductor-resource-cleanup.sh archive`, verify the exact owned simulator is deleted, and leave shared or unknown resources untouched.
- Each implementation task is dispatched to a fresh subagent and receives a separate implementation/review checkpoint.

## File map

- `HangTen/Models/WorkoutStepNormalization.swift` — literalizes multi-segment runtime steps into ordered one-segment steps while preserving stopwatch steps.
- `HangTen/Models/CustomRoutineStore.swift` — Codable custom definitions, target modes, validation, local persistence, duplicate conversion, and custom-plan resolution.
- `HangTen/Models/CustomRoutineDraft.swift` — pure editor state and add/remove/reorder/tag-normalization behavior.
- `HangTen/Models/TrainingModels.swift` — custom provenance, optional source URL support, and user-facing labels for phase/timing/feature pickers.
- `HangTen/Models/PlanStorage.swift` — shared metadata validation, definition-to-runtime normalization integration, and reusable step/target conversion.
- `HangTen/Models/AppStore.swift` — injectable custom store, combined plan collection, custom CRUD, metadata lookup, and custom persistence errors.
- `HangTen/Models/PlanFilters.swift` — unchanged matching semantics, with custom metadata supplied through `AppStore`.
- `HangTen/Views/CustomRoutineEditorView.swift` — routine header form, target-mode selection, board/feature target editing, step editing, and save errors.
- `HangTen/Views/RootView.swift` — Plans custom section/create action, detail edit/duplicate/delete actions, custom source card, and navigation to the editor.
- `HangTenTests/WorkoutStepNormalizationTests.swift` — literalization order, IDs, durations, and stopwatch preservation.
- `HangTenTests/CustomRoutineStoreTests.swift` — Codable, validation, CRUD, corruption recovery, target modes, and custom resolution.
- `HangTenTests/CustomRoutineAppStoreTests.swift` — combined plans, compatibility, metadata/filter lookup, duplicate/edit/delete behavior.
- `HangTenTests/CustomRoutineDraftTests.swift` — editor mutations, target-mode immutability, and tag normalization.
- `HangTen.xcodeproj/project.pbxproj` — manually register each new production/test source in the correct groups and source phases.
- `docs/IOS_SIMULATOR_VALIDATION.md` — reference only; do not change unless the implemented flow requires a new documented review route.

---

### Task 1: Normalize all plans into literal one-segment workout steps

**Files:**
- Create: `HangTen/Models/WorkoutStepNormalization.swift`
- Create: `HangTenTests/WorkoutStepNormalizationTests.swift`
- Modify: `HangTen/Models/PlanStorage.swift` at `PlanDefinitionResolver.resolve`
- Modify: `HangTen.xcodeproj/project.pbxproj` in the PBXBuildFile, PBXFileReference, Models group, HangTenTests group, and both PBXSourcesBuildPhase sections.

**Interfaces:**
- Produces `WorkoutStepNormalizationError: Error, Equatable` with `unsupportedCompoundTiming(stepID: String, segmentIndex: Int)`.
- Produces `WorkoutStepNormalizer.expand(_:) throws -> [WorkoutStep]`.
- `WorkoutStepNormalizer.expand(_:)` preserves a step with zero or one segment, including `.stopwatch` and `.undefined` timing.
- For a multi-segment step, every segment must be fixed; each work segment becomes a work step and each rest segment becomes a generated rest step. Derived IDs use `"\(sourceID).segment-\(index + 1)"` and numbers are assigned after expansion.
- `PlanDefinitionResolver.resolve(_:)` appends normalized outputs rather than appending a compound `WorkoutStep`.

**Consumes:** Existing `WorkoutStep`, `WorkoutSegment`, `WorkoutSegmentKind`, `WorkoutSegmentTiming`, and `WorkoutStepDefinition` values.

**Produces for later tasks:** Every plan returned by `PlanLibraryStore.plan(id:)` has at most one segment per step; `CustomRoutineStore` can duplicate `TrainingPlan.steps` without preserving a compound editor-only representation.

- [ ] **Step 1: Register the new test source and write the failing tests.**

Add `WorkoutStepNormalizationTests.swift` to the HangTenTests group/source phase. Write these behaviors before adding the production normalizer:

```swift
import XCTest
@testable import HangTen

final class WorkoutStepNormalizationTests: XCTestCase {
    func testFixedWorkAndRestSegmentsBecomeLiteralStepsInOrder() throws {
        let source = WorkoutStep(
            id: "repeaters",
            number: 4,
            title: "Repeaters",
            instruction: "Hang, then recover.",
            accessory: "20s work · 10s rest",
            duration: 30,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 20),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
            ],
            gripType: .halfCrimp,
            timedWorkDuration: 20
        )

        let result = try WorkoutStepNormalizer.expand(source)

        XCTAssertEqual(result.map(\.id), ["repeaters.segment-1", "repeaters.segment-2"])
        XCTAssertEqual(result.map(\.duration), [20, 10])
        XCTAssertEqual(result.map(\.phase), [.hang, .rest])
        XCTAssertEqual(result.map { $0.segments.count }, [1, 1])
        XCTAssertEqual(result[0].targets, [.kind(.edge)])
        XCTAssertTrue(result[1].targets.isEmpty)
    }

    func testSingleStopwatchStepRemainsOneStepWithItsCap() throws {
        let source = WorkoutStep(
            id: "max",
            number: 1,
            title: "Maximum hang",
            instruction: "Hang as long as possible.",
            accessory: "Up to 60s",
            duration: 60,
            phase: .hang,
            targets: [.feature(.roundSloper)],
            segments: [WorkoutSegment(
                kind: .work,
                target: .feature(.roundSloper),
                timing: .stopwatch,
                duration: nil
            )],
            gripType: .sloper
        )

        let result = try WorkoutStepNormalizer.expand(source)

        XCTAssertEqual(result, [source])
        XCTAssertEqual(result[0].segments[0].timing, .stopwatch)
        XCTAssertEqual(result[0].duration, 60)
    }

    func testCompoundNonFixedTimingIsRejected() {
        let source = WorkoutStep(
            id: "invalid",
            number: 1,
            title: "Invalid compound",
            instruction: "Invalid",
            accessory: "",
            duration: 60,
            phase: .hang,
            targets: [.kind(.edge)],
            segments: [
                WorkoutSegment(kind: .work, target: .kind(.edge), timing: .stopwatch, duration: nil),
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
            ]
        )

        XCTAssertThrowsError(try WorkoutStepNormalizer.expand(source)) { error in
            XCTAssertEqual(
                error as? WorkoutStepNormalizationError,
                .unsupportedCompoundTiming(stepID: "invalid", segmentIndex: 0)
            )
        }
    }
}
```

- [ ] **Step 2: Run the focused test target and verify the red failure.**

With `HANG_TEN_TEST_DEVICE_UDID` set to this workspace’s owned simulator UUID, run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/WorkoutStepNormalizationTests
```

Expected result: compilation fails because `WorkoutStepNormalizer` and its error type do not exist. Do not change the test to accommodate the missing implementation.

- [ ] **Step 3: Implement the minimal normalizer and resolver integration.**

Create `WorkoutStepNormalization.swift`. Return `[step]` for zero/one segments. For a compound step, require fixed timing and a non-nil duration for every segment. Copy source title/instruction/accessory/phase/targets/grip for work rows; create rest rows with title `Rest`, instruction `Step off the board, shake out, and breathe.`, accessory `"\(Int(duration))s rest"`, phase `.rest`, empty targets, and no grip. Put each original segment in the output row’s one-element `segments` array. In `PlanDefinitionResolver.resolve`, build the current resolved step, call the normalizer, and append each output with `withNumber(steps.count + 1)`.

- [ ] **Step 4: Run focused and regression tests.**

Run the focused command from Step 2, then run the existing plan-storage and timeline tests:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/WorkoutStepNormalizationTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/WorkoutTimelineTests
```

Expected result: all targeted tests pass. Existing built-in plans must still resolve, and the normalizer must not alter the already-flat Metolius step duration totals.

- [ ] **Step 5: Commit the normalization deliverable.**

```sh
rtk git add HangTen/Models/WorkoutStepNormalization.swift HangTen/Models/PlanStorage.swift HangTenTests/WorkoutStepNormalizationTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: normalize routines into literal workout steps"
```

---

### Task 2: Add validated local custom-routine definitions and persistence

**Files:**
- Create: `HangTen/Models/CustomRoutineStore.swift`
- Create: `HangTenTests/CustomRoutineStoreTests.swift`
- Modify: `HangTen/Models/TrainingModels.swift` to add `RoutineProvenance.custom`, optional `TrainingPlan.sourceURL`, and picker labels/conformance for `HoldFeature`, `WorkoutPhase`, and `WorkoutSegmentTiming`.
- Modify: `HangTen/Models/PlanStorage.swift` to make `PlanMetadata.sourceURL` optional, allow nil only for custom provenance, and expose reusable `WorkoutStepDefinition`/`WorkoutTargetDefinition` conversion.
- Modify: `HangTen.xcodeproj/project.pbxproj` to register both new Swift files.

**Interfaces:**
- Produces `CustomRoutineTargetMode: Codable, Hashable` with `.boardSpecific(boardID: String)` and `.generic`.
- Produces `CustomRoutineDefinition: Codable, Hashable, Identifiable` with `id`, `title`, `subtitle`, `difficulty`, `category`, `tags`, `targetMode`, and `[WorkoutStepDefinition] steps`.
- Produces `CustomRoutineLibrary: Codable, Hashable` with `schemaVersion` and `routines`; current custom schema is `1`.
- Produces `CustomRoutineStoring`:

  ```swift
  protocol CustomRoutineStoring: AnyObject {
      var routines: [CustomRoutineDefinition] { get }
      var persistenceError: String? { get }
      func save(_ routine: CustomRoutineDefinition) throws
      func delete(id: String) throws
  }
  ```

- Produces `CustomRoutineStore(defaults:key:availableBoards:)`, using the UserDefaults key `HangTen.customRoutines.v1` by default.
- Produces `CustomRoutineValidationIssue: Error, Equatable` and `CustomRoutineValidator.issues(for:availableBoards:)` for all save rules in the spec.
- Produces `CustomRoutineStore.plan(for:) throws -> TrainingPlan` and `CustomRoutineStore.definition(from:metadata:id:) throws -> CustomRoutineDefinition` for shared runtime resolution and duplication.
- `TrainingPlan.sourceURL` and `PlanMetadata.sourceURL` become optional. Existing built-in callers still pass their HTTP(S) URLs; custom plans pass nil.
- `RoutineProvenance.custom.label` is `Custom`; its detail is `Created in Hang Ten.`.

**Consumes:** Task 1’s one-segment runtime output and existing `WorkoutStepDefinition`/target definitions.

**Produces for later tasks:** A validated, Codable, local custom definition store and the exact types used by AppStore and the editor.

- [ ] **Step 1: Register the new test source and write failing persistence/validation tests.**

Add `CustomRoutineStoreTests.swift` to the HangTenTests group/source phase. Use isolated `UserDefaults(suiteName:)` values and remove each persistent domain in `defer`. Start with these behaviors:

```swift
import XCTest
@testable import HangTen

final class CustomRoutineStoreTests: XCTestCase {
    func testBoardSpecificDefinitionRoundTripsAndResolvesToTrainingPlan() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }

        let definition = CustomRoutineDefinition(
            id: "custom.board",
            title: "Edge strength",
            subtitle: "Short edge work",
            difficulty: "Advanced",
            category: "strength",
            tags: ["custom", "edges"],
            targetMode: .boardSpecific(boardID: BoardCatalog.compactII.id),
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Hang",
                    instruction: "Hang from the 19 mm edges.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    targets: [.holdIDs(["edge-19-left", "edge-19-right"])],
                    gripType: .halfCrimp,
                    activeDuration: 10
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines, [definition])
        let plan = try reloaded.plan(for: definition)
        XCTAssertEqual(plan.id, definition.id)
        XCTAssertEqual(plan.title, definition.title)
        XCTAssertEqual(plan.steps[0].targets, [.ids("edge-19-left", "edge-19-right")])
        XCTAssertEqual(plan.provenance, .custom)
        XCTAssertNil(plan.sourceURL)
    }

    func testGenericDefinitionRequiresTargetsThatResolveOnARegisteredBoard() throws {
        let definition = CustomRoutineDefinition(
            id: "custom.generic",
            title: "Generic edge work",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Edge hang",
                    instruction: "Hang.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    targets: [.feature(.mediumEdge, fallbacks: [])],
                    activeDuration: 10
                )
            ]
        )

        XCTAssertTrue(CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all).isEmpty)
    }

    func testValidationRejectsBlankNameMissingTargetsAndInvalidDuration() {
        let definition = CustomRoutineDefinition(
            id: "custom.invalid",
            title: "   ",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Hang",
                    instruction: "Hang.",
                    accessory: "",
                    duration: 0,
                    phase: .hang,
                    targets: []
                )
            ]
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.emptyTitle))
        XCTAssertTrue(issues.contains(.invalidDuration(stepIndex: 0)))
        XCTAssertTrue(issues.contains(.missingTargets(stepIndex: 0)))
    }

    func testCorruptStoredDataLoadsEmptyAndPublishesPersistenceError() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        defaults.set(Data("not-json".utf8), forKey: CustomRoutineStore.defaultKey)

        let store = CustomRoutineStore(defaults: defaults)

        XCTAssertTrue(store.routines.isEmpty)
        XCTAssertNotNil(store.persistenceError)
    }
}
```

- [ ] **Step 2: Run the focused test target and verify the red failure.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/CustomRoutineStoreTests
```

Expected result: compilation fails because the custom definition, validator, and store interfaces do not exist.

- [ ] **Step 3: Implement the model, validator, store, and shared metadata changes.**

Implement `CustomRoutineDefinition`, `CustomRoutineTargetMode`, and the versioned library with explicit Codable keys so future migrations can inspect `schemaVersion`. Normalize a definition before validation by trimming title/subtitle, mapping empty optional metadata to nil, and de-duplicating tags case-insensitively while preserving first occurrence order.

Implement validation exactly as follows: title must contain a non-whitespace character; at least one step is required; every duration must be finite and greater than zero; rest steps have no targets; non-rest steps have at least one target; board-specific board and hold IDs must exist; generic targets must resolve on at least one `availableBoards`; fixed segments need a finite duration; stopwatch/undefined segments must not carry a segment duration. Return all issues together.

Implement `CustomRoutineStore` to load `HangTen.customRoutines.v1`, treat missing data as an empty collection, treat decode/schema failure as empty plus a persistence error, validate before save, replace the complete encoded library in one `defaults.set`, and leave the previous valid data untouched when encoding fails. `delete(id:)` removes exactly one matching definition and writes the remaining collection.

Resolve a custom definition into a `PlanDefinition` containing one block, then use the existing resolver/target mapping to produce `TrainingPlan`. Custom metadata uses `provenance: .custom`, source label `Created in Hang Ten`, nil source URL, difficulty default `Custom`, category default `custom`, and the normalized tags. Board-specific mode supplies its board ID; generic mode supplies nil.

Move the existing runtime step/target conversion into a reusable non-private helper so duplication can convert `WorkoutStep` back to `WorkoutStepDefinition` without losing hold kinds, features, fallbacks, grip, timing, or one-segment rest rows. Preserve one-segment stopwatch steps and let Task 1’s normalizer handle any source plan before conversion.

- [ ] **Step 4: Run focused tests and built-in regression tests.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/CustomRoutineStoreTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/PlanFiltersTests
```

Expected result: all targeted tests pass; bundled plan validation still requires HTTP(S) source URLs and custom plans are the only plans allowed to omit them.

- [ ] **Step 5: Commit the persistence deliverable.**

```sh
rtk git add HangTen/Models/CustomRoutineStore.swift HangTen/Models/TrainingModels.swift HangTen/Models/PlanStorage.swift HangTenTests/CustomRoutineStoreTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: persist validated custom routines"
```

---

### Task 3: Compose custom plans through AppStore and shared metadata/filter APIs

**Files:**
- Create: `HangTenTests/CustomRoutineAppStoreTests.swift`
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTen/Views/RootView.swift` only where it currently asks `PlanCatalog.metadata(for:)`; UI presentation changes belong to Task 5.
- Modify: `HangTen.xcodeproj/project.pbxproj` to register the new test source.

**Interfaces:**
- `AppStore` initializer accepts `customRoutineStore: CustomRoutineStoring? = nil` and defaults to `CustomRoutineStore(defaults: defaults)`.
- Produces `AppStore.customPlans: [TrainingPlan]` containing valid custom definitions.
- Produces `AppStore.metadata(for plan: TrainingPlan) -> PlanMetadata` for both built-in and custom plans.
- Produces `AppStore.isCustom(_ plan: TrainingPlan) -> Bool`.
- Produces `AppStore.customDefinition(for id: String) -> CustomRoutineDefinition?`.
- Produces `AppStore.saveCustomRoutine(_ definition: CustomRoutineDefinition) throws` and `AppStore.deleteCustomRoutine(id: String) throws`.
- Produces `AppStore.duplicateRoutine(_ plan: TrainingPlan) throws -> CustomRoutineDefinition`, which creates a new UUID-backed definition but does not save it until the editor saves.
- `AppStore.plans` returns board-compatible built-in and custom plans in built-in order followed by custom creation order.

**Consumes:** Task 2’s `CustomRoutineStoring`, custom resolver, `.custom` metadata, and Task 1’s normalized plans.

**Produces for later tasks:** One AppStore API for the Plans UI and editor; custom plans participate in board selection, favorites, metadata filters, workout start, completion recording, and HealthKit activity creation without custom branches in the workout engine.

- [ ] **Step 1: Register the test source and write failing AppStore integration tests.**

Add `CustomRoutineAppStoreTests.swift` to the test group/source phase. Use a unique `UserDefaults` suite per test and the existing fake health store helpers. Begin with these behaviors:

```swift
import XCTest
@testable import HangTen

@MainActor
final class CustomRoutineAppStoreTests: XCTestCase {
    private func makeDefaults() -> (suiteName: String, defaults: UserDefaults) {
        let suiteName = "CustomRoutineAppStoreTests.\(UUID().uuidString)"
        return (suiteName, UserDefaults(suiteName: suiteName)!)
    }

    private func makeRoutine(
        id: String = "custom.edge",
        mode: CustomRoutineTargetMode = .boardSpecific(boardID: BoardCatalog.compactII.id)
    ) -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: id,
            title: "Custom edge routine",
            subtitle: "A local routine",
            difficulty: nil,
            category: nil,
            tags: ["custom"],
            targetMode: mode,
            steps: [WorkoutStepDefinition(
                id: "step-1",
                title: "Edge hang",
                instruction: "Hang from the edges.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: mode == .generic
                    ? [.feature(.mediumEdge, fallbacks: [])]
                    : [.holdIDs(["edge-19-left", "edge-19-right"])],
                gripType: .halfCrimp,
                activeDuration: 10
            )]
        )
    }

    func testPlansCombinesBuiltInAndCustomThroughTrainingPlan() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let customStore = CustomRoutineStore(defaults: defaults)
        try customStore.save(makeRoutine())

        let store = AppStore(customRoutineStore: customStore, defaults: defaults)

        XCTAssertTrue(store.plans.contains { $0.id == "custom.edge" })
        XCTAssertTrue(store.plans.contains { $0.id == PlanCatalog.all[0].id })
        let custom = try XCTUnwrap(store.plans.first { $0.id == "custom.edge" })
        XCTAssertEqual(store.board(for: custom).id, BoardCatalog.compactII.id)
        XCTAssertEqual(store.holdIDs(for: custom.steps[0], on: BoardCatalog.compactII), ["edge-19-left", "edge-19-right"] as Set)
    }

    func testGenericCustomRoutineUsesSameBoardCompatibilityAndMetadataLookup() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let customStore = CustomRoutineStore(defaults: defaults)
        try customStore.save(makeRoutine(id: "custom.generic", mode: .generic))

        let store = AppStore(customRoutineStore: customStore, defaults: defaults)
        let plan = try XCTUnwrap(store.plans.first { $0.id == "custom.generic" })
        let metadata = store.metadata(for: plan)

        XCTAssertNil(plan.boardID)
        XCTAssertEqual(metadata.provenance, .custom)
        XCTAssertEqual(metadata.category, "custom")
        XCTAssertEqual(metadata.tags, ["custom"])
    }

    func testDuplicateCreatesUnsavedLiteralCustomDefinitionWithNewID() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let source = try XCTUnwrap(store.plans.first)

        let duplicate = try store.duplicateRoutine(source)

        XCTAssertNotEqual(duplicate.id, source.id)
        XCTAssertTrue(duplicate.id.hasPrefix("custom."))
        XCTAssertEqual(duplicate.steps.flatMap(\.segments).count, duplicate.steps.count)
        let expectedMode: CustomRoutineTargetMode = if let boardID = source.boardID {
            .boardSpecific(boardID: boardID)
        } else {
            .generic
        }
        XCTAssertEqual(duplicate.targetMode, expectedMode)
    }
}
```

- [ ] **Step 2: Run the focused tests and verify the red failure.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/CustomRoutineAppStoreTests
```

Expected result: compilation fails because AppStore does not accept a custom store and does not expose the combined-plan APIs.

- [ ] **Step 3: Implement AppStore composition and CRUD APIs.**

Store the injected custom store, hydrate `customPlans` during initialization, and keep `customRoutinePersistenceError` separate from existing session/HealthKit errors. After a successful save or delete, reload custom definitions/plans and publish the updated collection. If an individual stored definition cannot resolve, omit only that custom plan and expose its error; never remove or fail built-in plans.

Implement `plans` as `PlanCatalog.all + customPlans`, filtered by the existing `isCompatible` logic. Generic plans use the selected board for `board(for:)`; board-specific plans use their assigned board. `metadata(for:)` returns custom metadata for custom IDs and `PlanCatalog.metadata(for:)` for built-in IDs. `isCustom(_:)` checks the custom definition ID rather than provenance alone so a future built-in `.custom` fixture cannot be mistaken for user data.

Implement `duplicateRoutine(_:)` by obtaining the source metadata, normalizing source steps with `WorkoutStepNormalizer`, converting each one-segment step through the shared definition factory, copying source target mode (`boardID == nil` means `.generic`), copying title/description/difficulty/category/tags, assigning `custom.\(UUID().uuidString)`, and returning the unsaved definition. For built-in plans, do not mutate the source catalog.

- [ ] **Step 4: Run focused integration and existing AppStore/favorites/filter tests.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/CustomRoutineAppStoreTests -only-testing:HangTenTests/AppStoreTests -only-testing:HangTenTests/AppStoreFavoritesTests -only-testing:HangTenTests/PlanFiltersTests
```

Expected result: custom plans appear in the same collection, generic compatibility follows the board resolver, built-in favorites/order remain unchanged, and all targeted tests pass.

- [ ] **Step 5: Commit AppStore composition.**

```sh
rtk git add HangTen/Models/AppStore.swift HangTen/Views/RootView.swift HangTenTests/CustomRoutineAppStoreTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: compose custom plans in app store"
```

---

### Task 4: Add a pure editor draft model with testable step mutations

**Files:**
- Create: `HangTen/Models/CustomRoutineDraft.swift`
- Create: `HangTenTests/CustomRoutineDraftTests.swift`
- Modify: `HangTen/Models/TrainingModels.swift` only if picker labels/conformance from Task 2 are incomplete.
- Modify: `HangTen.xcodeproj/project.pbxproj` to register the new model/test sources.

**Interfaces:**
- Produces `CustomRoutineStepDraft: Equatable, Identifiable` with stable `id`, title, instruction, accessory, duration, `phase: WorkoutPhase`, `[WorkoutTargetDefinition] targets`, `timing: WorkoutSegmentTiming`, `gripType: GripType?`, and read-only `isRest`/`isStopwatch` computed properties.
- Produces `CustomRoutineDraft: Equatable` with stable optional `id`, immutable `targetMode`, editable title/subtitle/difficulty/category, `tagsText: String`, and ordered `[CustomRoutineStepDraft] steps`.
- Produces `CustomRoutineDraft.init(createWith targetMode: CustomRoutineTargetMode)` and `CustomRoutineDraft.init(duplicate: CustomRoutineDefinition)`.
- Produces `mutating func addStep()`, `mutating func updateStep(_:)`, `mutating func removeSteps(at:)`, `mutating func moveSteps(from: IndexSet, to: Int)`, and `func definition() -> CustomRoutineDefinition`.
- The draft exposes `var tagsText: String` for the comma-separated editor field. `definition()` trims title/subtitle, normalizes tags, keeps target mode unchanged, preserves stopwatch timing, and emits one-segment `WorkoutStepDefinition` values.

**Consumes:** Task 2’s definition and target types; Task 3’s duplicate output.

**Produces for later tasks:** A view-independent state object that makes drag reorder, add/edit/delete, target mode immutability, and metadata normalization testable without SwiftUI UI tests.

- [ ] **Step 1: Register the test source and write failing draft tests.**

Add `CustomRoutineDraftTests.swift` to the test group/source phase. Test the real draft value type:

```swift
import XCTest
@testable import HangTen

final class CustomRoutineDraftTests: XCTestCase {
    func testMoveStepsChangesOnlyTheirOrder() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = [
            .init(id: "one", title: "One", instruction: "", accessory: "", duration: 1, phase: .hang, targets: [.kind(.jug)], timing: .fixed, gripType: nil),
            .init(id: "two", title: "Two", instruction: "", accessory: "", duration: 2, phase: .rest, targets: [], timing: .fixed, gripType: nil),
            .init(id: "three", title: "Three", instruction: "", accessory: "", duration: 3, phase: .hang, targets: [.kind(.edge)], timing: .fixed, gripType: nil)
        ]

        draft.moveSteps(from: IndexSet(integer: 0), to: 3)

        XCTAssertEqual(draft.steps.map(\.id), ["two", "three", "one"])
    }

    func testDefinitionNormalizesTagsAndKeepsTargetModeFixed() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.title = "  My routine  "
        draft.subtitle = "  Description "
        draft.tagsText = " strength, , strength, power "

        let definition = draft.definition()

        XCTAssertEqual(definition.title, "My routine")
        XCTAssertEqual(definition.subtitle, "Description")
        XCTAssertEqual(definition.tags, ["strength", "power"])
        XCTAssertEqual(definition.targetMode, .generic)
    }

    func testDuplicateDraftPreservesStopwatchAsOneSimpleStep() throws {
        let source = CustomRoutineDefinition(
            id: "custom.max",
            title: "Max",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "max-step",
                title: "Max hang",
                instruction: "Hang.",
                accessory: "Up to 60s",
                duration: 60,
                phase: .hang,
                targets: [.feature(.roundSloper, fallbacks: [])],
                segments: [WorkoutSegmentDefinition(
                    kind: .work,
                    target: .feature(.roundSloper, fallbacks: []),
                    timing: .stopwatch,
                    duration: nil
                )]
            )]
        )

        let draft = CustomRoutineDraft(duplicate: source)
        let definition = draft.definition()

        XCTAssertEqual(definition.steps.count, 1)
        XCTAssertEqual(definition.steps[0].segments[0].timing, .stopwatch)
    }
}
```

- [ ] **Step 2: Run the focused tests and verify the red failure.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/CustomRoutineDraftTests
```

Expected result: compilation fails because `CustomRoutineDraft` and `CustomRoutineStepDraft` do not exist.

- [ ] **Step 3: Implement the draft model.**

Use a default draft with one editable step only when the user explicitly taps `Add step`; an empty new routine remains empty so save validation can explain the missing-step error. Initialize a board-specific draft with the selected board ID and an empty hold selection; initialize generic drafts with `.generic` target mode. For duplicate initialization, map every normalized one-segment definition into a draft row without changing IDs or timing.

Implement move semantics using the same `IndexSet`/destination behavior as SwiftUI `ForEach.onMove`, remove exactly the selected rows, and retain the remaining IDs. `definition()` must not permit target mode mutation, must emit the current step order, and must preserve `.stopwatch`/`.undefined` values without creating compound segments.

- [ ] **Step 4: Run focused and store regression tests.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/CustomRoutineDraftTests -only-testing:HangTenTests/CustomRoutineStoreTests
```

Expected result: all targeted tests pass and a duplicate draft has no compound multi-segment definition.

- [ ] **Step 5: Commit the editor-state deliverable.**

```sh
rtk git add HangTen/Models/CustomRoutineDraft.swift HangTenTests/CustomRoutineDraftTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: add custom routine editor state"
```

---

### Task 5: Wire the SwiftUI editor, Plans actions, and custom detail lifecycle

**Files:**
- Create: `HangTen/Views/CustomRoutineEditorView.swift`
- Modify: `HangTen/Views/RootView.swift` in `PlansView`, `PlanCard`/`FavoritePlanCard`, `PlanDetailView`, and the custom source-card area.
- Modify: `HangTen/Models/AppStore.swift` only for navigation-facing helpers that are missing after Task 3.
- Modify: `HangTen.xcodeproj/project.pbxproj` to register the new view source.

**Interfaces:**
- Produces `CustomRoutineEditorView` with initializer `init(draft: CustomRoutineDraft, onSave: @escaping (CustomRoutineDefinition) throws -> Void)`.
- The editor calls the save closure only after local draft conversion; save errors remain visible in the editor and do not dismiss it.
- Existing `PlanDetailView` receives no new initializer parameters. It uses `store.isCustom(plan)` to conditionally show Edit and Delete actions; Duplicate is available for every plan.
- `PlansView` uses `store.metadata(for:)`, not `PlanCatalog.metadata(for:)`, for both built-in and custom cards/filter options.

**Consumes:** Tasks 2–4’s store, AppStore, target mode, draft, normalization, and metadata APIs.

**Produces:** Complete create/duplicate/edit/reorder/delete user flow using the same cards/detail/workout navigation as built-ins.

- [ ] **Step 1: Add the target-selection contract to the draft tests before view-only wiring.**

The view is a declarative composition over the already-tested draft/store behavior, so it must not introduce a second model. Before building the view, extend `CustomRoutineDraftTests` with the user-facing contract that the editor can represent both target modes and simple stopwatch steps. Use the draft model rather than mocking SwiftUI:

```swift
func testBoardSpecificDraftStoresExactSelectedHoldIDs() {
    var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.compactII.id))
    draft.steps = [
        .init(
            id: "hang",
            title: "Edge hang",
            instruction: "Hang.",
            accessory: "10s",
            duration: 10,
            phase: .hang,
            targets: [.holdIDs(["edge-19-left", "edge-19-right"])],
            timing: .fixed,
            gripType: .halfCrimp
        )
    ]

    let definition = draft.definition()

    XCTAssertEqual(
        definition.targetMode,
        .boardSpecific(boardID: BoardCatalog.compactII.id)
    )
    XCTAssertEqual(definition.steps[0].targets, [.holdIDs(["edge-19-left", "edge-19-right"])])
}

func testGenericDraftCanStoreKindAndFeatureTargets() {
    var draft = CustomRoutineDraft(createWith: .generic)
    draft.steps = [
        .init(id: "kind", title: "Jugs", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.kind(.jug)], timing: .fixed, gripType: .openHand),
        .init(id: "feature", title: "Edge", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.feature(.mediumEdge, fallbacks: [])], timing: .fixed, gripType: nil)
    ]

    XCTAssertEqual(draft.definition().steps.map(\.targets), [[.kind(.jug)], [.feature(.mediumEdge, fallbacks: [])]])
}
```

- [ ] **Step 2: Run the focused draft tests and verify the target-selection contract is green.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test -only-testing:HangTenTests/CustomRoutineDraftTests
```

Expected result: the target-selection contract passes from Task 4’s draft implementation. If it does not, return to Task 4 and add a focused failing test before changing the draft; do not add target state directly to the SwiftUI view.

- [ ] **Step 3: Implement the editor UI and navigation actions.**

Build `CustomRoutineEditorView` as a `Form`/`List` with these exact controls and identifiers:

- `customRoutine.targetMode` segmented picker with `Board-specific` and `Generic`; disable it when editing/duplicating an existing definition.
- `customRoutine.board` board picker shown only for board-specific mode.
- `customRoutine.name`, `customRoutine.description`, `customRoutine.difficulty`, `customRoutine.category`, and `customRoutine.tags` fields.
- `customRoutine.steps` list with `onMove`, `onDelete`, `customRoutine.addStep`, and `customRoutine.save` identifiers.
- Each step editor exposes `customRoutine.stepTitle`, `customRoutine.stepInstruction`, `customRoutine.stepPhase`, `customRoutine.stepDuration`, `customRoutine.stepTiming`, and `customRoutine.stepGrip`.
- Board-specific steps render `BoardMapView` with `onHoldTap` and active highlights from exact selected IDs.
- Generic steps render one target-kind/feature picker using all `HoldKind.allCases` and all `HoldFeature.allCases`; selected target definitions are stored as `.kind` or `.feature`.
- Rest steps hide/clear target selection and grip; non-rest steps require at least one target before save.
- Validation errors render beside the save action, and persistence errors render in an alert/banner without dismissing the editor.

In `PlansView`, add a `Create routine` button at the top and a `My routines` section backed by `store.customPlans`. Keep custom cards on the same `FavoritePlanCard`/`PlanDetailView` navigation path and let favorites continue to use the existing IDs.

In `PlanDetailView`, add an action menu for custom plans with Edit and Delete. Add Duplicate for built-ins and custom plans. Duplicate creates a draft using `try store.duplicateRoutine(plan)`; Save is the only point that persists it. Delete requires a confirmation dialog with identifier `customRoutine.deleteConfirm` and calls `store.deleteCustomRoutine(id:)` only after confirmation.

Change Plans filtering metadata to use `store.metadata(for:)` for every plan. Render an in-app custom-origin card when `plan.sourceURL == nil`; preserve the existing linked source card for built-ins.

- [ ] **Step 4: Build the app and run all unit tests.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines \
  test
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -sdk iphonesimulator -derivedDataPath .context/DerivedData-custom-routines build
```

Expected result: the full `HangTenTests` target passes and the app builds with no warnings introduced by custom-routine code.

- [ ] **Step 5: Commit the SwiftUI deliverable.**

```sh
rtk git add HangTen/Views/CustomRoutineEditorView.swift HangTen/Views/RootView.swift HangTen/Models/AppStore.swift HangTenTests/CustomRoutineDraftTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: add custom routine editor and lifecycle"
```

---

### Task 6: Validate the complete custom-routine workflow on an isolated simulator

**Files:**
- Modify: none unless validation finds an implementation defect; fixes return to the responsible task with a new focused test first.
- Create: `.context/custom-routines-validation.md` and screenshots only under `.context`.

**Interfaces:** Uses the shipped `AppStore`, `PlansView`, `CustomRoutineEditorView`, `PlanDetailView`, `WorkoutView`, and existing DEBUG review controls.

- [ ] **Step 1: Read and follow `validate-hang-ten-ios/SKILL.md` before simulator work.**

Use the skill’s isolated simulator workflow. Create exactly one simulator named `Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME Custom Routines`, record its UUID immediately in `.context/conductor-owned-simulators`, install an exit trap that invokes `scripts/conductor-resource-cleanup.sh archive`, and verify exact deletion before finishing. Do not use a shared or unknown simulator.

- [ ] **Step 2: Build and install the current commit using workspace-owned DerivedData.**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
  -derivedDataPath .context/DerivedData-custom-routines build
rtk xcrun simctl install "$HANG_TEN_TEST_DEVICE_UDID" .context/DerivedData-custom-routines/Build/Products/Debug-iphonesimulator/HangTen.app
```

- [ ] **Step 3: Exercise and record the required flows.**

Verify and record evidence in `.context/custom-routines-validation.md` for:

1. Create a board-specific routine named `Edge Test`, select both 19 mm edges, add a 10-second half-crimp hang and a 20-second rest, save, open its detail, and start it.
2. Create a generic routine named `Generic Test`, add a medium-edge target, switch the selected board if another registered board exists, and verify the routine is shown only when compatible.
3. Duplicate a built-in routine containing a compound work/rest step, verify the custom editor shows literal rows in source order, and verify no advanced segment editor appears.
4. Reorder and delete a custom step, edit the name, save, relaunch the app, and verify the changes persist.
5. Duplicate a maximum-effort routine, start the custom workout, verify its stopwatch control remains available, finish/skip safely, and verify the existing summary/session flow opens.
6. Delete a custom routine and verify it disappears while the built-in source remains.

Capture only the minimum required screenshots under `.context`, with names prefixed by `custom-routines-`.

- [ ] **Step 4: Verify cleanup before reporting completion.**

```sh
rtk xcrun simctl shutdown "$HANG_TEN_TEST_DEVICE_UDID"
rtk env CONDUCTOR_WORKSPACE_PATH="$PWD" CONDUCTOR_WORKSPACE_NAME="$CONDUCTOR_WORKSPACE_NAME" scripts/conductor-resource-cleanup.sh archive
rtk zsh -c 'test ! -e "$PWD/.context/DerivedData-custom-routines"'
rtk sed -n '1,120p' .context/conductor-owned-simulators
```

The final verification must show the owned UUID is absent after cleanup; if it remains, keep working until exact deletion succeeds and document the failure in `.context/custom-routines-validation.md`.

- [ ] **Step 5: Commit only validation documentation if it is intentionally retained.**

```sh
rtk git status --short
```

Do not commit `.context` artifacts. The implementation branch is ready for final review only when the full test suite, build, simulator flow, and exact resource cleanup all pass.

## Final review handoff

After Task 6, run the repository’s final whole-branch review against `origin/main`, verify the design spec and this plan are both present, and use `superpowers:verification-before-completion` before claiming completion. If a review finds a code defect, dispatch one fresh fix task with a failing regression test and one scoped re-review before final handoff.
