# Task 5 — single-cord suspension solver extraction

## Result

`SuspensionProfileSolver.solveSingle(pose:profile:bounds:)` now owns the
single-cord profile solve in `HangTen/Models/SuspensionProfiles.swift`.
`SuspendedBoardPresentation` remains the compatibility facade, forwarding its
single-cord compatibility projection to that model solver. The shared pure
catenary primitive moved with the profile solver; two-branch presentation
assembly remains in `SuspendedBoardPresentation.swift`.

`SolvedSuspension` owns one `SolvedCordBranch` and retains the old flattened
accessors used by SceneKit (`centerlineSamples`, `tangentSamples`, and
`cordArcLength`). `SuspendedCordSolution` and `SuspendedSolvedPresentation`
remain source-compatible aliases. The renderer now consumes `SolvedSuspension`
directly, while its transient cord replacement, non-pickable category, and
accessibility state remain unchanged.

## Test-first evidence

Fixtures were added before `SuspensionProfiles.swift`:

- `SuspendedBoardPresentationTests` pins slack samples, tangents, declared and
  measured lengths, transform, framing containment, facade forwarding, taut
  classification, and invalid/nonfinite input mapping.
- `BoardModelTests` verifies re-selection atomically replaces only the transient
  cord, keeps it non-pickable/inaccessible, and preserves a highlighted wood
  hold material.
- `BoardPackageStoreTests` verifies a decoded single-cord package produces the
  exact `BoardModelSingleCordSuspension` profile consumed by the solver.

The initial focused test command was issued before implementation. It could not
reach test compilation because the build's pre-existing `Stage Board Packages`
script rejects a derived-data path below `/tmp` (`Xcode resource root must not
contain symlinks: /tmp`). Re-running with workspace-owned derived data reached
the test target; its first failure was a test-only `Dictionary.Keys` versus
`[String]` assertion mismatch, which was corrected. No red run attributable to
the missing solver symbol was captured because package/bootstrap and staging
failures occurred before Swift compiled the newly added fixture.

## Commands and outcomes

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  -derivedDataPath /private/tmp/hangboard-3d-toolkit-extraction-derived \
  -clonedSourcePackagesDirPath /private/tmp/hangboard-3d-toolkit-extraction-sourcepackages \
  -only-testing:HangTenTests/SuspendedBoardPresentationTests/...
```

Red infrastructure result: SwiftPM dependencies initially required download;
once resolved, board-package staging rejected `/tmp` because it is symlinked.

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=8C3E2871-65AD-406D-AE11-ED90CAC2FC4F' \
  -derivedDataPath .context/hangboard-3d-toolkit-extraction-derived \
  -clonedSourcePackagesDirPath /private/tmp/hangboard-3d-toolkit-extraction-sourcepackages \
  -only-testing:HangTenTests/SuspendedBoardPresentationTests \
  -only-testing:HangTenTests/BoardModelTests \
  -only-testing:HangTenTests/BoardPackageStoreTests
```

Focused green attempt: after the test-only assertion correction, the runner
emitted `DVTDeviceOperation: Encountered a build number ""`, stopped after
package-graph resolution, and did not write a usable new `.xcresult`; therefore
neither compilation nor XCTest execution can be claimed as completed.

```sh
rtk xcodebuild build -quiet -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=8C3E2871-65AD-406D-AE11-ED90CAC2FC4F' \
  -derivedDataPath .context/hangboard-3d-toolkit-extraction-derived \
  -clonedSourcePackagesDirPath /private/tmp/hangboard-3d-toolkit-extraction-sourcepackages \
  CODE_SIGNING_ALLOWED=NO
```

Compile attempt: Xcode stopped after package-graph resolution with the same
`DVTDeviceOperation` warning and emitted no compiler diagnostics or success
marker. `rtk swiftc -parse` passed for every changed Swift source/test file;
`git diff --check` is clean and `codegraph sync` completed.

## Visual validation

The prescribed `validate-hang-ten-ios` workflow was read. It cannot safely
create its owned review simulator in this environment: `xcrun simctl list
devicetypes available` returned an empty device-type list, so no validated
device type can be selected for an owned simulator. Existing shared simulators
were not used. No visual simulator review was performed.

## Files changed

- `HangTen/Models/SuspensionProfiles.swift` (new pure profile solver/results)
- `HangTen/Views/SuspendedBoardPresentation.swift` (compatibility facade)
- `HangTen/Views/BoardModelView.swift` (consumes `SolvedSuspension`)
- `HangTen.xcodeproj/project.pbxproj` (new source registration)
- `HangTenTests/SuspendedBoardPresentationTests.swift`
- `HangTenTests/BoardModelTests.swift`
- `HangTenTests/BoardPackageStoreTests.swift`

## Concerns / follow-up

Repeat focused and full XCTest execution plus the isolated visual review once
CoreSimulator exposes a valid device type and produces result bundles. No push
was performed, per the task instruction.

## Review-fix round 1

- Corrected the zero-horizontal-slack fixture: its endpoint distance is now
  compatible with the 2.1 rest length, so it reaches the intended
  `zeroHorizontalSlack` branch rather than failing early as `cordTooShort`.
- Added a literal, independent pre-extraction numerical baseline captured from
  `f29f1255`: five interior samples and tangents, measured polyline length,
  framing axes/target/extents/distance, and the 42 included framing points.
  The baseline calls `SuspensionProfileSolver` directly and does not compare it
  with the facade or reuse solver helpers to construct expected values.
- Added a dedicated declared-attachment-node-missing fixture. It verifies the
  existing unavailable state has no rescue cord.
- Made transient cord replacement an explicit `SCNTransaction`: removal and
  addition execute with implicit actions disabled, then the established board
  and camera transition animation resumes in that same transaction. The
  existing replacement test now provides the observable evidence: the prior
  cord is detached, exactly one distinct root-owned replacement remains,
  segments retain the cord (non-pickable) category, accessibility remains off,
  and highlighted wood material identity is preserved.

Round-1 focused XCTest command:

```sh
rtk proxy xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=8C3E2871-65AD-406D-AE11-ED90CAC2FC4F' \
  -derivedDataPath .context/hangboard-3d-toolkit-extraction-derived \
  -clonedSourcePackagesDirPath /private/tmp/hangboard-3d-toolkit-extraction-sourcepackages \
  -only-testing:HangTenTests/SuspendedBoardPresentationTests/testSingleProfileSolverMatchesPreExtractionNumericalBaseline \
  -only-testing:HangTenTests/SuspendedBoardPresentationTests/testSingleProfileSolverCharacterizesTautSlackAndInvalidInputs \
  -only-testing:HangTenTests/BoardModelTests/testSuspendedSelectionReportsUnavailableWhenTheDeclaredAttachmentNodeIsMissing \
  -only-testing:HangTenTests/BoardModelTests/testReselectingSuspendedPositionAtomicallyReplacesTransientCordWithoutChangingHoldHighlights
```

The Xcode process again stopped after resolving packages with
`DVTDeviceOperation: Encountered a build number ""`; it produced neither build
nor test execution output. `rtk swiftc -parse` passed for the changed Swift
files, `git diff --check` passed, and CodeGraph remained synchronized.
