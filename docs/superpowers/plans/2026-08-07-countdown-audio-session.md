# Countdown audio session recovery Implementation Plan

> **For agentic workers:** REQUIRED: Use a fresh subagent for every implementation or configuration task. Execute this plan task-by-task using the checkbox (`- [ ]`) workflow.

**Goal:** Ensure spoken countdown cues stop and release iOS audio ducking only after speech has actually stopped, so music and podcasts recover their original volume.

**Architecture:** Keep `WorkoutAudioCoach` as the only AVFoundation speech boundary, but inject small speech and audio-session interfaces so its teardown ordering is testable. A stop request cancels the current utterance and waits for the synthesizer’s finish/cancel delegate callback before deactivating the shared `AVAudioSession`; replacement countdown cues keep the session active until the replacement utterance ends.

**Tech Stack:** Swift 5, SwiftUI, AVFoundation, XCTest, Xcode 26, iOS 17+.

## Global Constraints

- Preserve the `.playback` category, `.spokenAudio` mode, `.duckOthers` behavior, speech voice/rate/volume settings, and numeric countdown policy.
- Deactivate with `.notifyOthersOnDeactivation` only after the synthesizer reports that no utterance is speaking; do not leave the audio-session state marked inactive when deactivation throws.
- If final deactivation throws after speech has ended, queue at most one retry and run it only while the synthesizer remains stopped; keep the configured-session state true until a deactivation succeeds.
- Use test-driven development: the audio-coach regression test must fail before the production lifecycle change and pass afterward.
- Keep implementation changes focused on session teardown; do not change workout timing, cue phrases, Bluetooth behavior, HealthKit records, or visible UI.
- Keep logs, screenshots, simulator metadata, and other derived output under `.context`.
- Any simulator or other external resource must include `CONDUCTOR_WORKSPACE_NAME` in its exact name, have ownership recorded immediately, and be deleted by an exit cleanup trap before completion.

---

### Task 1: Make countdown audio-session teardown wait for speech completion

**Files:**
- Modify: `HangTen/Models/WorkoutAudioCoach.swift`
- Test: `HangTenTests/WorkoutTimelineTests.swift` by adding `WorkoutAudioCoachTests` and its test doubles
- Modify: `docs/IOS_RUNTIME_SERVICES.md` in the spoken-cues section

**Interfaces:**
- `WorkoutAudioCoach` consumes an injected `WorkoutSpeechSynthesizing` and `WorkoutAudioSessionManaging` boundary, with production defaults backed by `AVSpeechSynthesizer` and `AVAudioSession.sharedInstance()`.
- `WorkoutSpeechSynthesizing` exposes `delegate`, `isSpeaking`, `stopSpeaking(at:)`, and `speak(_:)` so tests can model asynchronous cancellation without using real audio output.
- `WorkoutAudioSessionManaging` exposes speech-session category configuration, activation, and deactivation-with-notification so tests can record the exact teardown order.

- [ ] **Step 1: Add the failing regression tests and deterministic test doubles.**

  Import `AVFoundation` in `HangTenTests/WorkoutTimelineTests.swift` and append an `@MainActor` `WorkoutAudioCoachTests` class. Add a recording audio-session fake and a speech-synthesizer fake whose `stopSpeaking(at:)` leaves `isSpeaking` true until the test explicitly sends `didCancel` or `didFinish` to the coach delegate.

  The first test must prove that stopping active speech does not deactivate the session while the synthesizer is still speaking, then does deactivate exactly once after cancellation is delivered:

  ```swift
  func testStopWaitsForSpeechCancellationBeforeDeactivatingAudioSession() async {
      let audioSession = RecordingWorkoutAudioSession()
      let synthesizer = RecordingWorkoutSpeechSynthesizer()
      let coach = WorkoutAudioCoach(
          synthesizer: synthesizer,
          audioSession: audioSession
      )

      coach.speak("3")
      coach.stop()

      XCTAssertEqual(audioSession.deactivationCount, 0)

      synthesizer.isSpeaking = false
      synthesizer.sendCancellation()
      await Task.yield()

      XCTAssertEqual(audioSession.deactivationCount, 1)
  }
  ```

  Add a second test that starts a cue, replaces it with the next numeric cue, delivers the old cue’s cancellation while the replacement is speaking, and asserts that the session remains active until the replacement finishes. The tests should also assert that activation occurs once for the cue sequence and the session deactivation uses the notification path.

