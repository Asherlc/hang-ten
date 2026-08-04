# Metolius Guided Task Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand each listed Metolius task into an ordered guided step while retaining ten 60-second source cycles and explicitly timing the remaining rest.

**Architecture:** Add an internal Metolius task descriptor and cycle builder beside the source-audited seed catalog. The builder emits task steps and a rest step for each source minute; existing timeline, board highlighting, audio, and plan-library export then consume ordinary `WorkoutStep` values. Adapted provenance records that five-second pull-up timing and one-second other-repetition timing are app decisions, not Metolius prescriptions.

**Tech Stack:** Swift 6, SwiftUI, XCTest, Xcode 26, schema-versioned `PlanLibrary.json`, `scripts/export-plan-library.sh`, and an isolated iOS Simulator.

## Global Constraints

- Every source minute remains a 60-second cycle.
- Each listed task becomes a `WorkoutStep` with its own hold target and task text.
- Explicit source hang durations remain unchanged.
- Pull-up-only tasks use an app default of 5 seconds per pull-up.
- Other count-only tasks use an app default of 1 second per repetition.
- Compound tasks whose source wording binds repetitions to a timed hang remain one task and use the source hang duration.
- A rest step fills `60 seconds - total duration of all tasks in the minute` when the task sequence finishes early; no negative rest step may be emitted.
- Maximum-effort tasks with no source duration occupy the remainder of their source minute and receive no invented rest segment.
- Keep the three Metolius plan IDs and levels unchanged, and keep each plan at 600 seconds total.
- Because default timing and task splitting change the app interval model, all three Metolius plans use `provenance: .adapted` and retain the source URL plus an adaptation note.
- Preserve source order, repetition counts, named holds, hand switches, stay-on/no-rest qualifiers, and choice alternatives; do not add exercises.
- Use `rtk` before every shell command.
- Never use a shared `booted` simulator; validation uses one explicit UUID owned by this workspace.

---

### Task 1: Add and test the Metolius cycle-expansion core

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` near `WorkoutStep` and `LegacyPlanSeedCatalog`.
- Modify: `HangTenTests/WorkoutTimelineTests.swift` by adding a `MetoliusTaskExpansionTests` test class.

**Interfaces:**
- Produces `MetoliusTaskDefinition` with `title`, `instruction`, `accessory`, `duration`, `phase`, `targets`, and optional `gripType`.
- Produces `MetoliusCycleBuilder.cycleDuration == 60`, `pullUpDuration == 5`, and `repetitionDuration == 1`.
- Produces `MetoliusCycleBuilder.expand(planID:minute:tasks:) throws -> [WorkoutStep]` with stable task/rest IDs and task order.

- [ ] **Step 1: Write the failing tests**

Add tests that exercise real expansion behavior:

```swift
func testPullUpTasksUseFiveSecondsPerPullUp() throws {
    let task = MetoliusCycleBuilder.pullUps(
        count: 3,
        title: "Three pull-ups",
        instruction: "Do 3 pull-ups on the jugs.",
        phase: .pull,
        targets: [.feature(.jug)]
    )

    let steps = try MetoliusCycleBuilder.expand(planID: "test", minute: 1, tasks: [task])

    XCTAssertEqual(steps[0].duration, 15)
    XCTAssertEqual(steps[1].phase, .rest)
    XCTAssertEqual(steps[1].duration, 45)
}

func testExpansionKeepsTaskOrderAndAddsRemainingMinuteRest() throws {
    let first = MetoliusCycleBuilder.fixed(
        title: "First hang", instruction: "Hang for 15 seconds.", duration: 15,
        phase: .hang, targets: [.feature(.largeEdge)]
    )
    let second = MetoliusCycleBuilder.pullUps(
        count: 2, title: "Pull-ups", instruction: "Do 2 pull-ups.",
        phase: .pull, targets: [.feature(.jug)]
    )

    let steps = try MetoliusCycleBuilder.expand(planID: "test", minute: 2, tasks: [first, second])

    XCTAssertEqual(steps.map(\.id), ["test.minute-2.task-1", "test.minute-2.task-2", "test.minute-2.rest"])
    XCTAssertEqual(steps.map(\.duration), [15, 10, 35])
    XCTAssertEqual(steps[0].targets, first.targets)
    XCTAssertEqual(steps[1].targets, second.targets)
}

