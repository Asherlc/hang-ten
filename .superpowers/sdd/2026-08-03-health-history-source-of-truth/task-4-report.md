# Task 4 report — Add history coordination and wire AppStore/Progress UI

## Status

Implementation is complete and uncommitted. Compilation verification succeeded. Simulator test execution is blocked by the command runner terminating Xcode during app installation before XCTest returns a result bundle.

## Changed files

- `HangTen/Models/WorkoutHistoryService.swift` — new serialized coordinator that persists completions before upload, reconciles visible HealthKit records, preserves read-privacy fallback records, prevents duplicate uploads, and publishes completions on the main queue.
- `HangTenTests/WorkoutHistoryServiceTests.swift` — synchronous configurable fake health store and coordinator coverage for fallback, authoritative HealthKit, save ordering/failure, migration idempotency, legacy matching, query failures, empty history, and an in-flight refresh/completion race.
- `HangTen/Models/AppStore.swift` — replaces mutable counters with the published `WorkoutHistorySnapshot`, delegates logging to the coordinator, injects protocol-based dependencies, and records the versioned visible-connect preference.
- `HangTen/Views/RootView.swift` — refreshes history with authorization on appearance/activation, uses exact history-source copy, applies action rules, and adds required accessibility identifiers.
- `HangTenTests/AppStoreTests.swift` — asserts the completion path updates the snapshot and computed compatibility values.
- `HangTen.xcodeproj/project.pbxproj` — includes the new source and test file in their targets.

## TDD evidence

### RED

```text
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service
```

Initial output: `Cannot find type 'WorkoutHistoryService' in scope` (twice), followed by `** TEST FAILED **`.

After the AppStore-facing test was added, the same command reported `Value of type 'AppStore' has no member 'workoutHistory'`, followed by `** TEST FAILED **`.

### GREEN / build evidence

```text
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-full
```

Output ended with `** TEST BUILD SUCCEEDED **`.

`rtk git diff --check` completed with no output (clean).

### Blocked XCTest execution

Attempted commands:

```text
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-full
rtk xcodebuild test-without-building -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-full -resultBundlePath .context/Task4TestsSplit.xcresult
```

Each returned after approximately 28 seconds with only the recurring Xcode warning:

```text
DVTDeviceOperation: Encountered a build number "" that is incompatible with DVTBuildVersion.
```

The diagnostic log in `.context/Task4Tests.xcresult/Staging/.../Session-HangTenTests-2026-08-03_084629-LIxRtC.log` ends while Xcode is installing `HangTen.app`. The generated result bundle remains in `Staging` and lacks `Info.plist`, so `xcresulttool` reports it is corrupted/incomplete. No `xcodebuild`, `xctest`, or `HangTenTests` process remains afterwards. Therefore no XCTest pass/fail result or count is available.

## Self-review

- Coordinator uses the required HealthKit/persistence protocols and the existing pure matcher.
- New completion is stored before HealthKit is called; failed saves reset the upload flag; successful but read-hidden saves remain pending and are not uploaded twice.
- Reconciliation reloads local persistence after a HealthKit query so a completion queued behind an in-flight refresh cannot be overwritten by stale records.
- Source publication follows Task 4 rules: HealthKit only with a visible accepted record, local fallback only with local entries, unavailable otherwise.
- AppStore has no independent mutable session counter/title. `sessionsCompleted` and `lastSessionTitle` are computed from `workoutHistory`.
- The authorization-request key is `HangTen.healthAuthorizationRequested.v1`, set only in `requestHealthAuthorization`, which is invoked by the visible Connect action. The prior DEBUG appearance prompt was removed.
- Progress keeps its pill/settings behavior, uses exact requested source strings, preserves End-session behavior, and adds `progress.sessionsCount` and `health.connect` identifiers.

## Concerns

- Actual simulator XCTest execution must be rerun in an environment that allows the test process to survive installation; only test compilation/build is currently evidenced.
- The DEBUG-only `HANGTEN_REVIEW_REQUEST_HEALTH` appearance route was removed because it requested Health authorization without a visible user Connect action. Any visual review that relied on that route must now tap the Connect control (`health.connect`).

