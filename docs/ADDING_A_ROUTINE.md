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

Set `provenance: .official` only when the prescription above—including task
timing and interval structure—is unchanged. Use `.adapted` when any task,
count, time, order, or interval changes, even if the adaptation is sensible.
A faithful expansion that keeps every source task, count, qualifier, and
source-order relationship but adds explicit app-guided task/rest timing is an
`.adapted` import; document the app timing rather than presenting it as the
manufacturer's prescription.

## 4. Model intervals according to the source

The app reads runtime plans from the schema-versioned
generated, ignored `HangTen/Resources/PlanLibrary.json`. Add the audited plan to
`LegacyPlanSeedCatalog` in `TrainingModels.swift`, where it acts as the export
fixture, then build the board resources needed by the exporter's staging step
and regenerate the library:

```sh
rtk proxy bash scripts/build-board-assets.sh
rtk scripts/export-plan-library.sh
rtk scripts/export-plan-library.sh --check
```

`PlanStorage.swift` turns the fixture into reusable block definitions,
semantic targets, source metadata, and provenance, then validates the bundled
JSON before the UI can use it. DEBUG builds compare every resolved JSON plan
against the fixture.

Commit the audited Swift definitions and source mappings. The JSON is rebuilt
from those sources locally and in CI; it is not a second editable plan source.
For a complete fresh-checkout app build run `scripts/build-runtime-assets.sh`
before Xcode. See [generated artifacts](GENERATED_ARTIFACTS.md).

For an unchanged official import, preserve the source's ten-minute task-cycle
structure exactly and leave `timedWorkDuration` `nil` unless the source
explicitly defines a continuous timed work segment. For a faithful adapted
Metolius expansion:

- retain ten source cycles of 60 seconds each and preserve task order;
- give each listed task its own guided step and add an explicit rest step for
  the unused portion of that source minute;
- keep generated task steps step-local: they may set `timedWorkDuration` to the
  fixed task's own duration even when no rest follows, while unused minute time
  is represented by a separate `.rest` step;
- use five seconds per pull-up and one second per other counted repetition
  only when Metolius gives no duration, and state that these are app defaults;
- keep explicit source hang durations unchanged and preserve stay-on,
  hand-switch, maximum, failure, and no-rest qualifiers.

Do not set `timedWorkDuration` to the first hang duration. A minute can contain
multiple hangs, pull-ups, a hand switch, or a “stay on” transition, and the
manufacturer—not the app—defines when the task is complete.

## 5. Resolve holds semantically

Choose the narrowest truthful `PlanContactPredicate` for each hand. Bundled
routines use ordered `tasks`; each task contains one or two simultaneous hand
targets. Routines never contain board contact IDs or visual-frame references:

- `kind` for a source term such as “jug,” “edge,” or “pocket”;
- `shape` only for a documented physical qualifier such as “flat,” “round,”
  “incut,” or “slot”;
- `depth: {"category":"medium"}` for a source size word, or
  `depth: {"minMM":20,"maxMM":35}` for a stated measurement or an explicitly
  documented inferred band in an adapted plan. Never present an inferred band
  as a manufacturer prescription; use equal bounds for one exact measurement;
- `fingerCapacity` when the source specifies it, and `handCapacity` only when
  source evidence supports multiple hands sharing one contact;
- `target: "any"` when the source explicitly lets the athlete choose a hold.

Default to two hand entries unless the source prescribes one arm. Put different
holds used together in the same task, and put successive holds in successive
tasks. Use `side: "left"` or `"right"` only when the source names a side. The
number of entries in a task is the hand count; do not add a separate `hands`
field. See [`PlanWorkTarget.schema.json`](schemas/PlanWorkTarget.schema.json).

The resolver matches those predicates against factual board metadata. Do not
hard-code a contact ID or visual frame into a routine. If the source names a
surface that the board inventory cannot represent, retain the source wording in
the instruction and omit that target; document the unresolved fact rather than
substituting another hold.

For a board-flexible source, semantic resolution may select the closest factual
size available—for example both “Medium Edge” and “Small Edge” can resolve to a
board whose only smaller edges are 19 mm. Keep the source term in the task,
make the board metadata truthful, and disclose the equivalence in review. Never
rename a pocket as a sloper or omit a required target silently.

### Metolius edge-name cross-reference (checked September 29, 2026)

The [10 Minute Sequences guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide)
uses Large, Medium, and Small Edge without millimeter measurements. The separate
[Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide)
uses numbered deep, medium, shallow, and extra-shallow edges. Metolius's
[numbered depth diagram](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/sim-num-dep.jpg?v=1759460619)
provides the following measurements. Matching the generic names across the
two guides is an inference, not a manufacturer-published conversion table.

| Generic guide term | Simulator 3D term | Number | Depth |
| --- | --- | ---: | ---: |
| Large Edge | Deep edge | 7 | 36 mm |
| Medium Edge | Medium edge | 5 | 25 mm |
| Small Edge | Shallow edge | 6 | 19 mm |
| No generic counterpart | Extra-shallow edge | 11 | 14 mm |

The Simulator matrix calls #5 “shallow” once in its Entry minute 6, despite
calling it “medium” elsewhere; the diagram still measures #5 at 25 mm. The
cross-reference supports an inferred 8–19 mm resolution band for the Metolius
generic plan's Small Edge tasks: 8–15 mm comes from Hang Ten's existing Small
category, and the inferred 19 mm upper bound admits Metolius's shallow edge.
This is specific to those tasks; the shared Small category remains 8–15 mm for
other plans and saved routines. The band overlaps Medium Edge on a board with
only two edge depths. On Simulator 3D, Hang Ten's center-nearest resolver
currently highlights the same #6 19 mm edge for both generic Small Edge and
Medium Edge tasks; that overlap is an app mapping, not a manufacturer-published
equivalence. It is not a manufacturer-prescribed numeric range and
does not change any contact's factual depth. Because numeric `HoldDepth.matches`
allows 1 mm of tolerance on each end, the serialized requirement uses 9–18 mm
to match point-depth contacts from 8 through 19 mm, excluding 7.5 and 20 mm.
Contacts with measured depth ranges still match when their range intersects
that band. The Intermediate generic guide's
minute 9 says only “Slope,” so its target is an unqualified sloper. Its
Advanced section explicitly says “Large Slope,” and that target remains
size-qualified.

## 6. Audit the implementation line by line

Build a source comparison before considering the import complete. For every
step, verify:

1. minute/index;
2. first task and hold;
3. second and later tasks in order;
4. every count and duration;
5. switch-hand, stay-on, maximum, failure, or no-rest qualifiers;
6. resolved hold IDs on every compatible board.

The current Metolius catalog should remain three plans with ten 60-second source
cycles per plan and 600 seconds total per plan. Guided expansion generates 20
steps for Entry, 26 for Intermediate, and 27 for Advanced; these generated
counts differ from the ten source cycles. The source explicitly says to
complete the task or tasks within each minute and use the remaining time to
rest.
DEBUG builds validate the current adapted Metolius audit with assertions for
step order, target mapping, timing, generated numbering, and the 60-second
cycle structure.

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
- Every simultaneous task resolves to factual hold contacts on each compatible board.
- Board-specific plans are hidden from other boards.
- Source link is visible in the app.
- `PlanLibrary.json` was regenerated and passes the exporter's `--check` mode.
- `scripts/validate-plan-work-targets.sh` validates every bundled work target.
- Representative timer, audio, text, and highlight states reviewed.
