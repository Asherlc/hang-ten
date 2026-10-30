# Hangboard warm-up imports

Primary evidence checked October 30, 2026. Both plans are board-flexible,
source-linked adaptations under Warm-ups. No numbered board inventory is used.
The former Lattice general progression, Beastmaker general guidance, Climbing
wall pyramid and CCC rope practice entries remain removed. Existing warm-up
sections inside other workouts are unchanged.

## PitchSix — `warmup.pitchsix.recruitment-prep`

[Collin McGee / PitchSix article](https://pitchsix.com/blogs/blog/the-best-hangboarding-warm-up),
“Recruitment Prep”, Figure 1 and Figure 4. The linked
[protocol whiteboard](https://cdn.shopify.com/s/files/1/0249/5525/6922/files/IMG_4558.heic?v=1729626186)
([retained original](2026-10-30-hangboard-warmups/pitchsix-protocol.heic))
adds the 5:10 repetition timing and thirty-second set rest omitted from the prose.
The [app example](https://cdn.shopify.com/s/files/1/0249/5525/6922/files/IMG_9793_d098737c-a718-447e-a95a-925adeefec0b.png?v=1729627093)
([retained original](2026-10-30-hangboard-warmups/pitchsix-app-example.png))
and caption show separate left/right sets (24 pulls); its recorded forces and
100 observed seconds are athlete results, not prescription values. The
[linked video](https://www.youtube.com/watch?v=Qnq5FgGsXtE) was not available as
retrievable text; no additional facts are attributed to it.

| Field / block | Evidence and representation |
| --- | --- |
| Title, subtitle, level, focus, labels | Source’s Recruitment Prep warm-up, summarized as six levels with two five-second pulls per hand. Warm-up is a purpose label, not an invented skill grade. |
| `set-1-*` through `set-4-*` | Article: OISO at 50%, 70%, 80%, 90% of the OISO maximum, two repetitions at each level. |
| `set-5-*`, `set-6-*` | Article: YISO at 60%, 80% of the YISO maximum, two repetitions at each level. |
| Each `rep-1`, `rep-2` | Five-second fixed work; `isometricPull`, single hand; left/right from the separate-side app example. Left before right at each level is the disclosed app ordering. |
| Instructions / grip | Slightly open half crimp. OISO isolates finger squeezing/curling without movement; YISO resists finger opening under larger-muscle loading. Measured maximum or perceived effort; no invented absolute weight. |
| Target / fingers | Chosen edge, one side-specific hand. Ideal uneven 25 mm+ edge remains a preference in prose, not a mandatory depth or unsupported shape constraint. No exact finger identities or count inferred. |
| Each `rep-rest` | Ten seconds between the two pulls, from whiteboard `2 x 5:10`. |
| Each `set-rest` | Thirty seconds between hand sets, from whiteboard; disclosed interpretation replaces the trailing repetition rest rather than stacking 10+30 seconds. Final pull ends the routine. |
| Totals | Twelve hand sets, 24 efforts, 12 ten-second rests and 11 thirty-second rests: 570 seconds. |

`adapted` covers side order and rest-boundary interpretation. It imports
Recruitment Prep only, excluding optional extra grip preparation and Endurance
Prep; neither is silently appended. Percentages stay in instructions because
the library has no relative-force prescription field; `externalLoadKGF` would
misrepresent them as absolute added load. All work has an edge target and
`halfCrimp`; a board’s inventory never supplies an additional exercise cue.

## Entralpi — `warmup.entralpi.max-hang-ramp`

[Félix Bourassa-Moreau / Entralpi](https://entralpi.com/help/train/plan-your-training/warm-up-routine),
step 6 and “Why ramp up before max hangs?”. Import is specifically the ramp
after lighter preparation, before max hangs or hard repeaters. The source’s
cardio, mobility and climbing pyramid are outside this requested excerpt.

| Field / block | Evidence and representation |
| --- | --- |
| Title / subtitle / labels | Identify the pre-max-hang ramp and progressive hangboard preparation; no claim that this replaces a complete general warm-up. |
| `hang-1`, `hang-2`, `hang-3` | About 50%, 70%, 85% maximum, in order. Select the source’s three-hang branch within its 2–3-hang allowance. |
| First instruction | Makes the source’s lighter-preparation prerequisite visible on the plan’s first-hold card and during playback. No extra timed task is added. |
| Work timing | Source permits 5–10 seconds; fixed timer selects five seconds. Instructions preserve the full range; notes disclose the selected value. |
| Recovery timing | Source permits 1–2 minutes between efforts; timer selects 60 seconds twice. Recovery instructions preserve the range; no final rest. |
| Hand / target / grip | Source says use the training edge and grip. Playback selects two hands, explicitly disclosed in notes; edge predicates have no inferred depth, shape, grip or finger identities. |
| Relative load / evidence limits | Percentages stay in instructions, not added-weight fields. Author identifies coaching practice, not a climbing-trial protocol. |
| Totals / provenance | Three efforts, two rests, 135 seconds; adapted for branch, timer and hand-count choices. |

## Compatibility and validation boundary

Both plans retain semantic edge predicates and a nil board ID. Compatibility
must resolve against the selected board, including sidedness, hand capacity and
PitchSix’s half crimp. No substitution or equivalence is inferred from catalog
metadata. Representative full boards: Beastmaker 1000 and Metolius Wood Grips
Compact II. Entralpi’s selected two-hand version can require two copies of a
one-hand board; PitchSix is unilateral. Generated resources establish contact
facts, never training prescriptions.

The source-prescription regressions in
`scripts/tests/test_original_routine_sources.py` assert ordered efforts,
percentages, contraction labels, side counts, rest boundaries and omissions.
`PlanStorageTests` retains full prescription hashes and tests runtime loading,
Warm-ups search, durations, hand/action cues, representative contact resolution,
and incompatibility on an edge-less fixture board.

## Other source checked

[TrainingBeta’s guide](https://www.trainingbeta.com/warming-hangboard-session/)
also supplies progressive twenty-second hangs but mixes in off-board activity
and lacks a fixed repetition/rest sequence. It is not imported.

Grip illustrations use the authored step hand use rather than the contact’s
maximum physical hand capacity. This preserves PitchSix’s explicit side even
when a wide hold is selected. Entralpi supplies no grip or finger cue, so its
workout intentionally omits the grip illustration; two-hand execution remains
in the step and semantic targets.
