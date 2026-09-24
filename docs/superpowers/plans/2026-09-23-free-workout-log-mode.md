# Free Workout Log Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace timeline-driven free workout mode with a Strong-style live set log: empty/template start, per-set logging, guided or manual hangs, auto rest timer, local history + named templates.

**Architecture:** New `FreeWorkoutLog` domain (exercises + set rows) with dedicated active/history/template stores. Session UI is log-centric; guided hang is an overlay that completes a set. Rest is a timer, not a step. Do not drive free mode through `WorkoutTimeline`. Reuse hold resolution, board map, countdown audio, and HealthKit session bounds.

**Spec:** [`docs/superpowers/specs/2026-09-23-free-workout-log-mode-design.md`](../specs/2026-09-23-free-workout-log-mode-design.md)  
**Supersedes plan:** [`2026-09-22-free-workout-mode.md`](2026-09-22-free-workout-mode.md)

**Tech Stack:** Swift, SwiftUI, XCTest / XCUITest, `xcodebuild`, workspace-owned simulator per repo conventions.

## Global constraints

- One active free log at a time; persist on every mutation.
- Finish requires ≥1 completed set to write history; otherwise discard only.
- Templates and history are log-shaped; do not route through `CustomRoutineDefinition` for v1.
- Hang sets support guided + manual; pull-ups are mark-done only (no work countdown).
- Default rest 180s; per-exercise `restAfterSeconds`.
- Put build/test artifacts under `.context`; use workspace-owned simulators; clean up owned resources.
- Each implementation task → fresh subagent + review checkpoint (per `AGENTS.md`).
- Keep iOS 17+; no new third-party deps.

## File map

| File | Change | Responsibility |
|------|--------|----------------|
| `HangTen/Models/FreeWorkoutLog.swift` | Create | `FreeWorkoutLog`, `FreeExercise`, `FreeSet`, hold selection reuse, mutations, template clone, draft migration |
| `HangTen/Models/FreeWorkoutLogStore.swift` | Create | Active log, history, template persistence (UserDefaults or Application Support JSON) |
| `HangTen/Models/FreeWorkoutRestTimer.swift` | Create | Rest countdown state: start/skip/adjust/dismiss |
| `HangTen/Views/FreeWorkoutLogSessionView.swift` | Create | Live log UI + finish + resume entry |
| `HangTen/Views/FreeWorkoutGuidedHangView.swift` | Create | Guided hang overlay |
| `HangTen/Views/FreeWorkoutAddExerciseSheet.swift` | Create | Hang/Pull-up + hold picker |
| `HangTen/Views/FreeWorkoutLogSetSheet.swift` | Create | Manual hang / pull-up log |
| `HangTen/Views/FreeWorkoutStartSheet.swift` | Create | Empty / Last / Template (+ resume-or-discard) |
| `HangTen/Views/TrainView.swift` | Modify | Wire Start Free Workout → new start flow |
| `HangTen/Views/FreeWorkoutBuilderView.swift` | Remove or gut | No longer primary entry |
| `HangTen/Views/FreeWorkoutSessionView.swift` | Remove or gut | Timeline session retired for free mode |
| `HangTen/Models/FreeWorkoutDraft.swift` | Keep briefly | Migration source only; delete after migrate helpers land |
| `HangTen/Models/FreeWorkoutSaver.swift` | Retire | Replaced by template store |
| `HangTenTests/FreeWorkoutLogTests.swift` | Create | Model + store + migration + rest timer |
| `HangTenUITests/FreeWorkoutLogUITests.swift` | Create | Entry → add set → finish smoke |
| `HangTen.xcodeproj/project.pbxproj` | Modify | Register new sources |

---

### Task 1: Core log model

