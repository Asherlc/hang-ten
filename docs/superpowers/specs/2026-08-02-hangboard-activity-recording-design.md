# Hangboard activity recording design

## Goal

Record the physical hangboard activity used during a completed Hang Ten
routine, rather than preserving only the routine's semantic wording. A
routine's target must resolve through the selected board before it is written
to Apple Health, so a nominal 20 mm target that maps to a 21 mm board hold is
recorded as the physical 21 mm hold.

## Approved behavior

- Keep the existing `HKWorkout` title, activity type, start date, end date, and
  completion flow unchanged.
- Add the selected board identity to the completed workout metadata.
- Store ordered activity segments for the routine. A segment is either work or
  rest.
- Work segments store the resolved physical hold IDs, hold type, physical size
  in millimeters when the board provides one, and a duration when one exists.
- Rest segments store their duration and step identity but no hold metadata.
- Preserve left/right board holds as one logical activity when they represent
  the same physical hold type and size; retain both resolved IDs in that
  activity.
- A fixed segment stores its prescribed active duration and excludes rest.
- A stopwatch segment stores the athlete's observed duration. If the athlete
  never starts that stopwatch, its duration remains undefined.
- A genuinely untimed work segment stores no duration field. The app must not
  invent a duration from the enclosing cycle.
- A completed or abandoned stopwatch segment is finalized when the athlete
  leaves the step, skips the step, or logs the session. Pausing or backgrounding
  the workout pauses an active stopwatch.
- Existing completion/error semantics remain intact: the local session is
  marked complete, while an Apple Health metadata or workout write failure is
  surfaced through the existing Health error state.
- Ending a session still does not write an Apple Health workout.

## User experience

Routine steps that contain a stopwatch activity expose a count-up Start/Stop
control in both portrait and landscape workout layouts. The existing routine
countdown remains the source of session navigation and completion; the
stopwatch measures only the selected max-effort activity.

The control is accessible and states whether the stopwatch is ready, running,
stopped, or finalized. A stopped value remains visible when the athlete
returns to that step and is not overwritten by later timeline ticks. The
normal fixed work/rest countdown and existing audio cues remain unchanged.

## Data model

### Physical board metadata

Extend `BoardHold` with an optional numeric `sizeMillimeters` field. Existing
board metadata supplies explicit values for the 19 mm, 29 mm, and 56 mm holds;
holds without a meaningful numeric size, such as the outer jugs, leave the
field absent. The recorder must not parse a size from the localized/display
name.

`BoardHold.kind` remains the source of the recorded hold type. The serialized
value uses its stable raw value (`edge`, `pocket`, `sloper`, or `jug`).

### Routine segments

Add a versioned, Codable segment definition to the routine library. A segment
contains:

- `kind`: `work` or `rest`;
- an optional semantic hold target, required for work segments that use the
  board;
- `timing`: `fixed`, `stopwatch`, or `undefined` for work segments;
- an optional duration in seconds.

Rest segments always use fixed timing and require a duration. Work segments
with fixed timing require a duration, stopwatch segments may receive an
observed duration at runtime, and undefined segments intentionally omit it.

`WorkoutStep.targets` remains available to the current board highlighting and
cue UI. The runtime step also carries its explicit segments so recording does
not infer different durations by parsing prose. The plan decoder accepts older
documents without segments and derives a conservative compatibility segment;
the bundled library is regenerated with explicit segment classifications and
schema version 3, from the current schema version 2.

### Recorded payload

Use a pure Codable payload builder between `AppStore` and `HealthKitService`.
Each recorded segment contains:

```swift
struct RecordedActivitySegment: Codable, Hashable {
    let stepID: String
    let stepNumber: Int
    let kind: WorkoutSegmentKind
    let holdIDs: [String]
    let holdType: String?
    let sizeMillimeters: Int?
    let durationSeconds: TimeInterval?
}
```

For rest segments, `holdIDs` is empty and `holdType` and `sizeMillimeters` are
`nil`. For undefined work, the hold fields are present but
`durationSeconds` is absent. Segment order is preserved so a consumer can
reconstruct work/rest intervals within each routine step.

## Data flow

1. `WorkoutView` completes a routine with the exact `TrainingBoard` it used.
2. `AppStore` resolves every work target against that board using the same
   mapping path used for active board highlights, including semantic and
   fallback mappings.
