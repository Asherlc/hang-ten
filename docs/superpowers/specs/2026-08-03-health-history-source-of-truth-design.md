# Hang Ten Health History Source of Truth Design

**Date:** 2026-08-03
**Status:** Approved design; implementation plan pending written-spec review

## Goal

Restore Hang Ten workout history when a person installs the app on another
phone by using Apple Health as the authoritative history store whenever its
workout data is usable, while retaining a local fallback when HealthKit is
unavailable or inaccessible.

The app imports only workouts that Hang Ten created. It does not import other
functional-strength workouts or attempt to infer that a workout belongs to
Hang Ten from its title alone.

## Existing context

Hang Ten currently writes completed routines as
`.functionalStrengthTraining` `HKWorkout` records. Each record contains the
standard `HKMetadataKeyWorkoutBrandName` value `Hang Ten` and the custom
`HangTen.PlanName` value. `AppStore` currently keeps `sessionsCompleted` and
`lastSessionTitle` only in memory, so a fresh process starts with an empty
progress history and the app does not request HealthKit read access.

The HealthKit capability, generated read/write usage descriptions, signed
simulator validation route, and user-initiated authorization card already
exist and should be preserved.

## Important HealthKit constraint

HealthKit treats read and write authorization separately. Apple intentionally
does not tell an app whether a person denied read access: a denied read query
appears as though no matching data exists. The implementation therefore cannot
make a literal, observable `if readAccessGranted` decision.

The app will use the following practical rule instead:

- A successful HealthKit query with readable Hang Ten workouts makes HealthKit
  authoritative for the displayed history.
- Local records that have not yet been reconciled with HealthKit remain visible
  as fallback/pending history.
- An empty or inaccessible HealthKit result falls back to local records. An
  empty result is acceptable both for a person with no Hang Ten history and for
  a person whose read access is hidden by HealthKit privacy.
- Once a later query exposes the corresponding HealthKit records, local
  fallback records are reconciled and removed.

This preserves the requested behavior without claiming knowledge that the
HealthKit API deliberately withholds.

## Approaches considered

### HealthKit-first with local pending fallback — selected

Persist a small local record before each completion, attempt the HealthKit
write, and query HealthKit for the authoritative history. Keep local records
only while they are pending, not yet confirmed by a HealthKit query, or needed
because HealthKit is unavailable. When authorization is later requested,
upload pending records, query again, reconcile by stable metadata, and remove
records confirmed in HealthKit.

This meets the restore requirement, protects sessions across failed writes, and
keeps HealthKit authoritative whenever the app can read it.

### Always mirror history locally and to HealthKit

Keep a permanent local copy and mirror HealthKit changes into it. This makes
the UI simpler but leaves two permanent sources of truth and creates conflict
rules for deletions and edits that the product does not need.

### HealthKit-only history

Skip local persistence and show only query results. This is simple, but loses a
completed session when permission is declined, HealthKit is temporarily
unavailable, or a write fails. It also cannot support the requested fallback.

## Architecture

### Workout history value types

Add a Codable local record with these fields:

- `id: UUID` — stable identifier shared with new HealthKit metadata;
- `planTitle: String`;
- `startDate: Date`;
- `endDate: Date`;
- `healthUploadAttempted: Bool` — prevents duplicate retries when a write
  succeeded but read access is currently hidden;
- `healthWorkoutUUID: UUID?` — optional confirmation identity from a completed
  HealthKit save.

Add a display model normalized from either a local record or an `HKWorkout`.
HealthKit-backed entries use the workout UUID as their identity; new records
also carry the local UUID in custom metadata. Historical Hang Ten workouts
without that new metadata remain importable through their existing brand and
plan metadata.

### Local fallback store

Create a focused `LocalWorkoutHistoryStore` that serializes the pending local
records as versioned JSON in `UserDefaults`. It must support loading, replacing
the complete record set, and removing reconciled IDs. Keep this store small and
replaceable so unit tests can use an in-memory implementation.

Local records are not a permanent mirror. They are durable fallback data and a
sync queue. A record is removed only after a matching HealthKit workout is
visible or after the app has a confirmed successful write and no local fallback
is needed for the current access state.

### HealthKit service

Extend `HealthKitService` to:

- request sharing and reading for `HKObjectType.workoutType()` in the existing
  user-initiated authorization flow;
- query all `HKWorkout` samples, then retain only workouts with activity type
  `.functionalStrengthTraining`, brand metadata exactly `Hang Ten`, and a
  non-empty `HangTen.PlanName` string;
- save a completed workout with the existing metadata plus
  `HangTen.SessionID` containing the local record UUID;
- return the saved workout or a typed error so the history coordinator can
  retain or reconcile the local record;
- keep reading independent from the write authorization status, because
  HealthKit does not expose read authorization through
  `authorizationStatus(for:)`.

The existing workout builder lifecycle and date safety remain unchanged:
begin at the session start, end at the log time or planned duration (whichever
comes first), and finish before reporting success.

### History coordinator and AppStore

