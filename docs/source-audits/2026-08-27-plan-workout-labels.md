# Built-in workout-label source audit

Checked 2026-08-27 against the direct source URLs and row-level audits in
[the built-in cue provenance audit](2026-08-10-plan-cue-provenance.md),
[the Metolius board-specific routine audit](2026-08-26-metolius-board-specific-routines.md),
and [the supplemental Hooper's Beta, Method, and REI audit](../TRAINING_PLAN_SOURCE_AUDIT_2026-08-10.md).

`workoutLabels` are athlete-facing discovery metadata. They do not add or
modify a workout prescription. A label is applied only where the documented
routine steps establish it; labels are not inferred from a routine title,
library category, provenance, or board metadata. Internal `tags` such as
`built-in`, source categories, and hardware requirements remain unavailable
in the athlete-facing Tags filter.

| Workout label | Plan IDs | Source-backed row basis |
| --- | --- | --- |
| `max-effort` | `metolius.generic-ten-minute.{entry,intermediate,advanced}` | Every generic sequence retains the source's final maximum sloper hang. |
| `max-effort` | `metolius.contact.{entry,intermediate,advanced}`, `metolius.simulator-3d.{entry,intermediate,advanced}` | Each official board-specific sequence ends with the source's dead hang to failure. |
| `max-effort` | `research.max-hangs`, `research.force-feedback-f100`, `coach.horst-seven-fifty-three`, `coach.bechtel-three-six-nine`, `method.intermediate-hangboarding.emom` | The audited rows explicitly prescribe near/maximal hangs, a maximal-force effort, a load tied to maximum, or a max sloper. |
| `repeaters` | `research.seven-three-repeaters`, `method.intermediate-hangboarding.repeaters` | The linked protocols explicitly prescribe the 7/3 or 5–7-second repeater series. |
| `endurance` | `device.zlagboard-sixty-sixty` | The direct source is the Zlagboard endurance protocol and specifies ten 60/60 sets. |
| `pull-ups` | `metolius.generic-ten-minute.{entry,intermediate,advanced}`, `metolius.contact.{entry,intermediate,advanced}`, `metolius.simulator-3d.{entry,intermediate,advanced}`, `hoopers-beta.introductory-home-hangboard`, `method.intermediate-hangboarding.emom`, `rei.hangboard-sample-workout` | Each audit retains source pull-up tasks, or for REI a source-provided pull-up warm-up alternative. |
| `core` | `metolius.generic-ten-minute.{entry,intermediate}`, `metolius.contact.{entry,intermediate,advanced}`, `metolius.simulator-3d.{entry,intermediate,advanced}`, `hoopers-beta.introductory-home-hangboard`, `method.intermediate-hangboarding.emom` | The retained rows specify knee raises, L-hangs/L-sit pull-ups, plank/side-plank, kicks, hollow work, or knee raises. |
| `warm-up` | `hoopers-beta.introductory-home-hangboard`, `rei.hangboard-sample-workout` | The linked source explicitly opens with the preserved warm-up sequence or alternatives. |

Custom-routine tags are user-provided labels. A custom routine with no tags
has no label chips and remains visible and usable.
