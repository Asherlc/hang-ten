# Self-paced legacy routines: source mapping

Primary sources checked **2026-10-27**. Canonical data is
`HangTen/Resources/PlanLibrary.json`. This mapping supersedes the app timing
estimates described in the October 5 audit. It changes execution boundaries
and adds editable count targets; it does not infer rep durations from counts.
All existing plan provenance remains unchanged.

## Field contract and source boundaries

`repTargets` records source-prescribed counted movements: `minimum` alone for
an exact count or an open-ended count, both bounds for a source range, neither
bound when the source supplies no numeric count. Titles distinguish movements
and sides. Approximate and percentage-of-maximum alternatives remain in the
instructions. A prefilled count is a target; only an athlete's confirmation
establishes an actual count. `isOptional: true` on Advanced minute 2's knee
curls represents the source's L-sit alternative, so it must begin unselected.

`restsAfterCompletion: true` means the athlete can mark the ordered work
finished and use the remaining source cycle as rest. Its clock continues;
completion neither restarts nor extends the cycle. All ten-minute protocols
remain ten 60-second cycles, including their final maximum-effort minute.
Counted work has no app-assumed seconds per repetition. Timed-only Method
minutes retain their fixed hang/rest segments. Instructions keep named hang,
lock-off, change-hand, stay-on, alternative, failure, and no-rest prescriptions.

An uncapped failure effort retains one `stopwatch` segment and omits enclosing
`duration`. A manual ladder omits enclosing `duration` and retains `undefined`.
Hooper's general conditioning can omit board-work segments, as before. Fixed
source hangs and recovery intervals outside the described migrations are
unchanged. No board geometry or factual hold inventory changes.

## Generic Metolius guide

[10 Minute Sequences](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide),
Entry, Intermediate, and Advanced tables and their shared opening instruction.
Each source minute becomes one step, preserving its historic first task ID,
with all original semantic target tasks concatenated in order. Redundant task
and remainder-rest rows are removed. Global grip/finger cues are retained
only when shared by every constituent task; differing cues remain in the
source instructions and per-task hold predicates. These plans remain board
flexible and adapted. No new conversion from source hold-size words to
millimeters is introduced.

The table maps every consolidated minute. Text is the retained app paraphrase
of the named source row. Every row has `duration: 60` and completion-rest;
minutes 1–9 use one `undefined` work segment, minute 10 one bounded `stopwatch`.