Add a `WorkoutHistoryService` (or equivalent focused coordinator) that owns the
source-selection and reconciliation rules. It depends on `HealthKitService` and
`LocalWorkoutHistoryStore`; `AppStore` depends on the coordinator rather than
implementing HealthKit queries itself.

The coordinator exposes:

- the current sorted Hang Ten history;
- the derived session count and latest plan title used by existing Progress and
  Today cards;
- whether the current result is HealthKit-backed, local fallback, unavailable,
  or synchronizing;
- a user-facing synchronization error when a local record cannot be uploaded.

`AppStore.markSessionComplete` first persists a local record, then asks the
coordinator to save/synchronize it. It no longer increments an in-memory count
as an independent source of truth.

## Data flow

### App launch and Progress refresh

Do not prompt at launch. When Progress appears or becomes active:

1. Refresh the existing write authorization state.
2. If HealthKit is available and the authorization flow has been requested,
   query Hang Ten workouts.
3. Load pending local records.
4. Reconcile visible HealthKit records with local IDs and exact legacy matches
   of plan title, start date, and end date.
5. Upload unmatched local records when writing is authorized.
6. Query again after uploads and remove local records confirmed in HealthKit.
7. Publish the HealthKit-derived history when readable records are available;
   otherwise publish local fallback history.

The refresh must be idempotent. Reopening Progress must not create duplicate
HealthKit workouts or double-count a session.

### Completing a routine

1. Create a local record with a new UUID before starting the HealthKit write.
2. Attempt the existing HealthKit builder save with `HangTen.SessionID`.
3. On a successful save, keep enough local state to reconcile the returned
   workout UUID on the next refresh; do not count the workout separately in
   `AppStore`.
4. On a write error, retain the local record and surface that the session is
   stored locally and can be synchronized later.
5. Refresh the published history after the save attempt.

### Later authorization and migration

The visible Connect Apple Health action requests both read and write access.
After the request callback, run the same idempotent synchronization flow. Each
pending local record is uploaded at most once per confirmed write attempt.
Records are removed only when the HealthKit query exposes a matching
`HangTen.SessionID`, a stored HealthKit UUID, or an exact legacy match. If read
access remains hidden, local records stay available rather than being silently
discarded.

## User interface behavior

Keep the existing Progress layout and Health card, but make its progress values
come from the history coordinator instead of `sessionsCompleted` and
`lastSessionTitle`.

Use clear status copy:

- HealthKit-backed: “History synced from Apple Health.”
- Local fallback: “History stored on this device until Apple Health is
  connected.”
- Syncing: “Syncing Hang Ten history with Apple Health…”
- Write failure: explain that the session is saved locally and will retry.
- Health unavailable or not yet connected: retain the existing connection
  action and do not show a misleading zero as proof that no history exists.

The app must continue to request permission only after the user taps Connect
Apple Health. Returning to the app from Settings refreshes both the HealthKit
status and the history query.

## Error handling and privacy

- Never import workouts from another app merely because they use functional
  strength training.
- Treat an empty HealthKit result as ambiguous, not as proof of denied access.
- Keep HealthKit data on-device and do not add network synchronization.
- Preserve local records when HealthKit is unavailable, locked, restricted, or
  a save/query fails.
- Do not delete HealthKit workouts from the app.
- Keep `NSHealthShareUsageDescription` explicit that Hang Ten reads its workout
  history to restore progress, and retain the existing update description for
  writes.

## Testing and validation

### Unit tests

Add tests for:

- filtering only Hang Ten functional-strength workouts;
- rejecting other brands, missing plan metadata, and other activity types;
- normalizing legacy workouts without `HangTen.SessionID`;
- saving/loading local records;
- preserving a local record when HealthKit is unavailable or a write fails;
- migrating a pending local record exactly once;
- reconciling by session ID and by legacy title/date match;
- deriving count and latest title from HealthKit-backed history;
- falling back to local history for an empty/inaccessible HealthKit result;
- refresh idempotency and duplicate prevention.

Tests must use an injected HealthKit abstraction or value-level adapters; they
must not require a real HealthKit database.

### Simulator and device validation

Use the existing signed, workspace-specific simulator workflow. Validate:

- the revised read/write permission sheet and read usage text;
- local fallback after completing a short session without HealthKit access;
- HealthKit-backed count after granting access and saving a session;
- a refresh that does not double-count the saved workout;
- restoration after relaunching the app;
- Progress UI in portrait and landscape where the history/status copy is
  visible.

Simulator validation cannot prove real cross-device HealthKit migration. A
physical-device test must verify that Hang Ten workouts written on one device
are visible and imported after installing the app on another device using the
same HealthKit account.

## Documentation changes

Update `docs/IOS_RUNTIME_SERVICES.md` to document read access, HealthKit-first
history, the local fallback queue, metadata filters, and the privacy-driven
empty-result behavior. Update `docs/IOS_SIMULATOR_VALIDATION.md` with the
fallback, migration, and duplicate-prevention scenarios.
