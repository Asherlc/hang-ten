# Unilateral Portable Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support one-hand and two-hand hangs, fixed-anchor pulls, and loaded lifting-edge workouts while resolving physical board objects accurately and recording Tindeq force against the active structured step.

**Architecture:** Board packages explicitly declare the independently usable equipment objects and every hold belongs to one. Workout steps carry hand use, side, action, repetitions, and signed external load; the resolver applies those requirements to either one object, two distinct objects, or an explicitly two-hand hold. All absent fields decode to the current bilateral timed-hang behavior.

**Tech Stack:** Swift 6 / SwiftUI, Codable JSON board packages and routine library, XCTest, Python board-package validator, Xcode iOS Simulator.

**Spec:** `docs/superpowers/specs/2026-08-28-unilateral-portable-training-design.md`

## Global Constraints

- Preserve all existing saved board packages, custom routines, and session history through absent-field defaults.
- Equipment objects are internal; athletes choose hand use and side, never an object ID.
- Author all Port-A-Board geometry directly from primary manufacturer evidence; do not create image-derived geometry.
- Preserve exact source prescriptions and source URLs for every new built-in routine field; omit fields the source does not establish.
- Push every task commit to `origin/single-armed-tindeq`.

---

### Task 1: Add explicit equipment-object package schema and migrate board fixtures

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:480-720`
- Modify: `HangTen/Models/BoardPackageStore.swift:844-1005`
- Modify: `HangTen/Models/BoardPackageWriter.swift:120-230, 450-490, 630-650`
- Modify: `Tools/HangboardWorkbench/hangboard_packages/board_catalog.py:400-575`
- Modify: `Tools/HangboardWorkbench/board_package.py:600-700`
- Modify: every `Hangboards/*/board.json`
- Modify: `Hangboards/metolius-rock-rings-3d/board.json`
- Test: `HangTenTests/BoardPackageStoreTests.swift`
- Test: `HangTenTests/BoardPackageWriterTests.swift`
- Test: `Tools/HangboardWorkbench/tests/test_board_catalog.py`
- Test: `Tools/HangboardWorkbench/tests/test_board_package.py`

**Interfaces:**
- Produces `EquipmentObject(id: String)` and `BoardHold.equipmentObjectID: String`.
- Produces `TrainingBoard.equipmentObjects: [EquipmentObject]` and `TrainingBoard.object(id:)`.
- Produces package JSON keys `equipmentObjects` and `holds[].equipmentObjectID`.

- [ ] **Step 1: Write Swift decoding and invariant tests**

```swift
func testPackageRequiresEveryHoldToBelongToAnEquipmentObject() throws {
    var document = validPackage()
    document["equipmentObjects"] = [["id": "primary"]]
    document["holds"][0]["equipmentObjectID"] = "missing"
    XCTAssertThrowsError(try BoardPackageStore.load(document))
}

func testLegacyFixtureNormalizesToOnePrimaryEquipmentObject() throws {
    let board = try BoardPackageStore.load(legacyFixtureWithoutObjectKeys)
    XCTAssertEqual(board.equipmentObjects.map(\\.id), ["primary"])
    XCTAssertTrue(board.holds.allSatisfy { $0.equipmentObjectID == "primary" })
}
```

- [ ] **Step 2: Write Python validator tests**

```python
def test_package_rejects_hold_with_unknown_equipment_object_id(tmp_path: Path) -> None:
    payload = valid_board_payload()
    payload["equipmentObjects"] = [{"id": "primary"}]
    payload["holds"][0]["equipmentObjectID"] = "missing"
    with pytest.raises(ValueError, match="unknown equipment object"):
        parse_board_payload(payload, tmp_path)
```

- [ ] **Step 3: Run the focused tests and verify they fail**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests`

Run: `rtk pytest Tools/HangboardWorkbench/tests/test_board_catalog.py Tools/HangboardWorkbench/tests/test_board_package.py -q`

Expected: failures for the missing schema/model symbols and unknown JSON keys.

- [ ] **Step 4: Implement the schema and backward-compatible defaults**

```swift
struct EquipmentObject: Codable, Hashable, Identifiable {
    let id: String
}

struct BoardHold: Identifiable, Hashable {
    let equipmentObjectID: String
    // Existing initializer gains equipmentObjectID: String = "primary".
}

struct TrainingBoard: Identifiable, Hashable {
    let equipmentObjects: [EquipmentObject]
    // Existing initializer gains equipmentObjects: [EquipmentObject] = [.init(id: "primary")].
}
```

Decode absent board-package keys as a single `primary` object and assign absent
hold IDs to `primary`; reject unknown object IDs, empty lists, duplicate IDs,
and objects without holds when fields are explicitly supplied. Mirror those
rules in the writer, Workbench parser, and Workbench save path.

- [ ] **Step 5: Migrate package data deliberately**

Add `equipmentObjects: [{"id":"primary"}]` and `equipmentObjectID:"primary"`
to every single-piece package. Add `left-ring` and `right-ring` to Rock Rings,
assigning each of its four existing left/right holds to the corresponding ID.
Do not alter paths, hold names, dimensions, or presentations.

- [ ] **Step 6: Run validation and focused tests**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk pytest Tools/HangboardWorkbench/tests/test_board_catalog.py Tools/HangboardWorkbench/tests/test_board_package.py -q`

Run: the focused `xcodebuild test` command from Step 3.

Expected: all pass.

- [ ] **Step 7: Commit and push**

```bash
rtk git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTen/Models/BoardPackageWriter.swift Tools/HangboardWorkbench Hangboards HangTenTests
rtk git commit -m "feat: model independent board equipment objects"
rtk git push
```

### Task 2: Define structured unilateral workout semantics and persist them

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:807-1010`
- Modify: `HangTen/Models/PlanStorage.swift:350-515`
- Modify: `HangTen/Models/CustomRoutineDraft.swift:1-230`
- Modify: `HangTen/Models/CustomRoutineStore.swift:69-110, 450-540`
- Modify: `HangTen/Models/MotherboardModels.swift:217-335`
- Test: `HangTenTests/PlanStorageTests.swift`
- Test: `HangTenTests/CustomRoutineDraftTests.swift`
- Test: `HangTenTests/CustomRoutineStoreTests.swift`
- Test: `HangTenTests/MotherboardModelsTests.swift`

**Interfaces:**
- Produces `WorkoutHandUse`, `WorkoutSide`, and `WorkoutAction` enums.
- Produces `WorkoutStep.handUse`, `.side`, `.action`, `.repetitions`, and `.externalLoadKGF`.
- Produces the same optional fields on `WorkoutStepDefinition` and custom drafts.

- [ ] **Step 1: Write round-trip and defaulting tests**

```swift
func testLegacyStepDefinitionDefaultsToBilateralTimedHang() throws {
    let step = try JSONDecoder().decode(WorkoutStepDefinition.self, from: legacyStepJSON)
    XCTAssertEqual(step.handUse, .double)
    XCTAssertEqual(step.side, .both)
    XCTAssertEqual(step.action, .hang)
    XCTAssertNil(step.repetitions)
    XCTAssertNil(step.externalLoadKGF)
}

func testSingleArmLoadedLiftRoundTripsSignedLoad() throws {
    let step = WorkoutStepDefinition(/* fields */, handUse: .single, side: .left,
        action: .loadedLift, repetitions: 7, externalLoadKGF: -8)
    XCTAssertEqual(try decode(encode(step)), step)
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/CustomRoutineDraftTests -only-testing:HangTenTests/CustomRoutineStoreTests -only-testing:HangTenTests/MotherboardModelsTests`

Expected: compilation failure for the new semantic fields.

- [ ] **Step 3: Add Codable semantic types and enforce valid combinations**

```swift
enum WorkoutHandUse: String, Codable, CaseIterable { case single, double }
enum WorkoutSide: String, Codable, CaseIterable { case left, right, both }
enum WorkoutAction: String, Codable, CaseIterable { case hang, isometricPull, loadedLift }

