# Task 3 report — media-aware board map and unavailable UI

Owner: `shaky-rat`

## Characterization and implementation

Task 2 fix `175ecc9f` already completed the required Task 3 production
behavior. Both `BoardMapView` and `BoardDetailMapView` exhaustively switch
`BoardPresentationMedia`: the raster branch alone constructs
`BoardPresentationImage` and canonical hold-path visuals, while the model
branch alone constructs the generic `BoardModelSurface`. `BoardModelSurface`
has no raster closure; loading is non-interactive and failed loading renders
`BoardModelUnavailableView`, whose generic textual UI is identified as
`boardModel.unavailable` and cannot hit-test.

No production routing change was needed. The focused regression added in this
task uses a native SceneKit model with one descriptor-bound hold plus an
unbound logical hold. It proves `BoardModelSCNView` creates an accessibility
element only for the descriptor-bound hold, preventing a hold that cannot be
rendered or picked from becoming selectable through accessibility.

## Verification

- `rtk swiftc -parse HangTenTests/BoardModelTests.swift` exited successfully.
- `rtk /usr/bin/env SRCROOT=<workspace> scripts/verify-board-source-boundary-manifest.sh` exited successfully.
- `rtk git diff --check` and `rtk git diff --check HEAD` exited successfully.

## Pending native/UI execution gate

`xcrun simctl list devices` failed before discovery with
`CoreSimulatorService connection became invalid` / `Connection refused`. No
simulator was created, reused, or targeted.

The first task-local locked-package `build-for-testing` attempt failed before
app/test compilation because the isolated clone had no generated package
workspace state, leaving Amplitude and Sentry products unresolved. A bounded
local `-resolvePackageDependencies` retry against copied repositories and the
checked-in `Package.resolved` returned an empty package graph while the same
CoreSimulator service outage persisted. No compile success or XCTest/UI-test
count is claimed. Re-run the focused `BoardModelTests` and
`OwlClimbPokerBoardMapInteractionUITests` with the exact owned
`Hang Ten Paseo shaky-rat Review` lifecycle when CoreSimulator recovers.

## Cleanup

The task-local DerivedData, SourcePackages clone, and package cache are
ephemeral and are removed before handoff. No simulator resource was created.
