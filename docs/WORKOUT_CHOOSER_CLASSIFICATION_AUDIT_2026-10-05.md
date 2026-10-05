# Workout chooser classification audit — 2026-10-05

The chooser's focus is optional editorial metadata, not a new exercise
prescription or a guaranteed training outcome. Classifications below are
explicitly **Hang Ten adaptations of source terminology**. They do not change
routine provenance, instructions, counts, timing, targets, or source summaries.
Unclassified routines remain discoverable under All workouts and exercise
filters. No goal is inferred from board metadata, difficulty, or a `.pull` phase.

Primary pages were checked on October 5, 2026. Existing retained task evidence
is also recorded in [the import audit](TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md)
and [routine authoring guidance](ADDING_A_ROUTINE.md).

## Accepted focus mappings

| Routine IDs | Focus | Specific source fact and adaptation |
| --- | --- | --- |
| `research.max-hangs` | `fingerStrength` | [Lattice Half 4 — Hang — Max](https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/) identifies maximum half-crimp finger strength as its intent. The category directly simplifies that intent. |
| `research.force-feedback-f100` | `fingerStrength` | [Devise et al., 2022](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full), Abstract and F100 Protocol, identifies F100 as a maximal-strength program at 100% maximal finger strength. |
| `research.force-feedback-f80` | `fingerEndurance` | The same [Devise et al. study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full), Abstract and Conclusion, identifies stamina as the targeted F80 capacity and reports stamina/endurance changes. “Finger endurance” is an explicit broad browsing adaptation of the paper's distinct stamina/endurance terminology, not a promise of benefit from one session. |
| `research.seven-three-repeaters` | `fingerStrength` | [Hermans et al., 2022](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full), Introduction, describes the supplemental finger-flexor protocol's primary goal as maximal and explosive strength, with muscular endurance secondary. Select the primary goal rather than assuming every repeater protocol is endurance-focused. |
| `research.eva-int-hangs` | `fingerEndurance` | [López-Rivera and González-Badillo, 2019](https://pubmed.ncbi.nlm.nih.gov/30988852/), Abstract, compares dead-hang training methods specifically for grip endurance and identifies intermittent dead-hangs as an endurance-development approach. |
| `research.megos-one-arm-7-3` | `fingerEndurance` | [Eric Hörst's report of Megos' protocol](https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/) describes repeated force production while fatigued and finger power-endurance. “Finger endurance” is a broad-category adaptation; retain the protocol's power-endurance wording and attribution in its source metadata. |
| `coach.horst-seven-fifty-three` | `fingerStrength` | [Eric Hörst's protocol article](https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/), Maximum Weight “7-53” Protocol, explicitly states maximum strength as its purpose. |
| `metolius.generic-ten-minute.entry`, `.intermediate`, `.advanced` | `mixed` | [Metolius 10 Minute Sequences](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide), task tables, combines hangs, pull-ups, and knee raises/L-sits. “Mixed workouts” describes the source's combination of movements without assigning a new physiological claim. |
| `metolius.contact.entry`, `.intermediate`, `.advanced` | `mixed` | [Metolius Contact guide](https://www.metoliusclimbing.com/pages/contact-training-guide), Ten Minute Sequence and task tables, combines hangs, pull-ups, and body-tension tasks. Its introduction describes strength and stamina together. |
| `metolius.simulator-3d.entry`, `.intermediate`, `.advanced` | `mixed` | [Metolius Simulator 3D guide](https://www.metoliusclimbing.com/pages/simulator-3d-training-guide), Ten Minute Sequence and task tables, combines hangs and pull-ups, with core tasks in the relevant levels. Its introduction describes strength and stamina together. |
| `metolius.rock-rings.ten-minute` | `mixed` | [Metolius Rock Ring guide](https://www.metoliusclimbing.com/pages/rock-ring-training-guide), Ten Minute Sequence and Principles, combines hangs, pull-ups, and L-hangs, and discusses contact strength and body tension. |
| `hoopers-beta.introductory-home-hangboard` | `mixed` | [Hooper's Beta introductory routine](https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine), rounds 1–5, combines finger loading, core work, and optional pull-ups. Retained line-by-line task evidence is in the import audit. |
| `method.intermediate-hangboarding.emom` | `mixed` | [Method Climbing Intermediate Hangboarding](https://methodclimb.com/intermediate-hangboarding/), Workout 2, is retained in the August 10 import audit as hangs plus pull-ups and knee raises. The live page timed out on this check; the mapping uses retained specific task evidence, not a newly inferred training benefit. |

Abbreviated Metolius IDs in the table retain the full prefix in each case.
For example, `.intermediate` in the Contact row means
`metolius.contact.intermediate`.

## Deliberately unclassified routines

| Routine ID | Retained source URL | Reason to leave focus absent |
| --- | --- | --- |
| `research.abrahangs` | [Lattice Abrahangs](https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol) | The source describes low-load finger-flexor/connective-tissue stimulus without accumulating fatigue. That does not establish a recovery workout or one of the four selected goal categories. |
| `rptc.seven-three-repeaters` | [Trango RPTC Use Instructions](https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155) | The retained prescription supports repeaters, but this check could not retrieve the primary PDF to establish a distinct goal mapping. Do not substitute another repeater protocol's intent. |
| `coach.bechtel-three-six-nine` | [Retained StrengthClimbing summary](https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/) | Retained URL is a secondary summary; no specific primary creator goal was established for this classification change. |
| `coach.density-hangs` | [Retained StrengthClimbing summary](https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/) | Retained URL is a secondary summary; no specific primary creator goal was established for this classification change. |
| `device.zlagboard-sixty-sixty` | [Retained StrengthClimbing summary](https://strengthclimbing.com/zlagboard-forearm-endurance-workout/) | Its existing title is not sufficient primary evidence for adding a goal. Leave available through All workouts rather than classifying from the name. |
| `method.intermediate-hangboarding.repeaters` | [Method Climbing](https://methodclimb.com/intermediate-hangboarding/) | Live page timed out; retained import audit establishes repetition/timing facts but does not distinguish strength from endurance intent. |
| `rei.hangboard-sample-workout` | [REI's own sample routine](https://www.rei.com/learn/expert-advice/how-to-use-a-hangboard-to-train-for-rock-climbing.html) | The sample establishes grip-specific hang repetitions and alternative warm-ups; it does not distinguish a single goal among the chooser's categories. An optional warm-up pull-up alternative does not make it a dedicated pulling session. |

No existing routine is assigned `pullingStrength`: pull-ups occurring within a
mixed session do not establish a dedicated pulling-strength goal. The enum may
support future source-audited routines, while the destination is hidden when
the compatible catalog has no matches. Recovery remains omitted. Metolius'
general description of possible ten-minute sequence uses does not make every
published sample a recovery prescription.

## Exercise labels and summaries

- **Hangs** means a hang/loading action in the actual routine. Finger
  recruitment pulls with feet on the floor remain their source-described action;
  they are not reclassified as pull-ups.
- **Pull-ups** requires affirmative pull-up exercise content. A `.pull` phase
  alone is insufficient: knee raises and other core exercises share that phase.
  Negative instructions such as Trango's prohibition against pulling up must
  not trigger the label.
- **Core** describes source-prescribed movements such as knee raises, L-sits,
  front levers, planks, kicks, and hollow rocks/holds where actually present.
  It is an exercise filter, not a newly asserted training goal.
- Results reuse each existing routine subtitle as its summary. This change
  adds no new coaching, accessory, grip, count, or duration claims. Optional or
  alternative tasks retain their existing qualifiers in workout details.
- Calculated time is an app duration estimate when the prescription includes
  manual, maximal, variable, or untimed work; it is not presented as an exact
  manufacturer session length.