func testExpansionRejectsTasksThatExceedTheMinute() {
    let overfull = MetoliusTaskDefinition(
        title: "Overfull", instruction: "Overfull", accessory: "", duration: 61,
        phase: .hang, targets: [.feature(.largeEdge)], gripType: nil
    )

    XCTAssertThrowsError(try MetoliusCycleBuilder.expand(planID: "test", minute: 3, tasks: [overfull]))
}
```

- [ ] **Step 2: Run the focused tests and confirm the expected RED failure**

Run:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' -derivedDataPath .context/DerivedData-metolius-task-steps test -only-testing:HangTenTests/MetoliusTaskExpansionTests
```

Expected: compilation/test failure because `MetoliusCycleBuilder` and its task descriptor do not exist yet.

- [ ] **Step 3: Implement the minimal builder**

Implement the exact interfaces above. `expand` must:

1. Reject a task list whose sum exceeds 60 seconds.
2. Create task IDs in one-based source order: `planID.minute-N.task-1`, `task-2`, etc.
3. Create a `planID.minute-N.rest` step only when remaining time is greater than zero.
4. Set task `timedWorkDuration` equal to its generated duration so task audio uses task wording rather than a fabricated minute cue.
5. Set rest phase to `.rest`, give it no targets, and let the runtime treat it as a rest segment.
6. Keep the source task’s targets in the exact order supplied by the seed definition.

The `pullUps` factory calculates `TimeInterval(count) * 5`; the generic `repetitions` factory calculates `TimeInterval(count) * 1`; `fixed` leaves the supplied source duration unchanged.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run the same focused `xcodebuild` command. Expected: all three expansion tests pass with zero failures.

- [ ] **Step 5: Commit the core**

```sh
rtk git add HangTen/Models/TrainingModels.swift HangTenTests/WorkoutTimelineTests.swift
rtk git commit -m "test: add Metolius task cycle expansion"
```

---

### Task 2: Convert all three Metolius catalogs to ordered task steps

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` in `LegacyPlanSeedCatalog` and its DEBUG catalog assertions.
- Modify: `HangTenTests/WorkoutTimelineTests.swift` by adding catalog-level regression tests.

**Interfaces:**
- Consumes `MetoliusTaskDefinition` and `MetoliusCycleBuilder` from Task 1.
- Produces `LegacyPlanSeedCatalog.metoliusEntry`, `.metoliusIntermediate`, and `.metoliusAdvanced` as expanded 600-second adapted plans.

- [ ] **Step 1: Write catalog regression tests before changing the seed data**

Add tests that verify representative source order and timing through `PlanCatalog`:

```swift
func testIntermediateMinuteTwoIsTwoTaskStepsThenRest() {
    let plan = PlanCatalog.metoliusIntermediate
    let steps = plan.steps.filter { $0.id.hasPrefix("intermediate.minute-2.") }

    XCTAssertEqual(steps.map(\.title), ["Round sloper pull-ups", "Medium-edge hang", "Minute 2 rest"])
    XCTAssertEqual(steps.map(\.duration), [10, 20, 30])
    XCTAssertEqual(steps[0].targets, [.feature(.roundSloper)])
    XCTAssertEqual(steps[1].targets, [.feature(.mediumEdge)])
    XCTAssertEqual(steps[2].phase, .rest)
}

func testIntermediateOffsetPullsTellTheHandSwitchAsSeparateSteps() {
    let plan = PlanCatalog.metoliusIntermediate
    let steps = plan.steps.filter { $0.id.hasPrefix("intermediate.minute-6.") }

    XCTAssertEqual(steps.map(\.duration), [15, 15, 30])
    XCTAssertTrue(steps[1].instruction.lowercased().contains("change hands"))
    XCTAssertEqual(steps[2].phase, .rest)
}

