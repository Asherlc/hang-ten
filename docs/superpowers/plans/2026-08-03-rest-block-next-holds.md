# Rest Block Next-Hold Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** During any workout rest block, preview the next work block’s highlighted holds while preserving the existing rest indication.

**Architecture:** Extend the pure `WorkoutTimeline` with a next-work-step lookup and a hold-preview lookup that understands both timed rest intervals and explicit `.rest` steps. Keep `WorkoutView`’s existing rest header, timer, cue card, and grip suppression, but resolve board highlights from the timeline preview step and pass them through both existing layouts.

**Tech Stack:** Swift 5, SwiftUI, XCTest, Xcode 26, iOS 17+, `xcodebuild`, and the repository’s isolated-simulator validation workflow.

## Global Constraints

- The minimum deployment target remains iOS 17.0.
- Both timed rest intervals and explicit `.rest` steps preview the next non-rest step’s resolved hold IDs.
- Consecutive rest steps are skipped when choosing the preview; a final rest step has no preview highlights.
- The visible `Rest` pill, rest-colored styling, rest timer label, recovery copy, and no-grip-diagram behavior remain in place during rest.
- Countdown and completed-session states suppress all board highlights.
- No plan-library schema, routine content, board mapping, persistence, audio, or HealthKit changes are in scope.
- Direct step selection and skip behavior continue to use existing full step boundaries.
- Portrait and landscape layouts must receive the same highlight set from the shared elapsed position.
- Use `rtk` for repository shell commands and run a failing test before each production behavior implementation.
- Simulator validation must use a workspace-owned simulator UUID explicitly for every operation; never use `booted`.

---

### Task 1: Add and implement pure rest-preview timeline behavior

**Files:**
- Modify: `HangTenTests/WorkoutTimelineTests.swift`
- Modify: `HangTen/Models/WorkoutTimeline.swift`

**Interfaces:**
- Consumes: existing `WorkoutStep` values and their `phase`, `activeDuration`, and `hasRestInterval` properties.
- Produces:

  ```swift
  extension WorkoutTimeline {
      func nextWorkStep(after stepID: String) -> WorkoutStep?
      func holdPreviewStep(at elapsed: TimeInterval) -> WorkoutStep?
  }
  ```

  `nextWorkStep(after:)` returns the first later step whose phase is not
  `.rest`, skipping any consecutive rest steps. `holdPreviewStep(at:)` returns
  the current step during work, the next work step during timed or explicit
  rest, and `nil` when the timeline has no step or no later work step.

- [ ] **Step 1: Add failing tests for the next-work and hold-preview contracts.**

  Append this fixture and these tests to `HangTenTests/WorkoutTimelineTests.swift` without changing the existing timeline tests:

  ```swift
  private let restPreviewSteps: [WorkoutStep] = [
      WorkoutStep(
          id: "work",
          number: 1,
          title: "Work",
          instruction: "Work instruction",
          accessory: "Work accessory",
          duration: 30,
          phase: .hang,
          targets: [.kind(.jug)],
          timedWorkDuration: 15
      ),
      WorkoutStep(
          id: "rest-one",
          number: 2,
          title: "Rest one",
          instruction: "Rest instruction",
          accessory: "Rest accessory",
          duration: 10,
          phase: .rest,
          targets: []
      ),
      WorkoutStep(
          id: "rest-two",
          number: 3,
          title: "Rest two",
          instruction: "Rest instruction",
          accessory: "Rest accessory",
          duration: 10,
          phase: .rest,
          targets: []
      ),
      WorkoutStep(
          id: "next-work",
          number: 4,
          title: "Next work",
          instruction: "Next work instruction",
          accessory: "Next work accessory",
          duration: 20,
          phase: .pull,
          targets: [.kind(.edge)]
      ),
      WorkoutStep(
          id: "final-rest",
          number: 5,
          title: "Final rest",
          instruction: "Final rest instruction",
          accessory: "Final rest accessory",
          duration: 5,
          phase: .rest,
          targets: []
      )
  ]

  func testNextWorkStepSkipsConsecutiveRestSteps() {
      let timeline = WorkoutTimeline(steps: restPreviewSteps)

      XCTAssertEqual(timeline.nextWorkStep(after: "work")?.id, "next-work")
      XCTAssertEqual(timeline.nextWorkStep(after: "rest-one")?.id, "next-work")
      XCTAssertEqual(timeline.nextWorkStep(after: "rest-two")?.id, "next-work")
      XCTAssertNil(timeline.nextWorkStep(after: "next-work"))
  }

  func testHoldPreviewUsesNextWorkStepDuringTimedAndExplicitRest() {
      let timeline = WorkoutTimeline(steps: restPreviewSteps)

      XCTAssertEqual(timeline.holdPreviewStep(at: 5)?.id, "work")
      XCTAssertEqual(timeline.holdPreviewStep(at: 20)?.id, "next-work")
      XCTAssertEqual(timeline.holdPreviewStep(at: 35)?.id, "next-work")
  }

  func testHoldPreviewHasNoHighlightSourceAfterTheFinalRestStep() {
      let timeline = WorkoutTimeline(steps: restPreviewSteps)

      XCTAssertNil(timeline.holdPreviewStep(at: 72))
  }
  ```

  The elapsed values exercise work (`0..<15`), timed rest in the first step
  (`15..<30`), the first explicit rest step (`30..<40`), the second explicit
  rest step (`40..<50`), next work (`50..<70`), and final rest (`70..<75`).

