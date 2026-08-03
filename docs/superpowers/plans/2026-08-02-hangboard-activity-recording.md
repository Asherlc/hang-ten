# Hangboard Activity Recording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the selected board, resolved physical hold size/type, ordered work/rest segments, and fixed or observed duration for every completed Hang Ten routine.

**Architecture:** Add explicit timing segments to the routine model and versioned plan library, then resolve those segments against the exact `TrainingBoard` used by `WorkoutView`. A pure recorder produces Codable HealthKit metadata, while a pure stopwatch state machine captures max-effort durations; `AppStore` passes the resolved payload into the existing `HKWorkoutBuilder` completion path.

**Tech Stack:** Swift 5, SwiftUI, XCTest, HealthKit, JSON Codable metadata, Xcode 26, iOS 17+, `xcodebuild`, and the repository’s isolated-simulator workflow.

## Global Constraints

- Keep the existing `HKWorkout` title, activity type, start date, end date, and completion flow unchanged.
- Record the selected board identity and resolve hold metadata through the same board mapping used for UI highlights.
- Store ordered work/rest segments; rest has duration but no hold metadata.
- Fixed durations exclude rest; stopwatch durations reflect observed time; genuinely untimed work omits duration.
- Max-effort steps expose a count-up Start/Stop stopwatch in portrait and landscape.
- Pausing or backgrounding pauses a running stopwatch; leaving/skipping/completion/dismissal finalizes it.
- Increment the plan library schema from version 2 to version 3 and keep older documents decodable through compatibility derivation.
- Do not parse physical sizes from display names; store explicit `BoardHold.sizeMillimeters` values.
- Do not add a local activity database; the completed `HKWorkout` metadata remains the source of record.
- Preserve existing Apple Health authorization, error reporting, end-session behavior, audio behavior, and workout navigation semantics.
- Keep the minimum deployment target at iOS 17.0.
- Use `rtk` for every repository shell command and run a failing test before each production behavior implementation.
- Each task below is implemented by a fresh worker and reviewed before the next task begins.

---

## File map

- `HangTen/Models/TrainingModels.swift`: physical hold sizes, segment enums/value types, runtime `WorkoutStep` segments, and (in Task 2) source-audited legacy routine segment data.
- `HangTen/Models/PlanStorage.swift`: Codable segment definitions, schema version 3, validation, and conversion from persisted definitions to runtime segments.
- `HangTen/Resources/PlanLibrary.json`: generated version-3 plan data with explicit work/rest/stopwatch/undefined segments.
- `HangTen/Models/WorkoutActivityRecording.swift`: pure board resolution, recorded segment values, HealthKit metadata envelope, and JSON encoding.
- `HangTen/Models/WorkoutStopwatch.swift`: injectable-clock stopwatch state machine.
- `HangTen.xcodeproj/project.pbxproj`: explicit app/test source registration for each new Swift file.
- `HangTen/Models/AppStore.swift`: reuse the pure resolver and pass board/activity metadata into HealthKit.
- `HangTen/Models/HealthKitService.swift`: attach board and activity metadata to the existing workout builder.
- `HangTen/Views/RootView.swift`: stopwatch state, portrait/landscape stopwatch controls, lifecycle finalization, and completion payload handoff.
- `HangTenTests/WorkoutSegmentTests.swift`: runtime segment and physical-size behavior.
- `HangTenTests/PlanStorageTests.swift`: version-3 decoding, validation, conversion, and older-document compatibility.
- `HangTenTests/WorkoutActivityRecordingTests.swift`: board resolution, grouping, segment payloads, and JSON encoding.
- `HangTenTests/WorkoutStopwatchTests.swift`: stopwatch state transitions and finalization.
- `docs/IOS_RUNTIME_SERVICES.md`: runtime and HealthKit recording contract.

---

### Task 1: Add physical hold sizes and runtime timing segments

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Create: `HangTenTests/WorkoutSegmentTests.swift`

**Interfaces:**
- Produces `WorkoutSegmentKind: String, Codable, Hashable` with `.work` and `.rest`.
- Produces `WorkoutSegmentTiming: String, Codable, Hashable` with `.fixed`, `.stopwatch`, and `.undefined`.
- Produces `WorkoutSegment`:

  ```swift
  struct WorkoutSegment: Hashable {
      let kind: WorkoutSegmentKind
      let target: HoldTarget?
      let timing: WorkoutSegmentTiming
      let duration: TimeInterval?
  }
  ```

- Extends `BoardHold` with `let sizeMillimeters: Int?` and a defaulted initializer argument so existing board call sites remain source-compatible.
- Extends `WorkoutStep` with `let segments: [WorkoutSegment]`, defaulting to an empty array for existing constructors.

