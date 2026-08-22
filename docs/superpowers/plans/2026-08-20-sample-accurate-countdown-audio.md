# Sample-accurate countdown audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make spoken countdown cues begin on exact one-second audio deadlines without live-speech queue lateness.

**Architecture:** A new countdown-audio scheduler renders the numeric system-voice cues to PCM buffers before playback, then schedules all remaining buffers with `AVAudioPlayerNode` host times in one `AVAudioEngine` timeline. `WorkoutAudioCoach` owns the scheduler and its existing audio-session lifecycle; `WorkoutView` starts one schedule at the first visible countdown number and ignores later tick-driven number updates for that schedule.

**Tech Stack:** Swift 5, AVFoundation (`AVSpeechSynthesizer.write`, `AVAudioEngine`, `AVAudioPlayerNode`, `AVAudioTime`), XCTest, iOS 17+.

**Spec:** `docs/superpowers/specs/2026-08-20-sample-accurate-countdown-audio.md`

## Global Constraints

- Preserve `.playback`, `.spokenAudio`, `[.duckOthers]`, and `.notifyOthersOnDeactivation`.
- The monotonic workout clock remains the timing source; audio host times are scheduled from its single countdown start instant.
- Render and schedule all remaining countdown buffers before the first cue is due; never schedule the next cue from a completion callback.
- Do not change non-numeric cue behavior, workout clock behavior, visible UI, Bluetooth behavior, or HealthKit records.
- Use test-driven development and verify the RED result before production code.
- Keep generated output under `.context` and create/delete only isolated simulators owned by `Hang Ten Conductor sudden-jellyfish Review`.

---

### Task 1: Build the countdown scheduling boundary

**Files:**
- Create: `HangTen/Models/CountdownAudioScheduler.swift`
- Test: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- Produces `CountdownAudioSchedule`, a value containing the remaining numeric phrases and host-time offsets.
- Produces `CountdownAudioScheduling`, with `schedule(remainingFrom: String, startHostTime: UInt64)` and `stop()`.
- `schedule` returns `false` for a duplicate active countdown, and `true` only after every remaining cue is scheduled.

- [ ] **Step 1: Write failing scheduling tests.**

Add XCTest coverage using a recording scheduler backend. Assert that starting at `"3"` produces exactly `3`, `2`, `1` at offsets `0`, `1`, and `2` seconds; starting at `"2"` produces `2`, `1`; and a later request for `"2"` with the same active schedule adds no cue. Name the production break each test catches.

```swift
func testThreeSchedulesEveryCountdownCueAtOneSecondOffsets() {
    var schedule = CountdownAudioSchedule(remainingFrom: "3")
    XCTAssertEqual(schedule.cues.map(\.phrase), ["3", "2", "1"])
    XCTAssertEqual(schedule.cues.map(\.offset), [0, 1, 2])
}
```

- [ ] **Step 2: Run the focused tests and verify RED.**

Run `rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' -derivedDataPath .context/countdown-audio-red -only-testing:HangTenTests/WorkoutAudioCoachTests test`.

Expected: compilation fails because the scheduler/schedule types do not exist, or the duplicate/offset assertions fail.

- [ ] **Step 3: Implement the pure schedule and test seam.**

Create the schedule value and a scheduler protocol with a recording-friendly backend boundary. Represent offsets as `TimeInterval` literals `0`, `1`, and `2`; validate only the supported strings `"3"`, `"2"`, and `"1"`.

- [ ] **Step 4: Verify the focused schedule tests pass.**

Re-run the Step 2 command. Expected: the scheduling tests pass before AVFoundation playback integration.

- [ ] **Step 5: Commit Task 1.**

Run `rtk git add HangTen/Models/CountdownAudioScheduler.swift HangTenTests/WorkoutTimelineTests.swift && rtk git commit -m "feat: add countdown audio schedule"`.

### Task 2: Render and pre-schedule numeric voice buffers

**Files:**
- Modify: `HangTen/Models/CountdownAudioScheduler.swift`
- Modify: `HangTen/Models/WorkoutAudioCoach.swift`
- Test: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- `CountdownAudioScheduler` uses `AVSpeechSynthesizer.write(_:toBufferCallback:)` to obtain `AVAudioPCMBuffer` speech data before starting a countdown.
- It attaches one `AVAudioPlayerNode` to one `AVAudioEngine`, schedules every PCM buffer at `AVAudioTime(hostTime:)`, and calls `play()` only after all buffers are scheduled.
- `WorkoutAudioCoach.startCountdown(remainingFrom:startUptime:)` returns whether it took ownership of that schedule; `stop()` cancels the scheduler before audio-session teardown.

- [ ] **Step 1: Write failing coach tests.**