## Completion handoff

The user authorized handoff with compile/build evidence despite unavailable XCTest runtime execution. A fresh `build-for-testing` and `git diff --check` are run immediately before committing the Task 4 implementation. Final status is `DONE_WITH_CONCERNS`: XCTest runtime remains unavailable, while compilation/test build succeeds.

Committed Task 4 implementation: `e06a9a7 feat: make HealthKit the workout history source`.

## Fix round 1 — review findings

### P1: stale asynchronous persistence writes

`WorkoutHistoryService` now reloads `persistence.load()` before selecting an upload, inside the save completion, and inside the final HealthKit refetch completion. The save completion updates only the record matching the saved record ID; the final refetch filters the freshly loaded records only when the fresh HealthKit response actually matches them. This preserves a completion queued while a delayed save or final refetch is in flight.

Covering coordinator regression:

- `testCompletionQueuedDuringSaveIsPreservedThroughFinalRefetch`

The existing `testCompletionQueuedDuringRefreshIsNotOverwrittenByStaleLocalRecords` remains in place for the initial-fetch boundary.

### P2: history versus completion error copy

`AppStore` now passes an explicit error context to its history publisher. Completion failures show `Session was saved locally and will retry Apple Health sync.` Refresh/query failures show `Apple Health history could not sync. Local history remains available.` A successful refresh with no service error clears the banner.

Covering AppStore regressions:

- `testRefreshFailureShowsHistorySyncErrorAndSuccessfulRefreshClearsIt`
- `testCompletionFailureShowsRetrySyncError`

### Verification commands and output

Focused runtime attempt:

```text
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service -only-testing:HangTenTests/WorkoutHistoryServiceTests -only-testing:HangTenTests/AppStoreTests
```

Output again stopped after the known simulator warning:

```text
DVTDeviceOperation: Encountered a build number "" that is incompatible with DVTBuildVersion.
```

No XCTest result bundle was finalized; simulator runtime execution remains unavailable in this workspace.

Compilation/test-build verification:

```text
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-full
rtk git diff --check
```

Output ended with `** TEST BUILD SUCCEEDED **`; `git diff --check` produced no output. The DEBUG review route and scene/source behavior were not changed in this fix round.

Fix round 1 commit: `732501f fix: preserve queued workout history`.

## Fix round 2 — review findings

### Successful-empty HealthKit source

`WorkoutHistoryService.publishedSnapshot` now receives an explicit `healthQuerySucceeded` value. A successful final query with no visible Hang Ten records and no local fallback preserves `.healthKit`; local records still produce `.localFallback`, while unavailable/query-failure paths pass `false` and remain `.unavailable` when empty.

Updated regression:

- `testEmptySuccessfulHealthKitQueryWithoutLocalRecordsIsHealthKit`

The existing `testQueryFailureWithoutLocalRecordsIsUnavailable` continues to cover the opposite source rule.

### Coalesced completion error priority

`AppStore` now retains the completion-specific error while coalesced callbacks drain. An independently initiated refresh resets that priority, allowing successful refreshes to clear the banner and later failed refreshes to show the history-sync message.

New regression:

- `testCoalescedRefreshPreservesCompletionErrorUntilIndependentRefresh`

This test defers a failed completion save, queues a refresh behind it, verifies the completion retry copy wins, then verifies an independent successful refresh clears it and an independent failed refresh shows the history-sync copy.

### Verification commands and output

Focused runtime attempt:

```text
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service -only-testing:HangTenTests/WorkoutHistoryServiceTests -only-testing:HangTenTests/AppStoreTests
```

Output again stopped after:

```text
DVTDeviceOperation: Encountered a build number "" that is incompatible with DVTBuildVersion.
```

No XCTest runtime result was finalized in this workspace.

Test-build and diff verification:

```text
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service
rtk git diff --check
```

Output ended with `** TEST BUILD SUCCEEDED **`; `git diff --check` produced no output. This round did not modify RootView, DEBUG review behavior, scene handling, or source-message strings.

Fix round 2 commit: `497eda2 fix: preserve HealthKit history state`.

## Fix round 3 — review findings

### Deferred retry completion in the coalescing regression

