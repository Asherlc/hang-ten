# Task 1 runtime review

Target: `e1e53c19ab3f12c517fb32793d4c49304c353392`

## Finding 1 — P1: focused XCTest evidence is absent

The Task 1 acceptance command never reached compilation or XCTest because Swift Package Manager could not check out the pinned Sentry and analytics-connector revisions. See `.context/shaky-rat-task1-green-2.log:3-6`. This leaves the required matching, raster, and Compact II substitution regressions unexecuted.

The failure is not evidence that either revision is invalid: `Package.resolved` pins the same revisions, and read-only inspection verified both commit objects and tag references in the existing shared Xcode package caches. Xcode supplied only `fatalError` and blank checkout details, so the resolver root cause remains undetermined. This review is static code review only; it does not approve runtime behavior.

## Finding 2 — P2: the committed regression coverage does not prove Task 1's model/default-only contract

The only test added in this commit, `testPresentationContentExcludesLogicalHoldWithoutResolvableMediaFrame` at `HangTenTests/BoardPackageStoreTests.swift:79-109`, exercises an empty raster geometry list and only `BoardMapPresentationContent`.

The plan requires focused proof that:

- a model hold returns the descriptor `facePlaneAABB` frame;
- a missing selected-media mapping is nil/unavailable;
- matching and frame-based side/symmetry decisions use only `board.defaultPresentation`, never another presentation; and
- `BoardTargetSubstitutionTests.testSloperFeatureTargetsOnCompactIIUseMatchingHoldIDs` remains green.

`HangTenTests/WorkoutActivityRecordingTests.swift` was named by Task 1 but has no commit change, and neither it nor `BoardTargetSubstitutionTests.swift:248-257` supplies a synthetic two-presentation model/default-only regression. The current static implementation appears to meet those rules (`TrainingModels.swift:724-739`, `884-889`; `WorkoutActivityRecording.swift:418-425`, `765-767`), but this gap would not detect a future return of the predecessor's cross-presentation fallback.

## Static audit notes

- `BoardHold` has no logical presentation, frame, or descriptor-bound field (`TrainingModels.swift:620-632`).
- Raster AABB uses the union of selected media pieces; model AABB comes from that presentation's descriptor (`TrainingModels.swift:724-739`).
- `BoardMapPresentationContent` consumes `TrainingBoard.holds(in:)` (`BoardMapView.swift:86-103`); the detail map re-resolves in that same content presentation (`BoardMapView.swift:17-31`).
- Candidate selection is deliberately limited to the default presentation and the former fallback across `board.presentations` was removed (`WorkoutActivityRecording.swift:418-425`, `765-767`).
- `holdIDs(inPosition:)` remains raw-membership metadata (`TrainingModels.swift:891-902`) but has no production caller; it is covered only by its package-store test.

## Verdict

Do not mark Task 1 runtime behavior approved until the dependency checkout issue is diagnosed or an isolated private dependency cache permits the specified focused XCTest command to execute, and the missing model/default-only regressions are added and run.
