# Task 4 report

## Evidence

The baseline focused run reproduced the two failures named in the brief:

- `testDuplicateDraftCreatesOneStableFreshCustomDefinition()` failed because the duplicate definition emits one literal fixed work segment while the source fixture has the default empty `segments` array.
- `testEditorLocalValidationRejectsNonFiniteAndNonPositiveStepDurations()` failed because the draft title was empty, adding the unrelated required-name validation issue.

All other tests in `HangTenTests/CustomRoutineDraftTests` passed in the baseline run.

## Changes

- Updated the duplicate assertion to compare the source step content and IDs with an explicitly expected literal one-segment fixed definition.
- Set a valid title in the duration-validation test so it isolates the three duration issues.
- No production code, `project.pbxproj`, or unrelated tests were changed.

## Verification

The focused rerun was started with:

```text
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'id=CEF0CFC2-6B3C-4029-871A-ADB78FF0674D' -only-testing:HangTenTests/CustomRoutineDraftTests
```

It produced only Xcode's simulator warning (`DVTDeviceOperation: Encountered a build number "" that is incompatible with DVTBuildVersion`) and no test progress for over two minutes. It was interrupted with exit code 130. The focused rerun could not be completed because of this simulator/Xcode startup hang.
