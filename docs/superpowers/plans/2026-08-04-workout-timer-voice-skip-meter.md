# Workout timer voice, skip preview, and motherboard meter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make skipped-step preparation a three-second hold preview, restrict workout speech to numeric countdowns without stage spillover, and hide the workout motherboard meter unless live Bluetooth data is streaming.

**Architecture:** Preserve `WorkoutSessionState` as the authoritative monotonic timer and countdown-kind owner. Extend the pure `WorkoutTimeline.boardCue` policy with explicit skip-countdown context so only skip preparation can show preview holds. Keep audio cue selection pure and numeric, and make the view stop the audio coach whenever the selected cue disappears. Add a small `MotherboardConnectionState` visibility predicate and use it only around the workout meter.

**Tech Stack:** Swift 5, SwiftUI, AVFoundation speech synthesis, CoreBluetooth service state, XCTest, Xcode/iOS Simulator.

## Global Constraints

- Skip preparation is exactly three seconds; the initial workout countdown remains three seconds.
- Every spoken workout cue is exactly one numeric countdown value; no labels, instructions, rest prompts, combined phrases, or completion text are spoken.
- Initial countdowns suppress board highlights; skip countdowns preview the destination holds in `.preview` mode and activate them when the countdown ends.
- The workout `MotherboardMeterView` is visible only while `MotherboardConnectionState.streaming`; the Progress dashboard sensor card is unchanged.
- Use test-driven development: each behavior change starts with a failing XCTest that fails for the intended missing behavior.
- Keep implementation changes focused; do not change Bluetooth protocol, plan content, HealthKit records, speech settings, or final-step completion semantics.
- Keep logs, screenshots, simulator metadata, and other derived output under `.context`.
- Any simulator or other external resource must include `CONDUCTOR_WORKSPACE_NAME` in its exact name, have ownership recorded immediately, and be deleted by an exit cleanup trap before completion.

---

## File and responsibility map

- `HangTen/Models/WorkoutTimeline.swift` — pure timeline and board-cue resolution, including whether a skip countdown may preview holds.
- `HangTen/Views/RootView.swift` — workout session presentation, audio cue selection/dispatch, portrait and landscape board/meter composition, and skip-countdown duration policy.
- `HangTen/Models/WorkoutAudioCoach.swift` — speech synthesizer interruption boundary; no new spoken content belongs here.
- `HangTen/Models/MotherboardModels.swift` — connection-state presentation predicate for the workout meter.
- `HangTenTests/WorkoutTimelineTests.swift` — timer, board-cue, session-state, audio-cue, and audio-action regression coverage.
- `HangTenTests/MotherboardModelsTests.swift` — connection-state visibility coverage.

Tasks that touch `RootView.swift` are intentionally sequential. Each worker must inspect the current tree before editing, preserve other workers' changes, and commit only its assigned slice.

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

- [ ] **Step 2: Run the focused tests and verify the intended failures.**

  Run:

  ```bash
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
    -only-testing:HangTenTests/WorkoutTimelineTests test
  ```

  Expected: the new skip-preview test fails because countdown board cues are currently suppressed, and the updated skip-duration assertions fail because the implementation still uses five seconds. If the target device is unavailable, select an installed iOS Simulator with `rtk xcrun simctl list devices available` and record that choice in `.context/workout-timer-voice-skip-meter-test.log`.

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

## Task 2: Enforce numeric-only speech and stop stale utterances

**Files:**
- Modify: `HangTen/Views/RootView.swift:938-1006, 1368-1375, 2316-2390`
- Modify: `HangTen/Models/WorkoutAudioCoach.swift:18-33`
- Test: `HangTenTests/WorkoutTimelineTests.swift:781-865`

**Interfaces:**
- Consumes: `WorkoutAudioCuePolicy.moment`, `WorkoutAudioMoment`, and `WorkoutSessionState.countdownKind` from Task 1.
- Produces: `WorkoutAudioCuePolicy.action(for:) -> WorkoutAudioCueAction`, where a missing moment maps to `.stop` and a numeric moment maps to `.speak(WorkoutAudioMoment)`; `WorkoutView.audioMoment` has no segment-start phrase branch.

