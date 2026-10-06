# Canonical plan library

`HangTen/Resources/PlanLibrary.json` is the checked-in plan source shared by
iOS and Android. Edit the canonical JSON and retain a source mapping for every
changed prescription or classification, following [routine authoring](../ADDING_A_ROUTINE.md).
Swift seed catalogs, label authoring helpers and the standalone exporter are
retired. `PlanStorage.swift` decodes and validates the bundled document; missing
or invalid data fails explicitly.

The main integration retains all 45 plans and 90 blocks, with 24 distinct plan
source URLs. Its canonical document is 1,306,373 bytes, with SHA-256
`1e102f27e36630bf4901c5344bf50b985acbf7c6ae6e00159435c8e353eb5757`.

The original migration transferred 31 plans and 62 blocks without changing
their training content. Before retiring the exporter, its fresh output matched
the original 823,585-byte JSON, SHA-256
`2c2ecd7ae62de57928c9434029a812dfae4043fa17b071408b6ee22c5aa481d1`.
The later integration retained those original blocks and plan definitions,
apart from the explicitly audited optional focus metadata described below.

The 14 additions are two Beastmaker presets, four Tension presets, two Cameron
Hörst presets, REI Hangboard Training 101 and five Rock Prodigy presets. Their
source URLs, prescriptions, adaptations and manual-selection disclosures are
documented in the [training-plan source audit](../TRAINING_PLAN_SOURCE_AUDIT_2026-10-05.md).

The 19 optional `metadata.focus` fields are editorial adaptations documented
in the [workout chooser classification audit](../WORKOUT_CHOOSER_CLASSIFICATION_AUDIT_2026-10-05.md).
Removing exactly those fields makes the complete parsed document equal to the
prior 45-plan source. All blocks, plan order, source URLs, prescriptions and
adaptation disclosures remain unchanged; focus introduces no exercise content.

Canonical tasks retain each hand target, source step order, grip/finger cues,
timing and explicitly self-selected work. Source tests read the JSON before
runtime segment expansion and independently check the resulting assignments.
Legacy compatibility fixtures still reject ambiguous bilateral pairs rather
than flattening simultaneous hand tasks.
