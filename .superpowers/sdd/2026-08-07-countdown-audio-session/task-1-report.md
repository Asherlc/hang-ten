# Task 1 implementation report

## Status

`DONE_WITH_CONCERNS`

The implementation is complete and committed. The app and the complete unit-test bundle compile and link successfully, but Xcode's simulator install/launch workers stalled before XCTest could execute either the focused tests or the full suite.

## Commit

- `cc076d732c1a417fde3ab85c71e1f500125e32de` — `fix: restore background audio after countdown cues`

## Files changed

The implementation commit contains only the four files allowed by the task brief:

- `HangTen/Models/WorkoutAudioCoach.swift`
- `HangTenTests/WorkoutTimelineTests.swift`
- `docs/IOS_RUNTIME_SERVICES.md`
- `docs/superpowers/plans/2026-08-07-countdown-audio-session.md`

This report is a separate SDD handoff artifact and is not part of the implementation commit.

## Implementation summary

- Added injectable `WorkoutSpeechSynthesizing` and `WorkoutAudioSessionManaging` boundaries with production adapters backed by `AVSpeechSynthesizer` and `AVAudioSession.sharedInstance()`.
- Preserved the production category as `.playback`, mode as `.spokenAudio`, options as `[.duckOthers]`, and deactivation as `.notifyOthersOnDeactivation`.
- Made `stop()`, `didCancel`, and `didFinish` defer teardown while the synthesizer still reports active speech. An old cue's cancellation therefore cannot deactivate the session while its replacement is speaking.
- Made deactivation clear `configuredAudioSession` only after `deactivateAndNotifyOthers()` succeeds. A thrown deactivation leaves the flag true for a later delegate-callback retry.
- Logged audio-session activation and deactivation errors through the existing `WorkoutAudio` logger.
- Added deterministic tests for active-speech cancellation and replacement-cue ordering, including single activation and notification-aware final deactivation assertions.
- Documented the deferred cancellation behavior in the iOS runtime-services note.

## Corrected RED evidence

The valid RED checkpoint is `.context/audio-session-red-corrected.log`. It was produced against the old production implementation with the new tests present:

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
  -derivedDataPath .context/audio-session-red-corrected \
  -only-testing:HangTenTests/WorkoutAudioCoachTests test \
  2>&1 | tee .context/audio-session-red-corrected.log
```

Exact outcome: build failure with `Cannot find type 'WorkoutSpeechSynthesizing' in scope` and `Cannot find type 'WorkoutAudioSessionManaging' in scope`, followed by `** TEST FAILED **`. This is the intended RED because the old implementation lacked the required injection boundaries.

`.context/audio-session-red.log` is not cited as RED because it incorrectly reports `TEST SUCCEEDED`.

## Focused GREEN verification

### Post-review XCTest evidence

The focused XCTest selection ran successfully after the review finding. The
first two `test-without-building` attempts (explicit iOS 26.5 and iOS 26.4
destinations) were bounded at 55 seconds and again stalled before XCTest
materialized. A final bounded `test` attempt rebuilt the bundle and executed
the selection on the explicitly booted iOS 26.3 destination:

```bash
perl -e 'alarm 90; exec @ARGV' xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=51BF665F-2E2B-45AE-B3F0-43B81676E576' \
  -derivedDataPath .context/audio-session-xctest-26-3 \
  -only-testing:HangTenTests/WorkoutAudioCoachTests test \
  2>&1 | tee .context/audio-session-xctest-26-3.log
```

Exact result: exit 0 and `** TEST SUCCEEDED **`. XCTest executed both focused
cases on Xcode's transient clone of that explicit destination:

- `WorkoutAudioCoachTests.testReplacementCueKeepsAudioSessionActiveUntilReplacementFinishes` — passed (0.042 seconds)
- `WorkoutAudioCoachTests.testStopWaitsForSpeechCancellationBeforeDeactivatingAudioSession` — passed (0.003 seconds)

The complete command output is `.context/audio-session-xctest-26-3.log`; the
fresh XCTest result bundle is
`.context/audio-session-xctest-26-3/Logs/Test/Test-HangTen-2026.08.07_11-58-14--0700.xcresult`.

Attempt 1 used the explicitly available shutdown iOS 26.4 simulator requested in the handoff:

```bash
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=0F2FE770-996B-40A8-A546-3CD611D97EEF' \
  -derivedDataPath .context/audio-session-focused-green \
  -only-testing:HangTenTests/WorkoutAudioCoachTests test \
  > .context/audio-session-focused-green.log 2>&1
