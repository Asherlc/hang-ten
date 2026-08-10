# Skip-to-break countdown design

## Date

2026-08-07

## Status

Approved

## Goal

When a user skips a workout step and the next timeline step is a break, move
to that break immediately instead of showing the three-second skip
preparation countdown. Skips to work steps retain the existing countdown.

## Approved behavior

- A skip whose destination step has `phase == .rest` transitions immediately.
- The immediate transition preserves the session's current running or paused
  state.
- A skip whose destination step is a work step continues to use the existing
  three-second countdown.
- Skipping the final step continues to seek directly to completion without a
  countdown.
- Existing cancellation, interruption, navigation, audio, board-preview, and
  completion behavior remains unchanged for skips that still use a countdown.

The destination is the step at the elapsed boundary returned by
`WorkoutTimeline.skipTarget(from:)`. This includes explicit rest steps after
work steps and consecutive rest steps. A timed rest interval within a work
step is not a separate destination step; the skip still targets the next
timeline boundary.

## Architecture and data flow

Keep `WorkoutSessionState.skipCurrentStep` as the single owner of skip
transition behavior. After resolving the target elapsed position:

1. If the target reaches the plan duration, use the existing direct seek path.
2. Otherwise, inspect `WorkoutTimeline.step(at: target)`.
3. If the destination step is `.rest`, use the existing `seek` method. Its
   `wasActive` handling keeps a running session running from the destination
   and keeps a paused session paused there. It also clears any countdown kind.
4. If the destination is a work step, use the existing skip-countdown path.

No new timer, UI state, audio policy, or timeline representation is needed.
The existing countdown value of three seconds remains unchanged for work-step
destinations.

## Testing

Add focused `WorkoutSessionStateTests` coverage for:

1. A running session that skips into a rest step transitions immediately,
   has no countdown kind, and remains running at the destination.
2. A paused session that skips into a rest step transitions immediately,
   has no countdown kind, and remains paused at the destination.
3. A skip into a work step still starts the three-second countdown.
4. Existing final-step skip coverage continues to prove completion remains
   immediate.

Run the focused `HangTenTests/WorkoutTimelineTests` tests, then the complete
`HangTenTests` target. No simulator-specific UI change is expected because the
existing rest presentation is already driven by the session state and
timeline position.

## Non-goals

This change does not alter workout durations, rest timing, step ordering,
countdown duration for work destinations, direct routine selection, board
highlight resolution, audio cues, completion logging, or Bluetooth behavior.
