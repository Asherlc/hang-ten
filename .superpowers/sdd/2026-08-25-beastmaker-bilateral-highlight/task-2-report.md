# Task 2 Report: Resolve paired metadata-light edges per hand

## Changes

- Added `testMetadataLightEdgeFallbackSelectsOneEdgePerBoardHalf`, which
  exercises the resolver directly with two left-side untagged edges and one
  right-side untagged edge.
- Updated `BoardTargetResolver.sameKindOrGroup(_:target:among:)` so an edge
  fallback returns the first candidate on each half when both halves are
  present. The result remains bounded to two IDs.
- Retained depth-ranked single-representative behavior when only one half is
  represented (including positionless candidates).
- Generalized the pocket-only `onePocketPerHand` helper and its comment to
  `oneHoldPerHand`, used for both pocket and edge bilateral selection.

## TDD record

1. Added the direct resolver test before the resolver implementation.
2. Initial required command attempted before production change:

   ```sh
   rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests/testMetadataLightEdgeFallbackSelectsOneEdgePerBoardHalf
   ```

   It did not reach XCTest: `CoreSimulatorService connection became invalid`,
   followed by sandbox-denied writes to user cache and SwiftPM state paths.
3. With workspace-local derived data and approved simulator access, repeated
   red and green focused-test attempts against the available `iPhone 17`
   simulator. Each created only `Data/` and `Staging/` under its result bundle;
   `xcresulttool` reported the missing `Info.plist`, so neither run produced a
   trustworthy XCTest outcome. Tests are therefore not reported as executed.

## Validation

- `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`: passed.
- Workspace-local `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator ...`: compiled the final resolver source; the resulting
  `Debug-iphonesimulator/HangTen.app/HangTen` and `HangTen.swiftmodule` exist.
- `git diff --check`: passed.

## Concerns

- Focused XCTest execution is unverified because CoreSimulator/Xcode produced
  incomplete result bundles in this workspace. Run the requested focused and
  suite commands in a healthy simulator environment before relying on runtime
  test status.
