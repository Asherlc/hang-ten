# Workout Step Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an active Hang Ten session skip the current timed step or jump to any other routine step while keeping one accurate timer across portrait and landscape.

**Architecture:** Add a pure `WorkoutTimeline` model that owns cumulative step offsets, current-step lookup, direct-selection targets, and skip targets. Keep live clock state in `WorkoutView`, rebase that clock for navigation, and expose a shared `WorkoutStepPickerView` sheet plus a secondary skip control in both layouts. Add an XCTest target for timeline behavior and validate the real controls on an isolated iOS Simulator.

**Tech Stack:** Swift 5, SwiftUI, XCTest, Xcode 26, iOS 17+, `xcodebuild`, and the repository’s isolated-simulator workflow.

## Global Constraints

- The minimum deployment target remains iOS 17.0.
- A new routine always starts at elapsed position 0, which is step 1.
- Step navigation and “Skip step” stay disabled before the first real start and throughout the initial three-second countdown.
- Running navigation keeps the timer running; paused navigation keeps it paused.
- A step boundary uses the full `WorkoutStep.duration`, including a timed rest interval.
- The existing completion action remains the only path that logs a session to Apple Health; ending a session still does not log it.
- No plan-library schema, routine content, board mapping, or persistence changes are in scope.
- Timer, board highlights, grip cues, audio moments, and completion must all derive from the same elapsed position.
- The UI must behave consistently in both existing portrait and landscape layouts.
- Use `rtk` for repository shell commands and run a failing test before each production behavior implementation.

---

### Task 0: Persist the subagent workflow instruction

**Files:**
- Create: `AGENTS.md`

**Interfaces:**
- Produces a repository-level instruction that requires future implementation
  and configuration work to use a fresh subagent with review checkpoints.

- [ ] **Step 1: Add the repository instruction.**

  Create `AGENTS.md` with this exact policy:

  ```markdown
  # Agent instructions

  ## Delegation

  Use a fresh subagent for every implementation task or configuration change.
  When an approved implementation plan exists, follow subagent-driven
  development with per-task implementation and review checkpoints. Do not
  make implementation changes directly in the controller session.
  ```

- [ ] **Step 2: Check the instruction file.**

  Run `rtk git diff --check` and confirm the file contains the policy above
  without unrelated repository instructions.

- [ ] **Step 3: Commit the repository instruction.**

  ```sh
  rtk git add AGENTS.md
  rtk git commit -m "chore: require subagent implementation workflow"
  ```

---

### Task 1: Add the XCTest target and write the red timeline tests

**Files:**
- Create: `HangTenTests/WorkoutTimelineTests.swift`
- Create: `HangTen.xcodeproj/xcshareddata/xcschemes/HangTen.xcscheme`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Produces the test target `HangTenTests`, which imports the application module with `@testable import HangTen`.
- Defines the expected `WorkoutTimeline` API used by the later model task:
  `init(steps: [WorkoutStep])`, `duration`, `step(at:)`,
  `elapsedInStep(at:)`, `startOffset(for:)`,
  `selectionTarget(for:at:)`, and `skipTarget(from:)`.

- [ ] **Step 1: Add a unit-test target to the Xcode project.**

  Add a `HangTenTests` group and file reference, a unit-test bundle product,
  a sources build phase, a target dependency on `HangTen`, and Debug/Release
  test-target build configurations. The test target must use the application
  as its host with `TEST_HOST = $(BUILT_PRODUCTS_DIR)/HangTen.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)`, enable generated Info.plist output, use Swift 5, and retain the app’s iOS 17 deployment target. Add the target to the shared Hang Ten scheme’s Test action so focused and full `xcodebuild test` commands execute it.

