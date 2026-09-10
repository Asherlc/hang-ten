# Task 2 fix 1 report

## Changes

- Removed the `BoardModelSurface` raster fallback closure and made the model
  surface model-only. Loading is non-interactive; failure renders the generic
  `boardModel.unavailable` state and cannot select a hold.
- Changed `BoardMapView` to switch on `BoardPresentationMedia` before creating
  either an image/path map or `BoardModelSurface`.
- Threaded `BoardModelMedia.display` to `BoardModelScene`; camera framing now
  projects the descriptor AABB on the declared orthographic direction/up basis
  and applies the declared fit padding. No Compact-II positions or scale remain.
- Rejected imported-root geometry before descriptor inventory validation.
- Added regressions for unavailable selection, root geometry, two descriptor
  camera configurations and rebind, native closest-hit/body nil, a model
  package whose asset disappears after package validation, and distinct SHA
  model keys.

## Verification evidence

- RED: the first focused native recipe used the exact created simulator
  `Hang Ten Paseo shaky-rat Review` (`A7F2B1A3-8CDC-452E-97D3-EB4ADA443CD3`).
  It reached compilation and exposed the initial `BoardMapView` view-builder
  and `orthographicScale` type errors, which were then corrected. The next
  test-target compile exposed the SceneKit hit-test option type, which was also
  corrected.
- GREEN compile: `rtk xcodebuild … build-for-testing` with absolute
  workspace-local locked `SourcePackages` and package cache completed with
  `** TEST BUILD SUCCEEDED **`. The resolver used only the four commits pinned
  in `Package.resolved`.
- Boundary: `rtk /usr/bin/env SRCROOT=<workspace> scripts/verify-board-source-boundary-manifest.sh` passed. `rtk git diff --check` passed. Static review found no fallback closure, static resource path, Compact-II coordinate/scale, or model `BoardPresentationImage` construction.
- Native test execution remains blocked by an unstable CoreSimulatorService:
  direct `simctl list` calls repeatedly returned connection-refused after the
  owned-device recipe. The recipe cleaned the exact manifests and all exact
  task-local DerivedData, SourcePackages, package-cache, and xcresult paths;
  no other workspace device was selected. A subsequent service recovery is
  required to record the focused XCTest case counts.
