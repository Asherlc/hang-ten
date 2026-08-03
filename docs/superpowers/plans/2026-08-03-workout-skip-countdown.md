# Workout Skip Countdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every non-final Skip step action five seconds for board preparation, then start the destination step automatically while preserving the existing workout clock and completion semantics.

**Architecture:** Keep `WorkoutView` as the owner of one elapsed session clock. Add an explicit initial-versus-skip countdown kind and pure countdown timing helpers to the existing `WorkoutSessionPolicy`; represent a skip countdown with the destination elapsed position plus a future `startedAt`. Keep direct Routine selection immediate, route final skips through the existing plan-duration completion path, and derive UI/audio from the same elapsed position.

**Tech Stack:** Swift 5, SwiftUI, XCTest, Xcode 26, iOS 17+, `xcodebuild`, `AVSpeechSynthesizer`, and the repository’s isolated-simulator validation workflow.

## Global Constraints

- The initial three-second start countdown remains unchanged.
- Every non-final Skip step action shows a five-second countdown, whether the session was running or paused.
- A skip countdown automatically starts the destination step in the running state.
- Skipping the final step reaches the existing completion UI immediately without a countdown.
- Direct Routine selection remains immediate and preserves running or paused state.
- `WorkoutView` continues to use one elapsed session clock; do not add a competing timer model.
- During a skip countdown, destination holds and grip cues remain inactive and Routine/Skip controls remain disabled.
- Countdown speech must announce `5`, `4`, `3`, `2`, and `1` once each.
- Cancelling or interrupting a skip countdown leaves the destination step paused and preserves the original routine start date.
- Existing completion, Apple Health, orientation, and initial-countdown behavior must remain intact.
- No plan-library schema, routine content, board mapping, persistence, or HealthKit record-format changes are in scope.
- Use `rtk` for repository shell commands and run tests before claiming success.

---

## File map

- `HangTen/Views/RootView.swift` — extend the existing countdown policy and integrate countdown kind, skip transition, cancellation/interruption behavior, and spoken countdown keys into `WorkoutView`.
- `HangTenTests/WorkoutTimelineTests.swift` — add pure countdown-policy tests beside the existing timeline and session-policy coverage.
- `docs/IOS_RUNTIME_SERVICES.md` — document the post-skip countdown and its interruption/completion contract.
- `docs/IOS_SIMULATOR_VALIDATION.md` — add explicit running/paused skip-countdown and spoken 5-4-3-2-1 review scenarios.

### Task 1: Specify and implement pure countdown timing policy

**Files:**
- Modify: `HangTenTests/WorkoutTimelineTests.swift:104-130`
- Modify: `HangTen/Views/RootView.swift:858-884`

**Interfaces:**
- Consumes: existing `WorkoutSessionPolicy` and `Date` values.
- Produces: the internal `WorkoutCountdownKind` enum and these testable policy APIs for `WorkoutView`:

  ```swift
  enum WorkoutCountdownKind: Equatable {
      case initial
      case skip
  }

  enum WorkoutSessionPolicy {
      static let initialCountdownDuration: TimeInterval = 3
      static let skipCountdownDuration: TimeInterval = 5

      static func startDate(for kind: WorkoutCountdownKind, now: Date) -> Date
      static func countdownRemaining(startedAt: Date?, now: Date) -> Int
  }
  ```

- [ ] **Step 1: Add failing tests for both countdown durations and remaining seconds.**

  Extend `WorkoutSessionPolicyTests` with this exact coverage:

  ```swift
  func testCountdownDurationsKeepInitialStartAtThreeAndSkipStartAtFive() {
      let now = Date(timeIntervalSinceReferenceDate: 2_000)

      XCTAssertEqual(
          WorkoutSessionPolicy.startDate(for: .initial, now: now),
          now.addingTimeInterval(3)
      )
      XCTAssertEqual(
          WorkoutSessionPolicy.startDate(for: .skip, now: now),
          now.addingTimeInterval(5)
      )
  }

  func testCountdownRemainingUsesCeilingAndReachesZeroAtStart() {
      let now = Date(timeIntervalSinceReferenceDate: 2_000)
      let start = now.addingTimeInterval(5)

      XCTAssertEqual(
          WorkoutSessionPolicy.countdownRemaining(startedAt: start, now: now),
          5
      )
      XCTAssertEqual(
          WorkoutSessionPolicy.countdownRemaining(
              startedAt: start,
              now: now.addingTimeInterval(1.1)
          ),
          4
      )
      XCTAssertEqual(
          WorkoutSessionPolicy.countdownRemaining(
              startedAt: start,
              now: start
          ),
          0
      )
      XCTAssertEqual(
          WorkoutSessionPolicy.countdownRemaining(startedAt: nil, now: now),
          0
      )
  }
  ```