- [ ] **Step 2: Run the focused tests and verify the red state.**

  Set `HANGTEN_REST_PREVIEW_SIMULATOR_UDID` to the explicit UUID of the
  workspace-owned iOS Simulator used for this plan, then run:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" \
    -derivedDataPath .context/DerivedData-rest-block-preview \
    test \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected red result: compilation fails because `WorkoutTimeline` does not
  yet define `nextWorkStep(after:)` or `holdPreviewStep(at:)`. Do not weaken
  the assertions or remove the tests.

- [ ] **Step 3: Implement the minimum timeline behavior.**

  Add these methods to `WorkoutTimeline` after the existing navigation methods:

  ```swift
  func nextWorkStep(after stepID: String) -> WorkoutStep? {
      guard let index = steps.firstIndex(where: { $0.id == stepID }) else {
          return nil
      }

      return steps.dropFirst(index + 1).first { $0.phase != .rest }
  }

  func holdPreviewStep(at elapsed: TimeInterval) -> WorkoutStep? {
      guard let currentStep = step(at: elapsed) else {
          return nil
      }

      let stepElapsed = elapsedInStep(at: elapsed)
      let isResting = currentStep.phase == .rest
          || (currentStep.hasRestInterval && stepElapsed >= currentStep.activeDuration)

      return isResting
          ? nextWorkStep(after: currentStep.id)
          : currentStep
  }
  ```

  Keep the methods Foundation-only and internal. The existing boundary and
  clamping behavior must remain unchanged.

- [ ] **Step 4: Run the focused tests, then the full XCTest target.**

  Run the focused command from Step 2 again and expect all timeline tests to
  pass. Then run the full target:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" \
    -derivedDataPath .context/DerivedData-rest-block-preview \
    test
  ```

  The focused and full runs must exit 0 with no failing tests.

- [ ] **Step 5: Commit the pure timeline behavior.**

  ```sh
  rtk git add HangTen/Models/WorkoutTimeline.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "feat: add rest hold preview timeline"
  ```

### Task 2: Wire the shared hold preview into the workout UI

**Files:**
- Modify: `HangTen/Views/RootView.swift`

**Interfaces:**
- Consumes: `WorkoutTimeline.holdPreviewStep(at:)` from Task 1 and the existing `AppStore.holdIDs(for:on:)` resolver.
- Produces: identical preview highlight IDs for portrait and landscape while preserving the current rest presentation.

- [ ] **Step 1: Confirm the Task 1 regression tests are green before changing the view.**

  Run the focused timeline command from Task 1, Step 2. The command must pass
  before the UI wiring begins; it proves the pure preview selection behavior
  that the view will consume.

- [ ] **Step 2: Derive rest state and board highlights from one elapsed position.**

  In `WorkoutView.body`, update the timeline-derived values so the existing
  rest state includes explicit `.rest` steps and the board uses the pure
  preview lookup:

  ```swift
  let isResting = step.phase == .rest || isRestInterval(step: step, stepElapsed: stepElapsed)
  let highlightedStep = timeline.holdPreviewStep(at: elapsed)
  let previewHoldIDs = highlightedStep.map { store.holdIDs(for: $0, on: board) } ?? []
  let highlightedHoldIDs = countdown > 0 || isComplete ? [] : previewHoldIDs
  let activeHold = board.holds.first { highlightedHoldIDs.contains($0.id) }
  ```

  Replace the existing `activeHoldIDs` argument passed to both
  `portraitSession` and `landscapeSession` with `highlightedHoldIDs`. Rename
  the corresponding parameter and `BoardMapView` arguments in both layout
  helpers to `highlightedHoldIDs`; do not change the grip-diagram guards, which
  must continue to exclude countdown, completion, and rest.

- [ ] **Step 3: Preserve the existing rest indication.**

  Update only the `isResting` derivation and board highlight source. Verify the
  existing `isResting` branches remain active in `landscapeHeader`,
  `sessionHeader`, `landscapeCueCard`, and `cueCard`, including their `Rest`
  pill, rest timer label, recovery copy, and rest-colored text. Do not add a
  second rest badge or alter audio behavior.

- [ ] **Step 4: Build and run the full test target.**

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" \
    -derivedDataPath .context/DerivedData-rest-block-preview \
    test
  ```

  Expect a successful build and the complete XCTest target to pass.

