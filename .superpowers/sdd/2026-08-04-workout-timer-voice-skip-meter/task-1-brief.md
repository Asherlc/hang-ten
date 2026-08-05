## Task 1: Make skipped-step preparation a three-second hold preview

**Files:**
- Modify: `HangTen/Models/WorkoutTimeline.swift`
- Modify: `HangTen/Views/RootView.swift:943-1014, 1290-1310, 1510-1635`
- Test: `HangTenTests/WorkoutTimelineTests.swift:208-257, 372-406, 867-1100`

**Interfaces:**
- Consumes: the existing `WorkoutSessionState.countdownKind`, `WorkoutTimeline.boardCue`, and `WorkoutSessionPolicy.countdownDuration(for:)` paths.
- Produces: `WorkoutTimeline.boardCue(..., isSkipCountdown: Bool = false)` behavior that returns the destination step in `.preview` mode only while a skip countdown is active; `WorkoutSessionPolicy.skipCountdownDuration == 3`.

- [ ] **Step 1: Add the failing board-cue and duration tests.**

  In `WorkoutTimelineTests.swift`, add a test beside the existing board-cue tests that supplies the destination work step, `countdown: 3`, `isComplete: false`, and `isSkipCountdown: true`, then asserts:

  ```swift
  XCTAssertEqual(cue.step?.id, "next-work")
  XCTAssertEqual(cue.mode, .preview)
  XCTAssertFalse(cue.isResting)
  XCTAssertFalse(cue.isSuppressed)
  ```

  Update the skip-duration assertion and paused-skip lifecycle expectations to require `3` seconds and an expiry at `now + 3`. Do not change the direct `WorkoutSessionPolicy.countdownRemaining` test that uses a manually supplied five-second anchor; it tests ceiling math, not the skip constant.

  **API-first RED acceptance:** This test intentionally names the new `isSkipCountdown` argument and `.preview` result before Step 3 adds that public API. Its initial RED checkpoint may therefore be a compile failure such as `Extra argument 'isSkipCountdown' in call` (and consequent type-inference errors), rather than an executable assertion failure. That compile failure is accepted evidence that the requested interface is absent. After the minimal API surface exists, the same test must exercise the behavioral branch and pass in Step 4; do not add a product-only API-surface commit merely to obtain a separate behavioral RED.

- [ ] **Step 2: Run the focused tests and verify the intended failures.**

  Run:

  ```bash
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
    -only-testing:HangTenTests/WorkoutTimelineTests test
  ```

  Expected: if the API-first test compiles, the new skip-preview test fails because countdown board cues are currently suppressed, and the updated skip-duration assertions fail because the implementation still uses five seconds. If the API-first test does not compile because `isSkipCountdown` is absent, record that compiler failure as the accepted RED checkpoint described in Step 1. If the target device is unavailable, select an installed iOS Simulator with `rtk xcrun simctl list devices available` and record that choice in `.context/workout-timer-voice-skip-meter-test.log`.

- [ ] **Step 3: Implement the minimal timeline/session change.**

  In `WorkoutTimeline.swift`, preserve the existing call sites by adding an optional `isSkipCountdown: Bool = false` parameter after the existing `isComplete` parameter on both `boardCue` overloads. Permit a cue during countdown only when `countdown > 0 && isSkipCountdown`; return the existing suppressed cue for initial countdowns and completion. For an allowed skip countdown, return the resolved current destination step with `.preview` mode and leave `isResting` derived from the destination step's actual rest state.

  In `RootView.swift`, change `WorkoutSessionPolicy.skipCountdownDuration` from `5` to `3`, pass `sessionState.countdownKind == .skip` into `timeline.boardCue`, and derive `showsHoldPreview` from `highlightMode == .preview && !highlightedHoldIDs.isEmpty` so skip preparation receives the existing preview label without being rendered as rest.

- [ ] **Step 4: Run the focused tests and verify the green result.**

  Re-run the command from Step 2. Expected: all `WorkoutTimelineTests` pass, including initial countdown suppression, skip timing, cancellation/interruption, final skip, rest preview, and the new skip-countdown preview.

- [ ] **Step 5: Commit the task.**

  ```bash
  rtk git add HangTen/Models/WorkoutTimeline.swift HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "fix: preview holds during skip preparation"
  ```
