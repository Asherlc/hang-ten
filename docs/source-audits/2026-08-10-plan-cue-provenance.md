# Built-in plan cue provenance audit

Checked 2026-08-10 against the source facts and URLs recorded in the Task 1
plan and design specification. No board metadata was treated as a training
prescription.

`keep` means the source fact remains identifiable in the catalog. `adapt`
means the source task remains identifiable but Hang Ten chose UI wording,
timer structure, a value from a published range, or a semantic board target; the
catalog labels that choice as an app adaptation. `remove` means the field is
absent because the linked source did not support it.

The ten plans below are board-flexible. Their former Compact II examples are
now generic semantic target adaptations: source/example 20 mm and 19 mm edges
use `mediumEdge`, 29 mm edges use `largeEdge`, and the Frontiers study's 12 mm
instrumented hold uses `smallEdge`. Finger choices remain structured finger
cues on edge targets; actual pocket prescriptions remain pocket targets with
their factual capacity. Explicit semantic fallbacks prefer the nearest edge
and then a large open-hand rail or jug only when a board has no compatible edge
or pocket; a fallback is an app substitution and does not change the primary
prescription.
F80 and F100 still require real-time force
measurement/feedback—the semantic target only highlights a suitable board
feature and does not reproduce the study protocol. F100 retains its alternating
right/left instruction without inventing board-side mappings.

## Field decisions for all 19 built-in plans

