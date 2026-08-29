# Task 1 — Android Play Billing entitlement access

## Delivered

- Added `PlayBillingClient` using Google Play Billing Library `9.1.0` for the
  one-time product `com.hangten.training.lifetime`.
- The client enables one-time pending purchases, queries the product before it
  is presented, observes `PurchasesUpdatedListener` lifecycle updates, queries
  current in-app purchases for preparation and restore, and acknowledges only
  `PURCHASED` records.
- Added the platform-neutral `PurchaseManager` entitlement state machine.
  Entitlement is retained only after acknowledgement succeeds. Pending,
  cancellation, failure, explicit revocation, and a later empty current-purchase
  query never grant or retain access.
- Added the two-free-workout access store and Compose `WorkoutAccessGate`.
  Saved unlocked workouts consume a free credit; exhausted credits present an
  unlock sheet. A missing product is represented only by retry/restore controls,
  never as a purchasable button.
- Added lifetime unlock/restore controls to Settings and injects the live client
  from `MainActivity`. Existing Android UI call sites retain a deterministic
  unavailable client overload for isolated UI tests.

## Test-first evidence

`PurchaseManagerTest` was written before the new billing types and initially
could not compile because the symbols did not exist. The requested direct
Gradle command was first blocked by a corrupt shared Gradle distribution:

```
java.nio.file.NoSuchFileException: /private/tmp/gradle-8.9/lib/gradle-runtime-api-info-8.9.jar
```

The clean workspace-owned toolchain then revealed two real implementation
issues, each fixed with its corresponding test:

1. `billing-ktx:9.1.0` requires Kotlin metadata 2.3 while this project pins
   Kotlin 2.0. The implementation uses `billing:9.1.0` callback APIs instead,
   preserving the specified Play Billing version without a broad compiler
   upgrade.
2. A current-purchase restore returning no lifetime product originally retained
   a prior entitlement. `restoreWithoutLifetimePurchaseRevokesPreviouslyGrantedAccess`
   failed, then passed after restore clears entitlement before applying the
   current purchase set.

Focused green run:

```
SDK_DIR="$PWD/.context/android-billing-sdk-0o9ylkoo"
GRADLE_USER_HOME="$PWD/.context/android-billing-gradle-0o9ylkoo"
ANDROID_HOME="$SDK_DIR" ANDROID_SDK_ROOT="$SDK_DIR" \
  ./Android/gradlew -p Android --no-daemon :app:testDebugUnitTest \
  --tests '*PurchaseManagerTest' --tests '*WorkoutAccessStoreTest' --rerun-tasks

BUILD SUCCESSFUL in 12s
23 actionable tasks: 23 executed
```

Covered behaviors:

- purchased lifetime unlock acknowledges before access is granted;
- pending purchase remains locked;
- lifecycle revocation removes access;
- restore acknowledges and unlocks current purchased access;
- a current-purchase query with no lifetime purchase revokes prior access;
- unavailable product is not exposed for purchase;
- free-credit exhaustion requires purchase while lifetime workouts do not spend
  more credits.

## Verification

The following fresh command passed after the implementation:

```
./Android/gradlew -p Android --no-daemon \
  :app:testDebugUnitTest :app:lintDebug :app:assembleDebug --rerun-tasks

BUILD SUCCESSFUL in 41s
52 actionable tasks: 52 executed
```

The Android UI test artifact also compiles successfully:

```
./Android/gradlew -p Android --no-daemon :app:assembleDebugAndroidTest --rerun-tasks

BUILD SUCCESSFUL in 12s
45 actionable tasks: 45 executed
```

`WorkoutAccessGateTest` covers the exhausted-free-workout path and asserts that
the unavailable-product gate does not start the workout or render a purchase
control.

## Emulator access-gate validation

An isolated API 35 Google APIs ARM64 AVD was created with the exact owned name
`bitter-scorpion-billing-api35`; it ran from the workspace-owned path
`.context/android-billing-avd-bitter-scorpion`. It booted as `emulator-5554`
with `sys.boot_completed=1` and ran the complete connected suite:

```
./Android/gradlew -p Android --no-daemon :app:connectedDebugAndroidTest

Starting 10 tests on bitter-scorpion-billing-api35(AVD) - 15
Finished 10 tests on bitter-scorpion-billing-api35(AVD) - 15
BUILD SUCCESSFUL in 1m 9s
```

This includes `WorkoutAccessGateTest`, which exercises the exhausted free-workout
gate and verifies unavailable purchase options remain non-purchasable. Play
Console/lifetime-product test-purchase validation remains an external release
gate; no Play credentials are included.

## Sources

- Android Developers, [Integrate the Google Play Billing Library](https://developer.android.com/google/play/billing/integrate): pending purchases, product queries, purchase updates, current-purchase queries, and purchased-only acknowledgement.
- Android Developers, [Play Billing release notes](https://developer.android.com/google/play/billing/release-notes): Billing Library 9.1.0.

## Workspace resource cleanup

The isolated Gradle home, Android SDK, and AVD were workspace-owned temporary
resources:

- `.context/android-billing-gradle-0o9ylkoo`
- `.context/android-billing-sdk-0o9ylkoo`
- `.context/android-billing-avd-bitter-scorpion`

After the connected suite passed, `adb -s emulator-5554 emu kill` stopped the
owned emulator, `avdmanager delete avd --name bitter-scorpion-billing-api35`
removed the exact owned AVD, `avdmanager list avd` returned no AVDs in its
isolated home, and `adb devices -l` returned no connected devices. The exact
isolated Gradle/SDK/AVD directories are then removed and their absence verified.
No shared Gradle cache, Android SDK, emulator, or AVD was modified.