- [ ] **Step 2: Run the focused tests and verify the intended RED result.**

  Run:

  ```bash
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
    -derivedDataPath .context/audio-session-red \
    -only-testing:HangTenTests/WorkoutAudioCoachTests test \
    2>&1 | tee .context/audio-session-red.log
  ```

  The run is expected to fail to compile because the current coach has no injectable test boundaries. A compile failure for the missing desired initializer/protocols is the intended RED checkpoint; fix test syntax or destination errors before continuing if they occur instead.

- [ ] **Step 3: Implement the minimal lifecycle fix.**

  In `WorkoutAudioCoach.swift`, add the two internal interfaces and production adapters. Keep the public behavior of `WorkoutAudioCoach.speak(_:)` and `stop()` unchanged except for ordering:

  ```swift
  func stop() {
      synthesizer.stopSpeaking(at: .immediate)
      isSpeaking = false
      deactivateAudioSessionIfSpeechStopped()
  }

  private func deactivateAudioSessionIfSpeechStopped() {
      guard !synthesizer.isSpeaking else { return }
      deactivateAudioSession()
  }
  ```

  Call the same helper from both `didFinish` and `didCancel`. This makes an immediate stop wait for the delegate callback when the synthesizer is still active, while a replacement cue keeps the session active because the new utterance is already speaking when the old cancellation callback arrives.

  Make `deactivateAudioSession()` attempt `deactivateAndNotifyOthers()` before clearing its configured-session flag. Log activation/deactivation errors with the existing `WorkoutAudio` logger instead of swallowing them. If final deactivation fails after speech has ended, schedule one retry that re-checks `isSpeaking` before attempting teardown; do not create unbounded retry tasks. Keep the production audio-session configuration exactly `.playback`, `.spokenAudio`, and `[.duckOthers]`, and keep deactivation exactly `.notifyOthersOnDeactivation`.

- [ ] **Step 4: Update the runtime note and run the focused green tests.**

  Add one concise sentence to `docs/IOS_RUNTIME_SERVICES.md` explaining that cancellation waits for the speech delegate before deactivating the session, preventing an AVAudioSession-busy teardown from leaving other audio ducked.

  Re-run the focused command from Step 2. Expected: both `WorkoutAudioCoachTests` pass with no test failures, and the audio-session fake records one notification-aware deactivation after the final utterance.

- [ ] **Step 5: Run the full unit-test target and commit the task.**

  Run:

  ```bash
  rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
    -derivedDataPath .context/audio-session-green \
    test 2>&1 | tee .context/audio-session-green.log
  ```

  Focused `WorkoutAudioCoachTests` and generic `build-for-testing` are mandatory green gates. For the full suite, success is required unless it reports only the known unrelated baseline failure exactly as:

  ```text
  Failing tests:
  	WorkoutActivityRecordingTests.testRecorderFailureSurfacesErrorWithoutCallingHealthKit()

  ** TEST FAILED **
  ```

  That exact non-zero baseline result is allowed only when no additional test failures appear. Record the full-suite output and validate the commit against the same rule; any changed signature or any new failure blocks the commit. Then commit only the plan, coach, test, and runtime-note changes:

  ```bash
  rtk git add docs/superpowers/plans/2026-08-07-countdown-audio-session.md \
    HangTen/Models/WorkoutAudioCoach.swift \
    HangTenTests/WorkoutTimelineTests.swift \
    docs/IOS_RUNTIME_SERVICES.md
  rtk git commit -m "fix: restore background audio after countdown cues"
  ```

## Integration verification

After Task 1 is reviewed, use the isolated iOS validation workflow with a simulator named `Hang Ten Conductor $CONDUCTOR_WORKSPACE_NAME Review`. Build with a workspace-local `.context/DerivedData`, exercise the DEBUG automatic countdown route with spoken cues enabled, and inspect the simulator with other audio playing when available. Confirm the countdown still speaks `3`, `2`, and `1`, the cue stops at the boundary, and the background audio returns after the final cue. Record the exact simulator UUID, commands, and observations under `.context`; the validation cleanup trap must remove the simulator and exact workspace-local artifacts before completion.