- [ ] **Step 2: Create the test fixture and behavioral tests before adding the production timeline.**

  Use this fixture shape so tests exercise both ordinary steps and a fixed
  active/rest interval without depending on any production routine:

  ```swift
  import XCTest
  @testable import HangTen

  final class WorkoutTimelineTests: XCTestCase {
      private let steps: [WorkoutStep] = [
          WorkoutStep(
              id: "first",
              number: 1,
              title: "First",
              instruction: "First instruction",
              accessory: "First accessory",
              duration: 60,
              phase: .hang,
              targets: [.kind(.jug)],
              timedWorkDuration: 30
          ),
          WorkoutStep(
              id: "second",
              number: 2,
              title: "Second",
              instruction: "Second instruction",
              accessory: "Second accessory",
              duration: 20,
              phase: .rest,
              targets: []
          ),
          WorkoutStep(
              id: "third",
              number: 3,
              title: "Third",
              instruction: "Third instruction",
              accessory: "Third accessory",
              duration: 10,
              phase: .hang,
              targets: [.kind(.jug)]
          )
      ]

      func testDurationAndOffsetsIncludeWholeSteps() {
          let timeline = WorkoutTimeline(steps: steps)

          XCTAssertEqual(timeline.duration, 90)
          XCTAssertEqual(timeline.startOffset(for: "first"), 0)
          XCTAssertEqual(timeline.startOffset(for: "second"), 60)
          XCTAssertEqual(timeline.startOffset(for: "third"), 80)
      }

      func testExactBoundaryResolvesToFollowingStep() {
          let timeline = WorkoutTimeline(steps: steps)

          XCTAssertEqual(timeline.step(at: 60)?.id, "second")
          XCTAssertEqual(timeline.elapsedInStep(at: 65), 5)
      }

      func testSelectionTargetsDifferentStepStartsAndCurrentStepIsNoOp() {
          let timeline = WorkoutTimeline(steps: steps)

          XCTAssertEqual(timeline.selectionTarget(for: "third", at: 10), 80)
          XCTAssertEqual(timeline.selectionTarget(for: "first", at: 75), 0)
          XCTAssertNil(timeline.selectionTarget(for: "second", at: 75))
      }

      func testSkipUsesTheFullStepBoundaryIncludingRest() {
          let timeline = WorkoutTimeline(steps: steps)

          XCTAssertEqual(timeline.skipTarget(from: 45), 60)
          XCTAssertEqual(timeline.skipTarget(from: 65), 80)
      }

      func testSkippingTheFinalStepStopsAtPlanDuration() {
          let timeline = WorkoutTimeline(steps: steps)

          XCTAssertEqual(timeline.skipTarget(from: 85), 90)
      }

      func testEmptyTimelineHasNoNavigationTargets() {
          let timeline = WorkoutTimeline(steps: [])

          XCTAssertEqual(timeline.duration, 0)
          XCTAssertNil(timeline.step(at: 0))
          XCTAssertNil(timeline.startOffset(for: "missing"))
          XCTAssertNil(timeline.selectionTarget(for: "missing", at: 0))
          XCTAssertNil(timeline.skipTarget(from: 0))
      }
  }
  ```

- [ ] **Step 3: Run the focused tests and confirm the red state is caused by the missing timeline behavior.**

  Run with the dedicated simulator UUID supplied by the validation workflow:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-step-navigation \
    test \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected red result: the test target builds, but the tests cannot resolve
  `WorkoutTimeline` because the production type does not exist yet. Do not
  change the assertions to make this run pass.

- [ ] **Step 4: Commit the red test and project-target scaffold.**

  ```sh
  rtk git add HangTenTests/WorkoutTimelineTests.swift HangTen.xcodeproj/project.pbxproj HangTen.xcodeproj/xcshareddata/xcschemes/HangTen.xcscheme
  rtk git commit -m "test: specify workout timeline navigation"
  ```

---

### Task 2: Implement and verify the pure workout timeline

