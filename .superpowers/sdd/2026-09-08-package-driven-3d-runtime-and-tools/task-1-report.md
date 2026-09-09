# Task 1 — implementation report

## Scope

Logical media-aware matching in `TrainingModels.swift`, `BoardMapView.swift`,
and `WorkoutActivityRecording.swift`, with focused XCTest coverage.

## Baseline and plan deviation

Before this task began, ancestor `05bb1c90225b1457a9b609af2c9002ec7be02e72`
already removed logical `BoardHold.presentationID`/stored frames and introduced
`BoardHold.resolvedFrame(in:)` using raster-geometry unions and model descriptor
face-plane AABBs. Its implementation is in the current branch. Therefore the
plan's prescribed model-frame RED would already have passed. This task adds a
RED regression for the remaining selection gap: a logical hold whose selected
media cannot resolve a frame must be unavailable to presentation content.

## RED evidence

The first two RED attempts used the mandated `rtk xcodebuild` wrapper, whose
filtered invocation returned before an XCTest bundle finalized and left an exact
owned simulator. The archive cleanup was run immediately for UUID
`A4B11572-2B3D-4F4B-8A19-17A0A69CEF3A`; a second attempt left UUID
`D8E251D6-8239-4C8C-96BB-FA557D1D0645`, which was likewise archived. Durable
incomplete command evidence is retained under `.context/shaky-rat-task1-*.xcresult`.

The raw-proxy attempt proved the new assertion reaches the current production
path (it builds the test target), but its result bundle was interrupted before
finalization by the command output limit. Source inspection establishes the
expected RED: `BoardMapPresentationContent` selected `containsHold`, which sees
the empty `holdGeometry["left"]` key even though `resolvedFrame(in:)` returns
nil, so the new `XCTAssertTrue(content.holds.isEmpty)` fails before this change.

## Validation status

The final captured GREEN command reached Xcode but could not resolve pinned
Swift package revisions (`fatalError` while checking out Amplitude/Sentry)
before test execution. Durable evidence: `.context/shaky-rat-task1-green-2.log`.
Every created simulator was recorded then archived; the final UUID was
`65409F84-3218-488C-A1AD-8CE799866B64`. A post-build cleanup retry is required
for `.context/DerivedData`, which Xcode left while resolving packages.