- [ ] **Step 1: Write the failing tests.**

  Add tests that first exercise the intended model API:

  ```swift
  func testBoardHoldPreservesPhysicalSizeSeparatelyFromDisplayName() {
      let hold = BoardHold(
          id: "edge-21",
          name: "Left 21 mm edge",
          shortLabel: "21E",
          detail: "Edge",
          kind: .edge,
          frame: HoldFrame(x: 0, y: 0, width: 1, height: 1),
          sizeMillimeters: 21
      )

      XCTAssertEqual(hold.sizeMillimeters, 21)
      XCTAssertEqual(hold.kind, .edge)
  }

  func testWorkoutStepKeepsOrderedWorkAndRestSegments() {
      let step = WorkoutStep(
          id: "hang",
          number: 1,
          title: "Hang",
          instruction: "Hang",
          accessory: "20s hang · 10s rest",
          duration: 30,
          phase: .hang,
          targets: [.kind(.edge)],
          segments: [
              WorkoutSegment(kind: .work, target: .kind(.edge), timing: .fixed, duration: 20),
              WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
          ]
      )

      XCTAssertEqual(step.segments.map(\.kind), [.work, .rest])
      XCTAssertEqual(step.segments.map(\.duration), [20, 10])
  }
  ```

  Use the project’s normal XCTest style and avoid mocks; these tests exercise real value types.

- [ ] **Step 2: Run the focused tests and confirm the red state.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording \
    test -only-testing:HangTenTests/WorkoutSegmentTests
  ```

  Expected result: compilation fails because `WorkoutSegment`, the new `segments` initializer argument, and `sizeMillimeters` do not yet exist. Do not weaken the assertions.

- [ ] **Step 3: Implement the minimal runtime model.**

  Add the enums and `WorkoutSegment` beside the existing workout value types. Add `sizeMillimeters` to `BoardHold`; populate the current Compact II catalog with numeric sizes for 19 mm, 29 mm, and 56 mm holds, leaving jugs without a numeric size. Add `segments` to `WorkoutStep` while preserving all existing computed timing properties and initializer defaults.

- [ ] **Step 4: Run the focused tests and verify green.**

  Re-run the exact focused `xcodebuild test` command from Step 2. Expected result: `WorkoutSegmentTests` passes with zero failures and no warnings caused by the new model.

- [ ] **Step 5: Commit the domain model.**

  ```sh
  rtk git add HangTen/Models/TrainingModels.swift HangTenTests/WorkoutSegmentTests.swift
  rtk git commit -m "feat: model physical hold activity segments"
  ```

---

### Task 2: Persist and validate version-3 routine segments

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/PlanStorage.swift`
- Modify: `HangTen/Resources/PlanLibrary.json`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Create: `HangTenTests/PlanStorageTests.swift`

**Interfaces:**
- Produces `WorkoutSegmentDefinition: Codable, Hashable`:

  ```swift
  struct WorkoutSegmentDefinition: Codable, Hashable {
      let kind: WorkoutSegmentKind
      let target: WorkoutTargetDefinition?
      let timing: WorkoutSegmentTiming
      let duration: TimeInterval?
  }
  ```

- Adds `segments: [WorkoutSegmentDefinition]` to `WorkoutStepDefinition`.
- Changes `PlanDefinitionSchema.currentVersion` from `2` to `3`.
- Converts persisted definitions into the runtime `WorkoutSegment` values from Task 1.

- [ ] **Step 1: Write failing decode/validation tests.**

  Add tests covering a version-3 step with fixed work/rest, a stopwatch step without duration, and an undefined step without duration. Add an older-document fixture with no `segments` key and assert the decoder derives a compatibility segment instead of throwing. Add validation assertions for a fixed segment missing duration and a negative duration.

  The core fixture should use the real definitions:

  ```swift
  let fixedWork = WorkoutSegmentDefinition(
      kind: .work,
      target: .feature(.mediumEdge, fallbacks: []),
      timing: .fixed,
      duration: 20
  )
  let fixedRest = WorkoutSegmentDefinition(
      kind: .rest,
      target: nil,
      timing: .fixed,
      duration: 40
  )
  ```

