# Workout Rest Preview and Board Primer Design

**Date:** 2026-08-04
**Status:** Approved

## Goal

Make workout state immediately legible while keeping the next work cue visible
during recovery, and replace the vague three-minute warm-up instruction with a
short, actionable board primer.

The athlete should be able to distinguish “load this hold now” from “these are
the holds you will use next” at a glance. During rest, they should be able to
step off, recover, and set up without losing the next hold information.

## User outcomes

- Active work highlights retain the existing strong treatment and hand cue.
- Rest remains visually calm and unmistakable, while the next work step's
  resolved holds remain visible on the board.
- Rest preview highlights are visibly different from active highlights and are
  labeled as a preview rather than an instruction to load immediately.
- The shared warm-up lasts 60 seconds and tells the athlete exactly what to do
  on the outer jugs.
- The warm-up explicitly says it is a board primer and that a broader warm-up
  should happen before training.

## Current root causes

`WorkoutTimeline` already resolves the next non-rest step through
`holdPreviewStep(at:)`, including timed rest portions and explicit `.rest`
steps. `WorkoutView` resolves those IDs, then clears them whenever
`isResting` is true. As a result, the data path exists but the rest UI receives
an empty highlight set.

`BoardDesign` and the generic board fallback accept only a set of highlighted
IDs. They have no concept of an active cue versus a rest preview, so the UI
cannot communicate the difference through the board itself.

The shared seed warm-up is created by `warmUpStep` with a 180-second default.
`PlanStorage` identifies that exact duration as the reusable shared warm-up,
and `PlanLibrary.json` is generated from the seed. The instruction says to
“move gently on the outer jugs” without explaining a physical action.

## Approved design

### 1. State-aware board highlights

Introduce a small board highlight mode with two cases:

- `.active`: the current work treatment, preserving the existing bright red
  fill and deep red shading.
- `.preview`: a cool blue, quieter treatment associated with recovery and the
  next step. It must remain clearly visible on the wood board but must not look
  like an active “load now” instruction.

The mode is passed through the existing board rendering path:

`WorkoutView` → `BoardMapView` → `DesignedBoardMap`/`GenericVectorBoardMap`
→ `BoardDesign.draw`/`GenericHoldVisual`.

The default mode remains `.active` so preparation cards and other existing
board-map call sites retain their current appearance. The bespoke Compact II
renderer and generic fallback must use the same semantic mode and equivalent
active/preview contrast.

During active work, `WorkoutView` passes the current step's resolved IDs and
`.active`. During timed or explicit rest, it passes the next non-rest step's
resolved IDs and `.preview`. Countdown and completed-session states pass an
empty set. The portrait and landscape layouts consume the same IDs and mode
from the shared elapsed position.

### 2. Rest language and layout cues

Rest continues to use the existing rest state across the header, timer, pill,
recovery cue, recorder pause behavior, and hand-cue suppression. The board
adds one concise textual cue when a preview exists:

`Next hold preview`

The rest recovery copy must describe the visible preview rather than promise
that the next cue appears only after rest. The intended behavior is: step off,
shake out, breathe, and use the blue board preview to prepare; do not load the
board until the timer permits the next work step.

When rest is final and there is no later work step, the board remains
unhighlighted and the extra preview label/copy is omitted or replaced with
ordinary recovery language. No hand diagram or hand cue card appears during
any rest state.

### 3. Shared 60-second board primer

Change the default shared warm-up step from 180 seconds to 60 seconds. Keep it
as one timed warm-up step targeting the outer jugs with an open-hand grip; the
existing board mapping remains valid.

Use this instruction:

> Start with easy 5-, 10-, and 20-second hangs on the outer jugs. Step off
> between hangs, keep an open grip, and stop if anything hurts. Do a broader
> warm-up before training.

