# Multi-position board workouts

## Goal

Let one-handed and portable boards use more than one physical position in a
single workout without duplicating boards or holds, changing sourced routine
timing, or assuming that every position change is equally practical.

The app resolves a stable position sequence before the workout begins. Easy
changes happen during ordinary rest. Changes that need more setup pause at the
end of the available rest until the athlete confirms readiness. Position pairs
that cannot be combined make that board/routine pairing incompatible.

## Existing foundation

Board packages already separate physical holds from visual presentations. A
presentation can own holds directly or render the holds from a canonical
`sourcePresentationID`, optionally inverted. This supports alternate faces and
rotated renderings without duplicating the hold inventory.

Today, presentations also carry an implied notion of physical setup. The board
map may switch presentations in response to a highlighted hold, but workout
data does not identify the athlete's current physical setup and cannot reason
about the effort required to reach the next one. A presentation picker also
allows the visual state to diverge from the setup needed by the workout.

## Terms and responsibilities

- A **hold** is a canonical physical contact surface. Its ID and metadata are
  not duplicated when the board is rotated or flipped.
- A **presentation** is a visual rendering: image, aspect ratio, canonical
  source presentation, and transform such as inversion.
- A **position** is an athlete-usable physical configuration of the board. It
  references one presentation and uses that presentation's athlete-facing name.
- A **placement** is a hold used in a particular position, represented at
  runtime by `(holdID, positionID)`.
- A **transition** is a directed board-owned rule from one position to another.
- A **resolved workout** is the immutable sequence of selected placements and
  positions produced during workout preparation.

Presentations remain the rendering layer. Positions and transitions describe
physical operation. Plans describe training tasks; board packages and the
board-specific semantic mapping layer describe how those tasks are realized on
a particular board.

## Board package model

A package may add `positions` and `positionTransitions`:

```json
{
  "positions": [
    { "id": "front", "presentationID": "front" },
    { "id": "back", "presentationID": "back" },
    { "id": "side", "presentationID": "side" }
  ],
  "positionTransitions": [
    {
      "fromPositionID": "front",
      "toPositionID": "back",
      "kind": "seamless"
    },
    {
      "fromPositionID": "back",
      "toPositionID": "front",
      "kind": "setupRequired"
    },
    {
      "fromPositionID": "front",
      "toPositionID": "side",
      "kind": "unsupported"
    }
  ]
}
```

Transition kinds are deliberately coarse:

- `seamless` means the transition is suitable for an ordinary timed rest. The
  workout clock does not wait for confirmation.
- `setupRequired` means the athlete may begin setup during rest, but the next
  work interval cannot start without confirmation.
- `unsupported` means the two positions cannot occur consecutively in one
  resolved workout.

Transitions are directed because changing from A to B can differ from changing
from B to A. Remaining in the same position is an implicit free transition; a
self-transition declaration is invalid. An omitted edge defaults
conservatively to `setupRequired`. `unsupported` must always be explicit.

Hold availability in a position is derived rather than copied. A position
references a presentation. Its available holds are those owned by that
presentation's canonical source: `sourcePresentationID` when present, otherwise
the presentation's own ID. Thus an inverted presentation naturally exposes the
same canonical holds in a different position.

Board-specific semantic mapping definitions, currently loaded from the plan
library and attached to the runtime board, may constrain a semantic target to a
subset of positions when the meaning depends on orientation:

```json
{
  "holdIDs": ["edge-20"],
  "positionIDs": ["front-inverted"]
}
```

Without `positionIDs`, every position exposing all mapped holds is a candidate.
This keeps physical setup knowledge in the board-specific mapping layer rather
than in generic routine content.

Every explicitly authored position and transition classification must be
traceable in the package's board-source audit. Authors must not infer
`seamless` or `unsupported` from artwork. When evidence does not establish a
classification, omitting the edge safely produces `setupRequired`.

## Compatibility

A package without `positions` receives one implicit position for each existing
presentation, inheriting that presentation's ID and name. A single-presentation
package therefore receives exactly one implicit position backed by its default
presentation. This preserves access to holds on alternate presentations in
legacy multi-presentation packages.

Until a package's physical positions are deliberately authored, workout
resolution treats every change between its implicit presentation positions as
`setupRequired`. No existing package is silently granted a seamless transition.

Plan files do not acquire setup instructions or transition durations. Existing
semantic mappings and direct hold targets continue to decode. Existing workout
history continues to decode because position and setup-wait fields are additive
and optional.

## Validation

Package validation rejects:

- duplicate position IDs;
- a position that references an unknown presentation;
- duplicate directed transition edges;
- a transition with an unknown endpoint;
- an explicitly declared self-transition; and
- a position that exposes no usable holds through its canonical presentation.

An omitted edge is valid and resolves to `setupRequired`. A board with one
implicit or explicit position requires no transition declarations.

A target-bearing normalized workout step must have at least one position that
exposes all of its top-level and segment targets. Position changes inside one
normalized step are not supported; such a board/routine pairing is
incompatible unless normalization can represent the target changes as separate
steps. Rest-only steps do not require a position.

## Workout preparation