// Validation:
// single requires .left or .right; double requires .both;
// loadedLift requires repetitions > 0; non-lift steps have no repetitions.
```

Carry all fields through `WorkoutStepDefinition`, plan compilation,
`CustomRoutineStepDraft`, and `WorkoutSessionRecord`. Decode absent values as
`.double`, `.both`, `.hang`, and `nil`. Preserve signed finite load values and
reject invalid semantic combinations in plan/custom validation.

- [ ] **Step 4: Run focused tests**

Run: the `xcodebuild test` command from Step 2.

Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
rtk git add HangTen/Models HangTenTests
rtk git commit -m "feat: add unilateral workout step semantics"
rtk git push
```

### Task 3: Resolve hold targets by hand use and independent object identity

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:86-550`
- Modify: `HangTen/Models/AppStore.swift:304-320`
- Test: `HangTenTests/WorkoutActivityRecordingTests.swift`
- Test: `HangTenTests/BoardTargetSubstitutionTests.swift`

**Interfaces:**
- Consumes `WorkoutStep.handUse` plus object-owned `BoardHold`s.
- Produces `BoardTargetResolver.resolveHoldIDs(for:handUse:on:gripType:) -> [String]`.
- Produces `BoardTargetResolver.resolveObjects(for:handUse:on:gripType:) -> [String]` for highlighting.

- [ ] **Step 1: Write resolver tests for one object, pair objects, and bilateral hold**

```swift
func testSingleHandRockRingTargetResolvesExactlyOneRing() {
    let ids = BoardTargetResolver.resolveHoldIDs(for: .kind(.pocket), handUse: .single, on: rockRings)
    XCTAssertEqual(Set(ids.map { rockRings.hold(id: $0)!.equipmentObjectID }).count, 1)
}

