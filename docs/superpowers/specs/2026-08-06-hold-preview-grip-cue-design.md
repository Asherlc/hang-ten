# Hold Preview Grip Cue Design

**Date:** 2026-08-06
**Status:** Approved

## Goal

During a workout rest interval, show the grip type and hand cue for the next
work hold alongside the existing blue board preview. The preview should carry
the same useful grip information as the corresponding active hold step and
should not make the board change size as the workout moves between work and
rest.

## Current behavior

`WorkoutTimeline.boardCue` already resolves the next non-rest step during an
explicit rest step or a timed rest interval. `WorkoutView` uses that step to
resolve the highlighted board holds, but the grip cue is currently rendered
only when the workout is active and the highlighted step has one target.

The portrait layout renders `GripDiagramView` below the board. The landscape
layout renders the two per-hand `GripHandCueCard` views beside the board. Both
layouts currently suppress those cues while resting. Landscape also applies a
special 60-point board height during rest, so the board footprint changes
between an active step and its preview.

## Approved design

### 1. Resolve one shared hold cue

Add a small pure hold-cue resolver/value in the workout model layer. It takes
the currently highlighted step and the first resolved board hold and returns a
cue only when the step has exactly one target. The returned value contains:

- the resolved `BoardHold` used by the board highlight;
- the effective `GripType`, preferring the step-level override and falling back
  to the board hold's default grip type.

The highlighted step is the source of truth, not the timer's original current
step. Therefore a rest preview uses the next work step's grip override, while
active work continues to use its current step's override. Multi-target steps
retain the existing behavior and do not show the generic single-hold cue.

### 2. Use the shared cue in both orientations

`WorkoutView` will derive the shared cue once from `highlightedStep` and
`activeHold`, then pass it to both layout functions.

- Portrait will render the existing full `GripDiagramView` whenever a cue is
  available, the session is not complete, and the countdown has reached zero.
  This includes active work and next-hold previews.
- Landscape will render the existing left and right `GripHandCueCard` views
  whenever the same conditions hold. The cards will use the shared cue's hold
  and effective grip type, so portrait and landscape cannot disagree about
  which grip is being previewed.

Countdown and completed-session states remain cue-free. A final rest with no
later work step remains cue-free as well, while preserving its ordinary rest
presentation.

### 3. Keep the landscape board footprint stable

Remove the landscape-only rest height override from `BoardMapView`. The board
will continue to use the existing constrained height of the landscape cue
row, regardless of whether its highlights are active or preview highlights.
The blue preview treatment and `Next hold preview` label remain unchanged.
Portrait keeps the board's existing aspect-ratio sizing; adding the cue below
the board does not alter the board map's own geometry.

## Data flow

1. `WorkoutTimeline` resolves the current active or next preview step.
2. `AppStore.holdIDs(for:on:)` resolves that step's semantic targets to board
   hold IDs.
3. `WorkoutView` selects the highlighted board hold and asks the hold-cue
   resolver for the effective grip metadata.
4. Both portrait and landscape consume that same cue value while the board
   consumes the same IDs and highlight mode as before.

No plan-library schema, persistence, audio, HealthKit, workout recording, or
board mapping changes are required.

## Edge cases

- Explicit and timed rest previews use the next non-rest step's grip type.
- Consecutive rest steps continue to preview the first later work step.
- A step-level grip override wins over the board hold's default grip type.
- A step with multiple targets does not show a single-hold grip cue.
- A final rest, countdown, and completed session do not show a grip cue.
- Existing active work cues remain visually and semantically unchanged.
- The landscape board no longer collapses to a rest-only height, preventing a
  work/rest resize jump.

## Testing and validation

Add focused unit coverage for the pure hold-cue resolver:

- a single-target step uses its explicit grip override;
- a single-target step falls back to the board hold's grip type;
- a multi-target step returns no cue.

Retain the existing `WorkoutTimelineTests` coverage for timed rest, explicit
rest, consecutive rest, final rest, and board cue suppression. Run the focused
XCTest cases and the complete XCTest target, then build the app target to
confirm the shared cue is wired into both SwiftUI orientations.