**Files:**
- Create: `HangTen/Models/WorkoutTimeline.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Test: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- Consumes: existing `WorkoutStep` values from `HangTen/Models/TrainingModels.swift`.
- Produces:
  ```swift
  struct WorkoutTimeline {
      init(steps: [WorkoutStep])
      var duration: TimeInterval { get }
      func step(at elapsed: TimeInterval) -> WorkoutStep?
      func elapsedInStep(at elapsed: TimeInterval) -> TimeInterval
      func startOffset(for stepID: String) -> TimeInterval?
      func selectionTarget(for stepID: String, at elapsed: TimeInterval) -> TimeInterval?
      func skipTarget(from elapsed: TimeInterval) -> TimeInterval?
  }
  ```

- [ ] **Step 1: Add `WorkoutTimeline.swift` to the app target.**

  Register the new model file in the Models group and Hang Ten sources build
  phase. Keep the file Foundation-only and make the type internal so the
  application and `@testable` unit target can use it without adding a public
  API.

- [ ] **Step 2: Implement cumulative offsets with one boundary convention.**

  Sum each step’s full `duration`. Use a strict `< cursor + duration` check
  while walking steps so an exact boundary resolves to the following step.
  Clamp negative elapsed values to zero and values at or past the plan
  duration to the final step for display; return `nil` for an empty timeline.
  `elapsedInStep(at:)` must return the clamped offset within the selected
  step, including its rest portion.

- [ ] **Step 3: Implement selection and skip targets.**

  `startOffset(for:)` returns the cumulative offset for a matching step ID.
  `selectionTarget(for:at:)` returns that offset only when the requested ID
  differs from the current step ID; otherwise it returns `nil` so tapping the
  current row is a no-op. `skipTarget(from:)` returns the end offset of the
  current step, clamped to the plan duration, and returns `nil` for an empty
  timeline.

- [ ] **Step 4: Run the focused test suite and verify green.**

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-step-navigation \
    test \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected result: all `WorkoutTimelineTests` pass with zero failures.

- [ ] **Step 5: Commit the timeline implementation.**

  ```sh
  rtk git add HangTen/Models/WorkoutTimeline.swift HangTen.xcodeproj/project.pbxproj
  rtk git commit -m "feat: add workout timeline navigation model"
  ```

---

### Task 3: Integrate seeking and skipping into `WorkoutView`

**Files:**
- Modify: `HangTen/Views/RootView.swift:633-1260`
- Test: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- Consumes: `WorkoutTimeline` from Task 2 and existing `startedAt`,
  `pausedElapsed`, `routineStartedAt`, and `audioCoach` state.
- Produces private `WorkoutView` behavior through:
  `canNavigate`, `seek(to:)`, `jump(to:)`, and `skipCurrentStep()`.

- [ ] **Step 1: Add a red timeline regression for the final navigation boundary before changing the view.**

  Extend `testSkippingTheFinalStepStopsAtPlanDuration` with a second
  assertion that selecting the final step from an earlier position returns
  its start offset. Run the focused test command and confirm it passes against
  the already-correct model; this locks the view’s later final-step behavior
  to the same model API rather than a duplicated loop.

- [ ] **Step 2: Make `WorkoutView` use one `WorkoutTimeline` instance.**

  Add a private timeline computed property from `plan.steps`. Replace the
  existing private `step(at:)` and `elapsedInStep(at:)` loops with calls to
  the helper while retaining the existing fallback for an unexpectedly empty
  plan. Use the timeline for all current-step and boundary decisions.

- [ ] **Step 3: Add navigation gating and elapsed-position rebasing.**

  Compute navigation availability from `routineStartedAt != nil`, a zero
  countdown, and `!isComplete`. Add:

  ```swift
  private func seek(to targetElapsed: TimeInterval) {
      let target = min(max(0, targetElapsed), plan.duration)
      pausedElapsed = target
      if startedAt != nil {
          startedAt = Date()
      }
      audioCoach.stop()
  }
  ```

  Guard `seek` callers with the navigation-availability rule. `jump(to:)`
  asks `timeline.selectionTarget(for:at:)` for the requested step and does
  nothing for the current step. `skipCurrentStep()` asks
  `timeline.skipTarget(from:)` for the current elapsed position. Neither
  method changes `routineStartedAt`, so the existing completion and HealthKit
  dates remain the session’s original dates.

- [ ] **Step 4: Run the app build and focused tests before adding the new controls.**

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-step-navigation \
    build

  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-step-navigation \
    test \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected result: the app compiles and all timeline tests remain green.

- [ ] **Step 5: Commit the clock integration.**

  ```sh
  rtk git add HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "feat: support workout step seeking"
  ```

---

### Task 4: Add the routine picker and portrait/landscape controls

**Files:**
- Create: `HangTen/Views/WorkoutStepPickerView.swift`
- Modify: `HangTen/Views/RootView.swift:633-1070`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: `TrainingPlan`, `WorkoutStep`, current step ID, and a selection
  closure from `WorkoutView`.
- Produces `WorkoutStepPickerView(plan:currentStepID:onSelect:)`, a sheet
  action labeled “Routine”, and a secondary action labeled “Skip step” in
  both workout layouts.

- [ ] **Step 1: Create the picker view as a focused SwiftUI component.**

  Build a `NavigationStack` sheet with a scrollable `LazyVStack` of one
  `Button` per `plan.steps`. Each row must show the existing step number,
  title, duration, instruction, accessory, and phase tint; give the current
  step a selected background and checkmark. Use a minimum row height of 64
  points, a full-row `contentShape`, and an accessibility label containing
  the step number, title, duration, and current-state marker.

- [ ] **Step 2: Add the “Routine” action and sheet presentation.**

  Add `@State private var showsStepPicker = false` to `WorkoutView`. Place a
  `Routine` button in the shared information area of each portrait and
  landscape header so it updates with the `TimelineView` state. Disable it
  before the first real start, during countdown, and after completion. Attach
  `.sheet(isPresented: $showsStepPicker)` with the current step ID and call
  `jump(to:)` from the picker’s selection closure.

- [ ] **Step 3: Add the skip action without changing the primary control.**

  Refactor the current single control view into a small control group that
  retains the existing start/pause/log behavior and adds a secondary `Skip
  step` button. Place the group in the existing portrait vertical stack and
  landscape bottom control area. Disable the skip action under the same
  `canNavigate` condition. Use a clear forward icon and
  `.accessibilityIdentifier("workout.skipStep")`.

- [ ] **Step 4: Add stable accessibility identifiers for simulator review.**

  Add `.accessibilityIdentifier("workout.routinePicker")` to the Routine
  action and an identifier based on the stable step ID, such as
  `workout.step.(step.id)`, to each picker row. Preserve the existing
  accessibility label for spoken-cue controls and End.

- [ ] **Step 5: Build and run the focused tests.**

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-step-navigation \
    build

  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-step-navigation \
    test \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected result: the app and tests build cleanly with all timeline tests
  green.

- [ ] **Step 6: Commit the workout navigation UI.**

  ```sh
  rtk git add HangTen/Views/WorkoutStepPickerView.swift HangTen/Views/RootView.swift HangTen.xcodeproj/project.pbxproj
  rtk git commit -m "feat: add workout step picker and skip control"
  ```

---

### Task 5: Document the runtime contract and validate the installed app

**Files:**
- Modify: `docs/IOS_RUNTIME_SERVICES.md`
- Modify: `docs/IOS_SIMULATOR_VALIDATION.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the final `WorkoutView` behavior and stable accessibility
  identifiers from Task 4.
