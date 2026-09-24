# Free Workout Mode Design

> **Superseded 2026-09-23** by [`2026-09-23-free-workout-log-mode-design.md`](2026-09-23-free-workout-log-mode-design.md).
> This document described the shipped timeline-driven builder + session (PR-era free mode). The approved redesign is a Strong-style live set log.

## Overview
Add a "free workout" mode similar to the Strong app — build custom hangboard workouts on-the-fly, run them with timer-driven guidance plus manual override, edit weight/time/reps during the session, and optionally save as a reusable plan.

## User Stories
- As a climber, I want to create a custom workout by adding hangs, pull-ups, and rests with specific holds, durations, and weights
- As a climber, I want to adjust weight, time, or reps mid-workout without stopping the timer
- As a climber, I want the session to use board-specific hold highlighting when available, falling back to generic hold types
- As a climber, I want my previous free workout to pre-fill as a starting template
- As a climber, I want to save the workout as a plan for future use or just log it to history

## Architecture: Extend Existing Models

Reuse existing types with minimal additions:
- `TrainingPlan` — add `isFreeWorkout: Bool` flag
- `WorkoutStep` — already supports all needed fields (duration, timedWorkDuration, externalLoadKGF, repetitions, gripType, fingerConfiguration, handUse, side, action, segments)
- `WorkoutTimeline` — add `updateStep(stepID: String, newValues: StepUpdates)` for live edits
- `ContactResolver` — resolves board holds from `ContactRequirement`
- `WorkoutHistoryService` / `LocalWorkoutHistoryStore` — records completed sessions
- `CustomRoutineStore` — saves as reusable plan (provenance: .custom)

## Components

### 1. FreeWorkoutBuilderView (New)
**Entry point**: "Start Free Workout" button in TrainView (Favorites section)

**Features**:
- Exercise list: reorderable, deletable, add Hang / Pull-up / Rest
- Per-exercise editor:
  - Hold picker: board holds (when board selected) + generic types (Edge 20mm, Jug, Sloper, Pocket 3-finger, Pinch)
  - Duration (work + rest)
  - Weight (for loaded hangs/pull-ups)
  - Reps (for pull-ups, loaded lifts)
  - Grip type, finger configuration
  - Hand use (single/double/either) + side
- Auto-fill from last free workout + history suggestions (most recent values per exercise type)
- "Save as Plan" toggle
- "Start Workout" → creates `TrainingPlan(isFreeWorkout: true)` → pushes `FreeWorkoutSessionView`

### 2. FreeWorkoutSessionView (New)
**Reuses**: `WorkoutTimeline`, `MotherboardWorkoutPreparationView`, `WorkoutBoardCue`, `WorkoutHoldCue`

**Layout**:
- Top: Current set card (exercise, hold, target duration/weight/reps)
- Middle: Board view with hold highlighting (via `ContactResolver`)
- Bottom: Quick adjust bar + main controls

**Live editing**:
- Tap current set card → inline editor sheet (modify duration, weight, reps, hold)
- Quick adjust bar (persistent):
  - `[-] [+] Weight` (loaded exercises)
  - `[-] [+] Time` (timed segments)
  - `[-] [+] Reps` (rep-based)
- Changes call `WorkoutTimeline.updateStep(stepID, newValues)` → recalculates offsets
- Manual override: "Complete Set" button (mark done early), "Skip" (skip to next)

**Timer behavior**:
- Countdown from `WorkoutTimeline` (work + rest phases)
- Audio cues via existing `CountdownAudioScheduler`
- Hold preview during rest (next work step)
- `WorkoutLiftCompletion` tracks loaded lift reps

### 3. TrainView Updates
- Add "Start Free Workout" button in Favorites section (or new section when empty)
- If free workout saved as plan → appears in Favorites with `provenance: .custom`, `boardID: nil`

### 4. Post-Session
On completion:
- Record to `WorkoutHistoryService` with **actual executed values**
- If "Save as Plan" enabled:
  - Save to `CustomRoutineStore` as `TrainingPlan(provenance: .custom, boardID: nil)`
  - Appears in Favorites for future use
