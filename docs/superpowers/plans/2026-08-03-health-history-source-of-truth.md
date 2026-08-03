# Health History Source of Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Hang Ten read its own Apple Health workouts as the authoritative progress history when readable, with durable local fallback records that migrate into HealthKit later.

**Architecture:** Add pure history value types and reconciliation rules, a small `UserDefaults`-backed pending-record store, and a HealthKit adapter that maps only Hang Ten functional-strength workouts. A coordinator will reconcile HealthKit records with local pending records and expose one snapshot to `AppStore`; the existing Progress UI will render that snapshot instead of in-memory counters.

**Tech Stack:** Swift 5, SwiftUI, HealthKit, XCTest, Xcode 26, iOS 17+, `xcodebuild`, signed iOS Simulator validation.

## Global Constraints

- Import only `HKWorkout` records with activity type `.functionalStrengthTraining`, brand metadata exactly `Hang Ten`, and a non-empty `HangTen.PlanName` value.
- New HealthKit records must include a stable `HangTen.SessionID` metadata value matching the local pending record UUID.
- Existing Hang Ten records without `HangTen.SessionID` must remain importable through exact plan-title/start-date/end-date matching.
- HealthKit-derived history is authoritative whenever readable Hang Ten workouts are returned; local records are fallback/pending data, not a permanent mirror.
- Request read and write authorization only from the existing user-initiated Connect Apple Health action; never prompt at launch or on Progress appearance.
- Treat an empty HealthKit result as ambiguous because Apple hides denied read access; retain local records instead of discarding them.
- Do not import other apps’ functional-strength workouts, add network synchronization, or delete HealthKit workouts.
- Preserve the current workout builder date safety: end a saved workout at the earlier of the planned duration and the user’s Log session time.
- Keep HealthKit data on-device and retain the existing HealthKit entitlement and generated usage-description keys, updating the read description to explain history restoration.
- Every production behavior change must follow a red-green test cycle; run the focused test after each task and the full test/build validation before completion.

---

### Task 1: Define history value types and pure reconciliation rules

**Files:**
- Create: `HangTen/Models/WorkoutHistory.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add `WorkoutHistory.swift` to the HangTen target
- Create: `HangTenTests/WorkoutHistoryTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add `WorkoutHistoryTests.swift` to the HangTenTests target

**Interfaces:**
- Produces `PendingWorkoutRecord`, `HealthWorkoutRecord`, `WorkoutHistoryEntry`, `WorkoutHistorySnapshot`, `WorkoutHistorySource`, and `WorkoutHistoryMatcher` for Tasks 2–4.
- `PendingWorkoutRecord` is Codable and stores `id`, `planTitle`, `startDate`, `endDate`, `healthUploadAttempted`, and `healthWorkoutUUID`.
- `HealthWorkoutRecord` stores `id`, `activityTypeRawValue`, `brandName`, `planTitle`, `sessionID`, `startDate`, and `endDate`.
- `HealthWorkoutRecord.isHangTen` identifies accepted records; `WorkoutHistoryMatcher` exposes `entry(from:)`, `matchingHealthWorkout(for:in:)`, and `snapshot(healthRecords:localRecords:healthQuerySucceeded:healthDataAvailable:)`.

- [ ] **Step 1: Add failing tests for HealthKit filtering.**

Create deterministic value-level records so the tests do not need a HealthKit database. Add this test-only helper before the test method so each variation keeps the same ID and dates:

