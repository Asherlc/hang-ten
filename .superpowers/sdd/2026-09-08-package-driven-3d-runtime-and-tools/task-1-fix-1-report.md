# Task 1 fix 1 — media-aware workout matching report

## Scope

Only `HangTenTests/WorkoutActivityRecordingTests.swift` and these Task 1 fix
records changed. `e1e53c19`'s production implementation already resolves
frames from the selected presentation and filters compatible workout holds
through `board.defaultPresentation`; no focused regression exposed a production
defect.

The added native regressions prove:

- a synthetic model hold resolves exactly to its descriptor
  `facePlaneAABB` frame;
- a logical hold absent from the selected model descriptor resolves to `nil`,
  is excluded from selected-presentation holdings, and cannot resolve an ID
  target; and
- matching, side selection, and bilateral symmetry use default-model geometry
  only. In the fixture, a non-default raster presentation owns the right
  pocket; matching still selects only the default model's left pocket and does
  not create an unsupported two-hand pair.

`testFallbackResolutionPrefersNearestFractionalDepthMeasurement` now declares
the raster frames its matching setup requires. Its former implicit primary
presentation had empty raster media; after Task 1 that is intentionally
unavailable rather than a legacy geometry fallback.

## RED and diagnosis evidence

The first actual raw focused XCTest attempt ran on owned simulator
`0B47407F-EB8C-41DC-B9FB-0DBD1E0B5656` and executed 209 tests with three
failures. Two failures were incorrect expectations in the newly added test:
single-side selection intentionally selects the sole available default hold.
The third was the existing fractional-depth fixture's empty selected raster
media. The failures were corrected in test fixtures/assertions, not masked in
production. The durable log is
`.context/shaky-rat-task1-fix-1-focused-2.log`.

The prior pre-XCTest failure remains accurately classified as an Xcode shared
SwiftPM checkout/resolver failure. Its only diagnostic is `fatalError` followed
by blank nested checkout details for the pinned Sentry and Analytics Connector
revisions (`.context/shaky-rat-task1-green-2.log`). Read-only `git cat-file`
and tag inspection found every `Package.resolved` commit in existing shared
SwiftPM caches, so the pins themselves are valid. The diagnostics do not prove
why that shared resolver failed; no deeper cause is claimed.

For the successful retry, the four verified bare repositories and checkouts
were copied into an exact workspace-local source-package directory. Xcode ran
with `-clonedSourcePackagesDirPath`, a workspace-local `-packageCachePath`,
`-disableAutomaticPackageResolution`, `-onlyUsePackageVersionsFromResolvedFile`,
and `-skipPackageUpdates`. Its resolver log records all four pinned packages
being checked out and resolved with no network fetch:
`.context/shaky-rat-task1-fix-1-resolve.log`.

## GREEN verification

`xcodebuild test` targeted only `WorkoutActivityRecordingTests`,
`BoardTargetSubstitutionTests`, and `BoardPackageStoreTests` on the exact
owned iPhone 16 / iOS 26.5 simulator
`66E64B77-4096-48DD-B039-BE6D1AEC5A68`.

- `BoardPackageStoreTests`: 108 passed, 0 failed.
- `BoardTargetSubstitutionTests`: 63 passed, 0 failed, including
  `testSloperFeatureTargetsOnCompactIIUseMatchingHoldIDs`.
- `WorkoutActivityRecordingTests`: 38 passed, 0 failed.
- Total: 209 passed, 0 failed, 0 skipped.

The result bundle and raw log are retained as durable workspace evidence:
`.context/shaky-rat-task1-fix-1-focused-3.xcresult` and
`.context/shaky-rat-task1-fix-1-focused-3.log`.

`SRCROOT=$PWD scripts/verify-board-source-boundary-manifest.sh` and
`git diff --check` both exited zero.

## Cleanup

Both exact owned simulators were recorded in pending and owned manifests before
use. Archive cleanup removed both; the final UUID was absent from `simctl`, and
both manifests are empty. Workspace-local `DerivedData`, cloned
`SourcePackages`, and package cache were removed and verified absent. Durable
`shaky-rat-task1-fix-1` logs and xcresults were intentionally retained.
