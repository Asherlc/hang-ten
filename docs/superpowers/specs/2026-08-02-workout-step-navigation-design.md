# Workout step navigation design

## Goal

Add safe, direct navigation to the active workout so an athlete can skip the
current timed step or jump to another step in the routine without changing
the routine definitions or creating a second timer model.

## Approved behavior

- A newly opened routine always starts at step 1.
- The initial three-second countdown remains the only start path and disables
  navigation controls.
- Before the first real start, step navigation and “Skip step” are disabled.
- While running, selecting another step seeks immediately to that step’s
  start and keeps the timer running.
- While paused, selecting another step seeks to that step’s start and keeps
  the timer paused.
- Selecting the current step is a no-op.
- “Skip step” advances to the end of the current `WorkoutStep`, including any
  timed rest interval. Skipping the final step advances to the existing
  completion state.
- Navigation controls are disabled after completion.
- A direct jump does not require confirmation.

## User experience

The workout keeps its existing primary start/pause/completion control and adds
a secondary “Skip step” action in both portrait and landscape layouts. A
“Routine” action opens a full-height sheet containing the routine’s numbered
step rows. Rows reuse the established step vocabulary—number, title, duration,
instruction, accessory, and phase styling—and identify the current step.

The sheet is preferred over an always-visible list because the portrait
workout is already scrollable and the landscape layout has limited vertical
space. A compact menu is rejected because it hides the step instructions and
provides smaller, less informative targets.

The sheet dismisses after a different step is selected. The current row is
visibly selected but does not reset the timer when tapped. All controls have
accessibility labels that state their action and current-step context.

## Timing and state model

Introduce a small pure `WorkoutTimeline` helper that is the single source of
truth for:

- each step’s start and end offset;
- resolving a step at an elapsed position;
- elapsed time within a step; and
- the next boundary used by “Skip step.”

`WorkoutView` continues to own the live clock state. Direct navigation and
skip both update the same elapsed-position state:

- when running, rebase the active clock at the requested offset so the timer
  continues without a pause;
- when paused, replace the paused elapsed position and leave the timer paused;
- preserve the original routine start date for the existing completion and
  HealthKit flow;
- stop the current audio utterance before seeking, allowing the normal audio
  moment for the selected step to speak once.

The timeline treats a step’s full `duration` as its boundary, so a step with a
fixed active interval and rest interval is skipped as one unit. At the exact
end of a step, lookup resolves to the following step; the final boundary is
the plan duration and produces the existing completion UI.

No plan-library schema, routine content, board mapping, or persistence changes
are needed.

## Logging and safety

Completion continues through the existing “Log session” action. Apple Health
behavior remains unchanged: the app logs the plan using the established
completion path, and ending a session still does not log it. Seeking does not
create an additional workout record or modify routine definitions.

## Testing and validation

Add focused unit coverage for `WorkoutTimeline` covering:

- cumulative offsets across multiple steps;
- fixed active/rest intervals;
- exact step-boundary lookup;
- direct selection of a later and earlier step;
- no-op selection of the current step; and
- skipping the final step to the plan duration.

Validate the installed app on a dedicated iOS Simulator in portrait and
landscape. Exercise initial-state disabling, the start countdown, running and
paused direct selection, skip through a timed-rest step, final-step skipping,
audio re-cueing, rotation, and the normal completion/logging path. Update the
runtime-services and simulator-validation docs with the navigation contract.

## Acceptance criteria

1. A new routine visibly starts at step 1 and cannot be redirected before or
   during its initial countdown.
2. An active routine exposes “Skip step” in portrait and landscape.
3. Skipping moves to the next step’s start, including across a step’s rest
   interval; skipping the final step shows the existing completion state.
4. The routine sheet exposes every step as a sufficiently large, labeled
   control.
5. Selecting a different step seeks to its start and preserves running or
   paused state.
6. The current-step selection is a no-op.
7. Timer, board highlights, hold/grip cues, audio, and completion state all
   derive from the same selected elapsed position.
8. Existing session logging semantics remain intact.
9. Focused tests and the project build pass, and the simulator validation
   scenarios are reviewed in both supported workout orientations.