```swift
private extension HealthWorkoutRecord {
    func with(brandName: String) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id,
            activityTypeRawValue: activityTypeRawValue,
            brandName: brandName,
            planTitle: planTitle,
            sessionID: sessionID,
            startDate: startDate,
            endDate: endDate
        )
    }

    func with(activityTypeRawValue: UInt) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id,
            activityTypeRawValue: activityTypeRawValue,
            brandName: brandName,
            planTitle: planTitle,
            sessionID: sessionID,
            startDate: startDate,
            endDate: endDate
        )
    }

    func with(planTitle: String?) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id,
            activityTypeRawValue: activityTypeRawValue,
            brandName: brandName,
            planTitle: planTitle,
            sessionID: sessionID,
            startDate: startDate,
            endDate: endDate
        )
    }
}

func testOnlyHangTenFunctionalStrengthRecordsAreAccepted() {
    let accepted = HealthWorkoutRecord(
        id: UUID(),
        activityTypeRawValue: HKWorkoutActivityType.functionalStrengthTraining.rawValue,
        brandName: HangTenHealthMetadata.brandName,
        planTitle: "Metolius Sequence",
        sessionID: nil,
        startDate: startDate,
        endDate: endDate
    )
    let otherBrand = accepted.with(brandName: "Other App")
    let otherActivity = accepted.with(
        activityTypeRawValue: HKWorkoutActivityType.running.rawValue
    )
    let missingPlan = accepted.with(planTitle: nil)

    XCTAssertTrue(accepted.isHangTen)
    XCTAssertFalse(otherBrand.isHangTen)
    XCTAssertFalse(otherActivity.isHangTen)
    XCTAssertFalse(missingPlan.isHangTen)
}
```

Add tests that `entry(from:)` preserves the HealthKit workout UUID and dates, and that a legacy record with no `sessionID` is still normalized when its plan title is present.

- [ ] **Step 2: Run the focused tests and verify the expected compile failure.**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-domain
```

Expected result: `WorkoutHistoryTests.swift` fails to compile because the history types and matcher do not exist yet.

- [ ] **Step 3: Implement the minimal pure history model.**

In `WorkoutHistory.swift`, define the metadata constants and value types. Keep the HealthKit dependency limited to the activity-type raw value comparison:

```swift
import Foundation
import HealthKit

enum HangTenHealthMetadata {
    static let brandName = "Hang Ten"
    static let planNameKey = "HangTen.PlanName"
    static let sessionIDKey = "HangTen.SessionID"
}

struct PendingWorkoutRecord: Codable, Equatable, Identifiable {
    let id: UUID
    let planTitle: String
    let startDate: Date
    let endDate: Date
    var healthUploadAttempted: Bool
    var healthWorkoutUUID: UUID?
}

struct HealthWorkoutRecord: Equatable, Identifiable {
    let id: UUID
    let activityTypeRawValue: UInt
    let brandName: String?
    let planTitle: String?
    let sessionID: UUID?
    let startDate: Date
    let endDate: Date

    var isHangTen: Bool {
        activityTypeRawValue == HKWorkoutActivityType.functionalStrengthTraining.rawValue &&
        brandName == HangTenHealthMetadata.brandName &&
        !(planTitle?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true)
    }
}

struct WorkoutHistoryEntry: Equatable, Identifiable {
    let id: UUID
    let planTitle: String
    let startDate: Date
    let endDate: Date
    let isPendingLocalRecord: Bool
}

enum WorkoutHistorySource: Equatable {
    case healthKit
    case localFallback
    case syncing
    case unavailable
}

struct WorkoutHistorySnapshot: Equatable {
    static let empty = WorkoutHistorySnapshot(entries: [], source: .unavailable)

    let entries: [WorkoutHistoryEntry]
    let source: WorkoutHistorySource

    var sessionCount: Int { entries.count }
    var latestSessionTitle: String? { entries.first?.planTitle }
}

enum WorkoutHistoryMatcher {
    static func entry(from record: HealthWorkoutRecord) -> WorkoutHistoryEntry

    static func matchingHealthWorkout(
        for localRecord: PendingWorkoutRecord,
        in healthRecords: [HealthWorkoutRecord]
    ) -> HealthWorkoutRecord?