| Level / minute | Retained ordered prescription | Editable counted targets |
| --- | --- | --- |
| entry / 1 | Hang from the jugs for 15 seconds. | — |
| entry / 2 | Do 1 pull-up on a round sloper. | Pull-ups: 1 |
| entry / 3 | Hang from a medium edge for 10 seconds. | — |
| entry / 4 | Hang from a pocket for 15 seconds and include 3 shrugs. | Shrugs: 3 |
| entry / 5 | Hang from a large edge for 20 seconds and include 2 pull-ups. | Pull-ups: 2 |
| entry / 6 | Hang from a round sloper for 10 seconds. Do 5 knee raises on a pocket. | Knee raises: 5 |
| entry / 7 | Do 4 pull-ups on a large edge. | Pull-ups: 4 |
| entry / 8 | Hang from a medium edge for 10 seconds. | — |
| entry / 9 | Do 3 pull-ups on the jugs. | Pull-ups: 3 |
| entry / 10 | Hang from a round sloper for as long as you can. | — |
| intermediate / 1 | Hang from a large edge for 15 seconds. Do 3 pull-ups on the large edge. | Pull-ups: 3 |
| intermediate / 2 | Do 2 pull-ups on a round sloper. Hang from a medium edge for 20 seconds. | Pull-ups: 2 |
| intermediate / 3 | Hang from a small edge for 20 seconds. Hold a pocket at a 90° bent arm for 15 seconds. | — |
| intermediate / 4 | Hang from a round sloper for 30 seconds. | — |
| intermediate / 5 | Hang from a large edge for 20 seconds. Do 4 pull-ups on a pocket. | Pull-ups: 4 |
| intermediate / 6 | Do 3 offset pulls with the high hand on a jug and low hand on a small edge. Change hands and repeat 3 offset pulls with the high hand on a jug and low hand on a small edge. | Offset pulls · first arm: 3; Offset pulls · other arm: 3 |
| intermediate / 7 | Do 15 knee raises on the jugs. Hang from a medium edge for 15 seconds. | Knee raises: 15 |
| intermediate / 8 | Hang from a medium edge for 25 seconds. | — |
| intermediate / 9 | Hang from a slope for 15 seconds. Do 3 pull-ups on the jugs. | Pull-ups: 3 |
| intermediate / 10 | Hang from a round sloper for as long as you can. | — |
| advanced / 1 | Hold a straight-arm hang on a large slope for 20 seconds. Do 3 pull-ups on a four-finger flat edge. | Pull-ups: 3 |
| advanced / 2 | Hold a slightly bent-arm hang on a large slope for 20 seconds. Stay on for a 20-second L-sit or 20 hanging knee curls. | Knee curls · if chosen: 20 (optional alternative) |
| advanced / 3 | Do 5 pull-ups on a three-finger pocket. Stay on for a 25-second straight-arm hang on the same three-finger pocket. | Pull-ups: 5 |
| advanced / 4 | Start at a three-finger pocket and move through every hold upward, staying on each for 5 seconds; finish with a 20-second large-slope hang. | — |
| advanced / 5 | Hang one-armed from a four-finger flat edge for 20 seconds. Switch hands and repeat the 20-second one-armed hang from a four-finger flat edge. | — |
| advanced / 6 | Do 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket. Change hands and repeat 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket. | Offset pull-ups · first side: 5; Offset pull-ups · other side: 5 |
| advanced / 7 | Hold a 90° bent-arm hang on a four-finger incut edge for 30 seconds. Then hold a straight-arm three-finger-pocket hang for 15 seconds. | — |
| advanced / 8 | Do 3 L-sit pull-ups, bending your knees if needed. Choose one: hold a 5-second front lever or 15-second straight-arm hang on a large slope. If choosing the front lever, finish at 5 seconds; do not perform both. | L-sit pull-ups: 3 |
| advanced / 9 | Hang straight-armed for 20 seconds using only 2 fingers in three-finger pockets. Then do 3 power pull-ups with weight or helper resistance. | Power pull-ups: 3 |
| advanced / 10 | Do a maximum slightly bent-arm hang on a large slope to failure with no rest, then a maximum straight-arm hang on the large slope. | — |

## Board-specific Metolius cycles

