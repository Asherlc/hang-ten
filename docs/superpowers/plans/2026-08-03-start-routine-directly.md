# Start Routine Directly Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the plan-detail “Start routine” action open the workout and begin the existing three-second countdown on the first tap.

**Architecture:** Add an opt-in `startsImmediately` intent to `WorkoutView`, defaulting to `false` so all existing entry points remain manual-start. `PlanDetailView` is the only production caller that opts in; `WorkoutView` evaluates a pure, one-shot `WorkoutSessionPolicy` decision from its existing session state and calls the existing `toggleRunning()` implementation, keeping one shared timer and countdown.

**Tech Stack:** Swift 5, SwiftUI, XCTest, Xcode 26, iOS 17+, `xcodebuild`, and the repository’s isolated-simulator workflow.

## Global Constraints

- The minimum deployment target remains iOS 17.0.
- The plan-detail “Start routine” action is the only production route that opts into immediate start.
- A `WorkoutView(plan:)` call without the opt-in starts idle, preserving the current manual control.
- The existing three-second countdown remains part of the shared workout clock; do not create a second timer or alter its duration.
- Repeated SwiftUI `onAppear` calls must not reset or duplicate the auto-start countdown.
- The existing `HANGTEN_REVIEW_AUTOSTART` DEBUG route remains supported and must not double-start an explicitly auto-started workout.
- Step navigation and “Skip step” remain disabled during the initial countdown.
- Existing pause, resume, cancellation, interruption, completion, destructive end, audio, board highlighting, and HealthKit behavior remain unchanged.
- No routine-library schema, routine content, board mapping, persistence, or dependency changes are in scope.
- Run a failing test before each production behavior implementation and use `rtk` for repository shell commands.

---

### Task 1: Add and wire the one-shot immediate-start intent

**Files:**
- Modify: `HangTenTests/WorkoutTimelineTests.swift` — extend the existing `WorkoutSessionPolicyTests` coverage.
- Modify: `HangTen/Views/RootView.swift:907-950` — add the pure auto-start decision to `WorkoutSessionPolicy`.
- Modify: `HangTen/Views/RootView.swift:949-970` — add the `WorkoutView` opt-in property and one-shot state.
- Modify: `HangTen/Views/RootView.swift:1080-1120` — evaluate the opt-in during normal workout appearance setup.
- Modify: `HangTen/Views/RootView.swift:727-745` — pass the opt-in from the plan-detail navigation link.

**Interfaces:**
- Consumes: Existing `WorkoutSessionPolicy.isFirstStart`, `WorkoutSessionPolicy.runStartDate`, `WorkoutView.toggleRunning()`, and `PlanDetailView` navigation.
- Produces: `WorkoutSessionPolicy.shouldAutoStart(startsImmediately:didAutoStart:startedAt:routineStartedAt:) -> Bool` and `WorkoutView(plan:startsImmediately:)`, where `startsImmediately` defaults to `false`.

- [ ] **Step 1: Add the failing policy tests.**

  Add these methods to the existing `WorkoutSessionPolicyTests` in
  `HangTenTests/WorkoutTimelineTests.swift`:

  ```swift
  func testImmediateStartIsAllowedOnlyForAnUnstartedFirstAppearance() {
      XCTAssertTrue(
          WorkoutSessionPolicy.shouldAutoStart(
              startsImmediately: true,
              didAutoStart: false,
              startedAt: nil,
              routineStartedAt: nil
          )
      )
  }

  func testImmediateStartIsDisabledAfterTheOneShotHasRun() {
      XCTAssertFalse(
          WorkoutSessionPolicy.shouldAutoStart(
              startsImmediately: true,
              didAutoStart: true,
              startedAt: nil,
              routineStartedAt: nil
          )
      )
  }

  func testImmediateStartDoesNotRestartAStartedOrPausedSession() {
      let startedAt = Date(timeIntervalSinceReferenceDate: 1_000)

      XCTAssertFalse(
          WorkoutSessionPolicy.shouldAutoStart(
              startsImmediately: true,
              didAutoStart: false,
              startedAt: startedAt,
              routineStartedAt: startedAt
          )
      )
      XCTAssertFalse(
          WorkoutSessionPolicy.shouldAutoStart(
              startsImmediately: true,
              didAutoStart: false,
              startedAt: nil,
              routineStartedAt: startedAt
          )
      )
  }

  func testManualWorkoutRouteDoesNotAutoStart() {
      XCTAssertFalse(
          WorkoutSessionPolicy.shouldAutoStart(
              startsImmediately: false,
              didAutoStart: false,
              startedAt: nil,
              routineStartedAt: nil
          )
      )
  }
  ```

