# Hang Ten Android Platform-Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task-by-task with a fresh implementer and review gate.

**Goal:** Add Android equivalents for all iOS platform integrations while retaining canonical content fidelity.

**Architecture:** Testable Kotlin adapters isolate Play Billing, Health Connect, BLE, secure GitHub sync, and diagnostics from Compose. They consume the existing workout/content contracts and surface platform-neutral states to the completed coach UI.

**Tech Stack:** Kotlin, Compose, Play Billing 9.1.0, Health Connect 1.1.0, Android BLE, AndroidX Security/DataStore, OkHttp, Amplitude Android, Sentry Android.

**Spec:** `docs/superpowers/specs/2026-08-29-android-platform-parity-design.md`

## Global Constraints

- Preserve portable source data exactly; do not invent instructions, hold metadata, sensor calibration, or canonical geometry.
- Platform permissions are user initiated; unavailable/denied adapters leave the core coach usable.
- A completed Play purchase is acknowledged before entitlement is retained; pending/cancelled transactions do not unlock.
- Health records use stable client record IDs and versioned notes; no launch-time permission prompt.
- BLE transport uses Android runtime permissions only after Connect sensor and retains deterministic test transport coverage.
- GitHub credentials use encrypted Android storage, HTTPS only, and no client secret/PAT is bundled.
- Test behavior first; configuration-only changes use lint/parser/build validation.

---

### Task 1: Add lifetime Play Billing access

**Files:** Create `Android/app/src/main/java/com/hangten/android/billing/PlayBillingClient.kt`, `PurchaseManager.kt`; test `Android/app/src/test/java/com/hangten/android/billing/PurchaseManagerTest.kt`; modify `Android/app/build.gradle.kts`, `WorkoutAccessGate` and Settings purchase UI.

**Interfaces:** `PurchaseClient.load(id)`, `purchase(activity,id)`, `restore()`, and `updates`; `PurchaseManager.prepare/purchase/restore` mirror iOS state. Product ID is `com.hangten.training.lifetime`.

- [ ] Write failing tests for purchased unlock + acknowledgement, pending/no unlock, revoke, restore, and product failure.
- [ ] Run `rtk ./Android/gradlew -p Android :app:testDebugUnitTest --tests '*PurchaseManagerTest'` and record unresolved-symbol failure.
- [ ] Implement adapter with `enablePendingPurchases`, one-time product query, purchased-only acknowledgement, and lifecycle update listener.
- [ ] Wire the existing access gate and restore/purchase UI without displaying an unavailable product as purchasable.
- [ ] Run focused/full unit suite, lint, emulator access-gate flow, and Debug APK; commit.

### Task 2: Add Health Connect workout write/read reconciliation

**Files:** Create `health/HealthConnectService.kt`, `HealthViewModel.kt`; test `health/HealthConnectServiceTest.kt`; modify manifest, Settings, completed-session handoff, and build dependencies.

**Interfaces:** `WorkoutHealthStore.requestAuthorization`, `saveCompletedWorkout`, `fetchHangTenWorkouts`; states are unavailable/notDetermined/denied/authorized.

- [ ] Write failing tests for explicit permission flow, stable client record ID, versioned notes, denied fallback, and read reconciliation.
- [ ] Implement Health Connect adapter and manifest permissions using `ExerciseSessionRecord` strength training; preserve local completion on write failure.
- [ ] Wire Connect Health only to visible user action and History reconciliation; test emulator fake client and lint/build; commit.

### Task 3: Port BLE force-sensor adapters and measured workout recording

**Files:** Create `sensors/` transport, protocol, recorder, and settings files; test protocol/transport/recorder suites; modify workout completion and Settings UI/manifest.

- [ ] Port iOS-reviewed Motherboard, Progressor, and PitchSix protocol state machines with Kotlin tests first, including fragments, calibration, tare, threshold debounce, merge gaps, and 20,000-measurement cap.
- [ ] Implement Android BLE scan/connect/notification transport with user-initiated permission flow and deterministic fake transport.
- [ ] Add sensor settings/meter and measured activity persistence; run unit/lint/emulator suites and document physical-device release tests; commit.

### Task 4: Add local board editor and secure GitHub device-flow sync

**Files:** Create `editor/` store, canvas, validator, sync client, encrypted token store, and screens; test editor/sync/validator suites; modify Settings/navigation/build config.

- [ ] Write failing tests for direct geometry edits, save validation, device-flow expiry/slowdown/cancellation, conflict handling, and only-whitelisted package paths.
- [ ] Implement explicit path editing using saved canonical paths; no generated geometry; validate `board.json` before atomically replacing it.
- [ ] Implement encrypted credential storage and GitHub HTTPS device flow/branch/pull/push behavior with public client ID only; add UI and emulator tests; commit.

### Task 5: Add telemetry/diagnostics, full verification, and release documentation

**Files:** Create `telemetry/` composition/adapters/tests; modify app composition, CI, release docs, and README.

- [ ] Write failing event mapping/no-op tests against iOS event names/properties.
- [ ] Implement optional Amplitude/Sentry adapters; missing keys are no-op and no personal workout content is transmitted.
- [ ] Expand CI Android suites, run comprehensive Gradle/lint/emulator checks, update physical-device Play/BLE/Health release checklist, conduct final code review, and commit.