- Option: save **template** (original planned values) or **executed** (actual values) — user choice dialog

## Data Model Additions

```swift
// TrainingPlan.swift
struct TrainingPlan {
    // ... existing fields
    let isFreeWorkout: Bool = false  // new
}

// WorkoutTimeline.swift
struct StepUpdates {
    var duration: TimeInterval?
    var timedWorkDuration: TimeInterval?
    var externalLoadKGF: Double?
    var repetitions: Int?
    var holdID: String?  // for board hold changes
}

extension WorkoutTimeline {
    mutating func updateStep(_ stepID: String, _ updates: StepUpdates) {
        // Find step, apply updates, recalculate startOffsets for this and subsequent steps
    }
}
```

## Integration Points

| Component | Reused | Extended |
|-----------|--------|----------|
| `TrainingPlan` | ✅ | `isFreeWorkout` flag |
| `WorkoutStep` | ✅ | All fields already exist |
| `WorkoutSegment` | ✅ | Timing modes (.fixed/.stopwatch/.undefined) |
| `WorkoutTimeline` | ✅ | `updateStep()` method |
| `ContactResolver` | ✅ | Resolves board holds for highlighting |
| `WorkoutHistoryService` | ✅ | Records free workout sessions |
| `CustomRoutineStore` | ✅ | Saves as custom plan |
| `MotherboardWorkoutPreparationView` | ✅ | Pre-workout tare/bodyweight |
| `CountdownAudioScheduler` | ✅ | Audio cues |

## Acceptance Criteria

1. **Builder**: Can create workout with 3+ exercises (hang, pull-up, rest), each with hold, duration, weight, reps
2. **Auto-fill**: Last free workout values pre-fill builder
3. **Session**: Timer runs, board highlights correct holds, audio cues play
4. **Live edit**: Tap current set → edit duration/weight/reps → timeline updates immediately
5. **Quick adjust**: +/- buttons modify current set values in real-time
6. **Manual override**: Can mark set complete early, skip to next
7. **History**: Session logs to WorkoutHistory with actual values used
8. **Save as plan**: Optional save creates custom plan in Favorites
9. **Board-agnostic**: Works without board selected (generic holds only)

## Out of Scope
- Supersets/circuits (single exercise at a time)
- Rest timer customization per-exercise (uses step rest duration)
- Plate calculator (user enters total weight)
- Cloud sync of free workouts (local only for v1)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Timeline mutation during active workout | `updateStep` only affects current + future steps; past steps immutable |
| Board hold resolution mid-workout | Hold changes re-resolve via `ContactResolver` on next highlight cycle |
| Data loss on crash | Auto-save session state to `WorkoutSessionStore` every 5s |
| Confusion: template vs executed save | Clear dialog: "Save what you planned" vs "Save what you did" |

## File Structure (New/Modified)

```
HangTen/Views/
├── FreeWorkoutBuilderView.swift          (new)
├── FreeWorkoutSessionView.swift          (new)
├── FreeWorkoutExerciseEditor.swift       (new, shared component)
├── FreeWorkoutQuickAdjustBar.swift       (new)
└── TrainView.swift                       (modified: add entry button)

HangTen/Models/
├── TrainingModels.swift                  (modified: isFreeWorkout flag)
├── WorkoutTimeline.swift                 (modified: updateStep method)
├── FreeWorkoutSessionState.swift         (new: builder draft state)
└── WorkoutSessionStore.swift             (new: auto-save session state)

HangTen/Services/ (or Models/)
├── WorkoutHistoryService.swift           (existing: records free workouts)
└── CustomRoutineStore.swift              (existing: saves custom plans)
```

## Testing Strategy

- Unit: `WorkoutTimeline.updateStep()` recalculates offsets correctly
- Unit: Builder creates valid `TrainingPlan` with all exercise types
- UI: Builder → Session flow with live edits
- UI: Quick adjust bar updates timeline in real-time
- Integration: Session → History → CustomRoutineStore round-trip
- Edge: Board hold resolution with/without board selected