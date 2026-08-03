# Numeric-only workout audio cues

**Date:** 2026-08-03  
**Status:** Approved for implementation

## Context

`WorkoutView` currently generates several kinds of spoken cues: the initial
3-2-1 countdown, segment-start labels such as a hang title or rest prompt,
final three-second countdowns, a combined label and countdown for very short
segments, and a session-complete phrase. The requested behavior is to keep
spoken timing information while removing spoken workout labels such as “set 2,
rep 3.”

## Goal

Every spoken workout cue must be a numeric countdown value: `3`, `2`, or `1`.
The initial countdown and existing interval timing remain intact, but the app
must not speak segment names, exercise titles, set/rep identifiers, rest
prompts, or completion text.

## Behavior

- The initial pre-workout countdown continues to speak `3`, `2`, and `1` as the
  timer approaches the first step.
- Each timed active or rest interval continues to speak its final applicable
  countdown values (`3`, `2`, `1`) at the existing interval boundaries.
- A segment-start event by itself produces no spoken cue. This removes phrases
  such as “Hang. F80 · set 2, rep 3,” “Rest,” and “Begin minute …”.
- Intervals three seconds or shorter use the same numeric countdown logic, so
  they produce only the applicable individual numbers rather than a combined
  phrase such as “Hang. 3, 2, 1”.
- Completion produces no spoken phrase.
- Audio enable/disable behavior, speech synthesis configuration, and the
  visible workout countdown are unchanged.

## Design

Extract the cue-selection logic into a small pure, testable audio-cue policy.
The policy receives the current initial countdown and interval timing state and
returns either no moment or a keyed `WorkoutAudioMoment` whose phrase is one
numeric value. `WorkoutView` remains responsible for deriving workout state
and passing the selected phrase to `WorkoutAudioCoach`; the policy has no
dependency on AVFoundation or view state.

The policy will use the existing moment keys to prevent `TimelineView` updates
from repeating a number within the same countdown second. It will return
initial countdown values first, then interval countdown values only when the
remaining interval is within three seconds. It will return no moment for
segment starts, normal interval time, and completion.

## Testing

Add focused XCTest coverage for the policy:

1. Initial countdown values `3`, `2`, and `1` are returned as numeric phrases.
2. An interval's final three seconds return the corresponding numeric phrase
   and stable key.
3. Segment-start and completion states return no moment.
4. A short interval returns only applicable numeric values and never includes
   a label or combined phrase.

Run the focused audio-policy tests and the full `HangTenTests` target. Build
and launch the app on a workspace-owned iOS Simulator, then exercise the
initial and interval countdowns with spoken cues enabled and disabled. Confirm
that no spoken label or completion phrase remains.

## Non-goals

This change does not alter workout durations, interval calculations, the audio
toggle, speech rate/voice configuration, or the visual countdown UI.