    static func snapshot(
        healthRecords: [HealthWorkoutRecord],
        localRecords: [PendingWorkoutRecord],
        healthQuerySucceeded: Bool,
        healthDataAvailable: Bool
    ) -> WorkoutHistorySnapshot
}
```

`WorkoutHistoryMatcher.snapshot` must sort newest first, deduplicate HealthKit entries by HealthKit UUID, include unmatched local entries as pending fallback entries, use `.healthKit` when the query succeeded and returned at least one accepted HealthKit record, use `.localFallback` when local entries are the only visible history, and use `.unavailable` only when HealthKit is unavailable/query-inaccessible and no local entries exist. An empty successful HealthKit query with no local records produces an empty `.healthKit` snapshot.

For legacy reconciliation, match a local record when any accepted HealthKit record has the same `sessionID`, the same stored `healthWorkoutUUID`, or the same plan title, start date, and end date.

- [ ] **Step 4: Run the focused tests and verify they pass.**

Run the same `rtk xcodebuild test` command from Step 2. Expected result: all filtering, normalization, sorting, and matching tests pass with no warnings.

- [ ] **Step 5: Add edge-case tests, then rerun.**

Cover empty/whitespace plan metadata, duplicate HealthKit UUIDs, local records newer than the latest HealthKit record, an unavailable HealthKit store with local records, and an empty successful HealthKit query with no local records. Rerun the focused test command and keep the output green.

- [ ] **Step 6: Commit the domain task.**

```bash
rtk git add HangTen/Models/WorkoutHistory.swift HangTenTests/WorkoutHistoryTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: define Hang Ten workout history rules"
```

### Task 2: Add durable local fallback storage

**Files:**
- Create: `HangTen/Models/LocalWorkoutHistoryStore.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add `LocalWorkoutHistoryStore.swift` to the HangTen target
- Create: `HangTenTests/LocalWorkoutHistoryStoreTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add `LocalWorkoutHistoryStoreTests.swift` to the HangTenTests target

**Interfaces:**
- Consumes `PendingWorkoutRecord` from Task 1.
- Produces `WorkoutHistoryPersistence` and `LocalWorkoutHistoryStore` for Task 4.
- The protocol is synchronous and intentionally small:

```swift
protocol WorkoutHistoryPersistence: AnyObject {
    func load() -> [PendingWorkoutRecord]
    func replace(_ records: [PendingWorkoutRecord])
}
```

- [ ] **Step 1: Write failing persistence tests.**

Use an isolated `UserDefaults` suite for every test. Verify round-trip persistence, replacement, and that a new store with the same suite reads the records written by the first store:

```swift
func testRecordsRoundTripThroughUserDefaults() {
    let suiteName = "HangTenTests.LocalHistory.\(UUID().uuidString)"
    let defaults = UserDefaults(suiteName: suiteName)!
    let record = PendingWorkoutRecord(
        id: UUID(),
        planTitle: "Metolius Sequence",
        startDate: startDate,
        endDate: endDate,
        healthUploadAttempted: false,
        healthWorkoutUUID: nil
    )

    let firstStore = LocalWorkoutHistoryStore(defaults: defaults)
    firstStore.replace([record])

    XCTAssertEqual(LocalWorkoutHistoryStore(defaults: defaults).load(), [record])
}
```

Add a replacement test proving that an empty array clears the persisted set, and a malformed-payload test proving `load()` returns an empty set without crashing.

- [ ] **Step 2: Run the focused tests and verify the expected failure.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-store
```

Expected result: the new tests fail to compile because `WorkoutHistoryPersistence` and `LocalWorkoutHistoryStore` are not defined.

- [ ] **Step 3: Implement the minimal UserDefaults store.**

Use one versioned key and JSON encoding. The initializer must accept `UserDefaults` so tests never touch the real standard suite:

```swift
final class LocalWorkoutHistoryStore: WorkoutHistoryPersistence {
    static let defaultKey = "HangTen.pendingWorkoutHistory.v1"

    private let defaults: UserDefaults
    private let key: String

    init(
        defaults: UserDefaults = .standard,
        key: String = LocalWorkoutHistoryStore.defaultKey
    ) {
        self.defaults = defaults
        self.key = key
    }

    func load() -> [PendingWorkoutRecord] {
        guard let data = defaults.data(forKey: key) else { return [] }
        return (try? JSONDecoder().decode([PendingWorkoutRecord].self, from: data)) ?? []
    }

    func replace(_ records: [PendingWorkoutRecord]) {
        guard let data = try? JSONEncoder().encode(records) else { return }
        defaults.set(data, forKey: key)
    }
}
```