- [ ] **Step 1: Add failing pure audio-action and skip-cue tests.**

  In `WorkoutTimelineTests.swift`, add tests equivalent to:

  ```swift
  func testMissingAudioMomentRequestsImmediateStop() {
      XCTAssertEqual(WorkoutAudioCuePolicy.action(for: nil), .stop)
  }

  func testNumericAudioMomentRequestsSpeechWithoutAStageLabel() {
      let moment = WorkoutAudioMoment(key: "skip-3", phrase: "3")
      XCTAssertEqual(
          WorkoutAudioCuePolicy.action(for: moment),
          .speak(moment)
      )
      XCTAssertTrue(moment.phrase.allSatisfy { $0.isNumber })
  }

  func testSkipCountdownCueUsesOnlyTheCountdownNumber() {
      XCTAssertEqual(
          WorkoutAudioCuePolicy.moment(
              stepID: stepID,
              segmentName: "active",
              initialCountdown: 3,
              intervalSecondsRemaining: 60,
              isComplete: false,
              countdownKind: .skip
          ),
          WorkoutAudioMoment(key: "skip-3", phrase: "3")
      )
  }
  ```

  Keep the existing tests for initial, interval, short-interval, segment-start, and completion policy behavior; update them only if the new optional countdown-kind parameter changes the call signature.

- [ ] **Step 2: Run the focused tests and verify the intended failures.**

  Run the `WorkoutTimelineTests` command from Task 1. Expected: compilation or assertion failures for the new action type and skip-cue path, while the existing policy tests remain green. Fix test syntax or target selection if the failure is unrelated to the missing behavior.

- [ ] **Step 3: Implement the numeric-only policy and view dispatch.**

  Add:

  ```swift
  enum WorkoutAudioCueAction: Equatable {
      case speak(WorkoutAudioMoment)
      case stop
  }
  ```

  Add `WorkoutAudioCuePolicy.action(for:)` and extend `moment` with an optional `countdownKind` parameter. Use `initial-\(countdown)` keys for the initial countdown and `skip-\(countdown)` keys for skip preparation; interval keys remain step/segment/countdown based. Remove the `segmentElapsed < 0.55` stage-start branch and `spokenStartPhrase(for:)` from `WorkoutView.audioMoment`; return the numeric policy result for countdown and interval state only.

  Change the `audioMoment` change handler to stop for `.stop` or when audio is disabled, and speak only the numeric phrase for `.speak`. In `WorkoutAudioCoach.speak`, call `stopSpeaking(at: .immediate)` before creating the replacement utterance, even if `isSpeaking` is currently false, so a boundary transition cannot leave a queued utterance.

- [ ] **Step 4: Run the focused tests and inspect the diff for forbidden phrases.**

  Run:

  ```bash
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
    -only-testing:HangTenTests/WorkoutTimelineTests test
  rtk rg -n 'Session complete|Begin minute|Begin warm up|Hang\. |Rest\. |spokenStartPhrase' HangTen/Views/RootView.swift
  ```

  Expected: all focused tests pass and the phrase search returns no workout speech implementation matches. UI copy may still contain visible text; only speech phrase construction is in scope.

- [ ] **Step 5: Commit the task.**

  ```bash
  rtk git add HangTen/Views/RootView.swift HangTen/Models/WorkoutAudioCoach.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "fix: keep workout voice cues numeric"
  ```

## Task 3: Hide the workout meter while the motherboard is disconnected

**Files:**
- Modify: `HangTen/Models/MotherboardModels.swift:110-120`
- Modify: `HangTen/Views/RootView.swift:1548-1556, 1624-1633`
- Test: `HangTenTests/MotherboardModelsTests.swift:4-10`

**Interfaces:**
- Consumes: `MotherboardConnectionState` in the workout view.
- Produces: `MotherboardConnectionState.showsWorkoutMeter -> Bool`, true only for `.streaming`.

- [ ] **Step 1: Add the failing connection-state visibility test.**

  Add a test that asserts `.streaming.showsWorkoutMeter` is true and every other state (`.bluetoothUnavailable`, `.unauthorized`, `.idle`, `.scanning`, `.connecting`, `.calibrating`, `.disconnected`, `.failed`) is false.