```

Exact outcome: the app and `HangTenTests.xctest` compiled, linked, signed, and reached `Testing started`, but no `Test Case` began. Xcode remained blocked in `_IDEInstalliPhoneSimulatorWorker` / `IDELaunchiPhoneSimulatorLauncher` with `waiting for workers to materialize`. The bounded run was interrupted after about 90 seconds and exited 130 with `** TEST INTERRUPTED **`.

Attempt 2 changed only the runtime, using the explicit shutdown iOS 26.5 simulator from the task's intended environment:

```bash
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=E6C8F0DB-CA68-44CC-A3E0-24DF9A64020A' \
  -derivedDataPath .context/audio-session-focused-green-26-5 \
  -only-testing:HangTenTests/WorkoutAudioCoachTests test \
  > .context/audio-session-focused-green-26-5.log 2>&1
```

Exact outcome: identical pre-XCTest stall after successful compile/link. The log reaches `Testing started`, then reports `waiting for workers to materialize` in the simulator install/launch workers without starting a test case. The bounded run was interrupted after about 90 seconds and exited 130.

Both source simulators were confirmed back in `Shutdown` state afterward. Xcode's transient test clones were absent from the available-device list, no persistent external resource was created, and no shared simulator was deleted.

## Full-suite verification

The full suite was not started because two bounded focused attempts proved that the simulator test service could not launch even the two-test selection. The full command that would otherwise have been run was:

```bash
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=E6C8F0DB-CA68-44CC-A3E0-24DF9A64020A' \
  -derivedDataPath .context/audio-session-green test \
  > .context/audio-session-green.log 2>&1
```

No current focused or full-suite pass/fail count exists because XCTest never began execution.

A pre-change baseline run in `.context/baseline.log` did execute the full target and records one unrelated pre-existing failure: `WorkoutActivityRecordingTests.testRecorderFailureSurfacesErrorWithoutCallingHealthKit()`, followed by `** TEST FAILED **`. Task 1 does not touch that test or its production area.

## Strongest available compile/build verification

After the bounded simulator failures, the full app and test target were built for testing without launching a simulator:

```bash
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/audio-session-build-for-testing \
  build-for-testing \
  > .context/audio-session-build-for-testing.log 2>&1