func testDoubleHandRockRingTargetResolvesMatchingHoldsOnTwoRings() {
    let ids = BoardTargetResolver.resolveHoldIDs(for: .kind(.pocket), handUse: .double, on: rockRings)
    XCTAssertEqual(Set(ids.map { rockRings.hold(id: $0)!.equipmentObjectID }), ["left-ring", "right-ring"])
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/BoardTargetSubstitutionTests`

Expected: resolver has no hand-use parameter.

- [ ] **Step 3: Implement object-aware selection**

Keep the current depth/finger-capacity ranking. After candidate selection,
partition candidates by `equipmentObjectID`: a single-hand step selects the
best single object; a double-hand step selects matching candidates from two
distinct objects, falling back only to one hold with `handCapacity == 2`.
Return no match rather than inventing a bilateral pair from a one-object board.
Thread `step.handUse` through `AppStore.holdIDs(for:on:)` and activity recording.

- [ ] **Step 4: Run focused tests**

Run: the `xcodebuild test` command from Step 2.

Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
rtk git add HangTen/Models/WorkoutActivityRecording.swift HangTen/Models/AppStore.swift HangTenTests/WorkoutActivityRecordingTests.swift HangTenTests/BoardTargetSubstitutionTests.swift
rtk git commit -m "feat: resolve workout targets by equipment object"
rtk git push
```

### Task 4: Expose unilateral and loaded-lift authoring/execution

**Files:**
- Modify: `HangTen/Views/CustomRoutineEditorView.swift:249-520`
- Modify: `HangTen/Views/RootView.swift:1740-2950`
- Modify: `HangTen/Views/WorkoutStepPickerView.swift:30-105`
- Modify: `HangTen/Views/WorkoutSummaryView.swift:1-250`
- Test: `HangTenTests/CustomRoutineDraftTests.swift`
- Test: `HangTenTests/WorkoutSummaryTests.swift`
- Test: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- Consumes Task 2 semantic fields and Task 3 resolution.
- Produces custom-step controls for action, hand use, side, repetitions, and signed load.
- Produces a completion action for each `loadedLift` repetition and persists it in the session.

- [ ] **Step 1: Write UI-independent formatting and timeline tests**

```swift
func testLoadedLiftSummaryUsesSignedLoadCopy() {
    XCTAssertEqual(WorkoutStepFormatting.externalLoadText(-5, unit: .kilograms), "5 kg assistance")
    XCTAssertEqual(WorkoutStepFormatting.externalLoadText(10, unit: .kilograms), "+10 kg")
}

func testLoadedLiftTimelineShowsPrescribedRepetitions() {
    let step = loadedLiftStep(repetitions: 7)
    XCTAssertTrue(WorkoutTimeline.labels(for: step).contains("7 lifts"))
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/CustomRoutineDraftTests -only-testing:HangTenTests/WorkoutSummaryTests -only-testing:HangTenTests/WorkoutTimelineTests`

Expected: missing formatter/timeline semantic support.

- [ ] **Step 3: Implement authoring and runner behavior**

In `CustomRoutineStepEditor`, show an action picker, hand-use picker, and side
picker; conditionally show repetitions and signed external-load fields for
`loadedLift`. Add an “Add left + right pair” action that duplicates compatible
values while assigning `.left` and `.right`. In `RootView`, display structured
copy, highlight resolver output, and show a `Complete lift` button that counts
the prescribed repetitions. Timed `hang` and `isometricPull` retain current
timer/force-meter execution. Summaries show action, side, completion count,
and signed load.

- [ ] **Step 4: Run focused tests**

Run: the `xcodebuild test` command from Step 2.

Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
rtk git add HangTen/Views HangTenTests/CustomRoutineDraftTests.swift HangTenTests/WorkoutSummaryTests.swift HangTenTests/WorkoutTimelineTests.swift
rtk git commit -m "feat: author and run unilateral lifting workouts"
rtk git push
```

### Task 5: Add Port-A-Board and source-backed unilateral plans

**Files:**
- Create: `Hangboards/frictitious-port-a-board/board.json`
- Create: `Hangboards/frictitious-port-a-board/assets/primary.png`
- Modify: `HangTen/Models/TrainingModels.swift` (built-in plan declarations)
- Modify: `HangTen/Resources/PlanLibrary.json`
- Create: `docs/source-audits/2026-08-28-unilateral-portable-training.md`
- Test: `Tools/HangboardWorkbench/tests/test_approved_board_packages.py`
- Test: `HangTenTests/PlanStorageTests.swift`

**Interfaces:**
- Consumes Tasks 1–4 schemas.
- Produces one Frictitious object/hold inventory, and only source-complete unilateral plan definitions.

- [ ] **Step 1: Write package/plan inventory tests**

```python
def test_port_a_board_has_one_object_and_declared_primary_asset() -> None:
    board = load_board(HANGBOARDS_ROOT / "frictitious-port-a-board")
    assert [item.id for item in board.equipment_objects] == ["primary"]
    assert all(hold.equipment_object_id == "primary" for hold in board.holds)
```

```swift
func testMegosRepeaterPlanAlternatesStructuredSides() throws {
    let plan = try PlanLibrary.plan(id: "research.megos-one-arm-7-3")
    XCTAssertEqual(plan.steps.filter { $0.side == .left }.count,
                   plan.steps.filter { $0.side == .right }.count)
    XCTAssertTrue(plan.steps.allSatisfy { $0.handUse == .single })
}
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `rtk pytest Tools/HangboardWorkbench/tests/test_approved_board_packages.py -q`

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/PlanStorageTests`

Expected: package/plan is absent.

- [ ] **Step 3: Author package and source audit**

Research and record the official product page, all official front/side imagery,
and exact eight-edge inventory. Deliberately draw every canonical hold path in
Workbench against the primary evidence, create a clean head-on presentation,
and visually review normal and active paths. Add one `primary` object only.
The audit maps each object, hold, size, and presentation field to a URL.

- [ ] **Step 4: Add only faithful plan data**

Add the Megos 7:3 plan with exact side alternation/timing/rest. Add the
Climbing one-arm lifting-edge plan only if every displayed rest and scheduling
field is directly sourced; otherwise make it a custom-routine starter without
invented timing. Preserve Tyler Nelson’s 3–5-second/3–5-rep and 60–120-second
ranges as range copy only; do not turn those ranges into false exact timers.
Record all mappings in the new source audit and regenerate PlanLibrary using
the repository’s existing plan-library generation workflow.

- [ ] **Step 5: Validate packages, plans, and assets**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk scripts/hangboard-packages.sh status --root Hangboards`

Run: focused test commands from Step 2.

Expected: all pass; no unsupported routine content.

- [ ] **Step 6: Commit and push**

```bash
rtk git add Hangboards/frictitious-port-a-board HangTen/Models/TrainingModels.swift HangTen/Resources/PlanLibrary.json docs/source-audits Tools/HangboardWorkbench/tests HangTenTests/PlanStorageTests.swift
rtk git commit -m "feat: add unilateral portable board training"
rtk git push
```

### Task 6: End-to-end verification and simulator visual review

**Files:**
- Modify only if defects are found in Tasks 1–5.
- Test: `HangTenTests/BoardPackageStoreTests.swift`
- Test: `HangTenTests/PlanStorageTests.swift`
- Test: `HangTenTests/WorkoutActivityRecordingTests.swift`
- Test: `HangTenTests/CustomRoutineStoreTests.swift`
- Test: `HangTenTests/WorkoutSessionStoreTests.swift`

**Interfaces:**
- Verifies the complete public behavior from Tasks 1–5.

- [ ] **Step 1: Run all relevant unit and package tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/CustomRoutineStoreTests -only-testing:HangTenTests/WorkoutSessionStoreTests`

Run: `rtk pytest Tools/HangboardWorkbench/tests/test_board_catalog.py Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_approved_board_packages.py -q`

Expected: all pass.

- [ ] **Step 2: Build and run the app in an owned simulator**

Read and follow `.codex/skills/validate-hang-ten-ios/SKILL.md`. Build, install,
and launch Hang Ten on the isolated simulator. Verify: default paired Rock
Rings presentation; one-arm step highlighting exactly one ring; bilateral step
highlighting both rings; Port-A-Board one-object highlighting; loaded-lift rep
completion; and Tindeq live force/peak capture on an isometric-pull step.

- [ ] **Step 3: Capture review evidence**

Save only workspace-owned screenshots under `.context/` showing normal and
highlighted Rock Rings, normal and highlighted Port-A-Board, and the loaded
lift runner. Confirm that saved paths drive both normal and active geometry.

- [ ] **Step 4: Fix any verified defect and rerun its focused test plus Step 1**

For every defect, first add a regression test in the test file named in the
failure output, then make the smallest fix, rerun that test, and rerun Step 1.

- [ ] **Step 5: Commit and push verification fixes**

```bash
rtk git add HangTen HangTenTests Hangboards Tools docs/source-audits
rtk git commit -m "test: verify unilateral portable training"
rtk git push
```

## Plan self-review

- Spec coverage: Tasks 1 and 3 implement universal object identity and Rock Rings pairing; Task 2 implements all structured workout fields and compatibility; Task 4 implements authoring, execution, sensor attribution context, and history presentation; Task 5 implements Port-A-Board and source-audited content; Task 6 verifies package validation and visual behavior.
- Placeholder scan: no undecided implementation field or unspecified validation remains. Task 5 explicitly omits any routine field unsupported by its source.
- Type consistency: `EquipmentObject`, `equipmentObjectID`, `WorkoutHandUse`, `WorkoutSide`, `WorkoutAction`, and resolver hand-use parameters are introduced before their consuming tasks.
