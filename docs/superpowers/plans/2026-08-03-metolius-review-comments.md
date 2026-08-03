# Metolius Review Comments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address all four unresolved PR review findings by preserving every Metolius hold target, making max-effort work stopwatch-recorded, replacing the catalog force unwrap, and correcting Advanced Minute 4 timing.

**Architecture:** Extend workout segments with a target list while retaining the existing singular `target` JSON shape for one-target segments and decoding it for compatibility. The Metolius task builder will emit one timed segment containing all simultaneous targets, and the recorder will emit one duration-bearing activity record for that multi-target action. Max-effort tasks remain 60-second cycle steps but use stopwatch timing with no fixed active duration.

**Tech Stack:** Swift, SwiftUI, XCTest, versioned JSON plan-library exporter.

## Global Constraints

- Keep `PlanDefinitionSchema.currentVersion` at `3`; old persisted segments using `target` must continue to decode.
- A multi-target work segment must preserve every target and must not create multiple duration-bearing records for one simultaneous action.
- Max-effort Metolius steps retain a 60-second cycle duration, emit `.work`/`.stopwatch` with `duration: nil`, and omit persisted `activeDuration`.
- Choice tasks retain `.undefined` timing because their source alternatives have different possible durations; only ordinary fixed/pull/repetition helpers default to `.fixed`.
- Advanced Metolius Minute 4 must contain 40 seconds of work and a 20-second generated rest step.
- `PlanLibrary.json` must be regenerated with `scripts/export-plan-library.sh`; do not hand-edit generated JSON.
- Replace `try!` in `LegacyPlanSeedCatalog.expanded` with a diagnostic failure containing the plan ID and minute number.

---

### Task 1: Resolve Metolius review findings across runtime, persistence, and generated catalog

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:229-245, 375-400, 661-820, 822-1080`
- Modify: `HangTen/Models/PlanStorage.swift:191-265, 538-637, 939-1001, 1329-1348`
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:94-137`
- Modify: `HangTenTests/WorkoutActivityRecordingTests.swift`
- Modify: `HangTenTests/PlanStorageTests.swift`
- Modify: `HangTenTests/WorkoutTimelineTests.swift`
- Modify: `HangTen/Resources/PlanLibrary.json` (generated only)
- Test: `scripts/export-plan-library.sh --check`

**Interfaces:**
- `WorkoutSegment` gains stored `targets: [HoldTarget]`, keeps a computed `target: HoldTarget?` compatibility accessor, and accepts both `target:` and `targets:` initializers.
- `WorkoutSegmentDefinition` gains stored `targets: [WorkoutTargetDefinition]`, keeps a computed `target: WorkoutTargetDefinition?` compatibility accessor, decodes either `targets` or legacy `target`, and encodes one target as `target` but multiple targets as `targets`.
- `MetoliusTaskDefinition` carries `WorkoutSegmentTiming`; ordinary task helpers default to `.fixed`, the existing choice helper remains `.undefined`, and a `maxEffort` helper creates a 60-second `.stopwatch` task.
- `WorkoutActivityRecorder.segments` resolves all targets on a multi-target segment and emits one duration-bearing record for the simultaneous action; single-target grouping behavior remains unchanged.

- [ ] **Step 1: Write failing regression tests**

Add tests that fail against the current implementation:

```swift
func testMultiTargetWorkRecordsAllHoldsWithOneDuration() throws {
    let segment = WorkoutSegment(
        kind: .work,
        targets: [.ids("edge-left"), .ids("jug-center")],
        timing: .fixed,
        duration: 10
    )

    let records = try WorkoutActivityRecorder().segments(
        for: plan([segment]),
        on: board
    )

    XCTAssertEqual(records.count, 1)
    XCTAssertEqual(records[0].holdIDs, ["edge-left", "jug-center"])
    XCTAssertEqual(records[0].durationSeconds, 10)
}

func testMaxEffortMetoliusStepsUseStopwatchTiming() {
    let step = PlanCatalog.metoliusEntry.steps.first { $0.title == "Maximum sloper hang" }!
    XCTAssertEqual(step.duration, 60)
    XCTAssertEqual(step.timedWorkDuration, nil)
    XCTAssertEqual(step.segments, [
        WorkoutSegment(
            kind: .work,
            target: .feature(.roundSloper),
            timing: .stopwatch,
            duration: nil
        )
    ])
}

func testAdvancedMinuteFourLeavesTwentySecondsToRest() {
    let steps = PlanCatalog.metoliusAdvanced.steps.filter { $0.id.hasPrefix("advanced.minute-4.") }
    XCTAssertEqual(steps.map(\.duration), [40, 20])
    XCTAssertEqual(steps.last?.phase, .rest)
}
```