3. A pure recorder converts resolved board holds and runtime stopwatch values
   into `RecordedActivitySegment` values. Symmetric holds are grouped only
   within the same source segment; separate repetitions remain separate
   records.
4. `AppStore` passes the board identity and recorded segments to
   `HealthKitService.saveCompletedWorkout`.
5. `HealthKitService` retains the existing `HKWorkoutBuilder` sequence and
   adds the custom metadata before ending and finishing the workout.

## Apple Health metadata contract

Keep `HangTen.PlanName` and add:

- `HangTen.BoardID`: the stable `TrainingBoard.id`;
- `HangTen.BoardName`: the user-facing board display name;
- `HangTen.ActivitySegments`: a JSON string with this envelope:

```json
{
  "version": 1,
  "segments": [
    {
      "stepID": "example-step",
      "stepNumber": 2,
      "kind": "work",
      "holdIDs": ["edge-example-left", "edge-example-right"],
      "holdType": "edge",
      "sizeMillimeters": 21,
      "durationSeconds": 20
    },
    {
      "stepID": "example-step",
      "stepNumber": 2,
      "kind": "rest",
      "durationSeconds": 10
    }
  ]
}
```

Optional JSON fields are omitted rather than encoded as made-up values. The
payload version allows future metadata changes without changing the
workout's title or custom-key meanings.

## Timing state

Add a small pure stopwatch state machine that accepts an injected `Date` (or
equivalent clock value) so behavior is unit-testable. It tracks accumulated
elapsed time, a running anchor, and finalization. The workout view owns one
state per stopwatch segment and updates it from the same periodic timeline
already used for the workout UI.

- Starting sets the anchor without changing the session clock.
- Pausing adds the elapsed interval to the accumulator and clears the anchor.
- Resuming starts a new anchor and continues the same accumulated value.
- Stopping finalizes the value for that segment.
- Leaving or skipping the step, completion, or dismissal finalizes the
  stopwatch. Scene deactivation pauses it and does not finalize the value.
- A stopwatch that was never started produces an undefined duration.

The main workout's original start date and completed interval remain the
source for the enclosing `HKWorkout` dates.

## Compatibility and error handling

The plan library schema is incremented from version 2 to version 3 for explicit
segments. Decoding older
library documents remains supported by deriving compatibility segments, so an
older document cannot prevent the app from launching or completing a routine.
The generated library and its source-audited seed must remain in sync.

If activity metadata encoding fails, the HealthKit write reports the existing
local Health error and does not silently save a workout with incomplete board
details. If a board target cannot resolve, the existing plan compatibility
guard prevents the routine from being offered; the recorder also omits no
resolved data silently and reports a validation failure to its caller.

## Testing and validation

Add focused XCTest coverage for:

- explicit board sizes and hold types, including a semantic target resolving
  to a different physical size;
- semantic, ID, and fallback target resolution using the selected board;
- left/right grouping without merging separate repetitions;
- fixed work and rest segment ordering and duration;
- undefined work durations being omitted from Codable output;
- stopwatch start, pause, resume, stop, finalization, and never-started state;
- completion and navigation finalizing stopwatch values;
- stable versioned JSON metadata encoding;
- preservation of the existing workout title, date interval, and HealthKit
  error flow.

Run the complete XCTest suite and a signed Debug simulator build using a
workspace-specific derived-data directory. Use the Hang Ten isolated
simulator workflow to inspect both workout orientations, a fixed work/rest
step, an undefined activity, a max-effort stopwatch, direct navigation,
pause/background behavior, and the user-triggered Apple Health completion
path. Simulator validation proves the wiring and UI; a physical device still
needs to verify the final HealthKit metadata in Apple Health.

## Acceptance criteria

1. A completed routine records the board actually selected for that session.
2. A routine target is recorded with the resolved board hold size and hold
   type, not the routine's nominal wording.
3. Work and rest segments remain ordered and rest durations are preserved.
4. Fixed durations exclude rest, stopwatch durations reflect observed time,
   and undefined durations are absent.
5. Max-effort steps provide a usable stopwatch in portrait and landscape.
6. Pausing, navigation, backgrounding, and completion do not lose or invent
   stopwatch time.
7. Existing completion logging, HealthKit authorization, error reporting, and
   end-session behavior remain intact.
8. Focused tests, the full test suite, and the signed simulator validation
   pass, with any physical-device-only verification called out explicitly.
