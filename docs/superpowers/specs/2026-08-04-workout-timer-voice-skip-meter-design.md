# Workout timer voice, skip preview, and motherboard meter design

**Date:** 2026-08-04  
**Status:** Approved

## Goal

Make workout transitions predictable and legible: spoken audio must remain a
numeric countdown, skipped steps must give the athlete a short preparation
window with the destination holds visible, and the live motherboard meter must
not occupy workout space when no motherboard is connected.

## Current root causes

The skip-countdown implementation currently uses a five-second duration and
passes a generic countdown value into `WorkoutTimeline.boardCue`. The timeline
therefore suppresses all board highlights during every countdown, including the
skip state where the destination step is already known.

The numeric-only audio policy exists, but `WorkoutView.audioMoment` adds a
separate segment-start branch that speaks labels, rest prompts, and combined
short-interval phrases. That branch was reintroduced by the later skip-timer
change. When the countdown moment changes to `nil`, the view also leaves the
last utterance running, allowing it to overlap the next stage.

`WorkoutView` renders `MotherboardMeterView` unconditionally in both portrait
and landscape layouts. The meter itself explains that the sensor is
unavailable, but the entire section is still visible when the Bluetooth service
is idle or disconnected.

## Approved behavior

### Skip preparation and board preview

- A non-final skipped step starts a three-second countdown.
- The destination step remains the displayed step during the countdown.
- The destination step's resolved holds are shown with preview styling during
  the skip countdown; they are not treated as active instructions yet.
- The initial workout countdown continues to suppress board highlights.
- When the skip countdown reaches zero, the destination holds switch to the
  normal active styling and the workout proceeds normally.
- The existing cancellation, interruption, navigation disabling, and final
  skip behavior remain unchanged except for the duration change.
- The existing “Next hold preview” label is shown for preview-mode holds during
  both rest and skip preparation. Skip preparation retains its “Get ready” and
  “starting in” timer presentation rather than using rest language.

### Numeric-only voice and transition cancellation

- Every spoken workout cue is exactly one numeric countdown value.
- Initial countdowns speak `3`, `2`, and `1`.
- Skip preparation speaks `3`, `2`, and `1`.
- Active and rest interval countdowns speak only their applicable final
  countdown values.
- Segment titles, set/rep labels, rest prompts, instructions, combined
  phrases, and completion text are never spoken.
- When the current audio cue becomes unavailable, the active utterance is
  stopped immediately. A new numeric cue replaces any older utterance without
  allowing it to queue into the next stage.
- The existing audio toggle and speech configuration remain unchanged.

### Motherboard meter visibility

- The live `MotherboardMeterView` in the workout appears only while the
  motherboard service is streaming live data.
- The condition applies equally to portrait and landscape workout layouts.
- The Progress dashboard's Training sensor card remains visible while
  disconnected so the user can see connection status and connect the device.

## Architecture and data flow

Keep the existing `WorkoutSessionState` as the source of elapsed time and
countdown kind. Change the skip duration constant to three seconds.

Extend `WorkoutTimeline.boardCue` with enough countdown context to distinguish
the initial countdown from skip preparation. For an initial countdown, return a
suppressed cue as today. For a skip countdown, resolve the current destination
step from the paused elapsed position and return its holds with `.preview`
mode. Once the countdown reaches zero, the existing active-mode path takes
over. The view derives the hold IDs and passes the same cue to portrait and
landscape layouts.

Make `WorkoutView.audioMoment` delegate all cue selection to
`WorkoutAudioCuePolicy`. Remove its segment-start speech branch and its
phrase-building helper. Update the audio-moment change handler to stop the
`WorkoutAudioCoach` when no cue is present, while continuing to speak only
numeric moments when audio is enabled.

Add a small connection-state predicate for workout-meter visibility, with
streaming as the only visible state. Use it around the existing meter calls;
do not alter the dashboard card or Bluetooth service lifecycle.

## Testing

Add or update focused XCTest coverage for:

1. Skip countdown duration is three seconds while initial countdown remains
   three seconds.
2. A skip countdown board cue returns the destination step in preview mode,
   while an initial countdown remains suppressed.
3. Numeric audio policy returns only countdown values and no cue for segment
   starts or completion.
4. The connection-state visibility predicate exposes the workout meter only
   for streaming state.
5. Existing cancellation, interruption, final-skip, rest-preview, and active
   board behavior remains green.

Run focused tests first, then the complete `HangTenTests` target. Build and
install the DEBUG app on a simulator owned by this Conductor workspace and
inspect portrait and landscape workout routes for initial countdown, skipped
step preparation, active transition, rest preview, and disconnected-meter
visibility. Keep all logs and screenshots in `.context`.

## Non-goals

This change does not alter workout durations other than the skip preparation
window, plan-library content, hold resolution, Bluetooth protocol behavior,
dashboard sensor-card behavior, HealthKit records, speech voice/rate settings,
or the existing final-step completion flow.