- [ ] **Step 2: Run the focused tests and confirm the red state.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording \
    test -only-testing:HangTenTests/PlanStorageTests
  ```

  Expected result: the test target cannot compile or decode `WorkoutSegmentDefinition` because the persisted segment model and schema conversion do not exist.

- [ ] **Step 3: Implement version-3 Codable storage and validation.**

  Add `WorkoutSegmentDefinition` and a custom `WorkoutStepDefinition.init(from:)` that defaults missing `segments` to `[]`. In the runtime conversion, use explicit segments when present. For older definitions without segments, derive a rest segment for rest-only steps, a fixed work segment when `activeDuration` is present, and an undefined work segment when the step has targets but no explicit work duration. Validate finite nonnegative durations; require fixed/rest durations and reject a duration greater than the enclosing step duration.

  Add source-seed segment helpers in `LegacyPlanSeedCatalog` and populate every bundled routine with ordered segment data: fixed work plus fixed rest for explicit work/rest seconds, stopwatch work for “as long as you can” max-effort steps, undefined work for genuinely untimed activities, and fixed recovery/rest segments for explicit recovery periods. For multi-activity minute steps, create one segment per source activity in source order and do not assign the enclosing 60-second cycle to an untimed activity. Then update the source-to-document conversion and run the repository exporter so `PlanLibrary.json` becomes schema version 3 with matching explicit segment arrays. Verify that the source-audited DEBUG fingerprint includes segment kind, timing, target, and duration so generated data cannot silently drift.

- [ ] **Step 4: Run storage tests and the generated-library check.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording \
    test -only-testing:HangTenTests/PlanStorageTests
  rtk scripts/export-plan-library.sh --check
  ```

  Expected result: all storage tests pass and the exporter reports that `HangTen/Resources/PlanLibrary.json` matches the source fixture.

- [ ] **Step 5: Commit persisted routine segments.**

  ```sh
  rtk git add HangTen/Models/PlanStorage.swift HangTen/Resources/PlanLibrary.json HangTenTests/PlanStorageTests.swift
  rtk git commit -m "feat: persist timed workout activity segments"
  ```

---

### Task 3: Build the resolved activity payload and HealthKit metadata

**Files:**
- Create: `HangTen/Models/WorkoutActivityRecording.swift`
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTen/Models/HealthKitService.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Create: `HangTenTests/WorkoutActivityRecordingTests.swift`

**Interfaces:**
- Produces `RecordedActivitySegment: Codable, Hashable` with `stepID`, `stepNumber`, `kind: WorkoutSegmentKind`, `holdIDs`, `holdType`, `sizeMillimeters`, and `durationSeconds`.
- Produces `WorkoutActivityMetadata: Codable, Hashable` with `version: Int` and `segments: [RecordedActivitySegment]`.
- Produces `WorkoutActivityRecorder.segments(for:on:stopwatchDurations:)` that resolves targets against a supplied board and returns ordered recorded segments.
- Produces `WorkoutActivityRecorder.json(for:) throws -> String` with stable JSON encoding and omitted optional fields.
- Changes `AppStore.markSessionComplete` to accept `board` and stopwatch durations, and changes `HealthKitService.saveCompletedWorkout` to accept board identity and recorded segments.

- [ ] **Step 1: Write failing recorder and metadata tests.**

  Use a fixture board with an edge whose explicit `sizeMillimeters` is `21`, and a semantic routine target whose text does not contain `21`. Assert that the recorded segment has `holdType == "edge"`, `sizeMillimeters == 21`, and the fixed active duration, proving the recorder uses board metadata rather than routine prose. Add tests for:

  - fixed work followed by fixed rest;
  - stopwatch work with a supplied observed duration;
  - stopwatch work without a supplied value encoding no duration;
  - undefined work encoding no duration;
  - left/right grouping with both IDs retained;
  - distinct repeated source segments remaining distinct;
  - JSON round-trip and version `1` envelope.