- [ ] **Step 2: Run the focused model tests and verify the intended failure.**

  Run:

  ```bash
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
    -only-testing:HangTenTests/MotherboardModelsTests test
  ```

  Expected: the test fails to compile because the predicate does not yet exist.

- [ ] **Step 3: Implement and apply the visibility predicate.**

  Add the computed property to `MotherboardConnectionState`:

  ```swift
  var showsWorkoutMeter: Bool {
      self == .streaming
  }
  ```

  Wrap the existing `meter(step: step)` call in both portrait and landscape workout layouts with `if motherboardBluetoothService.state.showsWorkoutMeter`. Do not remove or conditionally hide `MotherboardCard` from `ProgressDashboardView`.

- [ ] **Step 4: Run the focused model tests and verify the green result.**

  Re-run the command from Step 2. Expected: all motherboard model tests pass.

- [ ] **Step 5: Commit the task.**

  ```bash
  rtk git add HangTen/Models/MotherboardModels.swift HangTen/Views/RootView.swift HangTenTests/MotherboardModelsTests.swift
  rtk git commit -m "fix: hide workout meter without motherboard"
  ```

## Task 4: Integration verification and simulator review

**Files:**
- No production-file changes expected.
- Derived output: `.context/workout-timer-voice-skip-meter/`

- [ ] **Step 1: Establish workspace-owned simulator resource metadata.**

  Set a task-local workspace name from `CONDUCTOR_WORKSPACE_NAME` (falling back to `richmond-v1` only if unset), choose an available iOS Simulator, and create `.context/workout-timer-voice-skip-meter/ownership.txt` containing the exact device UDID, device name, workspace name, and creation timestamp. Install an exit trap in the validation shell that shuts down and deletes that exact device only; never delete shared or unknown devices.

- [ ] **Step 2: Run the complete XCTest target.**

  ```bash
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 16 Pro' test \
    2>&1 | tee .context/workout-timer-voice-skip-meter/full-tests.log
  ```

  Record the actual destination if the installed runtime uses another device. Require a clean pass with no test failures before simulator review.

- [ ] **Step 3: Build and install the DEBUG app using the existing review route.**

  Follow `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md`. Build the `HangTen` scheme for the workspace-owned device, install the resulting app, and use the existing DEBUG environment routes (`HANGTEN_REVIEW_WORKOUT`, `HANGTEN_REVIEW_AUTOSTART`, and `HANGTEN_REVIEW_LANDSCAPE`/`HANGTEN_REVIEW_PORTRAIT`) rather than changing production navigation. Store build/install logs under `.context/workout-timer-voice-skip-meter/`.

- [ ] **Step 4: Inspect the required behavior in portrait and landscape.**

  Capture screenshots under `.context/workout-timer-voice-skip-meter/` for:

  - initial three-second countdown with no board highlights;
  - a non-final skip showing `3`, `2`, `1` and the destination holds in preview styling;
  - the destination step after countdown with active hold styling;
  - a rest interval showing the existing next-hold preview;
  - a disconnected workout with no live motherboard meter section;
  - the Progress dashboard disconnected state retaining the Training sensor card.

  With audio enabled, inspect runtime logs for numeric `Speaking cue` entries only. Confirm that no utterance continues after a countdown cue becomes unavailable. Repeat the skip transition in both orientations.

- [ ] **Step 5: Verify cleanup before reporting completion.**

  Stop the app and simulator, run the exact cleanup trap or cleanup command, verify the owned UDID no longer exists, and leave shared simulators untouched. Check `rtk git status --short` and `rtk git diff origin/main...HEAD --check`; report any cleanup failure instead of claiming completion.

## Final handoff

After Tasks 1–4, run:

```bash
rtk git log --oneline origin/main..HEAD
rtk git status --short
rtk git diff origin/main...HEAD --stat
```

Confirm that the spec and plan commits plus the three focused implementation commits are present, all tests passed, simulator evidence is in `.context/workout-timer-voice-skip-meter/`, and no workspace-owned external resource remains.