- [ ] **Step 4: Run persistence tests and verify they pass.**

Run the same command from Step 2. Expected result: all local-store tests pass, including malformed input handling, with no changes to unrelated `UserDefaults` keys.

- [ ] **Step 5: Commit the local-store task.**

```bash
rtk git add HangTen/Models/LocalWorkoutHistoryStore.swift HangTenTests/LocalWorkoutHistoryStoreTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: persist local workout history fallback"
```

### Task 3: Extend the HealthKit adapter for read/query/sync metadata

**Files:**
- Modify: `HangTen/Models/HealthKitService.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add the new HealthKit adapter tests
- Create: `HangTenTests/HealthKitServiceTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add `HealthKitServiceTests.swift` to the HangTenTests target
- Modify: `HangTen.xcodeproj/project.pbxproj` in both app build configurations to update `INFOPLIST_KEY_NSHealthShareUsageDescription`

**Interfaces:**
- Consumes the value types and metadata constants from Task 1.
- Produces `WorkoutHealthStore` for Task 4:

```swift
protocol WorkoutHealthStore: AnyObject {
    var isHealthDataAvailable: Bool { get }
    var authorizationState: HealthAuthorizationState { get }

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    )

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    )

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    )
}
```

- [ ] **Step 1: Write the failing metadata-mapping tests.**

Construct `HKWorkout` values with Apple’s convenience initializer and assert that the adapter preserves the workout UUID, dates, plan title, brand, and optional session UUID. Include one legacy workout with no `HangTen.SessionID`, plus non-Hang Ten and non-functional-strength examples that map to `isHangTen == false`.

```swift
func testHealthKitWorkoutMapsHangTenMetadataAndSessionID() {
    let sessionID = UUID()
    let workout = HKWorkout(
        activityType: .functionalStrengthTraining,
        start: startDate,
        end: endDate,
        duration: endDate.timeIntervalSince(startDate),
        totalEnergyBurned: nil,
        totalDistance: nil,
        metadata: [
            HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
            HangTenHealthMetadata.planNameKey: "Metolius Sequence",
            HangTenHealthMetadata.sessionIDKey: sessionID.uuidString
        ]
    )

    let record = HealthKitService.record(from: workout)

    XCTAssertEqual(record.sessionID, sessionID)
    XCTAssertTrue(record.isHangTen)
    XCTAssertEqual(record.planTitle, "Metolius Sequence")
}
```