- [ ] **Step 2: Run the focused tests and confirm the red state.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording \
    test -only-testing:HangTenTests/WorkoutActivityRecordingTests
  ```

  Expected result: compilation fails because the recorder, recorded segment types, and JSON encoder do not yet exist.

- [ ] **Step 3: Implement pure board resolution and payload encoding.**

  Extract the existing `AppStore` target-resolution rules into a shared internal resolver used by both `AppStore.holdIDs(for:on:)` and `WorkoutActivityRecorder`. For each runtime segment, resolve matching `BoardHold` values from the supplied board. Group only symmetric holds with the same `HoldKind` and `sizeMillimeters` within that source segment; create separate recorded entries for different physical descriptors. Use fixed segment duration directly, stopwatch duration from the keyed runtime dictionary, and `nil` for undefined or never-started timing.

  Encode `WorkoutActivityMetadata` with `JSONEncoder` configured for stable key ordering. Omit `durationSeconds`, `holdType`, and `sizeMillimeters` when their values are nil; keep `holdIDs` empty for rest segments. Add `HangTen.BoardID`, `HangTen.BoardName`, and `HangTen.ActivitySegments` alongside the existing `HangTen.PlanName` in the HealthKit metadata dictionary.

  Preserve the existing builder stage error mapping. If payload encoding or target validation fails, report the Health write failure before saving an incomplete workout; keep the local completion counter behavior unchanged.

- [ ] **Step 4: Run the focused tests and verify green.**

  Re-run the exact focused test command from Step 2, then run the existing timeline tests to prove the resolver extraction did not change workout navigation behavior:

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording \
    test -only-testing:HangTenTests/WorkoutActivityRecordingTests \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

- [ ] **Step 5: Commit the recorder and HealthKit payload path.**

  ```sh
  rtk git add HangTen/Models/WorkoutActivityRecording.swift HangTen/Models/AppStore.swift HangTen/Models/HealthKitService.swift HangTenTests/WorkoutActivityRecordingTests.swift
  rtk git commit -m "feat: record resolved board activities in HealthKit"
  ```

---

### Task 4: Add the pure stopwatch state machine

**Files:**
- Create: `HangTen/Models/WorkoutStopwatch.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Create: `HangTenTests/WorkoutStopwatchTests.swift`

**Interfaces:**
- Produces `WorkoutStopwatch` with accumulated elapsed time, running/finalized state, and date-injected methods:

  ```swift
  struct WorkoutStopwatch: Equatable {
      var isRunning: Bool { get }
      var isFinalized: Bool { get }
      var hasStarted: Bool { get }
      func elapsed(at date: Date) -> TimeInterval?
      mutating func start(at date: Date)
      mutating func pause(at date: Date)
      mutating func stop(at date: Date)
  }
  ```

- `elapsed(at:)` returns `nil` before first start and the accumulated/observed seconds after start; finalized values cannot be restarted.

- [ ] **Step 1: Write failing state-transition tests.**

  Cover never-started `nil`, start after a known date, pause accumulation, resume accumulation, stop finalization, repeated stop idempotence, and the rule that a finalized stopwatch cannot restart.