`testCoalescedRefreshPreservesCompletionErrorUntilIndependentRefresh` now changes the fake save result to success and disables deferral before starting the independent successful refresh. That retry completes, clears the completion error, and leaves no outstanding save completion. The same test then changes the query to fail and verifies the later independent refresh shows the history-sync error copy.

### Authorization resets completion-error priority

`AppStore.requestHealthAuthorization()` now resets `preservesCompletionError` when it clears `healthAuthorizationError`. This prevents its subsequent independent refresh from suppressing a history-sync failure behind a stale completion-error priority.

New regression:

- `testAuthorizationRequestResetsCompletionErrorPriorityBeforeRefreshFailure`

This starts with a completion failure, requests authorization, then makes the authorization-triggered refresh fail and verifies the history-sync copy is published.

### Verification commands and output

Test build:

```text
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service
rtk git diff --check
```

Output ended with `** TEST BUILD SUCCEEDED **`; `git diff --check` produced no output.

Focused runtime attempt:

```text
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service -only-testing:HangTenTests/AppStoreTests
```

The runtime again ended before XCTest results after the recurring warning:

```text
DVTDeviceOperation: Encountered a build number "" that is incompatible with DVTBuildVersion.
```

No documentation or RootView/queue/source changes were made in this fix round.

Fix round 3 commit: `9e87357 fix: reset history error priority`.

## Fix round 4 — final branch-review findings

### Authorization cancellation and pre-connect gating

`AppStore` now exposes the current-state Connect decision so a callback that remains `.notDetermined` continues to show Connect Apple Health even when the versioned request flag is already persisted. Denied authorization still maps to Settings, and unavailable HealthKit still hides the action. The coordinator starts with HealthKit synchronization disabled unless the persisted request flag is true; the visible authorization action enables it before requesting permission.

Before Connect, refresh and completion paths load and publish only the local `UserDefaults` fallback. They do not call `fetchHangTenWorkouts` or `saveCompletedWorkout`. A later launch with the request flag set retains the existing synchronization path, and the app does not request permission during initialization.

### Immediate local hydration and SessionID deduplication

`WorkoutHistoryService` hydrates its snapshot from persistence during initialization without querying HealthKit, and `AppStore` publishes that snapshot immediately. HealthKit history matching now deduplicates accepted records by both HealthKit UUID and `HangTen.SessionID` after newest-first sorting, preserving the existing normalized-title/exact-date legacy matcher for records without a SessionID.

New regression coverage:

- `testInitializationHydratesPersistedLocalHistoryWithoutHealthKitRead`
- `testRefreshBeforeConnectUsesLocalFallbackWithoutReadingOrMigrating`
- `testCompletionBeforeConnectPersistsLocalFallbackWithoutHealthKitSave`
- `testConnectEnablesHealthKitRefreshAndPendingMigration`
- `testCancelledAuthorizationKeepsConnectActionAvailableAfterRequestWasPersisted`
- `testSnapshotDeduplicatesHealthRecordsBySessionIDKeepingNewestRecord`

### Workflow restoration

`.github/workflows/ci.yml` now matches `origin/main`, including `merge_group`, the iOS Simulator XCTest job, test diagnostics upload, and simulator cleanup. `.github/workflows/codeql.yml` was restored exactly from `origin/main`.

### Verification commands and output

TDD red check:

```text
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-fix4-red -only-testing:HangTenTests/AppStoreTests -only-testing:HangTenTests/WorkoutHistoryTests
```

The new regression suite initially failed to compile because `AppStore.shouldShowConnectAppleHealth` did not yet exist.

Final build/static checks:

```text
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-fix4-final
rtk git diff --check
rtk git diff --cached --check
rtk git diff --cached --exit-code origin/main -- .github/workflows/ci.yml .github/workflows/codeql.yml
```

`build-for-testing` exited 0. Both diff checks were clean, and the workflow comparison exited 0. Runtime XCTest execution remains unavailable in this workspace; no further runtime attempt was made after the handoff request.

Status: `DONE_WITH_CONCERNS` — implementation and test compilation are verified, but XCTest assertions could not be executed in the simulator environment.