- Produces: documentation that describes direct step navigation, skip
  boundaries, initial-state gating, and the simulator review checklist.

- [ ] **Step 1: Update the runtime-services contract.**

  Add a workout-navigation subsection stating that a new session starts at
  step 1, controls are disabled before and during the initial countdown,
  running and paused seeks preserve their state, skip advances across the
  full step duration including rest, current-step selection is a no-op, and
  audio is stopped/re-anchored after a seek.

- [ ] **Step 2: Update the simulator checklist.**

  Add review steps for the Routine sheet, selecting a later step while
  running, selecting an earlier step while paused, tapping the current row,
  skipping a timed-rest step, skipping the final step, and confirming the
  controls are disabled before start and during the countdown. Keep the
  dedicated-device and orientation requirements unchanged.

- [ ] **Step 3: Update the README feature list.**

  Expand the runnable-session bullet to mention direct step selection and
  skipping the current timed step, without changing the plan-source or safety
  claims.

- [ ] **Step 4: Invoke the Hang Ten iOS validation workflow.**

  Use the repository’s `validate-hang-ten-ios` skill to build, install, and
  launch this workspace’s app on a dedicated simulator. Review both portrait
  and landscape routes and exercise the accessibility identifiers from Task 4.
  Capture review evidence under `.context` only; do not use a shared `booted`
  simulator.

- [ ] **Step 5: Run the complete verification commands.**

  ```sh
  rtk git diff --check

  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-step-navigation \
    test

  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Release \
    -sdk iphonesimulator \
    -derivedDataPath .context/DerivedData-step-navigation-release \
    build
  ```

  Expected result: zero diff-check errors, zero test failures, and successful
  Debug test and Release simulator builds.

- [ ] **Step 6: Review the final diff against the approved spec and commit the docs.**

  Confirm every acceptance criterion in
  `docs/superpowers/specs/2026-08-02-workout-step-navigation-design.md` has
  evidence in tests, build output, or simulator review. Then commit:

  ```sh
  rtk git add README.md docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
  rtk git commit -m "docs: document workout step navigation"
  ```

## Plan self-review

- Spec coverage: the timeline model covers cumulative offsets, exact
  boundaries, full rest-inclusive skips, direct selection, current-step no-op,
  and empty-plan safety; `WorkoutView` tasks cover running/paused rebasing,
  countdown gating, audio, completion, and HealthKit preservation; UI tasks
  cover both orientations, accessibility, and the Routine sheet; docs and
  simulator validation cover the remaining acceptance criteria.
- Placeholder scan: no unfinished markers, vague “add validation” steps, or
  unassigned implementation decisions remain.
- Type consistency: every later task consumes the exact `WorkoutTimeline`
  methods produced in Task 2, and the picker closure consumes a `WorkoutStep`
  before calling `WorkoutView.jump(to:)`.
