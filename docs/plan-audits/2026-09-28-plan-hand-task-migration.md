# Bundled plan hand task audit — 2026-09-28

The earlier [`TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md`](../TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md) covers Hooper's Beta, Method, REI, and RPTC. The table below links the source for every bundled plan. This migration changes the grouping and hand count of existing predicates; it adds no duration, exercise name, or grip prescription.

## Mapping rules

- A work step with one listed hold predicate becomes one task with two equal hand targets. This is the catalog default approved for this migration, unless the cited source explicitly says one arm or one hand. It also applies to the 7/3 repeaters: one open edge predicate yields two hand targets.
- A source that says "any holds" yields `[{"target":"any"},{"target":"any"}]`. It states the athlete chooses each hold and keeps the two-hand count. In particular, [Contact Training Guide](https://www.metoliusclimbing.com/pages/contact-training-guide) Entry minutes 4, 7, and 10 and [Simulator 3D Training Guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) Entry minute 10 use this language. A subsequent specified hold is a later task.
- Two different hold predicates joined by "&" in an offset move form **one simultaneous task**. "Change hands", "other way", "reverse holds", or a per-side duration yields a second task with the predicate order reversed. The task array represents source order; the original minute or step timing remains unchanged.
- Consecutive moves separated by semicolons, a subsequent dead hang, a bump, or a campus instruction form consecutive tasks. The [generic Metolius advanced](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) hold ladder (minute 4) retains its four sequential predicates; each defaults to two hands. Neither the source nor this representation assigns invented subtask times.
- Source phrases "one arm" and "other arm" produce one-hand tasks. A starting side is left unspecified when the source does not choose it. The [Megos protocol](https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/) and F100 protocol have explicit left/right step IDs and keep those sides. Hooper's Beta prescribes each hand but not a starting side; its pre-existing left-then-right step order is an app adaptation, retained and now labeled here.

## Plan-by-plan source and hand mapping

The source URL in each row is also retained in `PlanDefinition.metadata.sourceURL`. “Default” means the approved two-hand count for source steps without an explicit one-arm direction; the mixed and one-arm exceptions are identified by source step or exported step ID below. The offset mapping table following this one gives the simultaneous/reversed task IDs.

| Bundled plan ID(s) | Source | Hand mapping |
| --- | --- | --- |
| `metolius.generic-ten-minute.entry`, `metolius.generic-ten-minute.intermediate` | [Metolius 10 Minute Sequences](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | Default; Intermediate minute 6 has two simultaneous mixed-hold tasks. |
| `metolius.generic-ten-minute.advanced` | [Metolius 10 Minute Sequences](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | Default except minute 5 tasks 1–2, which say one arm; minute 6 has mixed-hold tasks. |
| `metolius.contact.entry` | [Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Default; minutes 3, 6, and 9 are mixed-hold offset tasks. |
| `metolius.contact.intermediate` | [Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Default except minute 9's two one-arm sloper tasks; its later center-edge pull-ups are two-hand. Minutes 3, 5, and 6 are offsets. |
| `metolius.contact.advanced` | [Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Default except minute 6's one-arm tasks; minutes 3 and 8 are offsets. |
| `metolius.simulator-3d.entry` | [Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | Default; minutes 3 and 6 are offsets. |
| `metolius.simulator-3d.intermediate` | [Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | Default except minute 9's one-arm tasks; minutes 5 and 6 are offsets. |
| `metolius.simulator-3d.advanced` | [Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | Default except minute 6's one-arm tasks; minutes 2, 4, and 9 are offsets. |
| `metolius.rock-rings.ten-minute` | [Rock Ring guide](https://www.metoliusclimbing.com/pages/rock-ring-training-guide) | Default; minutes 3 and 8 combine four- and two-finger holds, then reverse. |
| `rptc.seven-three-repeaters` | [Trango RPTC instructions](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155) | Each of seven source-prescribed two-handed hangs has two `target: "any"` entries because the athlete chooses the grip. |
| `research.max-hangs` | [Lattice Max Hangs](https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/) | Default. |
| `research.force-feedback-f80` | [Force feedback study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | Source says both hands for F80. |
| `research.force-feedback-f100` | [Force feedback study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | Its 24 right/left hand steps are each one-hand tasks with the stated side. |
| `research.eva-int-hangs` | [Eva López comparison](https://pubmed.ncbi.nlm.nih.gov/30988852/) | Default; hold choice stays `target: "any"`. |
| `research.seven-three-repeaters` | [7/3 repeaters study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full) | Default, including the compact-board paired 29 mm edge cue. |
| `research.megos-one-arm-7-3` | [Megos protocol](https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/) | All left/right repetition steps are one-hand tasks with the stated side. |
| `research.abrahangs` | [Lattice Abrahangs](https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol) | Default. |
| `coach.horst-seven-fifty-three` | [Hörst protocols](https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/) | Default. |
| `coach.bechtel-three-six-nine` | [Bechtel ladders](https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/) | Default; hold choice stays `target: "any"`. |
| `coach.density-hangs` | [Density hangs](https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/) | Default. |
| `device.zlagboard-sixty-sixty` | [Zlagboard endurance workout](https://strengthclimbing.com/zlagboard-forearm-endurance-workout/) | Default. |
| `hoopers-beta.introductory-home-hangboard` | [Hooper's Beta introductory routine](https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine) | Default except Round 2's 30 single-arm recruitment pulls. The source says five reps per hand for three sets. The existing plan's left-then-right order is an app adaptation; each step is now one hand on its app-stated side. |
| `method.intermediate-hangboarding.repeaters`, `method.intermediate-hangboarding.emom` | [Method intermediate hangboarding](https://methodclimb.com/intermediate-hangboarding/) | Default; EMOM offset work keeps simultaneous mixed holds. |
| `rei.hangboard-sample-workout` | [REI sample workout](https://www.rei.com/learn/expert-advice/how-to-use-a-hangboard-to-train-for-rock-climbing.html) | Default. |

## Steps with simultaneous mixed holds

The `offsetSteps` and `reversedOffsetSteps` sets in `PlanTaskMigration` are the executable mapping. The source-to-ID groupings are:

| Source | Step IDs (minute unless shown) | Mapping |
| --- | --- | --- |
| [Metolius 10 Minute Sequences](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | Intermediate 6 tasks 1–2; Advanced 6 tasks 1–2 | One jug/edge or sloper/pocket pair per task; the second source task changes hands. |
| [Contact Training Guide](https://www.metoliusclimbing.com/pages/contact-training-guide) | Entry 3, 6, 9; Intermediate 3, 5, 6; Advanced 3, 8 | Two simultaneous targets, then the source's opposite-hand task. Entry 9 and Advanced 3 continue to their next prescribed hold. |
| [Simulator 3D Training Guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) | Entry 3, 6; Intermediate 5, 6; Advanced 2, 4, 9 | Two simultaneous targets followed by the reverse orientation. |
| [Rock Ring Training Guide](https://www.metoliusclimbing.com/pages/rock-ring-training-guide) | 3, 8 | Four-finger and two-finger holds together, then the other way. |
| [Method intermediate hangboarding](https://methodclimb.com/intermediate-hangboarding/) | `method-emom-minute-7` | Three offset pull-ups use one jug and one small edge simultaneously. The source gives no pull-up duration; the existing app estimate is 5 seconds per rep, so this single 15-second work segment leaves 45 seconds of the EMOM minute for rest. |

The explicitly one-arm steps are generic Metolius Advanced minute 5 tasks 1–2; Contact Intermediate minute 9 and Advanced minute 6; Simulator 3D Intermediate minute 9 and Advanced minute 6; every left/right repetition of the Megos protocol; all 24 F100 right/left steps; and Hooper's Beta Round 2's 30 right/left pulls. In the mixed Contact Intermediate minute 9, the subsequent center-edge pull-ups remain a two-hand task.

All other bundled work steps use the approved two-hand default. The bundled JSON has 493 explicit work targets, each using `tasks`; the schema validator checks every one.

## Center hold capacity evidence

The [Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide) prescribes two-hand hangs or pull-ups on center edge #17 (Entry minutes 1 and 10; Intermediate minutes 7 and 9, after the explicitly one-arm sloper hangs) and medium center edge #18 (Entry minute 3). The guide prescribes a two-hand hang on flat center sloper #15 in Entry minute 5 and Intermediate minute 10. Advanced minute 6 is explicitly one-arm on #17 and is not capacity-two evidence. Advanced minute 10 names a flat sloper #3; the guide's numbered diagram instead identifies #3 as a round sloper and #15 as the flat sloper, so that routine line does not establish the #15 mapping. Under the approved two-hand default, the supported tasks require a shared center contact with capacity two. `Hangboards/metolius-contact/board.json` records that capacity on center contacts #17, #18, and #15.

The [Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide) prescribes ordinary two-hand use of center round sloper #3 in Entry minute 8, Intermediate minute 4, and Advanced minute 10. The package has one center contact for #3, `round-sloper-3-center`, with capacity two. The Simulator 3D board has exactly one capacity-two contact record. These are hold metadata edits only; no geometry or model asset changed.

## Contact guide and numbered-diagram conflicts

Checked September 28, 2026 against the [current Contact routine table](https://www.metoliusclimbing.com/pages/contact-training-guide) and the [numbered hold diagram embedded in that same guide](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/con-num-dep.jpg?v=1759520708). The manufacturer publishes conflicting descriptions for these numbered holds. The board inventory follows the numbered diagram. The plan text and predicates generally keep the routine's printed hold *number* and use the diagram's physical hold type; those are explicit source reconciliations, not independent grip prescriptions.

| Routine minute(s) | Routine table description | Numbered diagram | Current plan mapping |
| --- | --- | --- | --- |
| Entry 2 | #4 four-finger edge | #4 30 mm four-finger pocket | #4 pocket |
| Entry 4, Intermediate 4, Advanced 4 | #11 pinch | #11 25 mm two-finger pocket | #11 pocket |
| Entry 8 and Entry 9 final hang | #3 four-finger hold | #3 63 mm round sloper | #3 round sloper |
| Entry 9 offset | #1 jug and #11 pinch | #1 variable pinch and #11 two-finger pocket | #1 pinch and #11 pocket |
| Intermediate 2; Advanced 1, 2, and 3 | #2 round sloper | #2 outer jug | #2 jug |
| Intermediate 8 | #7 two-finger pocket | #7 30 mm three-finger pocket | #7 three-finger pocket |
| Intermediate 9 | #3 jug | #3 round sloper | #3 round sloper |
| Advanced 1, 3, and 7 | #4 two-finger pocket | #4 30 mm four-finger pocket | #4 four-finger pocket |
| Advanced 5 | #2 round sloper | #2 outer jug; #3 round sloper | #3 round sloper |
| Advanced 7 | #1 jug | #1 variable pinch | #1 pinch |
| Advanced 10 first hold | #3 flat sloper | #3 round sloper; #15 flat sloper | #15 flat sloper |

Advanced minutes 5 and 10 are different from the number-preserving cases: the current plan follows the table's *hold type* and changes its printed number. Neither source explains whether the name or number is the typo. These two mappings remain unresolved manufacturer-source ambiguities; do not treat #3 or #15 as a verified correction to the table. The [product manual](https://cdn.shopify.com/s/files/1/0955/0030/4457/files/Training-Board-instructions.pdf?v=1759261826) contains general training and installation instructions, but no alternate numbered routine that settles them. The numbered-diagram reconciliation above changed no board geometry or hold metadata; the center-capacity edits are described separately in “Center hold capacity evidence.”
