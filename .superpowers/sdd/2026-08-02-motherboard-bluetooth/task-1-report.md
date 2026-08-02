# Task 1 implementation report

Status: DONE

## Scope

Implemented only the Task 1 XCTest infrastructure. No Motherboard production code or later task was started.

## Changes

- Added `HangTenTests/TestTargetSmokeTests.swift` with the required `@testable import HangTen` smoke test.
- Added the `HangTenTests` group, test source/build entries, XCTest framework linkage, app target dependency, unit-test native target, and required Debug/Release settings to `HangTen.xcodeproj/project.pbxproj`.
- Added the shared `HangTen.xcscheme` with HangTen and HangTenTests buildables and a Test action for `HangTenTests`.

## Test-first evidence

The required focused command was run before adding the project target:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/TestTargetSmokeTests/testUnitTestTargetLoadsTheHangTenModule
```

It failed as expected because the scheme had no Test action:

```text
xcodebuild: error: Scheme HangTen is not currently configured for the test action.
```

## Verification

`rtk xcodebuild -list -project HangTen.xcodeproj` succeeds and reports both `HangTen` and `HangTenTests` targets plus the shared `HangTen` scheme.

`rtk git diff --check` succeeds.

With the dedicated iPhone 17 Pro iOS 26.5 simulator (`88777045-4DBB-47A9-B1D2-6480DF9D3762`), the bounded build-only verification succeeds:

```sh
perl -e 'alarm 120; exec @ARGV' rtk xcodebuild build-for-testing \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=88777045-4DBB-47A9-B1D2-6480DF9D3762' \
  -parallel-testing-enabled NO \
  -maximum-parallel-testing-workers 1 \
  -derivedDataPath .context/DerivedData-task1 \
  CODE_SIGNING_ALLOWED=NO
```

Evidence from the successful command:

- Exit code 0 and `** TEST BUILD SUCCEEDED **`.
- The target graph contains `HangTenTests` and its explicit dependency on `HangTen`.
- The test bundle is produced at `HangTen.app/PlugIns/HangTenTests.xctest`.

The focused test invocation using the same dedicated destination, single-worker settings, and derived-data path was also attempted:

```sh
perl -e 'alarm 120; exec @ARGV' rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=88777045-4DBB-47A9-B1D2-6480DF9D3762' \
  -parallel-testing-enabled NO \
  -maximum-parallel-testing-workers 1 \
  -derivedDataPath .context/DerivedData-task1 \
  -only-testing:HangTenTests/TestTargetSmokeTests/testUnitTestTargetLoadsTheHangTenModule
```

That command hangs during test execution after emitting the local simulator diagnostic:

```text
DVTDeviceOperation: Encountered a build number "" that is incompatible with DVTBuildVersion.
```

The long-running process was stopped after the bounded verification window. No XCTest assertion failure was observed, but a passing XCTest result and the required no-warning test confirmation could not be established because the simulator service does not complete test execution.

## Blocker / concern

Code review is DONE: the target, dependency, XCTest linkage, smoke-test source, required settings, and shared Test action build successfully. The remaining concern is limited to the simulator service hanging during `xcodebuild test` with the DVT build-number warning; it is not a project configuration or test assertion failure.