- [ ] **Step 2: Run the focused tests and confirm the red state.**

  Run the focused XCTest suite against the dedicated simulator owned by this
  workspace:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-start-routine \
    test \
    -only-testing:HangTenTests/WorkoutSessionPolicyTests
  ```

  Expected result: the test target fails to compile because
  `WorkoutSessionPolicy.shouldAutoStart` does not exist yet. Do not weaken the
  assertions or add production code before recording this red result.

- [ ] **Step 3: Implement the pure policy and the opt-in view state.**

  Add this method to `WorkoutSessionPolicy`:

  ```swift
  static func shouldAutoStart(
      startsImmediately: Bool,
      didAutoStart: Bool,
      startedAt: Date?,
      routineStartedAt: Date?
  ) -> Bool {
      startsImmediately
          && !didAutoStart
          && startedAt == nil
          && isFirstStart(routineStartedAt: routineStartedAt)
  }
  ```

  Add an opt-in stored property and one-shot state to `WorkoutView`:

  ```swift
  let startsImmediately: Bool = false

  @State private var didAutoStart = false
  ```

  The stored-property default above keeps existing `WorkoutView(plan: plan)`
  call sites compiling unchanged. Do not change any existing `@State` initial
  values.

- [ ] **Step 4: Trigger the existing start logic once during appearance.**

  In the existing `WorkoutView.onAppear`, keep the DEBUG review-step and
  `HANGTEN_REVIEW_AUTOSTART` handling intact. After that DEBUG block and before
  `initializeStopwatches()`, add:

  ```swift
  if WorkoutSessionPolicy.shouldAutoStart(
      startsImmediately: startsImmediately,
      didAutoStart: didAutoStart,
      startedAt: startedAt,
      routineStartedAt: routineStartedAt
  ) {
      didAutoStart = true
      toggleRunning()
  }
  ```

  This must call `toggleRunning()` rather than duplicating its clock setup, so
  the plan-detail path receives the same `routineStartedAt` and three-second
  future `startedAt` used by a manual start. The existing DEBUG auto-start
  guard remains safe because it only starts when `startedAt == nil`.

- [ ] **Step 5: Opt the plan-detail link into immediate start.**

  Change only the destination of the existing plan-detail link:

  ```swift
  NavigationLink(destination: WorkoutView(plan: plan, startsImmediately: true)) {
      // Existing “Start routine” label and styling remain unchanged.
  }
  ```

  Leave the `HomeView` DEBUG workout route and every other `WorkoutView(plan:)`
  call site on the default `false` behavior.

- [ ] **Step 6: Run the focused tests and verify green.**

  Run the same focused command from Step 2. Expected result: all
  `WorkoutSessionPolicyTests` pass, including the new first-appearance,
  repeated-appearance, started/paused, and manual-route cases.

- [ ] **Step 7: Run the complete test suite and inspect the diff.**

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-start-routine \
    test
  rtk git diff --check
  ```

  Confirm the change is limited to the policy test and the plan-detail/workout
  start wiring. No routine data, board mapping, or unrelated formatting should
  appear in the diff.

- [ ] **Step 8: Commit the implementation.**

  ```sh
  rtk git add HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "fix: start routine from plan detail"
  ```

## Runtime validation after implementation

Use the `validate-hang-ten-ios` workflow on a dedicated simulator with an
explicit UUID. Build with the workspace-specific Derived Data path above,
install the exact built app, and launch the DEBUG plan-detail route.

Verify all of the following:

1. One tap on the visible plan-detail “Start routine” action opens the workout
   screen and immediately shows the existing “Cancel countdown” state; no
   second tap on the workout control is required.
2. During the countdown, Routine and Skip step remain disabled; after the
   countdown, the workout begins at step 1 with the normal board highlight and
   audio behavior.
3. The direct `HANGTEN_REVIEW_WORKOUT=1` route still opens idle with its normal
   “Start routine” control.
4. Repeated appearance/navigation does not restart or extend the countdown.
5. Portrait and landscape layouts show the same countdown and timer state.

Shut down only the dedicated simulator UUID after validation. Do not use
`booted` or modify another workspace’s simulator.
