# Restore Retry Fix Report

## Root cause

`PurchaseManager.prepare()` clears `product` before product metadata loading and
sets `.productLoadFailed` on failure. `LifetimeUnlockPaywall` previously
rendered `paywall.retryProduct` only while the state was exactly
`.productLoadFailed`. A Restore without an entitlement then changes the state
to `.nothingToRestore` (or to `.restoreFailed` when Restore errors), while
`product` remains nil. Buy consequently stays disabled and the recovery action
was hidden.

The paywall now shows Retry Loading Purchase whenever no product is available
and no loading or purchase operation is active. Retry continues to call only
`prepare()`; it does not change entitlement/access state.

## TDD evidence

### RED

Added `testRetryRemainsAvailableAfterProductLoadFailureAndEmptyRestore` to
`HangTenUITests/WorkoutPaywallUITests.swift`. It starts from a deterministic
one-time product-load failure, performs Restore with no entitlement, and
asserts that `paywall.retryProduct` remains present while Session remains
closed.

Command:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=D0AF1B1E-6AE3-46F1-82A3-55303F015308' \
  -only-testing:HangTenUITests/WorkoutPaywallUITests/testRetryRemainsAvailableAfterProductLoadFailureAndEmptyRestore \
  -derivedDataPath .context/DerivedData-restore-retry-red
```

Result: failed at the intended assertion: Retry Loading Purchase was absent
after the no-entitlement Restore result.

### GREEN

Changed the retry visibility condition from an exact
`.productLoadFailed`-state check to `product == nil && !isTransacting`.

Focused paywall UI suite command:

```sh
rtk xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=<owned simulator UUID>' \
  -only-testing:HangTenUITests/WorkoutPaywallUITests \
  -derivedDataPath .context/DerivedData-restore-retry-verify
```

Result: exit 0. This includes the new no-entitlement Restore regression and
the existing transient product-load retry test, which confirms retry makes Buy
available without launching Session.

## Files changed

- `HangTen/Views/WorkoutAccessGate.swift`
- `HangTenUITests/WorkoutPaywallUITests.swift`

## Cleanup

Each run created only a simulator named with the required
`Hang Ten Conductor fearless-swan ` prefix and registered its UUID before
testing. The final cleanup check confirmed the owned and pending manifests
were both 0 bytes and no matching test simulator remained. The known created
UUIDs included `D0AF1B1E-6AE3-46F1-82A3-55303F015308` and
`C636C87E-0A3A-4C47-AB74-AC7070EDA323`; temporary DerivedData directories
were removed by the cleanup lifecycle.

## Concerns

No live StoreKit test guards or StoreKit semantics were changed. The focused
UI test runs emitted the pre-existing Xcode DVT device build-number warning.

## Test-only completion round

The review's concern is covered without changing `PurchaseManager.prepare()`:
retry is permitted to recheck a current verified StoreKit entitlement, which
is validation of existing access rather than granting access. No production
code was modified in this round.

- Extended `testRetryRemainsAvailableAfterProductLoadFailureAndEmptyRestore`
  to assert retry is enabled, tap it after the no-entitlement Restore result,
  and verify the localized `Unlock for $2.99` Buy action becomes enabled while
  Session remains closed.
- Added
  `testRetryRemainsHittableAfterProductLoadFailureAndRestoreFailure`, which
  forces Restore to fail after the metadata-load failure, verifies retry is
  present and enabled, taps it, and confirms product metadata recovers without
  launching Session.

Command:

```sh
rtk xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=F85E7391-DACF-4117-8AF5-9406996E8480' \
  -only-testing:HangTenUITests/WorkoutPaywallUITests \
  -derivedDataPath .context/DerivedData-restore-retry-completion
```

Result: exit 0. The tests were added against an already-correct production
predicate, so the test-only round had no legitimate RED production failure;
the new forced restore-failure branch passed without a production edit.

Cleanup: `F85E7391-DACF-4117-8AF5-9406996E8480`
(`Hang Ten Conductor fearless-swan restore-retry-completion`) was deleted and
verified absent. The owned and pending simulator manifests are both 0 bytes,
and the temporary DerivedData directory was removed.