- [ ] **Step 2: Run the focused tests and confirm the red state.**

  Run:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-skip-countdown \
    test \
    -only-testing:HangTenTests/WorkoutSessionPolicyTests
  ```

  Expected result: the test target fails to compile because
  `WorkoutCountdownKind`, `startDate(for:now:)`, and
  `countdownRemaining(startedAt:now:)` do not exist yet. Do not weaken the
  assertions.

- [ ] **Step 3: Implement the minimal policy APIs.**

  Replace the hard-coded three-second addition in `WorkoutSessionPolicy` with
  the constants and helpers below, while preserving
  `isFirstStart` and `completedWorkoutInterval`:

  ```swift
  enum WorkoutCountdownKind: Equatable {
      case initial
      case skip
  }

  enum WorkoutSessionPolicy {
      static let initialCountdownDuration: TimeInterval = 3
      static let skipCountdownDuration: TimeInterval = 5

      static func startDate(for kind: WorkoutCountdownKind, now: Date) -> Date {
          let duration = kind == .initial
              ? initialCountdownDuration
              : skipCountdownDuration
          return now.addingTimeInterval(duration)
      }

      static func countdownRemaining(startedAt: Date?, now: Date) -> Int {
          guard let startedAt, startedAt > now else { return 0 }
          return max(1, Int(ceil(startedAt.timeIntervalSince(now))))
      }
  }
  ```

  Keep `runStartDate(routineStartedAt:now:)` returning `now` for an already
  started session and use `startDate(for: .initial, now:)` only for the first
  start.

- [ ] **Step 4: Run the focused tests and confirm green.**

  Re-run the command from Step 2. Expected result: all
  `WorkoutSessionPolicyTests` pass, including the pre-existing session-start
  and completion-interval tests.

- [ ] **Step 5: Commit the timing policy.**

  ```sh
  rtk git add HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "feat: add workout countdown timing policy"
  ```

### Task 2: Integrate skip countdown state, UI, and audio

**Files:**
- Modify: `HangTen/Views/RootView.swift:886-1564`
- Test: `HangTenTests/WorkoutTimelineTests.swift:104-160`

**Interfaces:**
- Consumes: `WorkoutCountdownKind`, `WorkoutSessionPolicy.startDate(for:now:)`, and `WorkoutSessionPolicy.countdownRemaining(startedAt:now:)` from Task 1; existing `WorkoutTimeline.skipTarget(from:)`.
- Produces: non-final skip behavior in portrait and landscape, with the existing `countdown`, `canNavigate`, board-highlight, control, and `WorkoutAudioMoment` rendering paths driven by the destination elapsed position.

- [ ] **Step 1: Run the existing focused policy/timeline tests before editing.**

  Run:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-skip-countdown \
    test \
    -only-testing:HangTenTests/WorkoutTimelineTests
  ```

  Expected result: the existing timeline/session-policy suite passes before
  the UI state change.

- [ ] **Step 2: Add explicit countdown-kind state to `WorkoutView`.**

  Add this state beside the existing `startedAt` and `pausedElapsed` values:

  ```swift
  @State private var countdownKind: WorkoutCountdownKind?
  ```

  Use `.initial` only when the first start schedules the existing three-second
  start. Use `.skip` only while a post-skip five-second start is pending. A
  future `startedAt` plus the destination `pausedElapsed` remains the single
  clock representation; do not create a `Timer` or a second elapsed value.

- [ ] **Step 3: Route first start, resume, pause, and cancellation through the kind.**

  In `toggleRunning()`:

  - For the first start, call `WorkoutSessionPolicy.startDate(for: .initial,
    now:)`, set `routineStartedAt` to that original start date, and set
    `countdownKind = .initial`.
  - For a resume from a paused session, start immediately and clear
    `countdownKind`.
  - When pausing an already-running session, add elapsed time, clear
    `startedAt`, clear `countdownKind`, and stop speech.

  Replace the unconditional reset in `cancelCountdown()` with a kind-aware
  branch:

  ```swift
  private func cancelCountdown() {
      switch countdownKind {
      case .skip:
          startedAt = nil
          countdownKind = nil
          audioCoach.stop()
      case .initial, nil:
          startedAt = nil
          routineStartedAt = nil
          countdownKind = nil
          audioCoach.stop()
      }
  }
  ```

  A cancelled skip retains `pausedElapsed`, so the destination step is
  paused and resumable. Keep the initial cancellation behavior unchanged.