func testMetoliusPlansRemainTenMinutesAndAreMarkedAdapted() {
    for plan in [PlanCatalog.metoliusEntry, PlanCatalog.metoliusIntermediate, PlanCatalog.metoliusAdvanced] {
        XCTAssertEqual(plan.duration, 600)
        XCTAssertEqual(plan.provenance, .adapted)
        XCTAssertGreaterThan(plan.steps.count, 10)
    }
}
```

- [ ] **Step 2: Run the catalog tests and confirm RED**

Run the focused test command from Task 1 with the catalog test filter. Expected: the existing ten-minute official catalog fails because minute 2 remains one 60-second step and provenance is still `.official`.

- [ ] **Step 3: Replace the single-minute seed helper with cycle expansion**

Use `MetoliusCycleBuilder.expand` in source order. The required source task mapping is:

| Plan | Minute | Ordered task definitions |
| --- | ---: | --- |
| Entry | 1 | 15s jug hang |
| Entry | 2 | 1 pull-up on round sloper |
| Entry | 3 | 10s medium edge hang |
| Entry | 4 | 15s pocket hang with 3 shrugs kept together |
| Entry | 5 | 20s large-edge hang with 2 pull-ups kept together |
| Entry | 6 | 10s round-sloper hang; 5 knee raises on pocket |
| Entry | 7 | 4 pull-ups on large edge |
| Entry | 8 | 10s medium edge hang |
| Entry | 9 | 3 pull-ups on jugs |
| Entry | 10 | Maximum round-sloper hang occupying the minute |
| Intermediate | 1 | 15s large-edge hang; 3 pull-ups on large edge |
| Intermediate | 2 | 2 pull-ups on round sloper; 20s medium-edge hang |
| Intermediate | 3 | 20s small-edge hang; 15s 90-degree bent-arm pocket hang |
| Intermediate | 4 | 30s round-sloper hang |
| Intermediate | 5 | 20s large-edge hang; 4 pull-ups on pocket |
| Intermediate | 6 | 3 offset pulls with high jug/low small edge; change hands and repeat as a second task |
| Intermediate | 7 | 15 knee raises on jugs; 15s medium-edge hang |
| Intermediate | 8 | 25s medium-edge hang |
| Intermediate | 9 | 15s slope hang; 3 pull-ups on jugs |
| Intermediate | 10 | Maximum round-sloper hang occupying the minute |
| Advanced | 1 | 20s straight-arm large-slope hang; 3 pull-ups on four-finger flat edge |
| Advanced | 2 | 20s slightly bent large-slope hang; 20s L-sit or 20 hanging knee curls kept as one stay-on task |
| Advanced | 3 | 5 pull-ups on three-finger pocket; 25s straight-arm hang on the same pocket |
| Advanced | 4 | Continuous five-second hold ladder ending in a 20s large-slope hang kept as one source task |
| Advanced | 5 | 20s single-arm flat-edge hang; switch hands and repeat as a second 20s task |
| Advanced | 6 | 5 offset pull-ups with large slope top/three-finger pocket bottom; change hands and repeat as a second task |
| Advanced | 7 | 30s 90-degree bent-arm incut-edge hang; 15s straight-arm three-finger-pocket hang |
| Advanced | 8 | 3 L-sit pull-ups; 5s front lever or 15s straight-arm large-slope hang |
| Advanced | 9 | 20s two-finger hang on three-finger pockets; 3 power pull-ups |
| Advanced | 10 | Maximum slightly bent-arm large-slope hang to failure with no rest; maximum straight-arm large-slope hang kept as one no-rest task |

Use `fixed` for explicit source durations, `pullUps` for standalone pull-up tasks, and `repetitions` for knee raises. Keep source qualifiers such as “stay on,” “change hands,” “repeat,” “to failure,” and “no rest” in task instructions. Give each expanded plan subtitle an adaptation note such as “Source sequence with guided task timing; pull-ups default to 5 seconds each.”

- [ ] **Step 4: Update DEBUG catalog assertions and replace the official fingerprint gate**

Remove the assertion that the Metolius plans are official ten-step plans and replace it with checks that:

- there are exactly three Metolius plans;
- all three use `.adapted` and the shared Metolius source URL;
- each plan lasts 600 seconds;
- each generated step has a unique ID and valid targets;
- every rest step has `.rest` phase and no targets;
- no source cycle exceeds 60 seconds.

Keep adapted research/coach assertions unchanged.

- [ ] **Step 5: Run catalog tests and the full XCTest suite**

Run the focused catalog test, then:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' -derivedDataPath .context/DerivedData-metolius-task-steps test
```

Expected: all tests pass and no DEBUG assertion fires while loading `PlanCatalog`.

- [ ] **Step 6: Commit the expanded catalog**

```sh
rtk git add HangTen/Models/TrainingModels.swift HangTenTests/WorkoutTimelineTests.swift
rtk git commit -m "feat: guide Metolius tasks as individual steps"
```

