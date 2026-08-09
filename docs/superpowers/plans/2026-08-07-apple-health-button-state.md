# Apple Health Button State Implementation Plan

> **For agentic workers:** Mandatory: use a fresh subagent for every implementation task or configuration change. Every task must include separate implementation and review checkpoints. Follow `superpowers:subagent-driven-development` or `superpowers:executing-plans` to execute this plan task-by-task. Retain checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the Progress card never shows `Connect Apple Health` when HealthKit reports that Hang Ten is already authorized.

**Architecture:** `HealthAuthorizationState` is the single source of truth for the Connect action exposed by `AppStore.shouldShowConnectAppleHealth`. The existing `RootView.healthAction` mapping consumes that property, so the fix stays in the AppStore model while denied, unavailable, and local-fallback settings behavior remains unchanged. Documentation and AppStore tests will be updated to match the new state contract.

**Tech Stack:** Swift, SwiftUI, XCTest, HealthKit, Xcode `xcodebuild`

## Global Constraints

- `.notDetermined` shows `Connect Apple Health`.
- `.authorized` never shows `Connect Apple Health`, regardless of history contents or the persisted sync-request flag.
- If `refreshHealthAuthorization` observes `.authorized` while the persisted request flag is false, persist the flag and enable HealthKit sync without prompting, then run the existing history refresh/import path.
- Reconcile an authorized state with a missing request flag non-promptingly before refreshing history.
- `.denied` keeps `Open app settings`; `.unavailable` shows no action.
- Do not change HealthKit APIs, persistence formats, authorization requests, or unrelated UI behavior.
- Follow a red-green TDD cycle: observe the regression test fail before changing production code, then verify focused and full test suites.
- Keep documentation consistent with the approved authorized-empty-history behavior.
- Keep all build and test output under `.context/DerivedData` or another workspace-owned `.context` path.

---

### Task 1: Make HealthKit authorization control the Connect action

**Files:**
- Modify: `HangTenTests/AppStoreTests.swift:266-285` to turn the authorized-empty-history test into a regression test and add the missing-request-flag case.
- Modify: `HangTen/Models/AppStore.swift:136-142` to derive Connect visibility solely from `healthAuthorizationState`.
- Modify: `docs/IOS_RUNTIME_SERVICES.md:263-272` to remove the authorized-empty-history recovery action description.
- Modify: `docs/IOS_SIMULATOR_VALIDATION.md:360-366` to stop instructing validation to keep Connect available after an authorized empty query.

**Interfaces:**
- Consumes: `HealthAuthorizationState`, `AppStore.shouldShowConnectAppleHealth`, `FakeWorkoutHealthStore`, and the existing `AppStoreTests` test helpers.
- Produces: `AppStore.shouldShowConnectAppleHealth == true` only when `healthAuthorizationState == .notDetermined`; `RootView` continues to use the existing property without modification.

- [ ] **Step 1: Write the failing regression tests**

Rename the existing authorized-empty-history test and change its final assertion, then add a test proving that an authorized HealthKit state wins even when Hang Ten has never persisted its request flag:

```swift
func testAuthorizedEmptyHealthKitHistoryHidesConnectActionAfterRefresh() {
    let suiteName = "AppStoreTests.\(UUID().uuidString)"
    let defaults = UserDefaults(suiteName: suiteName)!
    defer { defaults.removePersistentDomain(forName: suiteName) }
    defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)

    let healthStore = FakeWorkoutHealthStore(fetchResult: .success([]))
    healthStore.authorizationState = .authorized
    let appStore = AppStore(
        healthKitService: healthStore,
        workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
        defaults: defaults
    )

    appStore.refreshHealthAuthorization()
    waitUntil { appStore.workoutHistory.source == .healthKit }

    XCTAssertTrue(appStore.workoutHistory.entries.isEmpty)
    XCTAssertFalse(appStore.shouldShowConnectAppleHealth)
}

func testAuthorizedHealthKitHidesConnectActionWithoutPersistedRequestFlag() {
    let suiteName = "AppStoreTests.\(UUID().uuidString)"
    let defaults = UserDefaults(suiteName: suiteName)!
    defer { defaults.removePersistentDomain(forName: suiteName) }

    let healthStore = FakeWorkoutHealthStore(fetchResult: .success([]))
    healthStore.authorizationState = .authorized
    let appStore = AppStore(
        healthKitService: healthStore,
        workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
        defaults: defaults
    )

    XCTAssertFalse(appStore.hasRequestedHealthAuthorization)
    XCTAssertFalse(appStore.shouldShowConnectAppleHealth)
}
```

Keep `testCancelledAuthorizationKeepsConnectActionAvailableAfterRequestWasPersisted` unchanged so the not-determined state still proves Connect remains available after a cancelled request.

- [ ] **Step 2: Run the focused tests and verify the expected red failure**

Run:

```sh
rtk xcodebuild test \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/AppStoreTests
```

Expected: the focused test target builds, and the two new `XCTAssertFalse` assertions fail because the current `shouldShowConnectAppleHealth` implementation also checks the persisted request flag and empty HealthKit history.

- [ ] **Step 3: Implement the minimal production change**

Replace the current multi-condition body in `HangTen/Models/AppStore.swift` with the authorization-state rule:

```swift
var shouldShowConnectAppleHealth: Bool {
    healthAuthorizationState == .notDetermined
}
```

Do not change `RootView.healthAction`; its denied and local-fallback settings branches remain valid with this model contract.

- [ ] **Step 4: Run the focused tests and verify green**

Run the exact focused `rtk xcodebuild test` command from Step 2. Expected: `HangTenTests/AppStoreTests` passes, including the cancelled/not-determined Connect case and both authorized-state regression cases.

- [ ] **Step 5: Update the documentation wording**

In `docs/IOS_RUNTIME_SERVICES.md`, retain the explanation that an empty HealthKit query is ambiguous and local pending records must be preserved, but replace the action paragraph with:

```text
The Progress action is driven by the current HealthAuthorizationState. Before
authorization is determined it offers Connect Apple Health. Once HealthKit
reports authorized access, it never offers Connect Apple Health, including for
an empty .healthKit snapshot or when the persisted history-sync request flag is
false. Local fallback may offer Open app settings, while denied and unavailable
behavior remains as shown in the table.
```

In `docs/IOS_SIMULATOR_VALIDATION.md`, keep the empty-result ambiguity and local-fallback checks, but replace the instruction to keep Connect available with a check that an authorized empty result shows the `Connected` status and no Connect action. Preserve the existing checks for local-fallback settings, denied settings, and unavailable behavior.

- [ ] **Step 6: Run the complete test suite**

Run:

```sh
rtk xcodebuild test \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath .context/DerivedData
```

Expected: the full `HangTenTests` suite passes with zero test failures.

- [ ] **Step 7: Inspect the diff and commit the task**

Run:

```sh
rtk git diff --check
rtk git diff -- HangTen/Models/AppStore.swift HangTenTests/AppStoreTests.swift docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
```

Confirm that only the authorization predicate, its regression coverage, and the two contradictory documentation passages changed. Then commit:

```sh
rtk git add HangTen/Models/AppStore.swift HangTenTests/AppStoreTests.swift docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
rtk git commit -m "fix: hide Apple Health connect action when authorized"
```