- [ ] **Step 4: Start a five-second countdown for non-final skips.**

  Add this helper next to `seek(to:)`:

  ```swift
  private func startSkipCountdown(to targetElapsed: TimeInterval) {
      pausedElapsed = targetElapsed
      startedAt = WorkoutSessionPolicy.startDate(for: .skip, now: Date())
      countdownKind = .skip
      audioCoach.stop()
  }
  ```

  Update `skipCurrentStep()` so it keeps the existing timeline boundary
  calculation, but branches on the final boundary:

  ```swift
  private func skipCurrentStep() {
      guard canNavigate else { return }

      let elapsed = currentElapsed(at: Date())
      guard let target = timeline.skipTarget(from: elapsed) else { return }

      if target >= plan.duration {
          seek(to: target)
      } else {
          startSkipCountdown(to: target)
      }
  }
  ```

  This preserves full-step/rest boundaries, makes a paused skip automatically
  running after five seconds, and keeps final-step completion immediate.

- [ ] **Step 5: Make countdown gating and direct seeks state-safe.**

  Replace the view-local countdown math with the policy helper and gate it on a
  pending kind:

  ```swift
  private func countdownRemaining(at date: Date) -> Int {
      guard countdownKind != nil else { return 0 }
      return WorkoutSessionPolicy.countdownRemaining(startedAt: startedAt, now: date)
  }
  ```

  Update `seek(to:)` to clear `countdownKind` before applying the target. Keep
  the existing rule that a seek while running resets `startedAt` to `Date()`;
  a seek while paused keeps `startedAt` nil. This leaves direct Routine
  selection immediate and preserves its current running/paused state.

  Keep `canNavigate` as the single gate. Because it already checks
  `countdownRemaining == 0` and elapsed time below plan duration, both Routine
  and Skip step remain disabled during a skip countdown and after completion.

- [ ] **Step 6: Preserve interruption safety and update countdown audio keys.**

  Keep `pauseForInterruption()` calling `cancelCountdown()` when `startedAt`
  is in the future. The kind-aware cancellation must therefore leave a
  post-skip interruption paused at the destination while still resetting an
  initial countdown to the not-started state.

  Change only the countdown audio key from the initial-only namespace to a
  shared stable namespace:

  ```swift
  if countdown > 0 {
      return WorkoutAudioMoment(
          key: "countdown-\(countdown)",
          phrase: "\(countdown)"
      )
  }
  ```

  Keep `audioCoach.stop()` on skip, seek, pause, cancellation, interruption,
  and dismissal. The existing segment-start audio moment will speak the
  destination cue once the countdown reaches zero.

- [ ] **Step 7: Build and run the full XCTest suite.**

  Run:

  ```sh
  rtk xcodebuild \
    -project HangTen.xcodeproj \
    -scheme HangTen \
    -configuration Debug \
    -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" \
    -derivedDataPath .context/DerivedData-skip-countdown \
    test
  ```

  Expected result: the app target builds and all timeline/session-policy tests
  pass. If the build reports Swift formatting or concurrency warnings, fix
  only warnings introduced by this task before proceeding.

- [ ] **Step 8: Commit the workout integration.**

  ```sh
  rtk git add HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift
  rtk git commit -m "feat: count down before skipped workout steps"
  ```

### Task 3: Update runtime contract and simulator review scenarios

**Files:**
- Modify: `docs/IOS_RUNTIME_SERVICES.md:7-62`
- Modify: `docs/IOS_SIMULATOR_VALIDATION.md:150-169`

**Interfaces:**
- Consumes: the implemented five-second skip countdown and existing isolated
  simulator workflow.
- Produces: documentation that accurately describes countdown timing, paused
  skip behavior, cancellation/interruption, final-step completion, audio, and
  portrait/landscape review coverage.

