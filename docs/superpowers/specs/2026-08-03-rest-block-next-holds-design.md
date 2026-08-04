# Rest Block Next-Hold Preview Design

**Date:** 2026-08-03

## Goal

During a workout rest block, show the holds required by the next work block on
the board while preserving a clear, rest-specific indication in the timer UI.

## Current behavior

`WorkoutView` derives the current `WorkoutStep` from `WorkoutTimeline`. During a
timed rest interval, it clears the board highlights entirely and suppresses
the grip cue. Explicit `.rest` steps have no targets of their own, so they do
not identify the following work step's holds either.

## Proposed behavior

- Treat both kinds of rest as rest state:
  - the post-work portion of a step with `timedWorkDuration`; and
  - a step whose phase is `.rest`.
- While in rest state, highlight the next non-rest step's resolved hold IDs on
  the board.
- Keep the current rest presentation: the `Rest` pill, rest-colored styling,
  rest timer label, and recovery copy remain tied to the current rest state.
- Do not show a grip hand diagram during rest. The board highlight is a
  preview, not an instruction to load the board immediately.
- If no later non-rest step exists, leave the board unhighlighted while still
  showing the rest presentation.
- Countdown and completed-session states continue to suppress all highlights.
- A next rest step is skipped when resolving the preview, so consecutive rest
  steps eventually preview the next work step when one exists.

## Architecture and data flow

`WorkoutTimeline` will expose a small, pure lookup for the next non-rest step
after a given step. It will operate on the timeline's existing ordered steps
and return `nil` when no work step follows. `WorkoutView` will use that lookup
only while deriving board highlights:

1. Resolve the current step and elapsed time as today.
2. Compute the existing rest state, expanded to include explicit `.rest` steps.
3. Select the current step for normal work, or the next non-rest step for rest
   preview.
4. Resolve the selected step's hold targets through the existing
   `AppStore.holdIDs(for:on:)` mapping.
5. Pass those IDs to both portrait and landscape `BoardMapView` instances,
   while continuing to pass rest state into the existing headers and cue cards.

No plan-library schema, routine content, board mapping, persistence, audio, or
HealthKit changes are required.

## Edge cases

- A rest block followed by another rest block skips both rest steps.
- A final rest block has no preview and retains the rest indication.
- A countdown before the first step shows no preview highlights.
- At session completion, no preview highlights are shown.
- Direct step selection and skip behavior continue to use the existing full
  step boundaries; this change only affects the board preview and rest-state
  derivation.

## Testing and validation

Add focused `WorkoutTimeline` unit tests proving that the next non-rest lookup
returns the first later work step, skips consecutive rest steps, and returns
`nil` at the end. Add coverage for explicit rest-state derivation if the
derived helper is extracted for testability; otherwise verify it through the
existing workout UI path.

Run the focused and full XCTest targets with `rtk xcodebuild`. Build and install
the DEBUG app on a workspace-dedicated iOS Simulator, then inspect rest and
following-work states in both portrait and landscape. Confirm that the board
previews the next work holds, the `Rest` indication remains visible, no grip
diagram appears during rest, and the final rest block remains unhighlighted.
