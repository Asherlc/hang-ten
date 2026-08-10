# Built-in plan cue provenance audit

Checked 2026-08-10 against the source facts and URLs recorded in the Task 1
plan and design specification. No board metadata was treated as a training
prescription.

`keep` means the source fact remains identifiable in the catalog. `adapt`
means the source task remains identifiable but Hang Ten chose UI wording,
timer structure, a value from a published range, or a Compact II target; the
catalog labels that choice as an app adaptation. `remove` means the field is
absent because the linked source did not support it.

## Field decisions for all 13 built-in plans

| Plan ID | Source | Keep | Adapt | Remove |
| --- | --- | --- | --- | --- |
| `metolius.generic-ten-minute.entry` | [Metolius 10-minute guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | title, instruction, target, count | subtitle, accessory, duration, interval: source tasks expanded into app-guided task/rest steps | warmUp, cooldown, gripType, fingerConfiguration |
| `metolius.generic-ten-minute.intermediate` | [Metolius 10-minute guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | title, instruction, target, count | subtitle, accessory, duration, interval: source tasks expanded into app-guided task/rest steps | warmUp, cooldown, gripType, fingerConfiguration |
| `metolius.generic-ten-minute.advanced` | [Metolius 10-minute guide](https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide) | title, instruction, target, count, including source finger-count phrases, switches, stay-on transitions, choices, and failure/max qualifiers | subtitle, accessory, duration, interval: source tasks expanded into app-guided task/rest steps | warmUp, cooldown, gripType, fingerConfiguration; finger phrases remain in source-backed instructions rather than inferred structured cues |
| `research.max-hangs` | [Lattice Half 4 Hang Max](https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/) | title, instruction, gripType: 7-second, near-maximal, 20 mm, half-crimp, four-finger hangs | subtitle, accessory, target, count, duration, interval: Compact II 19 mm mapping and five-set/three-minute app timer structure | warmUp, cooldown, fingerConfiguration; the four-finger fact remains in instruction text |
| `research.force-feedback-f80` | [Frontiers F80/F100 study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | title, instruction, accessory, count, duration, interval: 80% MFSi, 10/6, 12 repetitions, three sets, eight-minute recovery | subtitle, target: Compact II substitutes its 19 mm edge for the study force-board hold | warmUp, cooldown, gripType, fingerConfiguration |
| `research.force-feedback-f100` | [Frontiers F80/F100 study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full) | title, accessory, duration: maximal 6-second alternating-hand efforts | subtitle, instruction, target, count, interval: Compact II left/right targets and app timer representation | warmUp, cooldown, gripType, fingerConfiguration |
| `research.eva-int-hangs` | [Eva López PubMed record](https://pubmed.ncbi.nlm.nih.gov/30988852/) | title: identifies the intermittent dead-hang comparison | subtitle, instruction, accessory, target, count, duration, interval: explicitly labeled app-guided realization; the linked record does not establish those exact values | warmUp, cooldown, gripType, fingerConfiguration |
| `research.seven-three-repeaters` | [Beastmaker 7/3 study](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full) | title, instruction, accessory, count, duration, interval, gripType, fingerConfiguration: two sets, six progressive series, seven reps, 7/3, 2:30 series recovery, six-minute set recovery, and documented grip/finger progression | subtitle, target: source positions mapped to Compact II edges | warmUp, cooldown |
| `research.abrahangs` | [Lattice Abrahangs](https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol) | title, instruction, count, gripType, fingerConfiguration: low-intensity feet-supported Half 4, F3 Open, M2 Open, F2 Open, B3 Half, and F3 Half variants | subtitle, accessory, target, duration, interval: Compact II mapping and 10/50 app timer | warmUp, cooldown |
| `coach.horst-seven-fifty-three` | [Eric Hörst protocols](https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/) | title, instruction, accessory, duration, gripType: 7/53, three hangs, and half/open or pocket options | subtitle, target, count, interval: Compact II choices and three-minute selection from the 3–5 minute recovery range | warmUp, cooldown, fingerConfiguration |
| `coach.bechtel-three-six-nine` | [Steve Bechtel 3–6–9](https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/) | title, instruction, duration: 3/6/9 sequence and source loading cue | subtitle, accessory, target, count, interval: three rounds and exact rest values selected from source ranges, plus Compact II targeting | warmUp, cooldown, gripType, fingerConfiguration |
| `coach.density-hangs` | [Tyler Nelson Density Hangs](https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/) | title, instruction: source ranges and 2:1 relationship remain identifiable | subtitle, accessory, target, count, duration, interval: 30/15, three reps, three-minute recoveries, set count, and Compact II holds are labeled app choices within the published ranges | warmUp, cooldown, gripType, fingerConfiguration |
| `device.zlagboard-sixty-sixty` | [Zlagboard endurance protocol](https://strengthclimbing.com/zlagboard-forearm-endurance-workout/) | title, instruction, accessory, count, duration, interval: ten 60/60 sets | subtitle, target: Compact II edge mapping | warmUp, cooldown, gripType, fingerConfiguration; unsupported feet-supported copy was removed |

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

    {"planID":"research.force-feedback-f80","fields":["title","instruction","accessory","count","duration","interval"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.force-feedback-f80","fields":["subtitle","target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.force-feedback-f80","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.force-feedback-f100","fields":["title","accessory","duration"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.force-feedback-f100","fields":["subtitle","instruction","count","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.force-feedback-f100","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.force-feedback-f100","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.eva-int-hangs","fields":["title"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.eva-int-hangs","fields":["subtitle","instruction","accessory","count","duration","interval"],"decision":"adapt","sourcePrescription":false,"adaptationType":"timer"},
    {"planID":"research.eva-int-hangs","fields":["target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
    {"planID":"research.eva-int-hangs","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false},

    {"planID":"research.seven-three-repeaters","fields":["title","instruction","accessory","count","duration","interval","gripType","fingerConfiguration"],"decision":"keep","sourcePrescription":true},
    {"planID":"research.seven-three-repeaters","fields":["subtitle","target"],"decision":"adapt","sourcePrescription":false,"adaptationType":"board"},
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
    {"planID":"device.zlagboard-sixty-sixty","fields":["warmUp","cooldown","gripType","fingerConfiguration"],"decision":"remove","sourcePrescription":false}
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
    {"planID":"research.seven-three-repeaters","stepIDPattern":".*","field":"gripType","decision":"keep","sourcePrescription":true},
    {"planID":"research.seven-three-repeaters","stepIDPattern":".*","field":"fingerConfiguration","decision":"keep","sourcePrescription":true},
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
    {"planID":"device.zlagboard-sixty-sixty","stepIDPattern":".*","field":"accessory","decision":"keep","sourcePrescription":true}
  ]
}
```
