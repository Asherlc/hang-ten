# Remove Unverified Grip Cues Design

## Goal

Remove Hang Ten's grip/finger cue UI and remove plan content that cannot be
traced to the linked routine, while allowing faithful paraphrases and
necessary app formatting of source-prescribed content.

## Scope

- Remove the grip diagram and hand/finger cue cards from plan detail and active
  workout layouts in portrait and landscape, regardless of whether a source
  happens to mention a grip.
- Remove grip and finger controls from the custom-routine editor.
- Audit every built-in plan field against its linked source. Preserve source
  facts and faithful paraphrases; remove unsupported coaching prose, arbitrary
  timing defaults, invented warm-ups/cooldowns, and unsupported grip/finger
  overrides. The audit must identify the source passage or mark the field for
  removal.
- Remove cue-only timeline policy/model code and hand cue assets that no longer
  have consumers.
- Keep persisted source-backed fields only when they are still needed for plan
  fidelity; old unsupported cue keys must decode safely and must not be
  re-emitted.
- Keep `BoardHold.gripType`, `fingerCapacity`, and `cueStyle` as board-catalog
  metadata only; these remain useful for factual board rendering and are not
  routine prescriptions.
- Keep task titles, instructions, accessories, source metadata, hold targets,
  timing, and board-map highlights unchanged.

## Architecture

The visible workout model becomes cue-agnostic: cue views and hold-cue policy
are removed, while source-backed routine fields remain only where the audit
shows that they represent the original prescription. The board map remains the
sole hold visualization, and the workout timeline continues to resolve
highlight IDs without producing a hold cue object.

Persistence remains backward-compatible for old custom-routine JSON by decoding
and ignoring removed or unsupported keys. Encoding and the generated plan
library omit unsupported data, preventing invented cues from surviving or being
recreated.

## Source-grounding standard

The implementation may adapt source content for a timer or concise UI copy when
the source fact remains identifiable. It must not invent an exercise, count,
duration, interval, hold/finger requirement, safety prescription, warm-up,
cool-down, or coaching claim. A chosen value from a source range must be
identified as an app adaptation; it must not be presented as the source's exact
prescription.

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
- Add/update model and persistence tests proving removed cue keys are ignored
  on decode and unsupported fields are absent on encode/export.
- Update custom-routine tests to prove custom steps no longer expose or persist
  cue fields.
- Update timeline/UI-facing tests to prove hold highlighting still resolves and
  no hold-cue policy remains.
- Search the source, generated JSON, and Xcode project for cue UI/data symbols.
- Run the plan-library exporter in check mode, the focused XCTest suite, and a
  Debug simulator build.