**Files:**
- Create: `HangTen/Models/FreeWorkoutLog.swift`
- Create: `HangTenTests/FreeWorkoutLogTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Behaviors:**
- Types per spec (`hang` / `pullUp`, set fields, optional tag/mode).
- Mutations: add/remove/reorder exercise; add set (prefill from previous set); update set fields; complete set (`completedAt`, `mode`); uncomplete.
- `templateClone()` / `uncheckedClone()` clears all `completedAt` and regenerates IDs for a new session.
- `finishedLog()` keeps only completed sets; drops empty exercises.
- Default `restAfterSeconds = 180`.

- [x] **Step 1:** Register test target + write failing tests for prefill-from-previous-set, clone clears completion, finishedLog drops unchecked.
- [x] **Step 2:** Implement model until tests pass.
- [x] **Step 3:** Run focused `FreeWorkoutLogTests`.

---

### Task 2: Persistence stores

**Files:**
- Create: `HangTen/Models/FreeWorkoutLogStore.swift`
- Modify: `HangTenTests/FreeWorkoutLogTests.swift`

**Behaviors:**
- `ActiveFreeWorkoutStore`: load/save/clear single active log; write-through API.
- `FreeWorkoutHistoryStore`: append finished logs; `latest` for last-workout; corruption → empty, don’t crash.
- `FreeWorkoutTemplateStore`: CRUD named templates (`id`, `name`, `log` shape with unchecked sets).
- Keys/paths versioned (`…v1`); DEBUG review env can reset like today’s draft store.

- [x] **Step 1:** Failing tests for round-trip active, history latest, template CRUD, corrupt payload recovery.
- [x] **Step 2:** Implement stores.
- [x] **Step 3:** Focused tests green.

---

### Task 3: Draft migration

**Files:**
- Modify: `HangTen/Models/FreeWorkoutLog.swift` (or `FreeWorkoutDraftMigration.swift`)
- Modify: `HangTenTests/FreeWorkoutLogTests.swift`

**Behaviors:**
- `FreeWorkoutLog.migrating(from: FreeWorkoutDraft) -> FreeWorkoutLog?`
- Hang/pull → one unchecked set each (duration/load/reps from draft); rest exercises dropped; map work+rest into set duration + exercise `restAfterSeconds` when rest was present.
- One-shot: if no history latest and draft exists, seed history or “last workout” candidate; clear or leave draft key documented.

- [x] **Step 1:** Failing migration tests (rest dropped; hang/pull mapped).
- [x] **Step 2:** Implement + run tests.

---

### Task 4: Rest timer

**Files:**
- Create: `HangTen/Models/FreeWorkoutRestTimer.swift`
- Modify: `HangTenTests/FreeWorkoutLogTests.swift`

**Behaviors:**
- Start with duration; remaining ticks; skip → inactive; ±30 / +60 clamp at 0; dismiss.
- Pure model preferred (clock injectable) for tests.

- [x] **Step 1:** Failing tests for start/skip/adjust/dismiss.
- [x] **Step 2:** Implement + green.

---

### Task 5: Start sheet + Train wiring

**Files:**
- Create: `HangTen/Views/FreeWorkoutStartSheet.swift`
- Modify: `HangTen/Views/TrainView.swift`
- Create stub or minimal: `HangTen/Views/FreeWorkoutLogSessionView.swift` (empty log shell OK)

**Behaviors:**
- Train “Start Free Workout” presents start sheet.
- If active log exists → Resume / Discard.
- Empty / Last (disabled if none) / Template picker → creates active log → pushes/presents `FreeWorkoutLogSessionView`.
- Run migration hook once on appear if needed.

- [x] **Step 1:** Wire entry; compile.
- [x] **Step 2:** Manual/UI smoke: button opens start choices.

---

### Task 6: Live log session UI

**Files:**
- Create/expand: `HangTen/Views/FreeWorkoutLogSessionView.swift`
- Create: `HangTen/Views/FreeWorkoutAddExerciseSheet.swift`
- Modify: active store write-through from all mutations

**Behaviors:**
- Exercise list, set rows, focus next unchecked, board map highlight via existing resolvers + selected board.
- Add Set / Add Exercise / delete / reorder.
- Inline edit weight/duration/reps.
- Rest bar bound to rest timer; start rest on set complete.
- Finish button → confirm → Task 8 hook (can stub save).
- Accessibility ids: `freeWorkout.log`, `freeWorkout.addExercise`, etc.

- [x] **Step 1:** Build UI against store.
- [x] **Step 2:** Unit/UI: add exercise + set persists across relaunch of view model/store.

---

### Task 7: Guided hang + manual log sheets

**Files:**
- Create: `HangTen/Views/FreeWorkoutGuidedHangView.swift`
- Create: `HangTen/Views/FreeWorkoutLogSetSheet.swift`

**Behaviors:**
- Hang focused set: Start Set → overlay countdown; audio via `CountdownAudioScheduler`; Complete early / Cancel / auto-complete → mark set `mode: .guided`, start rest.
- Log Set → sheet for hang duration+weight or pull-up weight×reps → `mode: .manual`, start rest.
- Pull-up: Mark done on row without overlay.

- [x] **Step 1:** Implement overlay + sheets.
- [x] **Step 2:** Tests or UI test: cancel leaves unchecked; complete sets completedAt.

---

### Task 8: Finish → history, Health, template prompt

**Files:**
- Modify: `HangTen/Views/FreeWorkoutLogSessionView.swift`
- Modify: Health / `AppStore.markSessionComplete` (or equivalent) integration point used by current free session
- Retire save-as-custom-routine path for free mode

**Behaviors:**
- Validate ≥1 completed set.
- `finishedLog()` → history append; clear active.
- Derive pending/Health work segments from completed sets (hang duration; pull-ups as work markers with sensible duration if required by existing API).
- Alert: Save as Template? → name → template store.
- Discard path clears active without history.

- [x] **Step 1:** Finish happy path unit/integration test with history + template.
- [x] **Step 2:** Wire Health path; verify no regression for non-free plans.

---

### Task 9: Remove timeline free-mode path

**Files:**
- Remove or stub-out: `FreeWorkoutBuilderView`, `FreeWorkoutSessionView`, `FreeWorkoutSaver` usages from Train
- Keep migration reader for `FreeWorkoutDraft` until Task 3 done; then delete draft/saver if unused
- Update/replace `HangTenUITests/FreeWorkoutUITests.swift` → log flow
- Update old design/plan pointers already in specs

**Behaviors:**
- No user-reachable path into timeline free session.
- Tests updated; project builds.

- [x] **Step 1:** Delete/unreachable old UI; fix references.
- [x] **Step 2:** Full free-workout test slice green.

---

### Task 10: Validation

**Files:** `HangTenUITests/FreeWorkoutUITests.swift`, `HangTenTests/FreeWorkoutLogTests.swift` (process + deeper UI)

- [x] **Step 1:** Focused unit tests for log/store/rest/migration (`HangTenTests/FreeWorkoutLogTests`).
- [x] **Step 2:** UI smoke + deeper log flows on workspace-owned simulator per `validate-hang-ten-ios` skill:
  - Empty → add hang → mark complete → rest bar → Finish → confirm → Skip template → Last enabled
  - Guided hang Cancel leaves set unchecked (no rest bar); XCTSkip if overlay controls unavailable
  - Resume / discard-then-finish path
- [x] **Step 3:** Confirm acceptance criteria in the design spec (AC1–8); UI covers AC3–5 finish/rest/guided-cancel/resume; unit tests cover stores/migration/rest defaults.

---

## Test commands (adjust destination to owned simulator)

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=<OWNED_UDID>' \
  -only-testing:HangTenTests/FreeWorkoutLogTests
```

## Review checkpoints

After each task: fresh review subagent checks spec compliance (no timeline driver, rest not a step, hold on exercise, per-set load), test presence, and no orphaned free-builder entry points after Task 9.
