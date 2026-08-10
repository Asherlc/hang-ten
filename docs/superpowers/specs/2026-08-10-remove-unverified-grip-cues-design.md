# Remove Unverified Grip Cues Design

## Goal

Remove Hang Ten's app-authored grip/finger cue UI and its plan-level data, while
keeping source-prescribed task text, hold targets, timing, and factual board
hold metadata intact.

## Scope

- Remove the grip diagram and hand/finger cue cards from plan detail and active
  workout layouts in portrait and landscape.
- Remove grip and finger controls from the custom-routine editor.
- Remove `gripType` and `fingerConfiguration` from workout-step and persisted
  plan-step data. Existing JSON that contains these keys must decode safely and
  must not re-emit them; regenerated built-in data must contain neither key.
- Remove cue-only timeline policy/model code and hand cue assets that no longer
  have consumers.
- Keep `BoardHold.gripType`, `fingerCapacity`, and `cueStyle` as board-catalog
  metadata only; these remain useful for factual board rendering and are not
  routine prescriptions.
- Keep task titles, instructions, accessories, source metadata, hold targets,
  timing, and board-map highlights unchanged.

## Architecture

The plan model becomes cue-agnostic: `WorkoutStep`, `WorkoutStepDefinition`,
`CustomRoutineStepDraft`, and the Metolius task seed no longer carry grip or
finger overrides. The board map remains the sole hold visualization, and the
workout timeline continues to resolve highlight IDs without producing a hold
cue object.

Persistence remains backward-compatible for old custom-routine JSON by decoding
and ignoring the removed keys. Encoding and the generated plan library omit the
keys, preventing unverified cue data from surviving or being recreated.

## Verification

- Add/update model and persistence tests proving removed cue keys are ignored
  on decode and absent on encode/export.
- Update custom-routine tests to prove custom steps no longer expose or persist
  cue fields.
- Update timeline/UI-facing tests to prove hold highlighting still resolves and
  no hold-cue policy remains.
- Search the source, generated JSON, and Xcode project for cue UI/data symbols.
- Run the plan-library exporter in check mode, the focused XCTest suite, and a
  Debug simulator build.
