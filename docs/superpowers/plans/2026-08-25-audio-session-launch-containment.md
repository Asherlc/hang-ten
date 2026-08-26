# Audio Session Launch Containment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for every implementation or configuration task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep other-app audio untouched during Hang Ten launch by deferring countdown audio-engine prewarm until an athlete starts an audio-enabled countdown.

**Architecture:** `WorkoutAudioCoach` will represent a cold countdown backend as `.idle`, expose an explicit preparation entry point, and return to idle after playback stops. `WorkoutView` will request that preparation at the start/skip interaction, preserving its existing pending-countdown path until preparation succeeds or fails.

**Tech Stack:** Swift 6, SwiftUI, AVFoundation, XCTest.

**Spec:** `docs/superpowers/specs/2026-08-25-audio-session-launch-containment-design.md`

## Global Constraints

- Do not activate or prewarm `AVAudioEngine` while the app is merely launching.
- Keep all numeric countdown audio scheduled through `CountdownAudioScheduler`; do not introduce live-speech fallback.
- Preserve the existing `AVAudioSession` `.duckOthers` behavior only while a spoken cue or scheduled countdown actually owns the session.
- Add behavior-level XCTest coverage and watch it fail before production changes.
- Keep the implementation scoped to launch/prewarm lifecycle behavior; do not alter routine content, timing, or audio assets.

---

### Task 1: Defer Countdown Audio Preparation Until User Request

**Files:**
- Modify: `HangTen/Models/WorkoutAudioCoach.swift:55-340`
- Modify: `HangTen/Views/RootView.swift:1386-1391,2432-2489`
- Test: `HangTenTests/WorkoutTimelineTests.swift:1350-1760,1866-1904`

**Interfaces:**
- Produces: `CountdownAudioPreparationState.idle` and `WorkoutAudioCoach.prepareCountdownAudio()`.
- Consumes: `WorkoutView.requestCountdownStart(_:)`, which must call the new method before testing whether preparation is pending.
- Preserves: `WorkoutAudioCoach.startCountdown(_:startUptime:) -> Bool` accepts only `.ready` preparation and `WorkoutSessionPolicy.shouldDeferCountdownStart(isFirstStart:preparationState:)` defers only `.preparing`.

- [ ] **Step 1: Write the failing regression tests**

Add a `WorkoutAudioCoachTests` case that constructs a coach with a manually-completing `RecordingCountdownAudioScheduler`, asserts `.idle` and zero `prewarmCallCount`, requests preparation, then asserts `.preparing`, one prewarm call, and `.ready` after completion. Add a lifecycle case that starts a ready countdown, completes it through `RecordingWorkoutCountdownCompletionScheduler`, and asserts the coach returns to `.idle` without an additional prewarm. Add an `.idle` assertion to the `WorkoutSessionPolicy.shouldDeferCountdownStart` table.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutAudioCoachTests -only-testing:HangTenTests/WorkoutSessionPolicyTests test`

Expected: the new launch-containment test fails because the current initializer calls `beginCountdownPrewarm()` and the preparation state is `.preparing`, not `.idle`.

- [ ] **Step 3: Implement the minimal lifecycle change**

In `WorkoutAudioCoach`, add `.idle`; initialize the published preparation state to it; remove automatic `beginCountdownPrewarm()` calls from initialization, `stop()`, cancellation, and completion; and add `prepareCountdownAudio()` that begins prewarm only from idle or failed states. After a countdown is stopped, cancelled, or completed, set the preparation state to `.idle` after stopping the scheduler. In `WorkoutView.requestCountdownStart(_:)`, when audio cues are enabled and the coach is idle, call `prepareCountdownAudio()` before the existing deferral check. Leave failed preparation on the visual-countdown path.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutAudioCoachTests -only-testing:HangTenTests/WorkoutSessionPolicyTests test`

Expected: all focused tests pass, including the new test that launch does not prewarm and the lifecycle test that completion returns to idle.

- [ ] **Step 5: Run the full test target and build**

Run: `xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' test`

Run: `xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' build`

Expected: both commands exit 0 with no test failures or build errors.

- [ ] **Step 6: Commit**

```bash
git add HangTen/Models/WorkoutAudioCoach.swift HangTen/Views/RootView.swift HangTenTests/WorkoutTimelineTests.swift docs/superpowers/specs/2026-08-25-audio-session-launch-containment-design.md docs/superpowers/plans/2026-08-25-audio-session-launch-containment.md
git commit -m "Fix launch-time audio interruption"
```