Also add a `PlanStorageTests` fixture with a multi-target segment and assert it round-trips all targets while a legacy one-target fixture still resolves through `target`.

- [ ] **Step 2: Run the focused tests and verify the expected failures**

Run:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/PlanStorageTests -only-testing:HangTenTests/MetoliusCatalogExpansionTests test
```

Expected: the new multi-target, stopwatch, and Minute 4 assertions fail because the current builder only uses `targets.first`, max-effort tasks are fixed, and Minute 4 consumes 60 seconds.

- [ ] **Step 3: Implement target-list compatibility and recorder attribution**

Use `targets` as the source of truth while preserving old call sites:

```swift
struct WorkoutSegment: Hashable {
    let kind: WorkoutSegmentKind
    let targets: [HoldTarget]
    var target: HoldTarget? { targets.first }
    let timing: WorkoutSegmentTiming
    let duration: TimeInterval?
}
```

Keep the existing `target:` initializer as a compatibility initializer that maps one non-nil target to a one-element array. Add a `targets:` initializer for simultaneous holds. Apply the same compatibility pattern to `WorkoutSegmentDefinition`, with custom `Codable` decoding that prefers `targets` and falls back to legacy `target`; encode one target under `target` and multiple under `targets`.

Update validation and resolution to require/resolve every work target. Update the exporter to serialize every segment target. In `WorkoutActivityRecorder`, resolve all targets for one segment, flatten the hold IDs, and for a multi-target segment emit one record with the combined hold IDs and one duration; retain descriptor grouping for existing single-target segments.

- [ ] **Step 4: Implement Metolius timing, diagnostics, and corrected duration**

Add a defaulted timing field to `MetoliusTaskDefinition`; make `expand` construct one segment with `targets: task.targets`, using each task's timing, `.fixed` plus `task.duration` for ordinary tasks, `.undefined` for variable-duration choice tasks, and `.stopwatch` with `duration: nil` for max-effort tasks. Set `timedWorkDuration` to `nil` for undefined/stopwatch tasks. Add `MetoliusCycleBuilder.maxEffort`, use it for the Entry, Intermediate, and Advanced max-effort tasks, and change Advanced Minute 4 Hold ladder duration from `60` to `40`.

Replace the force unwrap in `LegacyPlanSeedCatalog.expanded` with a `do/catch` around each minute that calls `preconditionFailure("Invalid Metolius plan \\(planID) minute \\(index + 1): \\(error)")`. Give `MetoliusCycleBuilder.Error` a useful description so future catalog mistakes identify the overfull total and cycle duration.

- [ ] **Step 5: Run the focused tests and verify they pass**

Run the same focused `xcodebuild` command from Step 2. Expected: all targeted tests pass, including legacy segment decoding, multi-target attribution, stopwatch max-effort semantics, and the 40-second Minute 4 cycle.

- [ ] **Step 6: Regenerate and validate the plan library**

Run:

```bash
rtk scripts/export-plan-library.sh --check
rtk git diff --check
```

Expected: the generated `PlanLibrary.json` matches source-audited definitions, max-effort segments have `timing: "stopwatch"` and no duration/activeDuration, offset segments contain all targets, and Advanced Minute 4 contains a 40-second task plus 20-second rest.

- [ ] **Step 7: Run the full test build and review the diff**

Run:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData-review-comments CODE_SIGNING_ALLOWED=NO build-for-testing
rtk git diff --check origin/main...HEAD
```

Review the diff to confirm only the four review findings, their tests, and generated output changed, then commit with a concise message.
