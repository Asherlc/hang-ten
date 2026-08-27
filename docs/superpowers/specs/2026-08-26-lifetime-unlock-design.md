# Lifetime Unlock Design

## Goal

Let every user save two completed workouts for free. Before a third workout can
start, require a one-time $2.99 lifetime unlock that is restorable through the
App Store.

## Scope and constraints

- Product type: StoreKit 2 non-consumable, product ID
  `com.hangten.training.lifetime`.
- Storefront price: $2.99 (configured in App Store Connect; the app displays
  StoreKit's localized product price rather than hard-coding a currency).
- A free credit is consumed only after the user presses **Save session** for a
  completed routine. Ending or discarding a workout never consumes a credit.
- The first two completed-and-saved workouts remain available without an
  entitlement. The third and every later start is gated until a verified
  lifetime entitlement exists.
- Existing users start with two free credits, irrespective of historical
  workout data, so the new monetization model does not retroactively lock
  people out.
- The gate applies wherever a `WorkoutView` can be launched, including the
  featured-plan path, plan details, and DEBUG review destinations. It does not
  interrupt a workout already in progress.
- Purchase, restore, pending, cancellation, and verification failures must be
  represented in the UI without granting access until StoreKit verifies an
  entitlement.

## Architecture

Add a focused `PurchaseManager` observable object backed by StoreKit 2. It
owns the verified lifetime entitlement, product loading, purchase/restore
state, and transaction-update observation. A small `WorkoutAccessStore` owns
the persisted number of saved free workouts and exposes a pure decision API
for whether a workout may start. Keeping the counter independent from
`WorkoutSessionStore` prevents history imports, HealthKit sync, and deletion
of old records from changing purchased access.

`HangTenApp` creates both services and injects them into `AppStore`.
`AppStore` combines the two services into a `WorkoutAccess` view state and
increments the counter exactly once after the existing successful Save session
path records the workout. Launch surfaces ask `AppStore` for access instead of
constructing `WorkoutView` directly. When access is locked, they present a
single paywall sheet. A successful purchase or restore dismisses the sheet and
continues with the pending workout launch.

## Data flow

1. At launch, `PurchaseManager` begins StoreKit transaction observation and
   refreshes `Transaction.currentEntitlements` for
   `com.hangten.training.lifetime`.
2. A launch request evaluates the access decision:
   - verified entitlement: launch;
   - fewer than two saved free workouts: launch;
   - otherwise: retain the requested plan and show the paywall.
3. The paywall loads the non-consumable product, displays its localized price,
   and offers Buy and Restore Purchases actions.
4. A verified purchased or restored transaction marks the entitlement active,
   finishes the transaction, dismisses the paywall, and launches the retained
   plan. A pending/cancelled/error result remains on the paywall with accurate
   status copy.
5. When **Save session** succeeds, `AppStore` records one free completion only
   when no verified entitlement exists and fewer than two credits have already
   been used. Repeated taps are protected by the existing one-save session
   guard and an idempotent access-store update.

## UI

The paywall is a SwiftUI sheet consistent with Hang Ten's existing card and
type styles. It includes:

- title: “Unlock Hang Ten”;
- body: “You’ve completed your 2 free workouts. Unlock unlimited workouts for
  a one-time purchase.”;
- a purchase button labelled with the localized StoreKit price, for example
  “Unlock for $2.99”;
- a **Restore Purchases** button;
- an activity indicator while StoreKit is loading or transacting; and
- concise inline status for pending, failed, and cancelled transactions.

The sheet is dismissible. Dismissing it leaves the user on the originating
screen and does not start a workout.

## Testing and validation

Unit tests cover the access decision at zero, one, and two saved workouts;
the lifetime-entitlement override; persistence; and idempotent credit use.
`AppStore` tests prove a saved third-free-session is impossible and that
completion consumption occurs only after a save. StoreKit-facing tests use a
protocol-backed fake to cover verified purchase, cancellation, pending, error,
and restore outcomes. UI tests cover the locked launch path, paywall copy,
restore affordance, and automatic continuation after a successful fake
purchase.

Before release, create the matching non-consumable in App Store Connect for
the existing `com.hangten.training` app, set its price to $2.99, add it to the
release, and exercise purchase and restore through a StoreKit configuration or
Sandbox tester. The production product ID must match the literal above.