---

### Task 3: Make the runtime label adapted task/rest steps correctly

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` in `WorkoutStep` duration semantics.
- Modify: `HangTen/Views/RootView.swift` in rest detection, interval labels, and task audio wording.
- Modify: `HangTenTests/WorkoutTimelineTests.swift` with rest-state duration tests.

**Interfaces:**
- Consumes expanded task/rest steps from Task 2.
- Keeps `WorkoutTimeline` navigation and `WorkoutView` state APIs unchanged.

- [ ] **Step 1: Write failing runtime tests**

Add tests proving that a rest-phase step has zero active work and that a timed pull step is treated as active for its full duration:

```swift
func testRestPhaseHasFullDurationAsRest() {
    let rest = WorkoutStep(
        id: "rest", number: 1, title: "Rest", instruction: "Rest.", accessory: "",
        duration: 30, phase: .rest, targets: []
    )

    XCTAssertEqual(rest.activeDuration, 0)
    XCTAssertTrue(rest.hasRestInterval)
    XCTAssertEqual(rest.restDuration, 30)
}

func testTimedPullTaskHasNoFollowingRest() {
    let pull = WorkoutStep(
        id: "pull", number: 1, title: "Pull", instruction: "Do 2 pull-ups.", accessory: "",
        duration: 10, phase: .pull, targets: [.feature(.jug)], timedWorkDuration: 10
    )

    XCTAssertEqual(pull.activeDuration, 10)
    XCTAssertFalse(pull.hasRestInterval)
}
```

- [ ] **Step 2: Run the runtime tests and confirm RED**

Run the focused test command. Expected: the rest test fails because the current `WorkoutStep` treats a rest step with no explicit active duration as fully active.

- [ ] **Step 3: Implement the runtime semantics**

Update `WorkoutStep.activeDuration` so `.rest` steps report zero active duration. Update `RootView.isRestInterval` to recognize `step.phase == .rest`, and update `intervalRemaining`/audio segment selection so a rest step counts down its full duration. Make `intervalLabel` show “Hang” or “Pull” for generated timed task steps instead of the generic “Cycle.” Keep official/adapted research plan behavior intact.

- [ ] **Step 4: Run focused and full tests GREEN**

Run the focused runtime tests and the complete XCTest command from Task 2. Expected: all pass with zero failures.

- [ ] **Step 5: Commit runtime behavior**

```sh
rtk git add HangTen/Models/TrainingModels.swift HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
rtk git commit -m "fix: render Metolius task and rest timing"
```

---

### Task 4: Update plan-library provenance, documentation, and generated JSON

**Files:**
- Modify: `HangTen/Models/PlanStorage.swift` metadata notes and any validation assumptions that still require ten Metolius steps.
- Modify: `HangTen/Resources/PlanLibrary.json` by running the exporter; do not hand-edit generated JSON.
- Modify: `README.md` routine scope and included-plan wording.
- Modify: `docs/ADDING_A_ROUTINE.md` rules distinguishing unchanged official imports from guided adapted expansions.

**Interfaces:**
- Consumes the expanded adapted plans from Task 2 and runtime semantics from Task 3.
- Produces a bundled library that exactly matches the seed catalog and documents the app-defined timing defaults.

- [ ] **Step 1: Add the source/adaptation documentation changes**

Update documentation to say that Hang Ten includes source-linked Metolius sequences with guided adapted timing, that the source-level cycles remain ten minutes, and that the app uses five seconds per pull-up and one second per other count-based repetition where Metolius gives no duration. Keep the source URL and safety language.

Change the routine guide’s official-import rule to require `.official` only for unchanged task timing/interval structure, while allowing `.adapted` for a faithful task-order expansion with explicit app timing.

- [ ] **Step 2: Regenerate the bundled plan library**

Run:

```sh
rtk scripts/export-plan-library.sh
```

Verify that the generated JSON contains expanded task and rest steps, adapted provenance, semantic targets, and 600-second plan durations.

- [ ] **Step 3: Run exporter check mode**

```sh
rtk scripts/export-plan-library.sh --check
```

Expected: `PlanLibrary.json matches the source-audited definitions`.

- [ ] **Step 4: Run the full build/test verification**

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' -derivedDataPath .context/DerivedData-metolius-task-steps test
```

