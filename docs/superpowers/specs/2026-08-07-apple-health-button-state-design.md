# Apple Health Button State Design

## Goal

Hide the `Connect Apple Health` action whenever HealthKit reports that Hang Ten already has workout authorization, including when the HealthKit history query returns no accepted Hang Ten workouts.

## Root cause

`AppStore.shouldShowConnectAppleHealth` currently combines three different concerns:

1. the current HealthKit sharing authorization state;
2. whether Hang Ten has persisted that the user requested history synchronization; and
3. whether the latest HealthKit history snapshot is empty.

The third condition was added as a conservative recovery action for an ambiguous empty HealthKit read. Because it is evaluated even when `healthAuthorizationState == .authorized`, the Progress card can display `Connect Apple Health` while its status pill says `Connected`.

## Approved behavior

The current `HealthAuthorizationState` is the source of truth for the connection action:

| Authorization state | Health action |
| --- | --- |
| `.notDetermined` | Show `Connect Apple Health` |
| `.authorized` | Do not show `Connect Apple Health`, regardless of history contents or the persisted sync-request flag |
| `.denied` | Keep `Open app settings` |
| `.unavailable` | Show no action |

The existing local-fallback behavior remains unchanged: if history is still represented by local fallback, the card may offer `Open app settings` so the user can manage Health permissions. This change only removes the misleading Connect action from an authorized state.

If `refreshHealthAuthorization` observes `.authorized` while the persisted
history-sync request flag is false, it persists the flag and enables HealthKit
sync without prompting, then runs the existing history refresh/import path.
This reconciliation does not change the authorization/button contract above:
the current authorization state remains authoritative, and `.authorized` still
hides `Connect Apple Health`.

## Implementation

- Change `AppStore.shouldShowConnectAppleHealth` so it is true only for `.notDetermined`.
- In `refreshHealthAuthorization`, reconcile an authorized state with a missing request flag by persisting the flag and enabling HealthKit sync without prompting before refreshing/importing history.
- Keep `healthAction` in `RootView` unchanged; it already delegates Connect visibility to the AppStore property and handles denied/local-fallback settings separately.
- Update `HangTenTests/AppStoreTests.swift` with a regression assertion that an authorized state with an empty HealthKit history does not show Connect. Also cover an authorized state without the persisted request flag so the current authorization state remains authoritative.
- Update the Apple Health runtime and simulator-validation documentation to remove the old instruction to keep Connect available after an authorized empty query.

## Verification

The implementation must follow a red-green TDD cycle:

1. run the focused AppStore regression test before the production change and observe the expected failure;
2. make the minimal AppStore change;
3. rerun the focused AppStore tests;
4. run the complete HangTen test suite or the repository's documented equivalent;
5. inspect the final diff for scope and documentation consistency.

No HealthKit API, persistence format, authorization request flow, or unrelated UI behavior changes are required.
