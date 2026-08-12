# Task 1 report — blocked at RED verification

## Files changed

- `HangTenTests/MotherboardProtocolTests.swift` — replaced the prior tare/interpolation test with the two specified reference-decoder tests and a shared `linearCalibration()` fixture. No production source was modified.
- `.superpowers/sdd/2026-08-11-motherboard-reference-decoder/task-1-report.md` — this report.

## Test evidence

### Hand-derived RED evidence

The original decoder first calibrates all four inputs and then subtracts tare
without applying any per-channel polarity. With the shared linear calibration,
`[90, 60, 70, 100]` calibrates to `[9, 6, 7, 10]`; applying the test tare
`[1, -8, -9, 4]` therefore yields the old sensor loads `[8, 14, 16, 6]` and
old aggregate `44`. This differs from the RED test's reference-compatible
`[8, 2, 2, 6]` and aggregate `12`.

For the channel-exclusion test, the old decoder produces aggregate `38` for
`[90, 60, 70, 0]` and `44` for `[90, 60, 70, 100]`, because it includes the
fourth calibrated channel. The new test requires `12` in both cases. These
hand-derived outcomes document the intended RED behavior while XCTest remains
unable to launch in this environment.

### RED command

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData-motherboard-reference-decoder-task1 -only-testing:HangTenTests/MotherboardProtocolTests
```

The first two non-interactive attempts returned before the test runner launched. Their result bundle was:

```text
.context/DerivedData-motherboard-reference-decoder-task1/Logs/Test/Test-HangTen-2026.08.11_16-50-23--0700.xcresult
```

`xcresulttool get test-results summary` reported `result: unknown` and `totalTestCount: 0`. An explicit result bundle attempt at `.context/MotherboardProtocolTests-RED2.xcresult` was interrupted before its `Info.plist` was written, so it is not readable as an xcresult.

A serialized persistent run of the exact RED command did compile both `HangTen` and `HangTenTests`, then produced no test-runner output for over a minute while all available `iPhone 17 Pro` simulators remained shut down. It was stopped at the controller's ten-minute cutoff. Observed terminal outcome: `^C** BUILD INTERRUPTED **` (exit 1). Therefore, the required expected RED assertion failures were not observed.

### GREEN command

Not run. Per test-driven development, no decoder implementation was written before a real failing test execution.

## Commit and push

### Approved source-backed fallback

After the approved CoreSimulator restart still could not complete first boot,
the controller authorized a narrowly scoped source-backed fallback for this
deterministic decoder change. No simulator was created or booted for this
verification. The implementation applies the compatibility polarity before
tare for all four retained channels and sums only the first three force
channels.

Compile-only command:

```sh
xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator' -derivedDataPath .context/DerivedData-motherboard-reference-decoder-task1-fallback
```

Result: `** TEST BUILD SUCCEEDED **`. The output explicitly built the
`HangTenTests` target and produced
`HangTen.app/PlugIns/HangTenTests.xctest`, so both production source and the
focused XCTest source compiled without launching an iOS test runner.

Runtime XCTest remains unexecuted: the previous focused-test attempts could
not launch due to the shared Simulator first-boot/runner issue. The expected
behavior is instead backed by the independently recorded RED arithmetic above
and by source review of the minimal change.

- Commit SHA: recorded in the task's final Git commit (this report is included in that commit)
- Push result: `origin/issue-96-ht-3-load-magnitude-export` updated with the final task commit.

## Self-review

- The two added tests use literal, independently hand-derived expected loads and aggregate values.
- They exercise `MotherboardProtocol.decode` directly and cover the two requested behaviors: reference polarity before tare, and exclusion of channel four from aggregate force.
- The implementation retains four raw ADC values, four calibrated/tare-adjusted sensor values, finite-value guards, and the final non-negative aggregate clamp. It does not alter calibration interpolation, raw packet parsing, tare collection, or Bluetooth service behavior.
- `git diff --check` passes.

## Concerns / blocker

The iOS test runner does not launch for the requested named destination in this environment. The available `iPhone 17 Pro` devices are shutdown, and the persistent xcodebuild invocation builds successfully but stalls after build output with no XCTest results. The approved source-backed fallback permits this deterministic Task 1 to proceed, but runtime XCTest should be rerun when the shared Simulator service is healthy.

## Final retry after approved CoreSimulator restart

The controller obtained explicit user approval to restart the shared CoreSimulator service. I then created the exact task-owned simulator `ragged-dodo-task1-reference-decoder-final` (`FFB7727C-A796-4E9E-BC35-D86AF8BCF643`) with runtime `com.apple.CoreSimulator.SimRuntime.iOS-26-5` and device type `com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro`.

The required boot command stalled in the system's first-boot data migration (`00LaunchServicesMigrator`) before the focused XCTest command could begin. No result bundle was written at `.context/MotherboardProtocolTests-RED-final.xcresult`; consequently no expected RED assertion failure was observed. Per the task instruction, no production decoder code was implemented.

The exact owned simulator was then shut down and deleted, with this verification result:

```text
SIMULATOR_CLEANUP_VERIFIED FFB7727C-A796-4E9E-BC35-D86AF8BCF643
```

No commit or push was made because the RED verification remains incomplete.