Preparation resolves targets to candidate placements for every target-bearing
step, then selects positions across the whole routine. Unsupported edges are
forbidden. The board's default position is the first declared position whose
`presentationID` is the board's default presentation; if more than one
position maps to that presentation, declaration order selects the default.
Valid sequences are ranked lexicographically by:

1. fewest `setupRequired` transitions;
2. fewest `seamless` transitions, thereby preferring to remain in position;
3. the accumulated default-position penalty for target-bearing steps: `0` for
   the derived default position and `1` for every other selected position; and
4. package declaration order for a deterministic final tie-break.

This ranking prefers any number of seamless changes over one setup gate. The
resolver has no assumed prior physical position, so every candidate for the
first target-bearing step starts with zero transition costs. Rest-only steps
add no default-position penalty. The resolver must use a deterministic
whole-sequence algorithm rather than making greedy choices one step at a time;
the declaration-order path remains the final tie-break.

The chosen placement and `positionID` are stored in a runtime resolved-workout
representation. The sequence is frozen before playback so target resolution
cannot unexpectedly select a different orientation mid-session. If no valid
sequence exists, workout launch explains that the selected board cannot realize
the routine's required position sequence.

## Playback behavior

Before the normal start countdown, the app shows the initial position and its
presentation. The athlete confirms `Ready`; this establishes the session's
current physical position.

For consecutive target-bearing steps in the same position, playback is
unchanged. Rest-only steps between them still run exactly as authored.

For a `seamless` transition, the next-position visual and spoken cue appear at
the start of the intervening rest. The rest clock continues and the next work
interval begins normally. If no rest exists, even a seamless change receives an
untimed `Ready` gate at the step boundary; the app must not start work while the
athlete is still manipulating the board.

For a `setupRequired` transition, the cue and `Ready` control appear as soon as
the intervening rest begins. The athlete can complete and confirm setup while
the authored rest continues. Confirmation never shortens the remaining rest.
If rest reaches zero before confirmation, playback pauses at the boundary and
waits. With no intervening rest, the untimed gate appears immediately after the
previous work step. Confirming readiness starts the normal countdown or next
work interval according to existing session rules.

The workout map is locked to the resolved position. Board-detail and routine
authoring surfaces may still expose position selection, but the workout's
presentation picker must not override the resolved setup.

Setup waiting time is recorded separately from authored work and rest time.
Health workout segments and routine duration retain their source-prescribed
values.

## Navigation during a workout

The session tracks the last position the athlete confirmed, independently of
the timer's current step. When the athlete skips or jumps, the app evaluates
the directed transition from that confirmed position to the destination
step's already-resolved position:

- same-position and seamless jumps proceed with the appropriate cue;
- setup-required jumps enter the untimed readiness gate; and
- unsupported jumps are disabled with an explanation.

Rewinding uses the same directed lookup and can therefore behave differently
from the original forward transition. Pausing and resuming do not clear the
confirmed position or any pending setup gate.

## Session records and diagnostics

Each recorded target-bearing step may include its resolved `positionID`.
Session-level diagnostics include accumulated setup-wait duration and the count
of setup gates. These fields support reproducibility and troubleshooting; they
do not alter completion, load, or prescribed-duration calculations.

Resolution failures distinguish between an unresolvable target, no common
position within a step, and no valid transition path. User-facing copy remains
brief, while diagnostics retain the failing target or position IDs.

## Cross-platform behavior

iOS and Android must decode the same position and transition schema, derive
hold availability through canonical presentations identically, and produce the
same deterministic position sequence. Android must gain parity for
`sourcePresentationID` and inversion before multi-position workout resolution
is considered complete.

## Testing

Model and package tests cover decoding, implicit single-position migration,
canonical-source availability, transition directionality, missing-edge
defaults, invalid references, duplicate edges, and self-edge rejection.

Resolver tests cover deterministic ties, multiple valid placements, preference
for unchanged and seamless positions, rejection of unsupported paths, semantic
position constraints, and steps whose targets have no common position. Shared
fixtures assert identical expected sequences on iOS and Android.

Playback tests cover initial readiness, seamless cues, setup confirmation before
rest expires, pausing when rest expires, no-rest transitions, pause/resume,
skip, forward jump, rewind, and unsupported jump behavior. History tests verify
optional-field compatibility and separation of setup-wait time from authored
workout timing.

Simulator review verifies portrait and landscape layouts, position-locked hold
highlighting, next-position previews, spoken cues, Dynamic Type, and VoiceOver
labels.

## Rollout

Implement schema and runtime support with backward compatibility first. Then
migrate one representative multi-position board, preferably the Frictitious
Port-A-Board, using its primary manufacturer evidence and a documented source
audit. Validate its full preparation and playback flow before auditing more of
the catalog. Existing boards remain conservative until each package's physical
positions and explicit transition edges have been deliberately reviewed.

## Out of scope

- Numeric transition-time estimates.
- Automatically inferred transition difficulty.
- Generated or image-derived hold geometry.
- Rewriting sourced routine rest durations to accommodate setup.
- Re-optimizing the position sequence after workout playback begins.
