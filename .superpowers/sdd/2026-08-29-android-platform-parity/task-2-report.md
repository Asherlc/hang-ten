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
