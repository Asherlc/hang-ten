# Task 1 implementation report

## Result

Implemented numeric-only workout audio cue selection. Initial 3-2-1 countdown
and final three-second interval countdowns remain; segment labels, task/title
cues, rest prompts, and completion audio are no longer selected by
`WorkoutView.audioMoment`.

## Files changed

- `HangTen/Views/RootView.swift`
  - Made `WorkoutAudioMoment` an internal `Hashable` value type.
  - Added the internal `WorkoutAudioCuePolicy.moment(...)` policy with the
    exact approved numeric-only behavior.
  - Routed `WorkoutView.audioMoment` through the policy using the existing
    interval timing and removed `spokenStartPhrase(for:)`.
- `HangTenTests/WorkoutTimelineTests.swift`
  - Added the five requested `WorkoutAudioCuePolicyTests` cases.
- `README.md`
  - Updated the workout audio summary to describe only the spoken start and
    final three-second countdown cues.

## Test commands and outputs

1. Red focused test, run before production implementation:

   ```text
   rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' -only-testing:HangTenTests/WorkoutAudioCuePolicyTests test
   ```

   Exit 65 as expected. Compilation reported missing
   `WorkoutAudioCuePolicy` and `WorkoutAudioMoment` symbols in
   `WorkoutTimelineTests.swift`; no production policy existed yet.

2. Focused green command, first post-implementation attempt:

   ```text
   rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' -only-testing:HangTenTests/WorkoutAudioCuePolicyTests test
   ```

   The shared wrapper stalled after the known Xcode
   `DVTDeviceOperation: Encountered a build number ""` warnings and was
   interrupted with exit 130 after a bounded wait; it produced no test
   failure output.

3. Bounded focused retry with parallel testing disabled:

   ```text
   rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' -parallel-testing-enabled NO -only-testing:HangTenTests/WorkoutAudioCuePolicyTests test
   ```

   Exit 65 because the shared simulator could not boot within 60 seconds:
   `Failed to prepare device 'iPhone 17 Pro' ... Timed out trying to boot simulator after waiting 60.00s.`

4. Production build verification:

   ```text
   rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
   ```

   Exit 0. The Hang Ten production target compiled successfully.

5. Test-target compile verification without launching a simulator:

   ```text
   rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -parallel-testing-enabled NO build-for-testing
   ```

   Exit 0. The Hang Ten app and `HangTenTests` test bundle compiled
   successfully. Xcode emitted only the known device build-number warnings.

6. Required full XCTest command:

   ```text
   rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,OS=26.5,name=iPhone 17 Pro' test
   ```

   Not completed because the same shared simulator/build environment was
   concurrently booting and building devices. The repository's preflight
   note already records a similar five-minute interruption with no reported
   failures. This remains a verification concern, not an observed test
   assertion failure.

7. Diff hygiene:

   ```text
   rtk git diff --check
   ```

   Exit 0 with no whitespace errors.

## Self-review

- The pure policy returns only `"1"`, `"2"`, or `"3"` phrases.
- Initial countdown keys are stable as `initial-N`.
- Interval keys remain stable as `stepID-segment-N`.
- Completion suppresses interval cues, including during the final three
  seconds.
- Short intervals return only the applicable numeric moment.
- Existing `startedAt` gating and `intervalRemaining` timing are preserved.
- The diff is limited to the three files requested by the brief plus this
  report, and no unrelated worktree changes were reverted.

## Commit

Commit created after review:

```text
COMMIT_HASH_RECORDED_AFTER_COMMIT
```

## Concerns

The focused and full simulator XCTest executions could not be conclusively
run because the shared iPhone 17 Pro simulator repeatedly stalled or timed
out while other workspace agents were using simulator/build resources. The
production build and test-target `build-for-testing` both passed.
