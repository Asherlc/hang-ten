# Hang Ten Android Platform-Parity Design

## Goal

Bring the Android coach to functional parity with iOS for purchase access,
health history, live force sensors, editable GitHub-backed board packages, and
production diagnostics without changing canonical content formats.

## Boundaries

Android remains Kotlin/Compose. It consumes the same board/plan/audio assets,
workout timeline, canonical paths, and source-linked instructions as iOS.
Platform SDKs sit behind testable interfaces. No Android component may invent
hold geometry, sensor calibration, training instructions, or plan fields.

## Purchase access

`com.hangten.training.lifetime` is a Google Play one-time product. A
`BillingClient` adapter loads product details, observes purchases, grants the
entitlement only for `PURCHASED` transactions, acknowledges completed purchases,
recognizes pending/cancelled/failed states, and restores through purchase
queries. The existing free-workout gate consumes a platform-neutral entitlement
state. Play testing is an external operator validation; no release credential
is bundled.

## Health Connect

An explicit Connect Health action requests only exercise read/write permissions.
Completed sessions write `ExerciseSessionRecord` records with stable client
record IDs, title/notes containing board and plan identity, start/end wall time,
and strength-training activity type. The adapter reads its own Hang Ten records
for history reconciliation, never prompts on app launch, keeps local history
when unavailable/denied, and reports user-visible errors without losing a local
completion. Health Connect has no direct custom-metadata equivalent to HealthKit;
the Android record's notes use versioned JSON for activity segments.

## BLE force sensors

Android uses Bluetooth LE scan/connect/notification adapters behind the existing
force-sensor protocol parsers. Permission requests occur only after Connect
sensor. The same calibrated Motherboard lifecycle, Progressor/PitchSix profiles,
tare, force conversion, thresholds, and measurement truncation semantics are
ported from the reviewed iOS protocol models. Deterministic fake transports
drive tests; physical-device validation remains required before public release.

## Board editing and GitHub sync

The Android editor opens a local copy of a board package, directly edits
canonical JSON geometry through explicit gestures, validates before saving, and
renders/highlights/hit-tests the same saved paths. GitHub device authorization
uses the existing public client ID, an Android encrypted credential store, HTTPS
only, cancellation/expiry/poll interval handling, branch creation, conflict
checks, pull, and commit/push of `board.json` and its referenced image. It never
ships a GitHub client secret or personal access token.

## Diagnostics and verification

Analytics and diagnostics are no-ops without configured keys. Configured builds
use Amplitude Android and Sentry Android through abstractions matching iOS event
names/properties. CI covers all adapter unit suites, emulator UI flows, lint,
and release AAB build. Play Console purchase/Health Connect/BLE physical-device
checks are documented release gates, not simulated proof.
