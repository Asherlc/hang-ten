# Metolius Guided Task Steps Design

## Goal

Make the Metolius routines behave like the source describes them: each listed
task is its own guided workout step, tasks remain in source order, and the
remaining portion of each one-minute interval is an explicit rest step.

## Source and provenance

Metolius says to complete the task or tasks within each one-minute interval and
use the remaining time to rest. The guide supplies exact durations for hangs,
but does not supply durations for pull-ups, knee raises, shrugs, or offset
pulls. The app will preserve the source wording, order, counts, hold names, and
special qualifiers, while adding app-only timing for task navigation.

Because splitting the source table into separately timed app steps and assigning
default repetition durations changes the interval model, all three Metolius
plans will be marked `adapted`. Their source link and the adaptation note will
remain visible.

## Timing model

- Every source minute remains a 60-second cycle.
- Each listed task becomes a `WorkoutStep` with its own hold target and task
  text.
- Explicit source hang durations remain unchanged.
- Pull-up-only tasks use an app default of 5 seconds per pull-up.
- Other count-only tasks use a short app default of 1 second per repetition so
  the generated cycle remains usable without pretending Metolius prescribed a
  duration.
- Compound tasks whose source wording binds the repetitions to a timed hang
  keep that task together and use the source hang duration.
- Rest duration is `60 seconds - the total duration of all tasks in the minute`.
  Emit it only when positive; the helper must never create a negative rest step,
  so source tasks must fit within their minute.
- Maximum-effort tasks with no source duration occupy the remainder of their
  source minute and do not receive an invented rest segment.

## Data flow

`LegacyPlanSeedCatalog` will define a small Metolius task descriptor and a
cycle-expansion helper. The helper emits numbered `WorkoutStep` values with
stable IDs, task-local targets, and rest steps. `PlanStorage` continues to use
the seed catalog as its export fixture, so `PlanLibrary.json` is regenerated
from the same source definitions.

The existing workout UI can then use its normal step timeline. A task step has
only the hold(s) needed for that task, so the board map and grip card no longer
need to infer a primary hold from board-catalog order. Rest steps have no hold
targets and show the normal rest state.

## Compatibility and validation

- Keep the three Metolius plan IDs and levels unchanged.
- Keep each plan at ten minutes total, even though its internal step count
  increases.
- Preserve semantic targets for board-flexible tasks.
- Update DEBUG assertions and documentation so adapted task timing is explicit
  rather than treated as an unchanged official fingerprint.
- Add unit tests for task order, generated rest duration, default pull-up
  timing, and the absence of negative rest.
- Regenerate `PlanLibrary.json`, run its `--check` mode, build the app, and
  visually inspect representative single-task, multi-task, offset, and rest
  states in a dedicated simulator.
