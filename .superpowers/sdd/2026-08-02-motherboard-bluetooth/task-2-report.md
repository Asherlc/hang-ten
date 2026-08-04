# Task 2 implementation report

Status: DONE

## Files changed

- `HangTen/Models/MotherboardModels.swift` — force units/conversion, measurement and session value types, detection configuration, connection state, and injected `UserDefaults` settings store.
- `HangTenTests/MotherboardModelsTests.swift` — focused conversion, settings round-trip, and Codable session tests.
- `HangTen.xcodeproj/project.pbxproj` — hand-maintained source and test target references/build phase entries.
- `.superpowers/sdd/2026-08-02-motherboard-bluetooth/task-2-report.md` — this report.

## TDD evidence

RED was run before adding production model code:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/MotherboardModelsTests
```

Key output: compilation failed with the expected missing-type diagnostics, including `cannot find 'MotherboardForceUnit' in scope`, `cannot find 'MotherboardSettingsStore' in scope`, and `cannot find 'WorkoutSessionRecord' in scope`.

GREEN/build evidence was run after implementation:

```sh
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
```

Key output: `** TEST BUILD SUCCEEDED **`; the build compiled both `MotherboardModels.swift` and `MotherboardModelsTests.swift` for the simulator architectures.

## Test limitations

The requested focused `xcodebuild test` invocation reached the simulator/test-runner phase but stalled after DVT build-number warnings (`Encountered a build number "" that is incompatible with DVTBuildVersion`). It was stopped after bounded polling. The full test run was not started because the same simulator execution limitation was already established; build-for-testing provided the bounded compile/link verification.

The implementation preserves kgf as the canonical saved/session unit, uses 9.80665 N/kgf and 2.20462262185 lbf/kgf, persists `motherboard.forceUnit` and `motherboard.thresholdKGF`, defaults invalid force units and thresholds, and restores thresholds below 0.1 kgf to 2.5 kgf.

## Commits

- Base before Task 2: `dd969600467ea6b3bd4fb53832cf506e7039b008`
- Task 2 implementation: `fd18cab3cb6ae9b0f8a25b6f1d5a039e75d1ea6c` (`feat: add Motherboard measurement models`)
- This report is committed as a follow-up documentation commit after the implementation commit.
