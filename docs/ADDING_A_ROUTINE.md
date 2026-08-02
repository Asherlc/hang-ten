# Adding a training routine

This guide defines how Hang Ten imports manufacturer training plans without
quietly rewriting them. Routine fidelity and board mapping are separate audits:
the task prescription must remain exact, while named hold types are resolved
through factual board metadata.

## 1. Start from a primary manufacturer source

Use the manufacturer's current product page, training guide, or manual. Search
the manufacturer's guide index because one company may publish generic and
board-specific plans separately. Record the direct source URL and the date
checked.

Do not use blog summaries, retailer transcriptions, or memory when the official
source is available. If an official page and PDF disagree, report the conflict
and do not guess which is authoritative.

## 2. Classify the routine before importing it

A board-flexible routine names semantic holds such as “Jug,” “Round Sloper,” or
“Large Edge.” It can use `boardID: nil` if every required feature resolves on
the selected board. `AppStore` hides a plan when even one of its targets does
not resolve; DEBUG catalog assertions require semantic targets and at least one
fully compatible registered board.

A board-specific routine refers to numbered holds, a board diagram, or unique
features whose meaning depends on one product. Set its `boardID` and do not show
it on other boards. Implement the physical board and its exact hold IDs first.

Metolius currently demonstrates both cases (sources checked August 1, 2026):

- The [10 Minute Sequences guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide)
  contains Entry, Intermediate, and Advanced routines named by semantic hold
  type. These are the three routines currently in Hang Ten.
- The [Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide)
  uses Contact-board hold numbers.
- The [Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide)
  uses Simulator hold numbers.

Contact is a separate wide training-board model, not a generic exercise name.
Its routines must not be translated onto the Compact II and called identical.

## 3. Preserve the prescription exactly

An official import must preserve:

- routine count and level names;
- task order;
- interval structure;
- every repetition count;
- every prescribed hang, lock-off, or rest duration;
- multi-part task order and “stay on,” switch-hand, or no-rest requirements;
- maximum/failure instructions.

Do not add a warm-up, cooldown, work interval, rest interval, repetition, or
exercise that the source does not place inside the routine. Safety guidance can
appear outside the timed plan and should link back to the manufacturer.

Concise app wording may paraphrase the prose, but it must retain all task data.
Link to the source rather than copying a long guide verbatim.

Set `provenance: .official` only when the prescription above is unchanged. Use
`.adapted` when any task, count, time, order, or interval changes—even if the
adaptation is sensible.

## 4. Model intervals according to the source

The app reads runtime plans from the schema-versioned
`HangTen/Resources/PlanLibrary.json`. Add the audited plan to
`LegacyPlanSeedCatalog` in `TrainingModels.swift`, where it acts as the export
fixture, then run:

```sh
scripts/export-plan-library.sh
scripts/export-plan-library.sh --check
```

`PlanStorage.swift` turns the fixture into reusable block definitions,
semantic targets, source metadata, and provenance, then validates the bundled
JSON before the UI can use it. DEBUG builds compare every resolved JSON plan
against the fixture.

For Metolius ten-minute task cycles:

- create exactly ten `WorkoutStep` values;
- set each `duration` to 60 seconds;
- leave `timedWorkDuration` as `nil`;
- preserve all tasks for that minute in one instruction;
- tell the athlete to rest for whatever remains after completing the tasks.

Do not set `timedWorkDuration` to the first hang duration. A minute can contain
multiple hangs, pull-ups, a hand switch, or a “stay on” transition, and the
manufacturer—not the app—defines when the task is complete.

Use `timedWorkDuration` only when the source explicitly defines one continuous
timed work segment followed by a fixed timed rest segment.

## 5. Resolve holds semantically

Choose the narrowest truthful target:

- `HoldTarget.ids(...)` for board-specific numbered or uniquely identified
  holds;
- `HoldTarget.feature(...)` for manufacturer terms such as `roundSloper`,
  `largeEdge`, or `threeFingerPocket`;
- `HoldTarget.kind(...)` only when the source genuinely allows any hold of that
  broad kind.

`AppStore.holdIDs(for:on:)` resolves targets against the selected
`TrainingBoard`. Add or correct `HoldFeature` metadata in the board catalog;
never hard-code a visual frame into a routine.

If the source names a more specific surface than the manufacturer documents
for a board, keep that source feature as the primary target and declare an
explicit factual fallback in the routine, such as
`.feature(.fourFingerIncutEdge, fallback: .largeEdge)`. Do not tag a generic
edge as both flat and incut merely to make compatibility pass.

For a board-flexible source, semantic resolution may select the closest factual
size available—for example both “Medium Edge” and “Small Edge” can resolve to a
board whose only smaller edges are 19 mm. Keep the source term in the task,
make the board metadata truthful, and disclose the equivalence in review. Never
rename a pocket as a sloper or omit a required target silently.

## 6. Audit the implementation line by line

Build a source comparison before considering the import complete. For every
step, verify:

1. minute/index;
2. first task and hold;
3. second and later tasks in order;
4. every count and duration;
5. switch-hand, stay-on, maximum, failure, or no-rest qualifiers;
6. resolved hold IDs on every compatible board.

The current Metolius catalog should remain three plans, ten 60-second steps per
plan, and 600 seconds total per plan. The source explicitly says to complete
the task or tasks within each minute and use the remaining time to rest.
DEBUG builds also compare the complete official-plan metadata, instructions,
targets, grip cues, and timing against a stable audit fingerprint. Update that
fingerprint only after repeating the line-by-line primary-source audit; never
change it merely to silence an assertion.

Other research and coach protocols in the plan library are deliberately marked
`adapted`: their app versions add guidance, warm-up/cooldown steps, or Compact
II hold mapping. Do not use those plans as precedent for assigning `official`
provenance to a modified manufacturer routine.

Preview representative steps with the DEBUG routes documented in
`docs/IOS_SIMULATOR_VALIDATION.md`. Inspect both the text and active holds.

## Completion checklist

- Primary source and date recorded.
- Generic versus board-specific classification justified.
- Routine count matches the source.
- Step order, repetitions, times, and qualifiers match line by line.
- No unrequested timed work/rest, warm-up, cooldown, or exercise added.
- `official` or `adapted` provenance is honest.
- Every target resolves to at least one factual hold on each compatible board.
- Board-specific plans are hidden from other boards.
- Source link is visible in the app.
- `PlanLibrary.json` was regenerated and passes the exporter's `--check` mode.
- Representative timer, audio, text, and highlight states reviewed.
