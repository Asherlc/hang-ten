# Workout skip countdown design

## Goal

Give an athlete five seconds to get onto the board whenever they skip a
non-final workout step, while keeping the existing single elapsed-session
clock and the current direct-routine navigation behavior.

## Approved behavior

- Skipping a non-final step moves the displayed position to the next step's
  start and begins a five-second countdown.
- The behavior is the same when the session was running or paused. After the
  countdown completes, the next step starts automatically and the session is
  running.
- During the countdown, the destination step is visible, but its board holds
  and grip cues remain inactive. Routine selection and Skip step are disabled.
- The countdown displays and speaks `5`, `4`, `3`, `2`, and `1` once each.
- When the countdown reaches zero, the destination step's normal start cue is
  allowed to play through the existing audio-moment flow.
- Skipping the final step advances directly to the existing completion UI; it
  does not show a five-second countdown.
- Direct selection from the Routine sheet remains immediate and preserves the
  existing running or paused state.
- The initial three-second start countdown remains unchanged.
- Cancelling a skip countdown leaves the session paused at the destination
  step, preserving the original session start date. The existing initial
  countdown cancellation behavior remains unchanged.
- If the app becomes inactive during a skip countdown, the pending start is
  cancelled and the session remains paused at the destination step.
- Completion still requires the existing user action to log the session.

## User experience

The existing “Skip step” control remains in both portrait and landscape
layouts. A non-final skip immediately changes the visible step title and
countdown label to “Get ready” / “starting in,” with the timer showing the
remaining whole seconds from five down to one. The controls are disabled while
the countdown is active, matching the initial countdown’s safety behavior.

The board map stays visible for orientation, but highlighted holds and grip
diagrams are hidden until the destination step actually begins. If the athlete
cancels the countdown, the primary action changes to the existing Resume
state, allowing an explicit start from the destination step.

The final-step path keeps the current completion presentation and “Log
session” action. It does not delay completion merely to show a countdown when
there is no upcoming board position.

## Timing and state model

`WorkoutView` continues to own one elapsed session clock. The existing future
`startedAt` representation is extended with an explicit countdown kind so the
view can distinguish the initial three-second countdown from a post-skip
countdown without introducing a second timer.

For a post-skip countdown:

1. Resolve the next boundary through `WorkoutTimeline.skipTarget(from:)`.
2. Store that boundary in the existing paused elapsed position.
3. Set the run start to five seconds in the future and mark the countdown as a
   skip countdown.
4. Derive the displayed step, progress, countdown, board highlights, and audio
   moment from that same elapsed position.
5. When the future start is reached, the existing clock naturally advances
   from the destination step's start while remaining running.

The original `routineStartedAt` is never replaced by a skip countdown. This
keeps completion timing and Apple Health logging semantics unchanged. A final
skip uses the existing seek-to-plan-duration path and therefore reaches the
completion UI immediately.

Cancellation and interruption branch on the countdown kind:

| State | Cancel/interruption result |
| --- | --- |
| Initial countdown | Return to the not-started state, as today |
| Skip countdown | Clear the future start, retain the destination elapsed position, and remain paused |
| Running session | Store current elapsed time and pause, as today |

Any direct seek clears a pending countdown before applying its target. The
existing `canNavigate` gate remains the single control for disabling Routine
and Skip step during countdowns and after completion.

## Audio

The existing `WorkoutAudioMoment` remains the source of spoken workout cues.
Countdown moments use stable keys based on the countdown value, allowing the
four-times-per-second `TimelineView` updates to speak each number once. The
post-skip countdown uses the same speech cadence as the initial countdown but
starts at five. Stopping or replacing a countdown stops the active utterance;
the destination step's normal cue is emitted once after the countdown ends.

## Testing and validation

Add focused unit coverage for the countdown policy and preserve the existing
`WorkoutTimeline` tests. Coverage should verify:

- initial countdown timing remains three seconds;
- skip countdown timing is five seconds;
- a non-final skip targets the next step and starts the destination normally
  after the delay;
- a skip from a paused session becomes running after the delay;
- cancelling or interrupting a skip leaves the destination paused;
- a final skip reaches plan duration without a countdown; and
- direct selection remains immediate and preserves its running/paused state.

Update `docs/IOS_RUNTIME_SERVICES.md` and
`docs/IOS_SIMULATOR_VALIDATION.md` with the new skip contract. Validate the
installed app in portrait and landscape, covering initial start, running skip,
paused skip, countdown cancellation, final-step completion, spoken 5-4-3-2-1,
hold activation after countdown, rotation, and the existing logging path.

## Scope

No plan-library schema, routine content, board mapping, persistence, HealthKit
record format, or direct Routine selection semantics change. The work is
limited to the active workout clock, countdown presentation/audio, focused
tests, and runtime validation documentation.

## Acceptance criteria

1. Every non-final Skip step action shows a five-second countdown before the
   destination step begins, regardless of whether the session was running or
   paused.
2. The countdown is visible and spoken as 5-4-3-2-1, exactly once per number.
3. Board holds and grip cues remain inactive during the countdown and activate
   when the destination step starts.
4. Routine and Skip step controls are disabled during the countdown.
5. Cancelling or interrupting the countdown leaves the destination step
   paused and resumable.
6. Skipping the final step reaches completion immediately without a countdown.
7. Direct Routine selection remains immediate and preserves running/paused
   state.
8. Existing completion, Apple Health, orientation, and initial-countdown
   behavior remains intact.
