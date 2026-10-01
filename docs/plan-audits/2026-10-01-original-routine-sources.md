# Original-source migration audit

Checked October 1, 2026. This audit supersedes the Abrahangs, Density Hangs,
Ladders, and Megos source rows in `2026-09-28-plan-hand-task-migration.md`.
Max Hangs has its separate `2026-10-01-lopez-max-hangs.md` audit.

## Abrahangs

Primary source: Emil Abrahamsson, [Hangboard Training 2 Times Per Day For 30
Days](https://www.youtube.com/watch?v=sBTI9qiH4UE), original video description,
program section (video chapter starts at 4:05). The author and full program
description were read from the public YouTube watch-page metadata.

| Source task, in order | App work rows | Target and fingers | Effort relative to lifting off |
| --- | --- | --- | --- |
| Four-finger crimp on 14 mm edge, three sets | grip 1, reps 1–3 | Bilateral 14 mm edge; index/middle/ring/pinky | 70–80% |
| Three-finger drag in deep pocket, three sets | grip 2, reps 1–3 | Bilateral three-finger pocket; index/middle/ring | 70–80% |
| Middle-two pocket, one set | grip 3, rep 1 | Bilateral two-finger pocket; middle/ring | 50–60% |
| Front-two pocket, one set | grip 4, rep 1 | Bilateral two-finger pocket; index/middle | 50–60% |
| Middle-two crimp, one set | grip 5, rep 1 | Bilateral edge, no prescribed depth; middle/ring | 30–40% |
| Front-two crimp, one set | grip 6, rep 1 | Bilateral edge, no prescribed depth; index/middle | 30–40% |

Every row keeps 10 seconds of loading and 50 seconds of rest, including the
last row: ten one-minute cycles, 600 seconds total. The final two rows retain
the instruction to stretch the pinky fingers during rest. Feet remain on the
ground. Effort percentages are explicitly relative to lifting off, not MVC.
The description does not specify crimp angle; no half/full-crimp angle is
invented. Drag/pocket tasks use the open-hand cue. The word “deep” remains in
the instruction, without an invented millimeter range or depth category.

The source's “crimp” edge tasks do not require physically two-finger-sized
edges: engaged-finger configuration carries that cue separately from the
contact's capacity. Board matching retains the existing numeric tolerance;
the 14 mm source value itself remains exact in the predicate. Provenance is
adapted because semantic matching cannot enforce relative effort or deep
pocket depth. The former Lattice six-grip sequence and universal 20 mm target
are removed.

## Density Hangs

Primary source: Tyler Nelson's authored [The Simplest Finger Training
Program](https://www.trainingbeta.com/the-simplest-finger-training-program/),
“Hangboard workout 2: Density Hangs” and
[Table 2](https://www.trainingbeta.com/wp-content/uploads/2019/08/Table-2.jpg).
The article and table image were both inspected. This is the beginner density
portion of a program that also contains recruitment and velocity workouts;
those are separate methods, not silently added to this session.

| Field | Source | App mapping |
| --- | --- | --- |
| Positions | Beginner: easy sloper/open hand and 25–25 mm half crimp | Easy sloper, then exact 25 mm edge; no sloper angle or size invented |
| Hands | Both arms | Bilateral targets |
| Sets/repetitions | One set, two repetitions per position | Four work rows, source position order |
| Duration/termination | Approximately 20–40 seconds, muscular failure | Stopwatch work; no fixed 30-second hang or 15-second rest |
| Loading | Slow static loading, moderate to low intensity | Instruction retains slow loading and difficulty chosen for approximate 20–40 seconds |
| Recovery | 3–5 minutes between efforts | Three explicit 180-second recoveries; minimum of source range selected as app adaptation |

The table literally prints “25–25 mm”; this audit treats it as the exact
25 mm value rather than silently correcting a possible author typo. The
article's broader prose allows selecting different sizes to match ability;
the bundled session uses the table's beginner example and is labeled as such.
Sixty seconds per stopwatch row is an app preview allocation, not a prescribed
hang time. Instructions tell the athlete to pause the enclosing session clock, start
the independent stopwatch, and advance when finished. The app session is adapted, not the full 4–5-week
program. Frequencies and the other two workouts are not invented into its
timed sequence. The former two identical edge groups, twelve 30/15 efforts,
and unsupported universal 20–35 mm edge prescription are removed.

## 3–6–9 Ladders

Primary source: [Steve Bechtel's own Power Company
interview](https://www.powercompanyclimbing.com/blog/2016/01/episode-2-resistance-training-with.html),
transcript at 49:21, 50:56, and 52:11. Bechtel describes 3, 6, and 9-second
hangs on the same hold and load, resting as long as needed; he increases
rounds before increasing load. At 52:11 his starting-point guidance is a
hold/load permitting a 15-second hang. This replaces the secondary article's
12-second starting-load cue and fixed rest timers.

Three ladders is retained as an explicitly labeled app session adaptation;
this interview does not prescribe three rounds. Each ladder is an undefined
manual task containing the whole ordered 3/rest/6/rest/9 sequence. Its
60-second row is an app preview only, not a prescribed task or rest duration.
The instruction explains pausing and advancing manually. Holds are
athlete-selected, with no invented depth, finger or grip-angle requirement.
The app does not claim to reproduce the later book or 2016 article's complete
periodization. Fixed 30-second inter-hang and 180-second inter-ladder rests are
removed rather than attributed to this interview.

## Megos One-arm 7/3 Repeaters

Primary presentation: Alexander Megos's [How to get Steel Fingers Part
2](https://www.youtube.com/watch?v=urTeUObQlsg). The exact video was identified
from the embed in the prior [Eric Hörst
report](https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/)
and confirmed using public watch-page metadata (title, author, and description
identifying the session as his full fingerboard power-endurance routine).

This migration changes the public source link and author label only. It
retains the existing six rounds, left then right arm, four 7/3 cycles per arm,
20–24 mm edge, half-crimp cue, and 120-second between-round recoveries. Those
fields remain traceable to the reporter's explicit account of this video;
the final three-second recovery remains preserved. An independently readable
video transcript was unavailable during this audit. Do not describe this
source-link migration as a new direct-video, frame-by-frame fidelity audit.
The prior report remains evidence in this repository audit, not an additional
secondary-source attribution in the app.

## Zlagboard 60/60: unresolved original

No change to the bundled routine or its visible attribution in this update.
Current prescription source is Jędrzej Banaszczyk's [Zlagboard Forearm
Endurance Workout](https://strengthclimbing.com/zlagboard-forearm-endurance-workout/).
Its ten 60-second efforts/60-second recoveries are reported as a Zlagboard
protocol developed by Duncan Brown. The
[manufacturer's training-plans page](https://zlagboard.com/training-plans)
confirms Brown is one of its coaches but does not expose the exact 60/60
prescription; [its app page](https://zlagboard.com/app) places professional
instructions inside the app. The linked athlete site was unavailable.

A manufacturer homepage is not evidence for counts or durations. Do not
replace the current URL with a homepage and claim that the original
prescription has been verified. The source gap is recorded here only, per
the user's request to avoid secondary-source attribution in the app.

## Additional Nelson sessions

The user also requested the other workouts identified in the original article.
Five additional sessions supply both levels of all three methods while retaining
the stable `coach.density-hangs` ID for the existing beginner density session.
All use the original article's URL and adapted provenance because the app
selects timer defaults within prescribed ranges.

| New plan | Primary table | Source grips / hands | Source sets and repetitions | App default |
| --- | --- | --- | --- | --- |
| Recruitment Pulls · Beginner | [Table 1](https://www.trainingbeta.com/wp-content/uploads/2019/08/Table1.jpg) | 20 mm open hand; 20 mm half crimp; one arm | 1 set, 3 reps | 3 reps per arm per grip, 4s work, 90s recovery |
| Recruitment Pulls · Expert | Table 1 | 15–20 mm open hand; 10–15 mm half crimp; one arm | 1–2 sets, 4–5 reps | 1 set, 4 reps per arm per grip, 4s work, 90s recovery |
| Density Hangs · Expert | Table 2 | Hard sloper/open hand; 10–15 mm half crimp; 10 mm full crimp; both arms | 1–2 sets, 3 reps | 1 set, 3 reps per grip; stopwatch work, 180s recovery |
| Velocity Pulls · Beginner | [Table 3](https://www.trainingbeta.com/wp-content/uploads/2019/08/Table-3.jpg) | Easy sloper/open hand; 35 mm pocket; both arms | 1 set, 2–4 reps | 1 set, 2 reps per grip, 2s work, 15s recovery |
| Velocity Pulls · Expert | Table 3 | 20 mm open hand; 15–20 mm half crimp; one arm | 1–2 sets, 5–8 reps or until power drops | 1 set, 5 reps per arm per grip, 2s work, 15s recovery; power-drop stop instruction retained |

Recruitment's source duration is 3–5 seconds, with slow loading and maximal
intensity, followed by 60–120 seconds between efforts. The original prose
specifies building force for 1–2 seconds, an elbow angle of 120–150 degrees,
and downward force even when lifting off is impossible. All these instructions
are retained; the selected 4s/90s defaults are disclosed. Recruitment and
velocity work record the existing `isometricPull` action, preserving the source
exercise type in saved activity rather than classifying it as a hang.

Velocity's source duration is 1–3 seconds, fastest loading, moderate to high
intensity, and 10–20 seconds between efforts. The original prose specifies
starting at 10–20% tension before loading rapidly. The selected 2s/15s defaults
are disclosed. The pocket's finger count and grip angle are not specified, so
they are omitted. Beginner velocity requires a completed cycle of recruitment
and density first; expert velocity follows recruitment. The tables prescribe
4–5-week cycles; these are retained as guidance, not fabricated timer tasks.

Unilateral side order is not prescribed. The app groups left-arm efforts then
right-arm efforts on each grip and discloses that ordering as an adaptation.
Between-effort rests apply at every effort boundary, including grip/side
transitions; no extra invented between-set rest or warm-up is added. “Easy” and
“hard” sloper are athlete-relative instructions, not inferred sloper geometry.
The existing numeric contact-matching tolerance remains unchanged. Source
depths stay exact in authored predicates. Compatible-board resolution must
not substitute a different hold kind to admit more boards.

## Verification

`scripts/tests/test_original_routine_sources.py` checks the generated shared
library against the source counts, grip ordering, effort tiers, termination
and source links. The normal exporter and work-target validator also check
the library and board resolution. Original-source fidelity is established by
the audit evidence above, not by tests alone.

A standalone DEBUG Swift check decoded the committed-format JSON through
`PlanLibraryStore`, confirmed that all 31 materialized plans match the source
seeds through the runtime drift guard, and used the production `ContactResolver`
with all bundled board packages. Every added session has at least one fully resolving board:
beginner recruitment and expert velocity on Beastmaker 1000; expert recruitment
on both Beastmakers; expert density on Beastmaker 1000, Helium Mobile, Moon
Armstrong, and Tension Honestone; beginner velocity on Beastmaker 2000 and
Metolius Simulator 3D. Beginner density resolves on Simulator 3D, Wood Grips
Deluxe II, Moon Armstrong, and So iLL Split Palm. Abrahangs resolves on Beastmaker
2000 with its complete edge/pocket inventory. These results do not loosen the
source's hold predicates to make other boards appear compatible.

Native validation attempted the complete `HangTenTests/PlanStorageTests` and
`HangTenTests/AppStoreTests` suites with Xcode, Debug configuration, explicit
destinations, and isolated DerivedData. Both iOS 26.5 attempts and an iOS 26.4
retry stalled during fresh-simulator startup. Launch services responded, but
screenshots showed the Apple logo and partially filled migration bar; AXe
returned no UI tree. Compilation completed, but no native test results or
routine UI screenshots were produced. These runtime and visual checks remain
unverified; the failed startup is not reported as a test pass. The exact owned
simulators and DerivedData were removed by their cleanup traps.

CI follow-up: Nelson's work instructions and recovery accessories now state the
selected effort/recovery durations and permitted ranges directly to the athlete.
The counts, timing, grip predicates, and termination qualifiers mapped to
Tables 1–3 above are unchanged; provenance and explanations of the selected
defaults remain in plan metadata and this audit. Tests now recognize Table 2's
supported open-hand/half-crimp cues without adding an exact finger selection.
The custom Max Hangs duplication test compares the complete copied contact
requirements with the original routine rather than hard-coding the superseded
20 mm prescription.