```

Exact outcome: exit 0 and `** TEST BUILD SUCCEEDED **`. The command compiled and linked the complete `HangTenTests` bundle for arm64 and x86_64. The only warnings were the existing AppIntents metadata notices that extraction was skipped because there is no AppIntents framework dependency; there were no compile or link errors.

`rtk git diff --cached --check` also exited 0 immediately before the implementation commit.

## Self-review

- The injected interfaces expose exactly the required speech/session operations and retain production defaults.
- `stop()` requests immediate cancellation, updates observable state, and tears down only when `synthesizer.isSpeaking` is false.
- Both delegate completion paths use the same guarded teardown helper, so replacement speech protects the active session from an old cancellation callback.
- Session configuration remains active across a cue sequence, matching the tests' one-activation assertion.
- Deactivation uses the notification path before clearing the configured flag; failures are logged and remain retryable.
- Existing speech language, voice, rate, pitch, volume, cue wording, countdown timing, and UI behavior are unchanged.
- The staged patch contained only the plan, coach, tests, and runtime documentation and passed whitespace/error checks.

## Concerns

- Focused GREEN and full-suite runtime execution remain unverified because the local Xcode simulator test service stalls before XCTest materializes a worker on both iOS 26.4 and 26.5.
- The unrelated baseline failure in `WorkoutActivityRecordingTests.testRecorderFailureSurfacesErrorWithoutCallingHealthKit()` remains outside this task.
- The plan's physical/runtime audio-ducking validation is explicitly post-review integration work and was not performed in Task 1.

## Review fix round 1

### Changes

- Updated the plan introduction to require a fresh subagent for every implementation or configuration task while retaining the checkbox workflow.
- Documented the exact known full-suite baseline signature:

  ```text
  Failing tests:
  \tWorkoutActivityRecordingTests.testRecorderFailureSurfacesErrorWithoutCallingHealthKit()

  ** TEST FAILED **
  ```

  The plan now permits only that exact baseline result and only when no new test failures appear; focused `WorkoutAudioCoachTests` and generic `build-for-testing` remain mandatory gates.
- Added a deterministic recording audio-session fake that fails a configurable number of deactivation attempts, plus a retry regression test. `WorkoutAudioCoach` now queues at most one next-turn retry after a final, stopped-speech deactivation failure. It retains `configuredAudioSession` until notification-aware deactivation succeeds and re-checks `synthesizer.isSpeaking` before retrying.

### TDD and verification evidence

- The retry regression test was added before the production retry implementation. The valid original Task 1 RED evidence remains preserved in `.context/audio-session-red-corrected.log`.
- The pre-fix owned retry run in `.context/retry-xctest.log` did reach XCTest: `WorkoutAudioCoachTests.testDeactivationRetriesAfterTransientFailureOnceSpeechHasFinished` failed, while the other two focused `WorkoutAudioCoachTests` passed. That failure predates the expectation-based test fix and is not a post-fix result.
- Post-fix focused attempts on the explicit existing simulator UUID `51BF665F-2E2B-45AE-B3F0-43B81676E576` reached Xcode's `Testing started` stage but stalled before any XCTest case materialized, so they produced neither the expected retry RED assertion nor a GREEN result. The relevant post-fix logs are `.context/audio-session-retry-red.log`, `.context/audio-session-retry-red-without-building.log`, and `.context/audio-session-retry-green.log`.
- A final bounded 50-second generic `build-for-testing` attempt wrote `.context/audio-session-retry-build-for-testing.log`. It compiled the app and test target work for both simulator architectures but did not reach a terminal Xcode result before the bound. No post-fix compiler diagnostic was emitted after the corrected retry-budget initializer.
- The exact workspace test process trees were terminated after the bounded attempts. No workspace `xcodebuild` or `simctl` process remains; the reused simulator was confirmed Shutdown. No simulator or external resource was created.

## Review fix round 2

### Change

- Replaced the retry test's two scheduler-dependent `Task.yield()` calls with an XCTest expectation. The recording audio-session fake now invokes the expectation only after its notification-aware deactivation has actually succeeded. The test still asserts exactly two deactivation attempts, exactly one successful deactivation, and notification-aware teardown.

### Commands and exact outcomes

The interrupted pre-fix attempt used a workspace-owned simulator named
`Hang Ten sao-tome Retry Round 2 20260807`
(`AE42B8A5-E705-482D-8E2A-CDA4D6D9770F`). Its first boot never completed
data migration, so XCTest did not start. The stale process tree discovered
after interruption was terminated explicitly. A second owned but unbooted
simulator (`289753CF-E4F0-4DC0-81D7-9FAE7CE0D32F`) was also deleted.

```bash
rtk proxy xcrun simctl shutdown AE42B8A5-E705-482D-8E2A-CDA4D6D9770F
rtk proxy xcrun simctl delete AE42B8A5-E705-482D-8E2A-CDA4D6D9770F
rtk proxy xcrun simctl shutdown 289753CF-E4F0-4DC0-81D7-9FAE7CE0D32F
rtk proxy xcrun simctl delete 289753CF-E4F0-4DC0-81D7-9FAE7CE0D32F
```

Exact deletion verification output:

```text
SIMULATOR_DELETE_VERIFICATION=PASSED AE42B8A5-E705-482D-8E2A-CDA4D6D9770F
SIMULATOR_DELETE_VERIFICATION=PASSED 289753CF-E4F0-4DC0-81D7-9FAE7CE0D32F
```

Two bounded generic `build-for-testing` attempts wrote
`.context/retry-round-2-build-for-testing.log` and
`.context/retry-round-2-build-for-testing-clean.log`. Both produced normal
compile output through `CompileAssetCatalogVariant thinned`, then stopped
without `** TEST BUILD SUCCEEDED **`, `** TEST BUILD FAILED **`, or a compiler
diagnostic. No `xcodebuild` or `simctl` process remained afterward. Therefore
these attempts do not constitute focused XCTest or successful build evidence.

## Final-review fix wave

### Evidence correction and focused attempt

- The Review fix round 1 evidence above now distinguishes the pre-fix XCTest
  failure in `.context/retry-xctest.log` from the later post-fix stalls while
  preserving the original log paths.
- The one permitted post-fix focused attempt at
  `d9cd23415cebaa56390c60634996a7fe89b15c94` used the workspace-owned iOS
  26.3 simulator `Hang Ten Conductor sao-tome Final Review`
  (`B248D09D-1722-464D-8111-4436C766798B`). It was registered in both
  `.context/conductor-pending-simulators` and
  `.context/conductor-owned-simulators` before boot, passed the explicit
  `launchctl print system` readiness probe, and ran exactly this bounded
  focused command:

  ```bash
  xcodebuild -project HangTen.xcodeproj -scheme HangTen \
    -destination 'platform=iOS Simulator,id=B248D09D-1722-464D-8111-4436C766798B' \
    -derivedDataPath .context/final-review-xctest-26-3 \
    -only-testing:HangTenTests/WorkoutAudioCoachTests test \
    > .context/final-review-xctest-26-3.log 2>&1
  ```

  The attempt had a 180-second watchdog but was stopped through its exact
  `xcodebuild` PID after the simulator service/build pipeline failed to reach
  any XCTest case or terminal test summary. The saved output is
  `.context/final-review-xctest-26-3.log`, and its partial result bundle is
  `.context/final-review-xctest-26-3/Logs/Test/Test-HangTen-2026.08.07_13-33-08--0700.xcresult`.
  There is no post-fix pass or fail result; the focused gate is unverified.

### Cleanup verification

- The exact `xcodebuild` PID was terminated; a process query found no remaining
  workspace `xcodebuild` or `simctl` process.
- The archive trap deleted `B248D09D-1722-464D-8111-4436C766798B`; an exact
  `simctl list devices` lookup returned no matching UUID or name. Both
  workspace simulator manifests are present but empty.
