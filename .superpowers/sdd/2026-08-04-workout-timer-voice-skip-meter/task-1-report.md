# Task 1 report: skipped-step preparation preview

## Files changed

- `HangTen/Models/WorkoutTimeline.swift`
- `HangTen/Views/RootView.swift`
- `HangTenTests/WorkoutTimelineTests.swift`

## RED

Exact command:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutTimelineTests test 2>&1 | rtk proxy tee .context/workout-timer-voice-skip-meter-test.log
```

Observed failure:

```text
Testing failed:
    Extra argument 'isSkipCountdown' in call
    Type 'Equatable' has no member 'preview'
Testing cancelled because the build failed.
** TEST FAILED **
```

The test compiled against the requested new API before that API existed, so the intended behavior assertion could not execute until the minimal overload change was added.

## GREEN

Exact focused command:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/WorkoutTimelineTests test
```

Result: completed with exit status 0 on the installed `iPhone 16 Pro` simulator. A final fresh raw-output run recorded output at `.context/workout-timer-voice-skip-meter-test.log` and also completed with exit status 0. Xcode emitted its existing `DVTDeviceOperation` empty-build-number warnings only.

## Commit

- `27d362e66733864d639ab261b4903fee5623b5c0` — `fix: preview holds during skip preparation`

## Concerns

- None for Task 1. The direct five-second `countdownRemaining` ceiling-math test remains unchanged, as required.

## Fix round 1: RED evidence clarification

### Plan/evidence change

Amended `task-1-brief.md` immediately after Step 1's required API-first test to state that its initial RED checkpoint may be the compiler failure caused by the absent `isSkipCountdown` API, including `Extra argument 'isSkipCountdown' in call` and consequent type-inference errors. The amendment also changes Step 2's expected outcome: behavioral failures are expected only if the API-first test compiles; otherwise the missing-API compilation failure is accepted RED evidence. It explicitly preserves the existing product implementation and test, and does not require an API-only production change to manufacture a separate behavioral RED.

### Verification

Command:

```sh
rtk proxy git diff --check
```

Result:

```text
exit status 0 (no whitespace errors)
```

No product files or tests were modified in this fix round.