Expected: build succeeds and all XCTest cases pass.

- [ ] **Step 5: Commit generated data and docs**

```sh
rtk git add HangTen/Models/PlanStorage.swift HangTen/Resources/PlanLibrary.json README.md docs/ADDING_A_ROUTINE.md
rtk git commit -m "docs: mark guided Metolius timing as adapted"
```

---

### Task 5: Visually validate the guided task flow

**Files:**
- Create review artifacts under `.context/` only; do not commit screenshots or simulator state.

**States to inspect:**
- Intermediate minute 2, first round-sloper pull-up task.
- Intermediate minute 2, second medium-edge hang task.
- Intermediate minute 2, explicit rest step.
- Intermediate minute 6, first offset-pull direction and the hand-switch step.
- Intermediate minute 9, slope task followed by jug pull-ups.

- [ ] **Step 1: Create a dedicated simulator and save its UUID**

```sh
metolius_review_uuid=$(rtk xcrun simctl create "Hang Ten paramaribo Metolius Task Steps Review" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)
rtk printf "%s\n" "$metolius_review_uuid" > .context/metolius-task-steps-review.uuid
```

Use the returned UUID for every subsequent command, and boot it only after confirming it is not shared by another workspace.

- [ ] **Step 2: Build, install, and launch through DEBUG review routes**

```sh
metolius_review_uuid=$(rtk sed -n '1p' .context/metolius-task-steps-review.uuid)
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$metolius_review_uuid" -derivedDataPath .context/DerivedData-metolius-task-steps build
rtk xcrun simctl install "$metolius_review_uuid" .context/DerivedData-metolius-task-steps/Build/Products/Debug-iphonesimulator/HangTen.app
```

Capture the five states with these exact artifact names:

```sh
SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID=metolius.generic-ten-minute.intermediate SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 SIMCTL_CHILD_HANGTEN_REVIEW_STEP=4 rtk xcrun simctl launch "$metolius_review_uuid" com.hangten.training
rtk xcrun simctl io "$metolius_review_uuid" screenshot .context/metolius-task-step-minute-2-pullups.png
SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID=metolius.generic-ten-minute.intermediate SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 SIMCTL_CHILD_HANGTEN_REVIEW_STEP=5 rtk xcrun simctl launch "$metolius_review_uuid" com.hangten.training
rtk xcrun simctl io "$metolius_review_uuid" screenshot .context/metolius-task-step-minute-2-medium-edge.png
SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID=metolius.generic-ten-minute.intermediate SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 SIMCTL_CHILD_HANGTEN_REVIEW_STEP=6 rtk xcrun simctl launch "$metolius_review_uuid" com.hangten.training
rtk xcrun simctl io "$metolius_review_uuid" screenshot .context/metolius-task-step-minute-2-rest.png
SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID=metolius.generic-ten-minute.intermediate SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 SIMCTL_CHILD_HANGTEN_REVIEW_STEP=16 rtk xcrun simctl launch "$metolius_review_uuid" com.hangten.training
rtk xcrun simctl io "$metolius_review_uuid" screenshot .context/metolius-task-step-minute-6-offset-switch.png
SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID=metolius.generic-ten-minute.intermediate SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 SIMCTL_CHILD_HANGTEN_REVIEW_STEP=24 rtk xcrun simctl launch "$metolius_review_uuid" com.hangten.training
rtk xcrun simctl io "$metolius_review_uuid" screenshot .context/metolius-task-step-minute-9-jug-pulls.png
```

Inspect board highlights, grip card, title, timer, and rest state in each artifact.

- [ ] **Step 3: Verify behavior against the approved design**

Confirm that each task shows only its task-local target, each hand-switch step is separately titled and timed, rest has no highlighted holds, pull-up timing is visibly labeled as app guidance, the plan remains 600 seconds, and the full instruction retains source counts/qualifiers.

- [ ] **Step 4: Shut down only the dedicated simulator**

```sh
metolius_review_uuid=$(rtk sed -n '1p' .context/metolius-task-steps-review.uuid)
rtk xcrun simctl shutdown "$metolius_review_uuid"
```

- [ ] **Step 5: Commit no review artifacts; report exact verification evidence**

Record the build command, simulator UUID/name, screenshots reviewed, test counts, and any behavior that still requires physical-device confirmation.