- [ ] **Step 2: Run the focused tests and verify the expected failure.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-healthkit
```

Expected result: the tests fail to compile because the mapper and new protocol methods do not exist.

- [ ] **Step 3: Implement the HealthKit adapter changes.**

Make `HealthKitService` conform to `WorkoutHealthStore`. Keep the existing authorization state as the write/share state, but request both sets:

```swift
healthStore.requestAuthorization(
    toShare: [HKObjectType.workoutType()],
    read: [HKObjectType.workoutType()]
) { [weak self] _, error in
    completion(self?.authorizationState ?? .unavailable, error)
}
```

Implement the internal mapper:

```swift
static func record(from workout: HKWorkout) -> HealthWorkoutRecord {
    let metadata = workout.metadata ?? [:]
    return HealthWorkoutRecord(
        id: workout.uuid,
        activityTypeRawValue: workout.workoutActivityType.rawValue,
        brandName: metadata[HKMetadataKeyWorkoutBrandName] as? String,
        planTitle: metadata[HangTenHealthMetadata.planNameKey] as? String,
        sessionID: (metadata[HangTenHealthMetadata.sessionIDKey] as? String).flatMap(UUID.init),
        startDate: workout.startDate,
        endDate: workout.endDate
    )
}
```

Implement `fetchHangTenWorkouts` with `HKSampleQuery` over `HKObjectType.workoutType()`, `HKObjectQueryNoLimit`, and descending end-date sorting. Map all returned `HKWorkout` samples and filter with `isHangTen`; pass query errors through the `Result` failure. Do not treat an empty successful result as an error.

Update the builder save to accept the local UUID, add `HangTen.SessionID` to the existing metadata, and return the finished workout UUID on success. Preserve every existing builder-stage error and return a typed failure for an invalid interval or unavailable write authorization so the coordinator can keep the local record.

Change both Debug and Release `NSHealthShareUsageDescription` values to:

```text
Hang Ten reads your Apple Health workout history to restore your progress on a new device.
```

Keep the existing update description and HealthKit entitlement unchanged.

- [ ] **Step 4: Run the focused adapter tests and verify they pass.**

Run the command from Step 2. Expected result: metadata mapping and filtering tests pass. The test target must compile against HealthKit without warnings.

- [ ] **Step 5: Build the signed simulator app to verify the HealthKit entitlement and generated usage descriptions.**

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -sdk iphonesimulator -derivedDataPath .context/DerivedData-healthkit CODE_SIGNING_ALLOWED=YES build
```

Inspect the generated app/derived entitlements as described in `docs/IOS_RUNTIME_SERVICES.md`; confirm `com.apple.developer.healthkit` remains enabled and the generated Info.plist contains the revised read usage text.

- [ ] **Step 6: Commit the HealthKit adapter task.**

```bash
rtk git add HangTen/Models/HealthKitService.swift HangTenTests/HealthKitServiceTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: read Hang Ten workouts from HealthKit"
```

### Task 4: Add history coordination and wire AppStore/Progress UI

**Files:**
- Create: `HangTen/Models/WorkoutHistoryService.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add `WorkoutHistoryService.swift` to the HangTen target
- Create: `HangTenTests/WorkoutHistoryServiceTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj` to add `WorkoutHistoryServiceTests.swift` to the HangTenTests target
- Modify: `HangTen/Models/AppStore.swift`
- Modify: `HangTen/Views/RootView.swift`

**Interfaces:**
- Consumes `WorkoutHealthStore` from Task 3, `WorkoutHistoryPersistence` from Task 2, and the pure matcher from Task 1.
- Produces `WorkoutHistoryService` with these methods:

```swift
final class WorkoutHistoryService {
    private(set) var snapshot: WorkoutHistorySnapshot
    private(set) var lastError: Error?

    init(
        healthStore: any WorkoutHealthStore,
        persistence: any WorkoutHistoryPersistence
    )

    func refresh(completion: @escaping () -> Void)

    func recordCompletion(
        planTitle: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping () -> Void
    )
}
```

- [ ] **Step 1: Write failing coordinator tests with a synchronous fake HealthKit store.**

Define a test-only fake conforming to `WorkoutHealthStore` with controllable availability, authorization state, returned records, save results, and `saveCallCount`. Add these tests with the exact assertions described:

- `testEmptyHealthKitFallsBackToLocalRecords` asserts the local record appears once with `.localFallback`.
- `testVisibleHealthKitRecordsBecomeAuthoritative` asserts the HealthKit workout supplies the count and latest title with `.healthKit`.
- `testCompletionPersistsLocallyBeforeHealthKitSave` asserts persistence contains the new record before the fake observes one save call.
- `testFailedHealthKitSaveRetainsLocalRecordAndError` asserts the failed record remains retryable and `lastError` is set.
- `testMigrationUploadsEachPendingRecordOnce` refreshes twice and asserts the fake save count stays at one.
- `testLegacyHealthWorkoutReconcilesLocalRecordByExactDatesAndTitle` asserts a legacy HealthKit record and local record produce one entry.

The tests must assert both the snapshot entries/count/latest title and the persistence contents. A HealthKit query failure with local records must yield `.localFallback`; the same failure with no local records must yield `.unavailable`.

- [ ] **Step 2: Run the focused coordinator tests and verify the expected failure.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-history-service
```