Sources: [Contact](https://www.metoliusclimbing.com/pages/contact-training-guide),
[Simulator 3D](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide),
and [Rock Ring](https://www.metoliusclimbing.com/pages/rock-ring-training-guide).
Each guide explicitly starts the work at the minute boundary and assigns the
remainder to rest. All existing numbered-hold mappings, ordered tasks,
instructions, fixed 60-second outer cycles, and board restrictions remain.
Every cycle gains completion-rest. Only the counted movements listed below
gain count fields; unlisted minutes contain no newly authored rep target.

Existing Contact text/diagram contradictions and Simulator's inconsistent
edge label are retained as documented in `ADDING_A_ROUTINE.md` and the
October 5 source audit. Those conflicts do not justify changing existing hold
mappings during this timing migration. Contact Intermediate minute 3 says
four offset pull-ups each arm; Entry minute 3 says two total, one each arm;
Advanced minute 3 says six total, three each arm. Separate fields preserve
that distinction without changing the instruction.

| Plan suffix (`metolius.`) / minute | Editable source targets |
| --- | --- |
| contact.entry / 1 | Pull-ups: 1 |
| contact.entry / 2 | Pull-up before hang: 1; Pull-up after hang: 1 |
| contact.entry / 3 | Offset pull-ups · first arm: 1; Offset pull-ups · other arm: 1 |
| contact.entry / 5 | Knee raises: 5 |
| contact.entry / 7 | Pull-ups: 3 |
| contact.entry / 9 | Offset pull-ups · first side: 1; Offset pull-ups · other side: 1 |
| contact.entry / 10 | Pull-ups: 2 |
| contact.intermediate / 1 | Pull-ups: 3 |
| contact.intermediate / 2 | Pull-ups: 2 |
| contact.intermediate / 3 | Offset pull-ups · first arm: 4; Offset pull-ups · other arm: 4 |
| contact.intermediate / 7 | Pull-ups: 4; Knee raises: 10 |
| contact.intermediate / 9 | Pull-ups: 4 |
| contact.intermediate / 10 | Pull-ups: 4 |
| contact.advanced / 1 | Pull-ups: 6 |
| contact.advanced / 2 | Pull-ups: 4 |
| contact.advanced / 3 | Offset pull-ups · first arm: 3; Offset pull-ups · other arm: 3 |
| contact.advanced / 7 | L-sit pull-ups: 5 |
| contact.advanced / 8 | Power pull-ups: 3 |
| contact.advanced / 10 | Pull-ups: 8 |
| simulator-3d.entry / 2 | Pull-ups: 1 |
| simulator-3d.entry / 3 | Offset pull-ups · first arm: 1; Offset pull-ups · other arm: 1 |
| simulator-3d.entry / 5 | Knee raises: 5 |
| simulator-3d.entry / 7 | Pull-ups: 3 |
| simulator-3d.entry / 9 | Pull-ups: 1 |
| simulator-3d.intermediate / 2 | Pull-ups: 3 |
| simulator-3d.intermediate / 3 | Knee raises: 10 |
| simulator-3d.intermediate / 7 | Pull-ups: 4; Knee raises: 10 |
| simulator-3d.intermediate / 10 | Pull-ups: 5 |
| simulator-3d.advanced / 1 | Pull-ups: 5 |
| simulator-3d.advanced / 2 | Offset pull-ups · first side: 5; Offset pull-ups · other side: 5 |
| simulator-3d.advanced / 4 | Offset pull-ups · first side: 5; Offset pull-ups · other side: 5 |
| simulator-3d.advanced / 7 | L-sit pull-ups: 5 |
| simulator-3d.advanced / 9 | Power pull-ups: 3 |
| simulator-3d.advanced / 10 | Fast pull-ups: 8 |
| rock-rings.ten-minute / 1 | Pull-ups: 3 |
| rock-rings.ten-minute / 3 | Offset pull-ups · first side: 2; Offset pull-ups · other side: 2 |
| rock-rings.ten-minute / 5 | Pull-ups: 5 |
| rock-rings.ten-minute / 10 | Pull-ups: 5 |

## Method EMOM

[Intermediate Hangboarding, Workout 2](https://methodclimb.com/blog/intermediate-hangboarding),
redirected from the retained plan source URL. The source explicitly assigns
one minute per row with rest after its listed work. Minutes 2, 3, 5, 7, and 9
become one ordered `undefined` work segment plus completion-rest; their count
targets are respectively 3 jug pull-ups, 5 jug knee raises, 3 jug pull-ups,
3 offset pull-ups, and 10 jug knee raises. Their instructed preceding hangs
remain respectively 15 seconds on deep three-finger pockets, 10 seconds on
20 mm, 10 seconds on sloper, no preceding hang in minute 7, and 20 seconds
on 20 mm. Minute 7 retains simultaneous jug/small-edge hand targets. No
change-hand repeat is invented for that minute. Minutes 1/4/6/8 retain fixed
20/15/10/25-second work and remainder rest. Minute 10 remains a maximum
sloper hang inside its source 60-second minute and gains completion-rest.

## Hooper's Beta

[Introductory Home Hangboard](https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine),
Warm up and Rounds 1–5. Only the seven warm-up conditioning rows and optional
paired Round 5 rows lose their app-assumed 60-second durations. Source
recovery windows remain: Round 1 starts 60 seconds immediately after each
30-second hang, Rounds 2/3 start 90 seconds after recruitment/weighted work,
and Round 4 starts a full 180 seconds after each 12-second hang. Conditioning
inside each recovery window gains completion-rest; completing it never
shortens that recovery. Existing timed hang steps and optional set structure
remain unchanged.

| Step family | New count mapping | Source qualifier / retained timing |
| --- | --- | --- |
| Normal pull-ups | 10 | Or approximately 75% maximum; self-paced |
| Normal push-ups | 10–20 | Or approximately 75% maximum; self-paced |
| Wide/narrow pull-ups and push-ups | No numeric default | Source names movement without a numeric count |
| Foam roll | No rep field | No source standalone duration |
| Round 1 taps, both sets | 30–40 | Or fatigue/form limit; within 60-second recovery |
| Round 2 kicks, all sets | Flutter 20–30; scissor 20–30 | Distinct fields; within 90-second recovery |
| Round 3 side plank, all sets | Hip abduction approximately 10 per side | Distinct left/right count fields; within 90-second recovery |
| Round 4 bird dog/stretch recovery | No rep field | 45–60 seconds bird dog and stretching within full 180-second recovery |
| Optional Round 5 pull-ups (all four authored sets) | Unbounded `pull-ups` count field; no numeric default | Freestyle ledges/offsets; 2–4 paired sets; no source per-set rep count |
| Optional Round 5 hollow rocks | 10–20 | Then hold; self-paced; retain source approximate 10-second pause before hold |

The linked article, rather than model assumptions, governs unknown rep counts.
The 2–4 figure counts optional paired sets, not pull-ups per set. Existing
source-linked open-hand, form, and hold cues remain intact. Source has no
fixed duration for the final hollow hold.

## Failure and athlete-paced protocols

| Plan IDs / source section | Changed source fields | Retained prescriptions and labeled adaptations |
| --- | --- | --- |
| `coach.density-hangs`, `coach.nelson-density-hangs.expert` / [Nelson, Workout 2](https://www.trainingbeta.com/the-simplest-finger-training-program/) | Remove 60-second outer work preview; retain uncapped stopwatch; replace pause/skip instructions with Done | Slow two-arm muscular failure, approximately 20–40 seconds; existing Table 2 grip/effort counts and selected 180-second recovery within source 3–5-minute range unchanged |
| `tension-long-hangs` / [Long Hangs](https://tensionclimbing.com/blogs/blog/hangboarding-a-way) | Remove 15-second outer cap; retain uncapped stopwatch; replace pause/skip instructions with Done | Form failure; load for 15–30 seconds, source allows 3–5 hangs and 2–4-minute recoveries; app still selects 3 hangs and 120 seconds |
| `tension-6-6-6-plus` / [6:6×6+](https://tensionclimbing.com/blogs/blog/hangboarding-a-way) | Remove 72-second aggregate cap; retain uncapped stopwatch; rep target minimum 6, no maximum; replace pause/skip instructions with Done | Source 6 seconds on / 6 seconds off, 6+ repetitions to form failure, 2-minute recovery; app still selects 4 sets from 4–6 and splits half/open crimp; stopwatch includes intra-set rests |
| `coach.bechtel-three-six-nine` / [Bechtel interview, 49:21–52:11](https://www.powercompanyclimbing.com/blog/2016/01/episode-2-resistance-training-with.html) | Remove 60-second ladder cap; retain `undefined`; replace pause/skip instructions with Done | Same hold/load for 3/6/9-second hangs, athlete-chosen rests, initial hold/load permitting 15 seconds. Three ladders remains explicitly an app volume adaptation, not a source round count |

Completion controls and editable actual-count entry are app presentation,
not additional coaching claims. The authored notes now state the execution
behavior directly rather than instructing athletes to pause a fake timer.

## Verification contract

`scripts/tests/test_original_routine_sources.py` checks source counts, unknown
numeric targets, optional alternatives, source-minute totals and boundaries,
ordered predicates, preserved named hangs, source recovery windows, and uncapped
failure efforts. `HangTenTests/PlanStorageTests.swift` retains exact expanded
JSON prescription fingerprints and source-target/runtime expectations. Only
these 17 migrated plans' fingerprints change. Fingerprints include metadata
and expanded source steps, serialized with sorted keys and unescaped slashes
before SHA-256; no runtime timer expansion is hashed.