- [ ] **Step 5: Commit the UI wiring.**

  ```sh
  rtk git add HangTen/Views/RootView.swift
  rtk git commit -m "feat: preview next holds during rest"
  ```

### Task 3: Validate timed and explicit rest previews on an isolated simulator

**Files:**
- Create: `.context/rest-block-preview-portrait.png` (gitignored validation artifact)
- Create: `.context/rest-block-preview-landscape.png` (gitignored validation artifact)

**Interfaces:**
- Consumes: the built app from Tasks 1–2 and the DEBUG review routes documented in `docs/IOS_SIMULATOR_VALIDATION.md`.
- Produces: fresh build, runtime screenshots, and a written validation result in the implementer report.

- [ ] **Step 1: Resolve a dedicated simulator and build with workspace-specific derived data.**

  Follow `docs/IOS_SIMULATOR_VALIDATION.md` and
  `docs/IOS_RUNTIME_SERVICES.md` completely. Create or resolve a simulator
  owned by this workspace, store its explicit UUID in
  `HANGTEN_REST_PREVIEW_SIMULATOR_UDID`, and never use `booted`. Build with:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" \
    -derivedDataPath .context/DerivedData-rest-block-preview \
    build
  ```

- [ ] **Step 2: Inspect a timed-rest preview in portrait.**

  Install the exact app produced above and launch the F100 plan at step 2:

  ```sh
  rtk xcrun simctl terminate "$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" com.hangten.training || true
  rtk xcrun simctl install "$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" .context/DerivedData-rest-block-preview/Build/Products/Debug-iphonesimulator/HangTen.app
  SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 \
  SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID=research.force-feedback-f100 \
  SIMCTL_CHILD_HANGTEN_REVIEW_STEP=2 \
  SIMCTL_CHILD_HANGTEN_REVIEW_AUTOSTART=1 \
  SIMCTL_CHILD_HANGTEN_REVIEW_PORTRAIT=1 \
  rtk xcrun simctl launch "$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" com.hangten.training
  ```

  After the six-second work interval enters its timed rest, capture and inspect
  `.context/rest-block-preview-portrait.png`. Confirm the next step’s hold is
  highlighted, the `Rest` indication and recovery copy remain visible, and no
  grip diagram is shown.

- [ ] **Step 3: Inspect an explicit-rest preview in landscape.**

  Relaunch the F80 plan at its first explicit recovery step (step 14) with
  landscape requested:

  ```sh
  SIMCTL_CHILD_HANGTEN_REVIEW_WORKOUT=1 \
  SIMCTL_CHILD_HANGTEN_REVIEW_PLAN_ID=research.force-feedback-f80 \
  SIMCTL_CHILD_HANGTEN_REVIEW_STEP=14 \
  SIMCTL_CHILD_HANGTEN_REVIEW_AUTOSTART=1 \
  SIMCTL_CHILD_HANGTEN_REVIEW_LANDSCAPE=1 \
  rtk xcrun simctl launch "$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" com.hangten.training
  rtk xcrun simctl io "$HANGTEN_REST_PREVIEW_SIMULATOR_UDID" screenshot .context/rest-block-preview-landscape.png
  ```

  Confirm the next work step’s board holds are highlighted in landscape, the
  landscape `Rest` pill and recovery cue remain visible, the board is centered,
  and no hand cue cards appear during rest. Use `view_image` to inspect both
  screenshots rather than treating a successful launch as visual validation.

- [ ] **Step 4: Check the no-preview edge case and clean up only this simulator.**

  Confirm the unit test for the final rest step remains green. Shut down only
  `$HANGTEN_REST_PREVIEW_SIMULATOR_UDID` after inspection:

  ```sh
  rtk xcrun simctl shutdown "$HANGTEN_REST_PREVIEW_SIMULATOR_UDID"
  ```

- [ ] **Step 5: Record validation evidence.**

  In the implementer report, record the simulator name and UUID, exact build
  and test commands, both states inspected, screenshot paths, and any behavior
  that still requires a physical device. Do not claim visual validation based
  only on compilation.
