# Final custom-routines fix round 2 report

Date: 2026-08-05
Starting HEAD: `6da571c`

## Scope

This change addresses only the remaining generic compound work/rest
compatibility defect described in
`.context/custom-routines-final-fix-round-2-brief.md`.

## Regression

Added `CustomRoutineStoreTests.testSavePersistsGenericCompoundWorkAndTargetlessRestRows`.
The test uses an isolated `UserDefaults` suite and the real `CustomRoutineStore`
save/reload path. It defines a generic compound fixed work/rest step, saves it,
and verifies that persistence contains two literal single-segment rows: a
targeted work row followed by a targetless rest row. It also verifies the
stored collection round-trips through a new store instance.

The test was added before the production edit. A generic simulator destination
can compile test bundles but cannot execute XCTest, and this task explicitly
prohibits creating or borrowing a simulator. Consequently, no runtime red
assertion could be observed; the pre-fix focused `build-for-testing` compiled
the regression only. The failing pre-fix behavior is the `save` call throwing
`CustomRoutineStoreError.validationFailed([.noCompatibleBoard])` after
flattening the rest row.

## Root cause and fix

`CustomRoutineStore.save` correctly validates the compound source definition,
resolves it through the shared `PlanDefinitionResolver`, and persists the
flattened definition produced by `WorkoutStepNormalizer`. The generated rest
step has the required literal form: phase `.rest` and no targets.

`CustomRoutineValidator.compatibleBoards` subsequently required
`targetsResolve(step.targets, on:)` for every flattened step. That helper
returns false for an empty target array, so every board was eliminated by a
valid rest row and generic validation added `.noCompatibleBoard`.

Compatibility now treats a step whose phase is `.rest` as target-compatible.
Every non-rest step still must resolve its own targets, and every work segment
still must resolve its targets. Existing `issues` validation remains unchanged:
non-rest targetless rows still produce `.missingTargets`, rest rows carrying
targets still produce `.restStepHasTargets`, target-mode enforcement is intact,
and work/rest segment validation is unchanged.

## Preserved contracts

- Custom persistence remains flat literal rows; no second representation was
  introduced.
- Rest rows remain targetless and retain their literal rest phase/timing.
- `CustomRoutineStore` still passes conversion through the shared
  `PlanDefinitionResolver` and `WorkoutStepNormalizer` boundary.
- Board-specific and generic immutable target-mode validation is unchanged.
- `AppStore`, `TrainingPlan`, `WorkoutStep`, and resolver interfaces are
  unchanged.
- The only custom compatibility call sites are the generic validation issue
  path and `plan(for:)`; both use the corrected shared `compatibleBoards`
  function.

## Verification

Focused generic test-bundle build:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData-custom-routines-final-fix-round-2 \
  build-for-testing -only-testing:HangTenTests/CustomRoutineStoreTests
```

Result: exit 0. The build compiled `CustomRoutineStore.swift` and
`HangTenTests`, with the pre-existing generic-destination DVT build-number
diagnostic and AppIntents metadata warning.

Full generic test-bundle build:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData-custom-routines-final-fix-round-2 \
  build-for-testing
```

Result: exit 0, `** TEST BUILD SUCCEEDED **`.

`rtk git diff --check` completed without output. All build artifacts remain
under `.context/DerivedData-custom-routines-final-fix-round-2`; no simulator
or external resource was created.

## Limitation

The regression could not be runtime-executed because no owned simulator UDID
is available and the task prohibited simulator creation or borrowing. Generic
`build-for-testing` provides compile/link verification only.
