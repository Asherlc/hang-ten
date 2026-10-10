# Adding a training routine

This guide defines how Hang Ten adds source-backed training plans. Audit the
prescription separately from board compatibility: preserve every sourced task,
and label adaptations and inferred mappings explicitly.

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
“Large Edge.” Use `boardID: nil` when the source is board-agnostic, and retain
every prescribed semantic hand target. `AppStore` lists these plans on every
board; compatibility is assessed separately, and unresolved targets mark the
plan “Needs hold substitutes.” The plan detail page offers explicit choices
from the selected board's factual inventory before the athlete starts.

Catalog resolution checks apply to plans with a declared `boardID`, not every
board-agnostic routine. Non-custom, source-linked board-agnostic work may record
as self-selected when its prescribed requirements or hand tasks cannot resolve.
Test each board mapping claimed to support the full source prescription.

A board-specific routine refers to numbered holds, a board diagram, or unique
features whose meaning depends on one product. Set its `boardID`; the app filters
it out on other boards. Implement and audit that physical board first, then map
the source's numbered holds to factual requirements supported by its inventory.

Metolius demonstrates both cases:

- The [10 Minute Sequences guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide)
  contains Entry, Intermediate, and Advanced routines named by semantic hold
  type. Hang Ten retains these three routines as adapted guided expansions.
- The [Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide)
  uses Contact-board hold numbers.
- The [Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide)
  uses Simulator hold numbers.

The catalog also includes the three Contact routines, three Simulator 3D
routines, and the [Rock Ring sequence](https://www.metoliusclimbing.com/pages/rock-ring-training-guide)
as board-specific source cycles. Use their audited requirement mappings rather
than copying numbered holds onto another board.

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

Both apps read the checked-in canonical `HangTen/Resources/PlanLibrary.json`.
Add the audited plan directly to its reusable block definitions and plan
references, retaining source metadata and provenance. Build board resources
before validating factual board compatibility, and validate the work targets:

```sh
rtk proxy bash scripts/build-board-assets.sh
rtk scripts/validate-plan-work-targets.sh
```

`PlanStorage.swift` decodes and validates the bundled JSON, then resolves its
blocks into runtime steps. Source-prescription tests inspect the canonical
definitions before segment expansion and verify the resulting runtime plans.

Commit the canonical JSON and source mappings for every changed field. There
is no separate Swift authoring catalog or plan export step.
Use reusable blocks and `repeatCount` for identical prescribed steps or cycles.
The count includes the first run. Keep different final efforts, recoveries,
targets or instructions separate. Reference `stepIDs` and `stepTitles` may
preserve the complete expanded sequence of historic identities and numbered
labels without copying the prescription. Do not flatten repeated blocks into
copied source rows to make the preview look repetitive: previews now render
only authored repetition. See the [canonical library mapping](source-audits/2026-10-05-canonical-plan-library.md)
for the override format and lossless authoring checks.

For a complete fresh-checkout app build run `scripts/build-runtime-assets.sh`
before Xcode. See [generated artifacts](GENERATED_ARTIFACTS.md).

For an unchanged task-cycle import, preserve the source's cycle structure and
leave `timedWorkDuration` `nil` unless the source explicitly defines a continuous
timed work segment. The official Metolius board-specific plans keep each
manufacturer minute as one source-governed cycle with remaining-time rest. The
adapted generic Metolius expansions:

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

## 5. Model source-backed hold targets

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
- `fingerCapacity` when the source specifies it. For edges this is the minimum
  room needed for the grip: larger authored capacities qualify, and omitted edge
  capacity adds no restriction. An explicitly smaller edge is rejected. For
  pockets and other kinds, capacity identifies the named hold size and remains
  an exact match; omitted capacity cannot establish that size;
- `target: "any"` when the source explicitly lets the athlete choose a hold.

Catalog packages require an authored capacity on every contact; see
[board authoring](ADDING_A_BOARD.md). The resolver's unknown-capacity handling
supports synthetic contacts and older activity snapshots. Reviewed board
capacity estimates do not establish a plan's finger or grip prescription.

Each task has one or two hand entries according to the sourced hand use. Put
holds used together in the same task and successive holds in successive tasks.
Use `side: "left"` or `"right"` only when the source names a side. The entry
count is the hand count; `hands` and `handCapacity` are not plan-predicate fields.
Factual board capacity governs whether two hands can share one contact. See
[`PlanWorkTarget.schema.json`](schemas/PlanWorkTarget.schema.json).

The resolver filters factual contacts by the predicate and the step's grip
metadata, then chooses contacts within that matching set. It does not broaden a
failed predicate to the closest size or substitute another hold type. Keep the
source wording and document unresolved compatibility rather than inventing a
target. `PlanHoldSubstitutions` is a separate athlete-choice flow: it groups
repeated missing requirements, verifies alternative holds with the same
resolver, and requires an explicit selection for every missing target. It keeps
task order, hand use, finger/grip cues, timing, rest, repetitions, and load, while
changing only the chosen task targets in the session copy. Its choices show the
actual resolved contact names; they do not claim that another hold is equivalent
to a manufacturer prescription. The session is marked `adapted` (an existing
custom routine remains `custom`), and affected instructions identify the chosen
substitutes separately from the retained original plan text. The source-linked
catalog and its audit mappings remain the original prescription. Board-specific
catalog routines remain restricted to their declared board. Requirements with
no valid alternative remain unavailable.
Required-hold labels omit internal numeric range bands: some compensate for
matching tolerance or an audited size inference and are not source-prescribed
measurements. The original source wording remains in the instructions; substitute
choices show the selected board's actual measured depths, including effective
depths for adjustable positions.

The legacy `.selfSelected` work form is restricted to the validator's
explicit source allowlist and custom plans. Modern `tasks` may contain
`target: "any"` without that allowlist; this structural permission does not
establish a source prescription. Justify every athlete-choice target from the
plan's evidence. Custom athlete-authored routines may also use exact contact IDs.

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

The three generic Metolius plans each retain ten 60-second source cycles and
600 seconds total. Their guided step counts differ from the ten source cycles.
The source explicitly says to
complete the task or tasks within each minute and use the remaining time to
rest.
Catalog tests validate the current adapted Metolius audit with assertions for
step order, target mapping, timing, generated numbering, and the 60-second
cycle structure.

Other research and coach protocols in the plan library are deliberately marked
`adapted`: their app versions add guidance, warm-up/cooldown steps, or Compact
II hold mapping. Do not use those plans as precedent for assigning `official`
provenance to a modified manufacturer routine.

Preview representative steps with the DEBUG routes documented in
[the simulator guide](IOS_SIMULATOR_VALIDATION.md). Inspect both the text and
active holds.

## Completion checklist

- Primary source and date recorded.
- Generic versus board-specific classification justified.
- Routine count matches the source.
- Step order, repetitions, times, and qualifiers match line by line.
- No unrequested timed work/rest, warm-up, cooldown, or exercise added.
- `official` or `adapted` provenance is honest.
- Every target maps to source evidence and resolves on the boards claimed compatible.
- Board-specific plans are hidden from other boards.
- Source link is visible in the app.
- Canonical `PlanLibrary.json` changes and their source mappings are committed.
- `scripts/validate-plan-work-targets.sh` validates every bundled work target.
- Representative timer, audio, text, and highlight states reviewed.
