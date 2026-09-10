# Task 3 review — media-aware board map and unavailable UI

Reviewer: `shaky-rat` runtime review lane
Reviewed commit: `6464451b` (`feat: surface unavailable package models`)
Baseline: Task 2 fix `175ecc9f`; original runtime plan and lean parallel delivery plan

## Approval status

**APPROVED with the native/UI execution gate pending.** Static review finds the
intended Task 3 contract present in the inherited Task 2-fix production code,
and the Task 3 commit adds the requested focused accessibility regression. This
review does not claim that native XCTest or UI tests executed.

## Findings

- **Typed routing is exhaustive.** `BoardDetailMapView` and `BoardMapView`
  switch on `BoardPresentationMedia`; only `.raster` constructs
  `BoardPresentationImage` and `PhysicalHoldVisual`, while only `.model`
  constructs `BoardModelSurface`. The Task 3 commit itself makes no production
  changes, so raster card rendering and tap paths remain the Task 2-fix
  behavior.
- **Model loading is model-only and fail-closed.** `BoardModelSurface` has no
  fallback/image closure. Loading renders a hidden, non-hit-testable
  `ProgressView`; missing package bytes, invalid SceneKit/descriptor binding,
  or a cancelled/failed load reaches the generic
  `BoardModelUnavailableView`, identified as `boardModel.unavailable` and
  non-hit-testable. Model loading uses the package asset URL and SceneKit; it
  does not construct a `UIImage` or call the raster image surface.
- **No model image URL route exists.** `BoardPackageStore.presentationImageURL`
  returns a URL only for raster media. The model branch uses
  `presentationAssetURL` exclusively for SceneKit loading, and the map image
  view is reachable only from the raster switch arm.
- **Accessibility coverage is specific and meaningful.**
  `testModelAccessibilityEnumeratesOnlyDescriptorBoundHolds` creates a real
  descriptor-bound `left` hold and an additional logical `not-in-descriptor`
  hold, installs both in `BoardModelSCNView.holds`, and asserts the exact
  accessibility identifier `boardModel.hold.left` and label `Bound left`.
  Production enumeration is driven by `model.holdNodes[hold.id]`, so only
  descriptor-bound mesh holds become accessibility elements; body and
  unbound logical holds are omitted. This is not a weak count-only
  characterization.
- **Scope is correct.** `git diff --name-only 6464451b^ 6464451b` contains only
  `task-3-brief.md`, `task-3-report.md`, and
  `HangTenTests/BoardModelTests.swift`; no unnecessary production file or
  unrelated test was changed. The pre-existing untracked
  `Tools/HangboardModels/beastmaker_1000.py` was left untouched.

## Verification

Passed:

- `rtk swiftc -parse HangTenTests/BoardModelTests.swift`
- `rtk /usr/bin/env SRCROOT="$PWD" scripts/verify-board-source-boundary-manifest.sh`
- `rtk git diff --check HEAD`
- `rtk git diff --check 6464451b^ 6464451b`
- Static inspection of `BoardMapView.swift`, `BoardModelView.swift`,
  `BoardPackageStore.swift`, and the focused test.

Pending:

- The single CoreSimulator preflight
  `xcrun simctl list devices` failed before discovery with
  `CoreSimulatorService connection became invalid` / `Connection refused`.
  No simulator was created, reused, booted, or targeted. Consequently the
  exact `Hang Ten Paseo shaky-rat Review` lifecycle, native
  `BoardModelTests`, and `OwlClimbPokerBoardMapInteractionUITests` remain
  pending and must be rerun when CoreSimulator recovers.