| Plan ID | Source type | Source | Keep | Adapt | Remove |
| --- | --- | --- | --- | --- | --- |
| `metolius.generic-ten-minute.entry` | manufacturer | [Metolius 10 Minute Sequences — Hangboard Training Guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | title, instruction, target, count | subtitle, accessory, duration, interval: source tasks expanded into app-guided task/rest steps | warmUp, cooldown, gripType, fingerConfiguration |
| `metolius.generic-ten-minute.intermediate` | manufacturer | [Metolius 10 Minute Sequences — Hangboard Training Guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | title, instruction, target, count | subtitle, accessory, duration, interval: source tasks expanded into app-guided task/rest steps | warmUp, cooldown, gripType, fingerConfiguration |
| `metolius.generic-ten-minute.advanced` | manufacturer | [Metolius 10 Minute Sequences — Hangboard Training Guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | title, instruction, target, count, including source finger-count phrases, switches, stay-on transitions, choices, and failure/max qualifiers | subtitle, accessory, duration, interval: source tasks expanded into app-guided task/rest steps | warmUp, cooldown, gripType, fingerConfiguration; finger phrases remain in source-backed instructions rather than inferred structured cues |
| `research.max-hangs` | research | [Lattice max hang protocol](https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/) | title, instruction, gripType: 7-second, near-maximal, 20 mm, half-crimp, four-finger hangs | subtitle, accessory, target, count, duration, interval: generic `mediumEdge` target and five-set/three-minute app timer structure | warmUp, cooldown, fingerConfiguration; the four-finger fact remains in instruction text |
| `research.force-feedback-f80` | research | [Frontiers force-feedback hangboard study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | title, subtitle, instruction, accessory, count, duration, interval: 80% MFSi, 10/6 between repetitions, 12 repetitions, three sets, eight-minute recovery, real-time force measurement/feedback, and instrumented 12 mm study hold | target: generic `smallEdge` highlight is an adaptation and does not supply the required measurement/feedback; the final post-routine 6-second rest is omitted by Hang Ten's terminal-work policy | warmUp, cooldown, gripType, fingerConfiguration |
| `research.force-feedback-f100` | research | [Frontiers force-feedback hangboard study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | title, subtitle, instruction, accessory, duration: maximal 6-second alternating-hand efforts, real-time force measurement/feedback, and instrumented 12 mm study hold | target, count, interval: generic `smallEdge` highlight and app timer representation; right/left instructions remain without board-side mapping | warmUp, cooldown, gripType, fingerConfiguration |
| `research.eva-int-hangs` | research | [Eva López hangboard comparison](https://pubmed.ncbi.nlm.nih.gov/30988852/) | title: identifies the intermittent dead-hang comparison | subtitle, instruction, accessory, target, count, duration, interval: generic `mediumEdge` target and explicitly labeled app-guided realization; the linked record does not establish those exact values | warmUp, cooldown, gripType, fingerConfiguration |
| `research.seven-three-repeaters` | research | [Beastmaker 7/3 study protocol](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full) | title, instruction, accessory, count, duration, interval: two sets, six progressive series, seven reps, 7/3, 2:30 series recovery, and six-minute set recovery | subtitle, target, gripType, fingerConfiguration: documented progression expressed with generic `largeEdge`/`mediumEdge` targets and structured cues; Beastmaker study context does not make the prescription product-specific | warmUp, cooldown |
| `research.abrahangs` | research | [Lattice Abrahangs protocol](https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol) | title, instruction, count, gripType, fingerConfiguration: low-intensity feet-supported Half 4, F3 Open, M2 Open, F2 Open, B3 Half, and F3 Half variants | subtitle, accessory, target, duration, interval: generic `mediumEdge` target and 10/50 app timer; the final app-adapted 50-second recovery is omitted by Hang Ten's terminal-work policy, analogous to F80 | warmUp, cooldown |
| `coach.horst-seven-fifty-three` | coach | [Eric Hörst fingerboard protocols](https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/) | title, instruction, accessory, duration, gripType: 7/53, three hangs, and half/open or pocket options | subtitle, target, count, interval: generic `largeEdge`/`mediumEdge` and factual two-finger-pocket targets plus three-minute selection from the 3–5 minute recovery range | warmUp, cooldown, fingerConfiguration |
| `coach.bechtel-three-six-nine` | coach | [Steve Bechtel 3–6–9 ladder protocol](https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/) | title, instruction, duration: 3/6/9 sequence and source loading cue | subtitle, accessory, target, count, interval: three rounds and exact rest values selected from source ranges, plus generic `largeEdge` target | warmUp, cooldown, gripType, fingerConfiguration |
| `coach.density-hangs` | coach | [Tyler Nelson density hang protocol](https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/) | title, instruction: source ranges and 2:1 relationship remain identifiable | subtitle, accessory, target, count, duration, interval: 30/15, three reps, three-minute recoveries, set count, and generic `largeEdge`/factual four-finger-pocket targets are app choices within the published ranges | warmUp, cooldown, gripType, fingerConfiguration |
| `device.zlagboard-sixty-sixty` | device | [Zlagboard endurance protocol](https://strengthclimbing.com/zlagboard-forearm-endurance-workout/) | title, instruction, accessory, count, duration, interval: ten 60/60 sets | subtitle, target: generic `largeEdge` target | warmUp, cooldown, gripType, fingerConfiguration; unsupported feet-supported copy was removed |
| `lattice.lite-home-adaptations` | coach | [Lattice Training · Lite Guide to Home Adaptations](https://latticetraining.com/app/uploads/2020/03/Lite-Guide-to-home-adaptations.pdf) | title and the source sample week's named tasks and frequencies | subtitle, instruction, accessory, target, count, duration, interval, gripType: app rows, preview durations, semantic board targets, and structured grip cues are not presented as source prescriptions | warmUp, cooldown, fingerConfiguration |
| `hoopers-beta.introductory-home-hangboard` | coach | [Hooper's Beta · Jason Hooper PT, DPT, OCS, CAFS](https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine) | title and identifiable routine order, counts, ranges, durations, and qualifiers | subtitle, instruction, accessory, target, count, duration, interval, gripType: the app splits the source routine into guided rows and semantic targets | warmUp, cooldown, fingerConfiguration |
| `method.intermediate-hangboarding.repeaters` | coach | [Method Climbing · Intermediate Hangboarding](https://methodclimb.com/intermediate-hangboarding/) | title and identifiable five-round 5–7-second repeater ranges | subtitle, instruction, accessory, target, count, duration, interval, gripType: app selects range endpoints, expands rows, and supplies semantic targets/cues | warmUp, cooldown, fingerConfiguration |
| `method.intermediate-hangboarding.emom` | coach | [Method Climbing · Intermediate Hangboarding](https://methodclimb.com/intermediate-hangboarding/) | title and identifiable ten-minute task order | subtitle, instruction, accessory, target, count, duration, interval, gripType: app defaults untimed counted work and maps source holds to semantic targets/cues | warmUp, cooldown, fingerConfiguration |
| `lattice.beginner-climbers-training-guide` | coach | [Lattice Training · The Beginner Climber's Training Guide](https://latticetraining.com/blog/the-beginners-guide) | title and identifiable foundational task names/priorities | subtitle, instruction, accessory, target, count, duration, interval, gripType: reference rows and preview timing are app representations, not a fabricated source protocol | warmUp, cooldown, fingerConfiguration |
| `rei.hangboard-sample-workout` | retailer | [REI Expert Advice · How to Use a Hangboard to Train for Rock Climbing](https://www.rei.com/learn/expert-advice/how-to-use-a-hangboard-to-train-for-rock-climbing.html) | title and identifiable warm-up alternatives, five-grip order, repetitions, timing ranges, and recovery guidance | subtitle, instruction, accessory, target, count, duration, interval, gripType: app selects preview/range defaults and semantic targets/cues | warmUp, cooldown, fingerConfiguration |

## Removed catalog content

- Removed the shared invented “Progressive warm-up” steps in full: title,
  60/120-second timer, jug target, instruction, accessory, and open-hand cue.
- Removed generic “shake out,” breathing, shoulder-position, pain, form, and
  logging coaching where the linked plan did not prescribe it.
- Removed inferred grip/finger overrides from Metolius slopers, slopes and
  pockets, F80/F100, Eva, Bechtel, Density, and Zlagboard. Physical board
  metadata does not establish a plan cue.
- Removed Zlagboard feet-supported instruction/accessory text because the
  recorded source fact supports ten 60/60 sets, not that scaling cue.
- Kept empty recovery instructions empty. Source-backed recovery duration is
  still represented by the timer/accessory where applicable.

## Machine-readable regression manifest

The test suite reads this block. Plan rules cover every required field; step
rules cover every non-empty instruction/accessory and every retained structured
grip/finger cue.

```json
{
  "planSources": [
    {"planID":"metolius.generic-ten-minute.entry","sourceType":"manufacturer","sourceLabel":"Metolius 10 Minute Sequences — Hangboard Training Guide","sourceURL":"https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"},
    {"planID":"metolius.generic-ten-minute.intermediate","sourceType":"manufacturer","sourceLabel":"Metolius 10 Minute Sequences — Hangboard Training Guide","sourceURL":"https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"},
    {"planID":"metolius.generic-ten-minute.advanced","sourceType":"manufacturer","sourceLabel":"Metolius 10 Minute Sequences — Hangboard Training Guide","sourceURL":"https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"},
    {"planID":"research.max-hangs","sourceType":"research","sourceLabel":"Lattice max hang protocol","sourceURL":"https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/"},
    {"planID":"research.force-feedback-f80","sourceType":"research","sourceLabel":"Frontiers force-feedback hangboard study","sourceURL":"https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full"},
    {"planID":"research.force-feedback-f100","sourceType":"research","sourceLabel":"Frontiers force-feedback hangboard study","sourceURL":"https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full"},
    {"planID":"research.eva-int-hangs","sourceType":"research","sourceLabel":"Eva López hangboard comparison","sourceURL":"https://pubmed.ncbi.nlm.nih.gov/30988852/"},
    {"planID":"research.seven-three-repeaters","sourceType":"research","sourceLabel":"Beastmaker 7/3 study protocol","sourceURL":"https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full"},
    {"planID":"research.abrahangs","sourceType":"research","sourceLabel":"Lattice Abrahangs protocol","sourceURL":"https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol"},
    {"planID":"coach.horst-seven-fifty-three","sourceType":"coach","sourceLabel":"Eric Hörst fingerboard protocols","sourceURL":"https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/"},
    {"planID":"coach.bechtel-three-six-nine","sourceType":"coach","sourceLabel":"Steve Bechtel 3–6–9 ladder protocol","sourceURL":"https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/"},
    {"planID":"coach.density-hangs","sourceType":"coach","sourceLabel":"Tyler Nelson density hang protocol","sourceURL":"https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/"},
    {"planID":"device.zlagboard-sixty-sixty","sourceType":"device","sourceLabel":"Zlagboard endurance protocol","sourceURL":"https://strengthclimbing.com/zlagboard-forearm-endurance-workout/"},
    {"planID":"lattice.lite-home-adaptations","sourceType":"coach","sourceLabel":"Lattice Training · Lite Guide to Home Adaptations","sourceURL":"https://latticetraining.com/app/uploads/2020/03/Lite-Guide-to-home-adaptations.pdf"},
    {"planID":"hoopers-beta.introductory-home-hangboard","sourceType":"coach","sourceLabel":"Hooper's Beta · Jason Hooper PT, DPT, OCS, CAFS","sourceURL":"https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine"},
    {"planID":"method.intermediate-hangboarding.repeaters","sourceType":"coach","sourceLabel":"Method Climbing · Intermediate Hangboarding","sourceURL":"https://methodclimb.com/intermediate-hangboarding/"},
    {"planID":"method.intermediate-hangboarding.emom","sourceType":"coach","sourceLabel":"Method Climbing · Intermediate Hangboarding","sourceURL":"https://methodclimb.com/intermediate-hangboarding/"},
    {"planID":"lattice.beginner-climbers-training-guide","sourceType":"coach","sourceLabel":"Lattice Training · The Beginner Climber's Training Guide","sourceURL":"https://latticetraining.com/blog/the-beginners-guide"},
    {"planID":"rei.hangboard-sample-workout","sourceType":"retailer","sourceLabel":"REI Expert Advice · How to Use a Hangboard to Train for Rock Climbing","sourceURL":"https://www.rei.com/learn/expert-advice/how-to-use-a-hangboard-to-train-for-rock-climbing.html"}
  ],
  "planFieldRules": [
    {"planID":"metolius.generic-ten-minute.entry","fields":["title","instruction","target","count"],"decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.entry","fields":["subtitle","accessory","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.entry","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},
    {"planID":"metolius.generic-ten-minute.intermediate","fields":["title","instruction","target","count"],"decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.intermediate","fields":["subtitle","accessory","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.intermediate","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},
    {"planID":"metolius.generic-ten-minute.advanced","fields":["title","instruction","target","count"],"decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.advanced","fields":["subtitle","accessory","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.advanced","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.max-hangs","fields":["title","instruction","gripType"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.max-hangs","fields":["subtitle","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.max-hangs","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.max-hangs","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.force-feedback-f80","fields":["title","subtitle","instruction","accessory","count","duration","interval"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.force-feedback-f80","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.force-feedback-f80","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.force-feedback-f100","fields":["title","subtitle","accessory","duration"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.force-feedback-f100","fields":["instruction","count","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.force-feedback-f100","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.force-feedback-f100","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.eva-int-hangs","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.eva-int-hangs","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.eva-int-hangs","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.eva-int-hangs","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.seven-three-repeaters","fields":["title","instruction","accessory","count","duration","interval"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.seven-three-repeaters","fields":["subtitle","target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.seven-three-repeaters","fields":["gripType","fingerConfiguration"],"decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"research.seven-three-repeaters","fields":["warmUp","cooldown"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.abrahangs","fields":["title","instruction","count","gripType","fingerConfiguration"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.abrahangs","fields":["subtitle","accessory","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.abrahangs","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.abrahangs","fields":["warmUp","cooldown"],"decision":"remove","sourcePrescription":false},

    {"planID":"coach.horst-seven-fifty-three","fields":["title","instruction","accessory","duration","gripType"],"decision":"keep","sourcePrescription":true},
    {"planID":"coach.horst-seven-fifty-three","fields":["subtitle","count","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"range"},
    {"planID":"coach.horst-seven-fifty-three","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"coach.horst-seven-fifty-three","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"coach.bechtel-three-six-nine","fields":["title","instruction","duration"],"decision":"keep","sourcePrescription":true},
    {"planID":"coach.bechtel-three-six-nine","fields":["subtitle","accessory","count","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"range"},
    {"planID":"coach.bechtel-three-six-nine","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"coach.bechtel-three-six-nine","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"coach.density-hangs","fields":["title","instruction"],"decision":"keep","sourcePrescription":true},
    {"planID":"coach.density-hangs","fields":["subtitle","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"range"},
    {"planID":"coach.density-hangs","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"coach.density-hangs","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"device.zlagboard-sixty-sixty","fields":["title","instruction","accessory","count","duration","interval"],"decision":"keep","sourcePrescription":true},
    {"planID":"device.zlagboard-sixty-sixty","fields":["subtitle","target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"device.zlagboard-sixty-sixty","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"lattice.lite-home-adaptations","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"lattice.lite-home-adaptations","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"structure"},
    {"planID":"lattice.lite-home-adaptations","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"lattice.lite-home-adaptations","fields":["gripType"],"decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"lattice.lite-home-adaptations","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"hoopers-beta.introductory-home-hangboard","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"hoopers-beta.introductory-home-hangboard","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"structure"},
    {"planID":"hoopers-beta.introductory-home-hangboard","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"hoopers-beta.introductory-home-hangboard","fields":["gripType"],"decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"hoopers-beta.introductory-home-hangboard","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"method.intermediate-hangboarding.repeaters","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"method.intermediate-hangboarding.repeaters","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"structure"},
    {"planID":"method.intermediate-hangboarding.repeaters","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"method.intermediate-hangboarding.repeaters","fields":["gripType"],"decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"method.intermediate-hangboarding.repeaters","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"method.intermediate-hangboarding.emom","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"method.intermediate-hangboarding.emom","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"structure"},
    {"planID":"method.intermediate-hangboarding.emom","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"method.intermediate-hangboarding.emom","fields":["gripType"],"decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"method.intermediate-hangboarding.emom","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"lattice.beginner-climbers-training-guide","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"lattice.beginner-climbers-training-guide","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"structure"},
    {"planID":"lattice.beginner-climbers-training-guide","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"lattice.beginner-climbers-training-guide","fields":["gripType"],"decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"lattice.beginner-climbers-training-guide","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"rei.hangboard-sample-workout","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"rei.hangboard-sample-workout","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"structure"},
    {"planID":"rei.hangboard-sample-workout","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"rei.hangboard-sample-workout","fields":["gripType"],"decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"rei.hangboard-sample-workout","fields":["warmUp","cooldown","fingerConfiguration"],"decision":"remove","sourcePrescription":false}
  ],
  "stepFieldRules": [
    {"planID":"metolius.generic-ten-minute.entry","stepIDPattern":".*task-.*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.entry","stepIDPattern":".*task-.*","field":"accessory","decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.entry","stepIDPattern":".*rest$","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.entry","stepIDPattern":".*rest$","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.intermediate","stepIDPattern":".*task-.*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.intermediate","stepIDPattern":".*task-.*","field":"accessory","decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.intermediate","stepIDPattern":".*rest$","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.intermediate","stepIDPattern":".*rest$","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.advanced","stepIDPattern":".*task-.*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.advanced","stepIDPattern":".*task-.*","field":"accessory","decision":"keep","sourcePrescription":true},
    {"planID":"metolius.generic-ten-minute.advanced","stepIDPattern":".*rest$","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"metolius.generic-ten-minute.advanced","stepIDPattern":".*rest$","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},

    {"planID":"research.max-hangs","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"research.max-hangs","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.max-hangs","stepIDPattern":".*","field":"gripType","decision":"keep","sourcePrescription":true},
    {"planID":"research.force-feedback-f80","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"research.force-feedback-f80","stepIDPattern":".*","field":"accessory","decision":"keep","sourcePrescription":true},
    {"planID":"research.force-feedback-f100","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.force-feedback-f100","stepIDPattern":".*","field":"accessory","decision":"keep","sourcePrescription":true},
    {"planID":"research.eva-int-hangs","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.eva-int-hangs","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.seven-three-repeaters","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"research.seven-three-repeaters","stepIDPattern":".*","field":"accessory","decision":"keep","sourcePrescription":true},
    {"planID":"research.seven-three-repeaters","stepIDPattern":".*","field":"gripType","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"research.seven-three-repeaters","stepIDPattern":".*","field":"fingerConfiguration","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"research.abrahangs","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"research.abrahangs","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.abrahangs","stepIDPattern":".*","field":"gripType","decision":"keep","sourcePrescription":true},
    {"planID":"research.abrahangs","stepIDPattern":".*","field":"fingerConfiguration","decision":"keep","sourcePrescription":true},
    {"planID":"coach.horst-seven-fifty-three","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"coach.horst-seven-fifty-three","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"range"},
    {"planID":"coach.horst-seven-fifty-three","stepIDPattern":".*","field":"gripType","decision":"keep","sourcePrescription":true},
    {"planID":"coach.bechtel-three-six-nine","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"coach.bechtel-three-six-nine","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"range"},
    {"planID":"coach.density-hangs","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"coach.density-hangs","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"range"},
    {"planID":"device.zlagboard-sixty-sixty","stepIDPattern":".*","field":"instruction","decision":"keep","sourcePrescription":true},
    {"planID":"device.zlagboard-sixty-sixty","stepIDPattern":".*","field":"accessory","decision":"keep","sourcePrescription":true},

    {"planID":"lattice.lite-home-adaptations","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"lattice.lite-home-adaptations","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"lattice.lite-home-adaptations","stepIDPattern":".*","field":"gripType","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"hoopers-beta.introductory-home-hangboard","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"hoopers-beta.introductory-home-hangboard","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"hoopers-beta.introductory-home-hangboard","stepIDPattern":".*","field":"gripType","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"method.intermediate-hangboarding.repeaters","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"method.intermediate-hangboarding.repeaters","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"method.intermediate-hangboarding.repeaters","stepIDPattern":".*","field":"gripType","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"method.intermediate-hangboarding.emom","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"method.intermediate-hangboarding.emom","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"method.intermediate-hangboarding.emom","stepIDPattern":".*","field":"gripType","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"lattice.beginner-climbers-training-guide","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"lattice.beginner-climbers-training-guide","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"lattice.beginner-climbers-training-guide","stepIDPattern":".*","field":"gripType","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"},
    {"planID":"rei.hangboard-sample-workout","stepIDPattern":".*","field":"instruction","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"rei.hangboard-sample-workout","stepIDPattern":".*","field":"accessory","decision":"adapt","sourcePrescription":false,"adaptationType":"wording"},
    {"planID":"rei.hangboard-sample-workout","stepIDPattern":".*","field":"gripType","decision":"adapt","sourcePrescription":false,"adaptationType":"cue"}
  ]
}
```
