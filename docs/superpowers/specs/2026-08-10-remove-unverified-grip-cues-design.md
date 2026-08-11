# Remove Unverified Grip Cues Design

## Goal

Keep Hang Ten's grip/finger cue UI when the cue is backed by the linked routine,
and remove only plan content that cannot be traced to that source. Faithful
paraphrases and necessary app formatting of source-prescribed content are
allowed.

## Scope

- Keep the grip diagram and hand/finger cue cards in plan detail and active
  workout layouts when the current source-backed plan step supplies the cue;
  hide them when the source does not specify the relevant grip or fingers.
- Remove grip and finger controls from custom routines because they have no
  linked source provenance; custom routines retain their source-neutral task
  and hold-target editing only.
- Audit every built-in plan field against its linked source. Preserve source
  facts and faithful paraphrases; remove unsupported coaching prose, arbitrary
  timing defaults, invented warm-ups/cooldowns, and unsupported grip/finger
  overrides. The audit must identify the source passage or mark the field for
  removal.
- Apply the same audit to the small instruction/accessory card: display a task
  instruction, count, duration, rest label, or coaching phrase only when it is
  source-backed or a faithful adaptation of source text. If a field has no
  source basis, omit it from the card rather than replacing it with invented
  copy.
- Keep the cue timeline policy/model and hand cue assets where they render
  source-backed cue data; remove only dead or unsupported cue branches.
- Keep persisted source-backed fields only when they are still needed for plan
  fidelity; old unsupported cue keys must decode safely and must not be
  re-emitted.
- Keep `BoardHold.gripType`, `fingerCapacity`, and `cueStyle` as board-catalog
  metadata only; these remain useful for factual board rendering and are not
  routine prescriptions.
- Keep task titles, instructions, accessories, source metadata, hold targets,
  timing, and board-map highlights unchanged.

## Architecture

The workout model remains cue-aware, but cue values are provenance-audited at
the plan-step level. The timeline resolves source-backed grip/finger cues when
present and suppresses them when absent. The board map continues to resolve
hold highlights independently of the cue card.

The resolver must not fall back from an absent source-backed step cue to
`BoardHold.gripType` or `fingerCapacity`; board metadata may describe the
physical hold, but it does not establish what the linked routine prescribed.

Persistence remains backward-compatible for old custom-routine JSON by ignoring
legacy cue keys on decode. Encoding and the generated built-in plan library
omit unsupported cue data, while source-backed built-in cues remain
representable.

## Source-grounding standard

The implementation may adapt source content for a timer or concise UI copy when
the source fact remains identifiable. It must not invent an exercise, count,
duration, interval, hold/finger requirement, safety prescription, warm-up,
cool-down, instruction-card text, accessory label, or coaching claim. A chosen
value from a source range must be identified as an app adaptation; it must not
be presented as the source's exact prescription.

The research set includes the [Metolius 10-minute guide], [Lattice Max Hangs],
[Lattice Abrahangs], the [F80/F100 Frontiers study], the [Eva López study],
the [Beastmaker 7/3 study], the [Hörst protocols], the [Bechtel 3–6–9
protocol], the [Nelson Density Hangs protocol], and the [Zlagboard protocol].
The source audit will distinguish primary manufacturer/study prescriptions from
secondary protocol summaries.

[Metolius 10-minute guide]: https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide
[Lattice Max Hangs]: https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/
[Lattice Abrahangs]: https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol
[F80/F100 Frontiers study]: https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full
[Eva López study]: https://pubmed.ncbi.nlm.nih.gov/30988852/
[Beastmaker 7/3 study]: https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full
[Hörst protocols]: https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/
[Bechtel 3–6–9 protocol]: https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/
[Nelson Density Hangs protocol]: https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/
[Zlagboard protocol]: https://strengthclimbing.com/zlagboard-forearm-endurance-workout/

## Verification

- Add a source audit covering every visible plan title, subtitle, instruction,
  accessory, target, count, duration, interval, warm-up/cool-down, and cue
  field, with an explicit keep/adapt/remove decision.
- Add/update model and persistence tests proving source-backed cue fields survive
  and unsupported built-in cue fields are absent on export.
- Update custom-routine tests to prove legacy cue fields are ignored and are not
  re-emitted.
- Update timeline/UI-facing tests to prove source-backed cues render, absent
  cues are hidden, and hold highlighting still resolves independently.
- Search the source, generated JSON, and Xcode project for cue UI/data symbols.
- Run the plan-library exporter in check mode, the focused XCTest suite, and a
  Debug simulator build.