- [ ] **Step 2: Run the focused tests and confirm the red state.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording \
    test -only-testing:HangTenTests/WorkoutStopwatchTests
  ```

  Expected result: the test target cannot compile because `WorkoutStopwatch` is missing.

- [ ] **Step 3: Implement the minimal date-injected state machine.**

  Keep all elapsed-time arithmetic in this Foundation-only type. Starting stores the date anchor; pausing adds the interval and clears the anchor; resuming creates a new anchor; stopping adds any active interval and marks the value finalized. Clamp negative clock movement to zero and make stop/pause safe when already stopped.

- [ ] **Step 4: Run the focused tests and verify green.**

  Re-run the exact focused command from Step 2 and confirm all stopwatch state tests pass.

- [ ] **Step 5: Commit the stopwatch model.**

  ```sh
  rtk git add HangTen/Models/WorkoutStopwatch.swift HangTenTests/WorkoutStopwatchTests.swift
  rtk git commit -m "feat: add observable max-effort stopwatch"
  ```

---

### Task 5: Integrate stopwatch controls and completion handoff

**Files:**
- Modify: `HangTen/Views/RootView.swift`

**Interfaces:**
- Consumes `WorkoutSegment`, `WorkoutStopwatch`, and the new `AppStore.markSessionComplete` signature from earlier tasks.
- Produces portrait and landscape controls for stopwatch segments, a `[String: TimeInterval]` duration snapshot for completion, and lifecycle-safe finalization.

- [ ] **Step 1: Add a failing UI/integration test or review route assertion.**

  Add DEBUG accessibility identifiers and a focused review assertion in the existing simulator validation route for a plan containing a stopwatch segment. The route must expose:

  - `workout.stopwatch` with a visible `00:00` value before start;
  - `workout.stopwatch.toggle` labeled Start stopwatch;
  - a running state labeled Stop stopwatch;
  - a stopped state showing the observed value.

  Run the route’s existing UI test/review command before adding the UI and confirm the identifiers are absent. If the repository has no automated UI target for the route, capture the absence through the existing AXe/review script and record the failing assertion in the worker report before implementation.

- [ ] **Step 2: Implement stopwatch state in `WorkoutView`.**

  Add state keyed by stable step/segment identity. Render the count-up control from the current step’s stopwatch segment in both portrait and landscape layouts, with accessibility labels and identifiers. Keep the regular workout timer, board highlights, routine picker, skip button, and audio moments unchanged.

  Pause the current stopwatch from `pauseForInterruption` and normal pause. Finalize it before `jump(to:)`, `skipCurrentStep()`, `completeSession()`, and dismissal. On completion, pass the finalized duration dictionary together with `plan`, the exact `board`, and the completed interval to `store.markSessionComplete`.

  If the athlete never starts a max-effort stopwatch, pass no duration for that segment. If the athlete starts and the session reaches completion without pressing Stop, finalize at the completion date. A normal “End session” still dismisses without calling the completion logger.

- [ ] **Step 3: Build and run the focused app tests.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording \
    test -only-testing:HangTenTests/WorkoutTimelineTests \
    -only-testing:HangTenTests/WorkoutStopwatchTests \
    -only-testing:HangTenTests/WorkoutActivityRecordingTests
  ```

  Then compile the signed app:

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -sdk iphonesimulator -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording build
  ```

- [ ] **Step 4: Commit the workout UI integration.**

  ```sh
  rtk git add HangTen/Views/RootView.swift
  rtk git commit -m "feat: measure max-effort activity durations"
  ```

---

### Task 6: Update runtime documentation and perform full validation

**Files:**
- Modify: `docs/IOS_RUNTIME_SERVICES.md`
- Modify: `docs/IOS_SIMULATOR_VALIDATION.md` only if the existing checklist lacks the new stopwatch and Health metadata scenarios.

**Interfaces:**
- Documents the final segment schema, stopwatch lifecycle, board resolution contract, and physical-device HealthKit limitation for future workers.

- [ ] **Step 1: Write the documentation checklist first.**

  Add explicit checks for selected-board metadata, physical size/type resolution, ordered work/rest segments, undefined durations, max-effort stopwatch capture, pause/background behavior, and HealthKit completion. Keep the existing “End session does not log” and authorization rules.

- [ ] **Step 2: Run documentation and generated-data checks.**

  ```sh
  rtk git diff --check
  rtk scripts/export-plan-library.sh --check
  ```

- [ ] **Step 3: Commit the documentation.**

  ```sh
  rtk git add docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
  rtk git commit -m "docs: describe board activity recording"
  ```

- [ ] **Step 4: Read the required validation guides and create an owned simulator.**

  Read `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` completely. Create or resolve the simulator owned by this workspace and save its explicit UUID. Never use `booted` or another workspace’s device.

- [ ] **Step 5: Run the full test suite and signed simulator build.**

  ```sh
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording test
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
    -sdk iphonesimulator -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-activity-recording build
  ```

  Record the exit codes and complete test counts; do not claim success from a partial log.

- [ ] **Step 6: Validate the installed app in both orientations.**

  Install and launch the exact signed build on the owned UUID. Exercise a fixed work/rest plan, a genuinely undefined activity, a max-effort stopwatch in portrait and landscape, pause/resume, backgrounding, direct navigation, skip, completion, and the user-triggered Apple Health permission flow. Confirm the review route shows the selected board and resolved hold cues. Inspect screenshots and accessibility identifiers; verify that the HealthKit write path still requires user authorization.

- [ ] **Step 7: Report physical-device-only verification.**

  State explicitly that simulator validation covers wiring and UI, while final inspection of custom `HKWorkout` metadata in Apple Health requires a physical device with HealthKit authorization. Include the simulator UUID, commands, screenshots reviewed, and any remaining device-only check.

---

## Plan self-review checklist

- Spec coverage: board identity, physical size/type resolution, ordered rest, fixed/stopwatch/undefined timing, stopwatch UI, lifecycle, HealthKit metadata, compatibility, tests, and simulator/physical-device validation are covered by Tasks 1–6.
- Placeholder scan: no task relies on “TBD”, “TODO”, “implement later”, or unspecified test behavior; each task names files, interfaces, commands, and expected red/green results.
- Type consistency: `WorkoutSegment` is produced by Task 1, persisted by Task 2, consumed by `WorkoutActivityRecorder` in Task 3, measured by `WorkoutStopwatch` in Task 4, and integrated by `WorkoutView` in Task 5.
- Write ownership: Task 1 owns the model/board portions of `TrainingModels.swift` and the first project/test registrations; Task 2 owns source-seed segment data in `TrainingModels.swift`, `PlanStorage.swift`, generated JSON, and its project/test registration; Task 3 owns recorder/AppStore/HealthKit and its project/source/test registrations; Task 4 owns stopwatch files and its project/source/test registrations; Task 5 owns `RootView.swift`; Task 6 owns docs. These project-file edits are sequential append-only registrations, and Task 2’s source-seed edits intentionally follow Task 1’s independently green model task; workers must not revert earlier registrations or unrelated edits.