Expected result: the tests fail to compile because `WorkoutHistoryService` and the AppStore history snapshot do not exist.

- [ ] **Step 3: Implement idempotent synchronization.**

Implement this sequence in `WorkoutHistoryService.refresh`:

1. Load local pending records.
2. If HealthKit is unavailable, publish the local snapshot with `.localFallback` when non-empty or `.unavailable` when empty.
3. Otherwise fetch HealthKit records. On query failure, publish the same local fallback/unavailable state and retain the error.
4. Filter and reconcile visible records with pending local records using session ID, stored HealthKit UUID, or exact legacy title/date matching.
5. For unmatched records, call `saveCompletedWorkout` only when the HealthKit write authorization state is `.authorized`. Set `healthUploadAttempted = true` before the call to prevent concurrent duplicate saves; if the save fails, reset it to `false`, retain the record, and retain the error. If it succeeds, store the returned HealthKit UUID and leave the record until a follow-up query confirms it or the current access state permits removing the fallback.
6. After all writes finish, fetch HealthKit again, reconcile again, and replace persistence with only records that still need local fallback. A successfully written record that is still hidden by read privacy remains in persistence with its upload-attempted flag so it is not uploaded twice.
7. Publish a sorted snapshot. Include unmatched local records as pending entries; use `.healthKit` when at least one accepted HealthKit record is visible, `.localFallback` when only local entries are visible, and `.unavailable` when neither source has entries.

Do not start a second synchronization while one is in flight. The completion callback must always run on the main queue after the snapshot and error are updated.

Implement `recordCompletion` by creating and persisting a new `PendingWorkoutRecord` before invoking `refresh`, so a process termination or HealthKit failure cannot lose the session.

- [ ] **Step 4: Run coordinator tests and verify they pass.**

Run the command from Step 2. Expected result: all fallback, HealthKit-authoritative, migration, failure-retention, legacy-reconciliation, and idempotency tests pass.

- [ ] **Step 5: Wire `AppStore` to the coordinator without preserving an independent counter.**

Replace the mutable `sessionsCompleted` and `lastSessionTitle` fields with a published `workoutHistory` snapshot and computed compatibility properties:

```swift
@Published private(set) var workoutHistory = WorkoutHistorySnapshot.empty

var sessionsCompleted: Int { workoutHistory.sessionCount }
var lastSessionTitle: String? { workoutHistory.latestSessionTitle }
```

Inject `any WorkoutHealthStore` and `any WorkoutHistoryPersistence` into `AppStore` with production defaults of `HealthKitService()` and `LocalWorkoutHistoryStore()`. Add `refreshWorkoutHistory()` and invoke it from `refreshHealthAuthorization()` and the authorization callback. `markSessionComplete` must delegate to `WorkoutHistoryService.recordCompletion` and show a local-save/sync error without incrementing a separate counter.

Persist `hasRequestedHealthAuthorization` under the versioned key `HangTen.healthAuthorizationRequested.v1`. Set it only when the user taps Connect Apple Health; never set it during initialization or Progress appearance. The button logic must still allow a person with existing write authorization to request the new read permission.

- [ ] **Step 6: Update the Progress UI and add deterministic accessibility identifiers.**

In `ProgressDashboardView`:

- refresh authorization and workout history on appearance and when the scene becomes active;
- keep the existing Apple Health authorization pill and settings behavior;
- show `workoutHistory.source` copy from the snapshot rather than claiming an empty result proves denial;
- keep the session count and latest plan title driven by `AppStore.workoutHistory`;
- show the existing Connect Apple Health action when authorization has not been requested, and show the settings action when the write state is denied or a previously requested HealthKit connection still exposes only local fallback history;
- add `.accessibilityIdentifier("progress.sessionsCount")` to the visible session count and `.accessibilityIdentifier("health.connect")` to the Connect button.

