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
