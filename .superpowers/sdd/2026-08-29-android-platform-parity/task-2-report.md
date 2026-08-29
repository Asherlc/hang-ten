# Task 2 — Health Connect workout reconciliation

## Delivered behavior

- `WorkoutHealthStore` has a testable Health Connect implementation with the four
  required authorization states: unavailable, not determined, denied, and
  authorized.
- The Health Connect permission launcher exists only on Settings' visible
  **Connect Health** action. App construction and normal navigation do not request
  permissions.
- The adapter requests exactly exercise read/write permissions, writes
  `ExerciseSessionRecord` records as strength training, and gives each completed
  session a deterministic SHA-256 client record ID plus client-record version 1.
- Record title and versioned JSON notes contain the plan/board identity and the
  canonical plan-step activity segments. Reads accept only Hang Ten's versioned
  strength-training records and reconcile them with the local history by that
  stable identity.
- Completion persists locally before Health Connect writing. Denied, unavailable,
  or failed writes leave the local completion visible and surface a user-visible
  sync error where appropriate.
- Local persisted records now retain board and plan title (while preserving decode
  compatibility with the existing three-field history format), so future
  reconciliation remains stable across process recreation.

## Test-first evidence

`HealthConnectServiceTest` was added before the adapter implementation, covering:

1. explicit permission flow with no request before the Settings action;
2. deterministic client ID, record version, strength-training type, and exact
   versioned segment notes;
3. denied local fallback;
4. failed write local retention and visible error; and
5. read reconciliation deduplication with unmatched local history retained.

Initial focused execution could not compile because the feature did not yet exist
and the workspace had no Android SDK. A temporary owned SDK made the first real
dependency check possible. It exposed that Health Connect 1.1.0 requires
`compileSdk 36` and Android Gradle Plugin 8.9.1 or newer; the project was updated
to the compatible AGP 8.9.1 / Gradle 8.11.1 / API 36 combination. The next
compile found and corrected the actual 1.1.0 API mappings: use
`InsertRecordsResponse.recordIdsList.single()` and
`Metadata.manualEntry(clientRecordId, clientRecordVersion)`.

## Fresh verification

All commands below ran from the current worktree using only the owned temporary
SDK/cache noted in the cleanup section.

```text
env GRADLE_USER_HOME=.context/android-health-connect-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android :app:testDebugUnitTest \
  --tests '*HealthConnectServiceTest'
# BUILD SUCCESSFUL — 5 tests, 0 failures

env GRADLE_USER_HOME=.context/android-health-connect-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android :app:testDebugUnitTest
# BUILD SUCCESSFUL — 41 tests, 0 failures, 0 errors

env GRADLE_USER_HOME=.context/android-health-connect-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android :app:lintDebug :app:assembleDebug
# BUILD SUCCESSFUL — lint 0 errors (5 non-blocking warnings),
# Debug APK produced at Android/app/build/outputs/apk/debug/app-debug.apk
```

No owned Android emulator gate was available: the isolated SDK intentionally has
no `emulator` executable or system image, and no shared SDK/AVD was used. The
adapter's gateway and workout-history seams are covered by deterministic fakes in
the focused unit suite. Physical Health Connect permission/write validation remains
a release-device gate because it requires the provider and a user-controlled
Health Connect account.

## Owned-resource cleanup

The task created and then removed these exact workspace-owned paths after the
verification runs; each was checked absent before commit:

- `.context/android-health-connect-sdk-bitter-scorpion`
- `.context/android-health-connect-gradle-bitter-scorpion`
- `.context/android-health-connect-aar-bitter-scorpion`
- `Android/local.properties` (temporary SDK pointer, ignored by git)

## Review round 1 — origin-safe paginated reads and emulator coverage

The review findings were reproduced with red tests, then fixed as follows:

- Health Connect reads now carry the Hang Ten application package as a
  `DataOrigin` filter and iterate every response `pageToken` before reconciling.
- The SDK boundary now preserves the actual `ExerciseSessionRecord.exerciseType`:
  strength training maps to `StrengthTraining`; every other SDK value maps to an
  explicit `Other(value)` and is rejected by the existing Hang Ten record
  validator.
- Reconciliation deduplicates remote workouts by stable `clientRecordId` before
  comparing them with local stable IDs.
- `AndroidHealthConnectGatewayTest` uses a fake SDK client to prove both origin
  filtering request construction and two-page aggregation/type preservation.
- `HealthConnectUiTest` uses only fakes and was exercised on-device for: no
  Health Connect prompt before the explicit Connect button, denied local
  fallback, write-error local retention, and duplicate remote reconciliation.

Fresh round-1 verification used only these workspace-owned resources:

```text
env GRADLE_USER_HOME=.context/android-health-connect-round1-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android :app:testDebugUnitTest \
  --tests '*AndroidHealthConnectGatewayTest' --tests '*HealthConnectServiceTest'
# BUILD SUCCESSFUL

env GRADLE_USER_HOME=.context/android-health-connect-round1-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android :app:compileDebugAndroidTestKotlin
# BUILD SUCCESSFUL

# owned API-36 arm64 Google APIs AVD: hangten-health-connect-bitter-scorpion
# isolated ADB server port: 5038
./Android/gradlew --no-daemon -p Android :app:connectedDebugAndroidTest
# BUILD SUCCESSFUL — 16 instrumented tests, 0 failures, 0 errors
# HealthConnectUiTest: 4 tests, 0 failures

env GRADLE_USER_HOME=.context/android-health-connect-round1-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android \
  :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
# BUILD SUCCESSFUL — 43 unit tests, 0 failures; lint 0 errors;
# Debug APK assembled
```

The connected test launcher installed an exit trap before starting the AVD. It
stopped emulator-5556 and its isolated port-5038 ADB server when Gradle exited;
the exact workspace-owned SDK, Gradle cache, AVD directory, emulator log, and
temporary `Android/local.properties` are removed and checked absent below.

## Re-review round 2 — empty pagination token

`AndroidHealthConnectGateway.readRecords` now terminates after the first page
when `nextPageToken` is null, empty, or whitespace-only. The new
`stopsPagingWhenTheProviderReturnsAnEmptyNextToken` fake-client test was first
run red: the previous implementation made a second request for `""`, and the
fake failed because that page did not exist. After changing the guard to
`!pageToken.isNullOrBlank()`, the focused gateway/service test command passed.

```text
env GRADLE_USER_HOME=.context/android-health-connect-round2-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android :app:testDebugUnitTest \
  --tests '*AndroidHealthConnectGatewayTest' --tests '*HealthConnectServiceTest'
# BUILD SUCCESSFUL

env GRADLE_USER_HOME=.context/android-health-connect-round2-gradle-bitter-scorpion \
  ./Android/gradlew --no-daemon -p Android \
  :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
# BUILD SUCCESSFUL — 44 unit tests, 0 failures; lint 0 errors; Debug APK assembled
```

The round-2 temporary SDK, Gradle cache, downloaded command-line tools archive,
and `Android/local.properties` SDK pointer are workspace-owned and removed after
the verification commands.
