# Free Workout Log Mode Design

**Status:** Approved 2026-09-23  
**Supersedes:** [`2026-09-22-free-workout-mode-design.md`](2026-09-22-free-workout-mode-design.md) (timeline-driven builder + session)

## Overview

Replace the current free-workout “build a plan, then run a countdown timeline” model with a Strong-style **live set log**: the workout starts empty (or from a template of unchecked rows), grows as the athlete performs sets, and uses a rest timer between sets rather than scheduled rest steps.

Hangs keep Hang Ten’s board highlighting and optional guided countdown; the same hang set can also be logged manually after the fact.

## Product decisions (locked)

| Decision | Choice |
|---|---|
| Mental model | Full Strong-style live log |
| Hang sets | Both guided countdown and manual log |
| Rest | Auto rest timer after each completed set (default 3:00, per-exercise override) |
| Templates | Last finished workout + named saved templates as unchecked rows |
| Exercise types (v1) | Hang + Pull-up only (no rest exercises) |
| Architecture | New log model + UI (do not drive free mode through `WorkoutTimeline`) |

## User stories

- As a climber, I want to start an empty workout and add hangs/pull-ups and sets as I go
- As a climber, I want set 1 at 30 lb and set 2 at 10 lb on the same hold without rewriting a plan
- As a climber, I want a guided hang countdown with board hold highlighting, or to type the hang in after I did it
- As a climber, I want a rest timer to start when I complete a set, and to dismiss when I start the next
- As a climber, I want last workout / saved templates to prefill unchecked rows
- As a climber, I want Finish to log history and optionally save a named template

## Data model

```
FreeWorkoutLog
├── id: UUID
├── startedAt: Date
├── boardID: String?
└── exercises: [FreeExercise]
    ├── id: UUID
    ├── type: hang | pullUp
    ├── title: String
    ├── holdSelection: FreeWorkoutHoldSelection   // hold on the exercise (v1)
    ├── restAfterSeconds: TimeInterval            // default 180
    └── sets: [FreeSet]
        ├── id: UUID
        ├── weightKGF: Double?                    // added load; varies per set
        ├── duration: TimeInterval?               // hang sets
        ├── reps: Int?                            // pull-up sets
        ├── tag: warmUp | drop | failure?         // optional v1
        ├── mode: guided | manual?                // how it was completed
        └── completedAt: Date?                    // nil = unchecked
```

### Invariants

- Hold lives on the exercise; weight / duration / reps live on the set (Strong parity: same exercise, different loads).
- Different hold → different exercise (or change the exercise’s hold for future sets).
- Rest is **not** a set or exercise; it is UI chrome driven by `restAfterSeconds`.
- One active log at a time, persisted on every mutation.
- Finished history stores completed sets only (`completedAt != nil`).

### Set lifecycle

```
REST/IDLE ──focus next unchecked set──▶ CONFIGURED
   ▲                                      │
   │         edit weight/duration/reps    ├── Start Set (hang guided)
   │         / hold inline                │      → RUNNING countdown
   │                                      │      → auto-complete → rest timer
   │                                      └── Log Set / Mark done
   └──── rest timer ◀───────────────────────── completes immediately → rest timer
```

- **Guided hang:** Start Set → countdown overlay + board highlight + audio → auto-✓ (or Complete early) → rest timer. Cancel leaves set unchecked.
- **Manual hang:** Log Set sheet (duration + weight) → ✓ → rest timer.
- **Pull-up:** configure weight × reps → Mark done / checkbox → rest timer (no work countdown).
- **Finish:** require ≥1 completed set to save history; empty active log can be discarded. Then optional Save as Template.

## Screens

### Entry (Train)

**Start Free Workout** opens the live log (not a pre-build sheet).

If an active log exists → Resume or Discard before starting Empty / Last / Template.

Start choices:

1. Empty
2. Last workout (most recent finished free log → unchecked copy)
3. Named template (from Favorites / Free Templates)

### Live log (main session)

- Header: title, elapsed time, Finish
- Scrollable exercises with set rows: `# | weight | duration|reps | ✓`
- Focused = next unchecked set; board map highlights that exercise’s hold
- `+ Add Set` prefills from previous set on that exercise
- `+ Add Exercise` → Hang or Pull-up → hold picker → one empty set
- Reorder / delete exercise via menu (v1: move up/down + delete)
- Rest bar when resting: remaining, Skip, −30 / +30 / +1m, full-screen toggle
- Starting next set dismisses rest