- [ ] **Step 1: Update the runtime-services clock and navigation sections.**

  Preserve the existing initial-countdown statement and add the following
  contract to the workout navigation section:

  ```markdown
  Skipping a non-final step seeks to the next step's start, then schedules a
  five-second 5-4-3-2-1 countdown before that step begins automatically. This
  happens from both running and paused sessions; the session is running after
  the countdown. During the countdown, Routine and Skip step are disabled and
  board/grip cues remain inactive. Cancelling or interrupting the countdown
  leaves the destination step paused and preserves the original session start.
  Skipping the final step still reaches completion immediately without a
  countdown.
  ```

  Add the five-number countdown to the audio-moment list and state that stable
  countdown keys speak each number once before the destination start cue.

- [ ] **Step 2: Update simulator validation scenarios.**

  Keep the existing initial countdown, direct-selection, final-step, and
  orientation checks, and replace the immediate-skip wording with explicit
  scenarios:

  ```markdown
  - Skip during timed work and confirm the next step appears immediately with
    inactive holds, then observe and hear 5-4-3-2-1 before the next cue starts.
    Confirm the same behavior after pausing first; the session must be running
    once the countdown completes.
  - During a skip countdown, confirm Routine and Skip step are disabled. Cancel
    it and verify the destination remains paused and resumable. Background the
    app during the countdown and verify it returns paused at that destination.
  - Skip during timed rest and confirm the target still uses the full current
    step duration, including rest. Skip the final step and confirm completion
    appears immediately without a five-second countdown.
  ```

  Repeat these checks in portrait and landscape, including board highlights,
  grip cues, spoken audio, rotation, and the existing completion/logging path.

- [ ] **Step 3: Check documentation changes and commit.**

  Run:

  ```sh
  rtk git diff --check
  rtk git diff -- docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
  ```

  Confirm the docs do not claim that final skips count down or that paused
  skips remain paused after the countdown. Then commit:

  ```sh
  rtk git add docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
  rtk git commit -m "docs: describe skipped-step countdown validation"
  ```

### Task 4: Validate the installed app before handoff

**Files:**
- Read/validate: `docs/IOS_SIMULATOR_VALIDATION.md`
- Read/validate: `.codex/skills/validate-hang-ten-ios/SKILL.md`
- Validate: the installed `HangTen` app and generated validation artifacts under `.context/`

**Interfaces:**
- Consumes: the completed code, tests, and updated runtime contract from Tasks
  1–3.
- Produces: evidence that the countdown works in the real app in both supported
  workout orientations and that no existing completion/audio behavior regressed.

- [ ] **Step 1: Build, install, and launch on the isolated simulator.**

  Follow the repository validation skill and use a task-specific derived-data
  directory. At minimum, run the project build/test command from Task 2 and
  install the resulting app on the dedicated simulator selected by
  `$HANG_TEN_TEST_DEVICE_UDID`.

- [ ] **Step 2: Exercise the behavior in portrait.**

  Confirm all of the following on the installed app:

  - a new session still uses the three-second initial countdown;
  - Skip is disabled during that initial countdown;
  - a running non-final skip changes to the next step, counts 5-4-3-2-1,
    keeps holds inactive during the countdown, then activates the destination;
  - a paused non-final skip has the same countdown and is running afterward;
  - cancelling or backgrounding during the countdown leaves the destination
    paused and resumable;
  - a final skip reaches completion immediately and still requires Log session;
  - spoken countdown numbers and the destination start cue occur once each.

- [ ] **Step 3: Repeat the workout checks in landscape and during rotation.**

  Confirm the same countdown, control disabling, board highlights, grip cues,
  direct Routine behavior, and final completion state in landscape. Rotate
  during countdown, running, and paused states; timer state and the selected
  destination must not reset.

- [ ] **Step 4: Capture verification evidence and inspect the final diff.**

  Save screenshots/logs under `.context/` as directed by the validation skill,
  then run:

  ```sh
  rtk git status --short
  rtk git diff origin/main... --stat
  rtk git diff origin/main... --check
  ```

  Report the exact test command, simulator destination, and any validation
  limitation before claiming completion.

## Plan self-review

- Spec coverage: behavior, UI safety, audio, timing state, cancellation,
  interruption, final completion, direct selection, tests, docs, and both
  orientations are covered by Tasks 1–4.
- Completeness review: no unresolved requirements or open implementation
  choices are present; all commands and expected outcomes are specified.
- Type consistency: Task 1 defines `WorkoutCountdownKind` and both policy
  helpers before Task 2 consumes them. Task 2 keeps existing
  `WorkoutTimeline` APIs and UI state names intact.