Inject a recording countdown scheduler into `WorkoutAudioCoach`. Assert that the first numeric cue starts one schedule containing all remaining cues, later numeric SwiftUI updates do not call `speak(_:)` or schedule again, and `stop()` calls the scheduler stop before the audio session deactivates.

```swift
func testCountdownStartsOnePreScheduledSequenceAndIgnoresLaterTicks() {
    coach.startCountdown(remainingFrom: "3", startUptime: 100)
    coach.startCountdown(remainingFrom: "2", startUptime: 101)
    XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"]])
}
```

- [ ] **Step 2: Run the focused test and verify RED.**

Run the focused `WorkoutAudioCoachTests` command from Task 1. Expected: test fails because the coach exposes no countdown scheduler boundary.

- [ ] **Step 3: Implement rendering and scheduling.**

Render the three voice cues during scheduler preparation using the same `preferredLanguageCode`, rate, pitch, and volume currently assigned in `WorkoutAudioCoach`. Convert callback buffers to retained PCM buffers, prepare the engine, then schedule all remaining cues at `AVAudioTime(hostTime: startHostTime + AVAudioTime.hostTime(forSeconds: offset))`. If preparation cannot complete before the start deadline, do not enqueue late live speech; log the failure and leave the visual countdown authoritative. Keep one active audio session through the scheduled sequence. Do not remove the existing grace-path teardown in this task: Task 3 removes it only after `WorkoutView` routes numeric countdowns to the new scheduler.

- [ ] **Step 4: Verify GREEN.**

Run focused `WorkoutAudioCoachTests`, then all `WorkoutTimelineTests`. Expected: all pass with no live `AVSpeechSynthesizer.speak(_:)` call for a scheduled numeric sequence.

- [ ] **Step 5: Commit Task 2.**

Run `rtk git add HangTen/Models/CountdownAudioScheduler.swift HangTen/Models/WorkoutAudioCoach.swift HangTenTests/WorkoutTimelineTests.swift && rtk git commit -m "feat: pre-schedule countdown speech audio"`.

### Task 3: Integrate the monotonic deadline and validate runtime behavior

**Files:**
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTen/Models/WorkoutAudioCoach.swift`
- Modify: `docs/IOS_RUNTIME_SERVICES.md`
- Test: `HangTenTests/WorkoutTimelineTests.swift`

**Interfaces:**
- `WorkoutView` passes the monotonic boundary at which `3` is current to `WorkoutAudioCoach.startCountdown`; it keeps existing `WorkoutAudioCuePolicy` keys for deduplication.
- Non-numeric audio moments retain their existing `audioCoach.speak(_:)` path.

- [ ] **Step 1: Write failing integration tests.**

Test the audio action routing so an initial, skip, and final-segment `3` starts one scheduler-owned sequence rather than three individual live-speech calls. Test that a `2` or `1` delivered after a `3` has no independent action.

- [ ] **Step 2: Run the focused integration tests and verify RED.**

Run `rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' -derivedDataPath .context/countdown-audio-integration-red -only-testing:HangTenTests/WorkoutAudioCuePolicyTests -only-testing:HangTenTests/WorkoutAudioCoachTests test`.

Expected: the schedule-routing assertions fail until `WorkoutView` supplies the monotonic start boundary.

- [ ] **Step 3: Route numeric countdown starts and delete the grace workaround.**

At the existing `audioMoment` change site, call `startCountdown` only when a numeric `3`, `2`, or `1` begins a schedule; pass the current monotonic deadline rather than the SwiftUI tick time. Keep `audioCoach.stop()` on disable, pause, and dismissal. Remove the deferred grace task and its tests because it is replaced by scheduled sequence ownership.

- [ ] **Step 4: Update runtime documentation.**

Replace the grace-interval note with a concise description that numeric countdown buffers are rendered before the start boundary and host-time scheduled as one sequence, while non-numeric speech remains synthesized normally.

- [ ] **Step 5: Run GREEN and isolated iOS validation.**

Run all `WorkoutTimelineTests`, then use the repository’s isolated simulator workflow with `HANGTEN_REVIEW_WORKOUT=1` and `HANGTEN_REVIEW_AUTOSTART=1`. Confirm logs show one scheduled `3`, `2`, `1` sequence at one-second intervals, inspect the countdown UI, and record that physical-device listening is required to quantify route latency. Delete the exact owned simulator and `.context` artifacts in the exit trap.

- [ ] **Step 6: Commit Task 3.**

Run `rtk git add HangTen/Views/RootView.swift HangTen/Models/WorkoutAudioCoach.swift HangTenTests/WorkoutTimelineTests.swift docs/IOS_RUNTIME_SERVICES.md docs/superpowers/specs/2026-08-20-sample-accurate-countdown-audio.md docs/superpowers/plans/2026-08-20-sample-accurate-countdown-audio.md && rtk git commit -m "fix: schedule countdown cues on audio clock"`.