### Guided hang overlay

- Countdown, hold name, weight, board map
- Pause / Cancel / Complete early
- Reuses `CountdownAudioScheduler` and existing highlight resolvers

### Finish

1. Confirm finish
2. Persist to `FreeWorkoutHistoryStore` (completed sets only)
3. HealthKit / pending record: session bounds + work segments from completed hang/pull sets
4. Prompt Save as Template? → name → `FreeWorkoutTemplateStore`
5. Clear active log

## Templates & reuse

| Source | Behavior |
|---|---|
| Empty | Zero exercises |
| Last workout | Finished log → clone exercises/sets with `completedAt = nil` |
| Saved template | Named log shape; all unchecked |

- Template body = completed sets from the finished workout, tags preserved.
- Unchecked leftover rows at Finish are dropped from the template.
- Use `FreeWorkoutTemplateStore` (log-shaped). Do **not** force templates through `CustomRoutineDefinition` (cannot express per-set load variation without flattening).

### Migration from current free mode

- Convert last `FreeWorkoutDraftStore` draft once: hang/pull → exercises with one unchecked set each; drop rest exercises; map rest duration into `restAfterSeconds` when present.
- Do not migrate in-flight timeline sessions; discard or finish under the old path once.

## History mapping

| Store | Role |
|---|---|
| Active log persistence | Crash-safe in-progress log |
| `FreeWorkoutHistoryStore` | Finished free logs; last-workout source; future detail UI |
| Existing Health / pending path | Title + start/end + activity work segments |
| Thin `WorkoutHistoryEntry` list | Unchanged listing; free detail optional later |

Out of scope for v1: editing past free workouts in history UI.

## What we keep vs drop

| Keep / adapt | Stop using for free mode |
|---|---|
| Hold picker, `ContactResolver`, board map | `FreeWorkoutDraft` → `TrainingPlan` as session driver |
| Guided countdown audio | Rest-as-`WorkoutStep` in free drafts |
| HealthKit session save | Builder sheet as primary entry |
| Train “Start Free Workout” entry | Treating free workouts as long-lived `isFreeWorkout` timeline plans |

`TrainingPlan.isFreeWorkout` and timeline `updateStep` may remain for back-compat until the old session path is removed; new free mode does not depend on them.

## Out of scope (v1)

- Supersets / circuits
- RPE
- Plate / warm-up calculators
- Editing past free workouts
- Manufacturer `TrainingPlan`s as free-log templates
- Cloud sync
- Export template → custom guided routine (possible later)

## Acceptance criteria

1. Start Empty → add hang + pull-up → add multiple sets with different loads → complete mixed guided/manual → Finish → history + optional template
2. Last workout and named template prefill unchecked rows; completing sets does not mutate the template
3. Rest timer auto-starts on set complete; Skip / adjust work; dismissed by next set start
4. Guided hang shows board highlight + audio; Cancel leaves set unchecked
5. Active log survives kill/relaunch via Resume
6. Crash mid-set does not lose already-completed sets
7. Migrated last draft (if any) appears as last-workout/template-compatible unchecked rows without rest exercises
8. Works board-agnostic with generic holds; with a board selected, exact holds highlight

## Risks

| Risk | Mitigation |
|---|---|
| Dual free-mode paths confuse users during transition | Single entry opens new log UI; remove builder→timeline path in the same redesign ship |
| Health segments less precise without timeline | Derive work segments only from completed sets’ duration/reps timestamps |
| Template vs custom routine confusion | Name UI “Template”; keep out of `CustomRoutineStore` |
| Scope creep (tags, supersets) | Tags optional; supersets explicitly out |

## Testing strategy

- Unit: log mutations (add exercise/set, complete, prefill from previous set, template clone clears `completedAt`)
- Unit: active / history / template store round-trips + corruption recovery
- Unit: draft migration (rest dropped, hang/pull → one set)
- Unit: rest timer default and per-exercise duration
- UI: Train entry → empty log → add set → finish (`FreeWorkoutUITests`)
- UI: hang mark-complete → rest bar → Finish → Skip template → Last enabled
- UI: guided hang overlay complete / cancel (cancel leaves set unchecked; no rest bar)
- UI: Resume after close; discard without completed sets keeps Last locked
- Integration: Finish → history → Start from last workout
