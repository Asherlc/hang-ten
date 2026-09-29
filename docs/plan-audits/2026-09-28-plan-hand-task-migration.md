# Bundled plan hand task audit — 2026-09-28

The existing source audit in [`TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md`](../TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md) maps each of the 26 plan IDs, exercise instructions, times, and hold predicates to its source URL. This migration changes the grouping and hand count of those existing predicates. No source duration, exercise name, or grip prescription is added here.

## Mapping rules

- A work step with one listed hold predicate becomes one task with two equal hand targets. This is the catalog default approved for this migration, unless the cited source explicitly says one arm or one hand. It also applies to the 7/3 repeaters: one open edge predicate yields two hand targets.
- A source that says "any holds" yields `[{"target":"any"},{"target":"any"}]`. It states the athlete chooses each hold and keeps the two-hand count. In particular, [Contact Training Guide](https://www.metoliusclimbing.com/pages/contact-training-guide) Entry minutes 4, 7, and 10 and [Simulator 3D Training Guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) Entry minute 10 use this language. A subsequent specified hold is a later task.
- Two different hold predicates joined by "&" in an offset move form **one simultaneous task**. "Change hands", "other way", "reverse holds", or a per-side duration yields a second task with the predicate order reversed. The task array represents source order; the original minute or step timing remains unchanged.
- Consecutive moves separated by semicolons, a subsequent dead hang, a bump, or a campus instruction form consecutive tasks. The [generic Metolius advanced](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) hold ladder (minute 4) retains its four sequential predicates; each defaults to two hands. Neither the source nor this representation assigns invented subtask times.
- Source phrases "one arm" and "other arm" produce one-hand tasks. A starting side is left unspecified when the source does not choose it. The [Megos protocol](https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/) has explicit left/right step IDs and keeps those sides.

## Steps with simultaneous mixed holds

The `offsetSteps` and `reversedOffsetSteps` sets in `PlanTaskMigration` are the executable mapping. The source-to-ID groupings are:

| Source | Step IDs (minute unless shown) | Mapping |
| --- | --- | --- |
| [Metolius 10 Minute Sequences](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | Intermediate 6 tasks 1–2; Advanced 6 tasks 1–2 | One jug/edge or sloper/pocket pair per task; the second source task changes hands. |
| [Contact Training Guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Entry 3, 6, 9; Intermediate 3, 5, 6; Advanced 3, 8 | Two simultaneous targets, then the source's opposite-hand task. Entry 9 and Advanced 3 continue to their next prescribed hold. |
| [Simulator 3D Training Guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | Entry 3, 6; Intermediate 5, 6; Advanced 2, 4, 9 | Two simultaneous targets followed by the reverse orientation. |
| [Rock Ring Training Guide](https://www.metoliusclimbing.com/pages/rock-ring-training-guide) | 3, 8 | Four-finger and two-finger holds together, then the other way. |

The explicitly one-arm steps are generic Metolius Advanced minute 5 tasks 1–2; Contact Intermediate minute 9 and Advanced minute 6; Simulator 3D Intermediate minute 9 and Advanced minute 6; and every left/right repetition of the Megos protocol. In the mixed Contact Intermediate minute 9, the subsequent center-edge pull-ups remain a two-hand task.

All other bundled work steps use the approved two-hand default. Their plan source URLs and existing predicate audit are in the previous source audit and in each `PlanDefinition.metadata.sourceURL`. The bundled JSON has 487 work targets, each using `tasks`; the schema validator checks every one.

## Center hold capacity evidence

The [Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide) prescribes ordinary dead hangs or pull-ups on center edge #17 (Entry 1 and 10, Intermediate 7 and 9), medium center edge #18 (Advanced 3), and the flat center sloper #15 (Entry 5, Intermediate 10, Advanced 10), while identifying one-arm hangs explicitly elsewhere. Under the approved two-hand default, these tasks need one shared center contact with capacity two. `Hangboards/metolius-contact/board.json` now records that capacity on those three contact records. The [Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) similarly prescribes ordinary two-hand hangs on its center round sloper #3 (Entry 8, Intermediate 4 and 10, Advanced 10), so its corresponding contact records capacity two. These are hold metadata edits only; no geometry or model asset changed.

## Source discrepancy retained for follow-up

The currently published Contact guide describes its #11 hold as a **pinch** in Entry minute 4, whereas the checked-in board inventory labels #11 a two-finger pocket and the older source-audited plan text uses that label. This migration retains the existing predicate and wording pending a separate manufacturer revision audit, rather than silently changing the exercise or board inventory.