Use these exact source messages:

```swift
case .healthKit: "History synced from Apple Health."
case .localFallback: "History stored on this device until Apple Health is connected."
case .syncing: "Syncing Hang Ten history with Apple Health…"
case .unavailable: "Apple Health history is unavailable; completed sessions stay on this device."
```

Preserve the existing workout completion path, including the rule that End session does not log a workout.

- [ ] **Step 7: Run the full unit test suite and commit the integration task.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-full
rtk git diff --check
```

Expected result: the existing timeline/session tests and all new history tests pass with no compiler warnings relevant to the changed files.

```bash
rtk git add HangTen/Models/WorkoutHistoryService.swift HangTenTests/WorkoutHistoryServiceTests.swift HangTen/Models/AppStore.swift HangTen/Views/RootView.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: make HealthKit the workout history source"
```

### Task 5: Document the runtime contract and validation scenarios

**Files:**
- Modify: `docs/IOS_RUNTIME_SERVICES.md`
- Modify: `docs/IOS_SIMULATOR_VALIDATION.md`

**Interfaces:**
- Consumes the behavior delivered by Tasks 1–4.
- Produces the documented validation contract used for final simulator review and physical-device handoff.

- [ ] **Step 1: Update the Apple Health runtime documentation.**

Replace the current “does not request read access” statement with the HealthKit-first contract:

- read and write both target `HKObjectType.workoutType()`;
- only Hang Ten functional-strength records with the exact brand and plan metadata are imported;
- `HangTen.SessionID` identifies newly saved records;
- old records reconcile by exact plan title/start/end values;
- local `UserDefaults` records are pending/fallback data and migrate after Connect Apple Health;
- Apple’s hidden read-denial behavior means an empty query remains ambiguous;
- Progress refreshes on appearance and scene activation without prompting.

Document that physical-device testing is required for cross-device HealthKit restoration.

- [ ] **Step 2: Extend the simulator checklist.**

Add checks for:

- the combined read/write permission sheet and revised read usage text;
- completing a short session without granting HealthKit access and seeing the local fallback count;
- granting access later, syncing the pending record, and confirming the same session is not counted twice;
- relaunching Progress and confirming the HealthKit-backed count persists;
- returning from Settings and seeing authorization/history refresh;
- preserving the existing signed HealthKit entitlement inspection and physical-device caveat.

- [ ] **Step 3: Review the documentation for consistency and commit it.**

Run:

```bash
rtk rg -n "does not request read access|HangTen.SessionID|local fallback|empty.*ambiguous|HealthKit" docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
rtk git diff --check
rtk git add docs/IOS_RUNTIME_SERVICES.md docs/IOS_SIMULATOR_VALIDATION.md
rtk git commit -m "docs: describe HealthKit history sync and fallback"
```

Expected result: no stale statement says Hang Ten does not request read access, and the changed docs have no whitespace errors.

## Final verification and handoff

After all task commits:

1. Read `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` completely before running the validation workflow.
2. Create or reuse only this workspace’s dedicated simulator and record its explicit UUID; never use `booted`.
3. Build a signed Debug app with a workspace-specific derived-data path and install that exact app on the dedicated simulator.
4. Validate local fallback, permission flow, a saved HealthKit workout, refresh/relaunch deduplication, and Progress status copy in portrait and landscape.
5. Inspect the signed simulator entitlement/intermediate simulated entitlement for `com.apple.developer.healthkit`.
6. Run the complete unit test command again and capture the exit code/output.
7. Report that cross-device restore still requires a physical-device test using the same HealthKit account.

Final verification commands:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath .context/DerivedData-health-history-final
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -sdk iphonesimulator -derivedDataPath .context/DerivedData-health-history-final CODE_SIGNING_ALLOWED=YES build
rtk git diff --check origin/main...
```

The final review must compare the complete branch against `origin/main`, verify every Global Constraint, and include the physical-device limitation in the handoff.