Use accessory text that identifies the step as a board primer and does not
claim that 60 seconds is a complete warm-up. Update the source seed and
regenerate `HangTen/Resources/PlanLibrary.json` through the existing export
workflow. Update the shared-warm-up detection in `PlanStorage` to match the new
60-second source step. Leave unrelated three-minute recovery steps unchanged;
only the default warm-up duration changes.

This framing follows the board manufacturer's recommendation to begin with
very easy climbing, pull-ups, and hangs and gradually increase intensity, and
the progressive jug-hang sequence used in a controlled hangboard study. It is
not medical advice and does not replace a user's general warm-up or clinical
guidance.

References:

- Metolius, *Training Board and Rock Rings User's Manual*, “Warm Up, Warm
  Down”: https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826
- Mundry et al., *Hangboard training in advanced climbers: A randomized
  controlled trial*: https://www.nature.com/articles/s41598-021-92898-2
- Johns Hopkins Medicine, *Rock Climbing: Common Injuries and Prevention
  Tips*: https://www.hopkinsmedicine.org/health/conditions-and-diseases/sports-injuries/rock-climbing-common-injuries-and-prevention-tips

## Data flow

1. Resolve the current step and elapsed time through the existing
   `WorkoutTimeline` APIs.
2. Derive rest as explicit `.rest` or the post-active portion of a step with a
   timed work duration.
3. Ask `holdPreviewStep(at:)` for the current step during work or the next
   non-rest step during rest.
4. Resolve that step's semantic/direct targets through
   `AppStore.holdIDs(for:on:)`.
5. Suppress IDs for countdown and completion; otherwise pass IDs and the
   active/preview mode to both workout layouts.
6. Show the “Next hold preview” label and preview-aware recovery copy only
   while rest has a non-empty preview source.

No plan-library schema, persistence, audio, HealthKit, workout recording, or
board mapping changes are required beyond the warm-up source content and its
generated JSON.

## Edge cases

- Consecutive explicit rest steps skip forward to the first later non-rest
  step.
- A timed rest interval previews the next step without changing the current
  rest timer, pill, recovery copy state, or recorder behavior.
- A final rest step has no preview IDs and remains a clearly marked recovery
  state.
- Countdown and completed-session states never show active or preview holds.
- Both portrait and landscape use the same preview IDs and mode.
- Other `BoardMapView` callers continue to receive `.active` by default.
- Three-minute recovery intervals in research protocols remain three minutes.
- `scripts/export-plan-library.sh --check` detects any source/generated JSON
  drift.

## Testing and validation

### Unit and source tests

- Keep the existing `WorkoutTimelineTests` coverage for timed rest, explicit
  rest, consecutive rest, and final rest.
- Add assertions for the 60-second shared warm-up duration, primer instruction,
  and primer accessory/source classification.
- Run `scripts/export-plan-library.sh --check` after regeneration.
- Run the focused timeline/plan-storage tests and the complete XCTest target.

### Simulator review

Build with workspace-local derived data and validate on a simulator owned by
this workspace using its explicit UUID. Inspect both portrait and landscape:

- an active work step shows the normal red active cue;
- a timed rest step shows blue next-hold preview styling and
  `Next hold preview`;
- an explicit rest step behaves the same way;
- no hand diagram or hand cue card appears during rest;
- final rest has no hold highlight but keeps the recovery presentation;
- countdown and completion show no board highlight;
- the shared warm-up displays 60 seconds and the primer instruction.

Screenshots, logs, derived data, simulator ownership records, and any review
notes belong under `.context`. Any simulator created for validation must use a
name containing `CONDUCTOR_WORKSPACE_NAME`, have ownership recorded before
use, and be shut down and deleted before completion.

## Scope boundaries

This change does not redesign routine timing, alter manufacturer task order,
change the meaning of three-minute recovery steps, add user-configurable
warm-up duration, or introduce a new board-specific mapping. It changes the
shared warm-up source content and the visual/state plumbing needed to make
existing rest previews useful.
