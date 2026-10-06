# Canonical plan library migration

`HangTen/Resources/PlanLibrary.json` becomes the checked-in plan source shared
by iOS and Android. The original 31-plan migration changed storage and loading
without changing training content. The later main integration preserves main's
14 additional audited presets in the same canonical source format. A subsequent
main integration adds only audited optional chooser focus metadata.

Before removing the Swift authoring catalog, the existing
`scripts/export-plan-library.sh --check` completed successfully: its fresh export
of all 31 plans matched the retained JSON byte for byte. The original document
and parsed snapshot were saved in workspace-owned
`.context/mad-tiger-linux-port/PlanLibrary.original.json` and
`PlanLibrary.original.parsed.json` before editing production code.

The original migration retained exactly those 823,585 bytes:

```text
SHA-256: 2c2ecd7ae62de57928c9434029a812dfae4043fa17b071408b6ee22c5aa481d1
31 plans, 62 blocks, 18 distinct plan source URLs
```

In the original migration, byte equality and parsed-document equality covered
every metadata field, source URL, provenance value, block reference, repetition
count, step ID and order,
duration, segment, hand target, grip and finger cue, instruction, accessory,
note, and workout label. Their existing source links and audited adaptations
remain the authority for those fields; this migration introduces no new
prescription or source claim.

`PlanStorage.swift` continues to decode, validate, and resolve the bundled document.
Missing or invalid bundled data now fails explicitly, with no Swift source
fallback. The Swift seed catalog, its task migration and label assignments, the
DEBUG seed comparison, and the standalone exporter are removed. Plan source
tests read the canonical JSON at the original step boundary before runtime
segment expansion, retaining the source-prescription assertions.

The retired catalog's named seeds exposed legacy contact requirements or a
self-selected target, while its `.all` export already converted these into
canonical per-hand tasks. The original migrated JSON retained that shipped task format.
Tests now assert the exact hand targets, counts, sides, grip/finger cues, and
timing in the canonical source and resolve contact assignments through the
task-aware API. Athlete-selected work remains a task with no contact predicates.
Legacy selection compatibility tests retain explicit requirement fixtures,
including rejection of ambiguous bilateral pairs, rather than flattening hand
tasks and losing their simultaneous assignment semantics.

Before the main integration, focused Simulator validation passed 585 unit tests
and the Mini Bar two-board UI regression, with no failures and one existing
historical-audit skip. This includes all 11 adapted canonical-source cases and
the original complete built-in catalog comparison against independently expanded
canonical fixtures.

The earlier integration of main `838f112dc68c6a0fdd3a8e19ceb85634e3c8af5f` used
that commit's `HangTen/Resources/PlanLibrary.json` byte for byte. That version
contained:

```text
1,305,794 bytes
SHA-256: 3ecdd44a939671dd6efabc95cfac5168a6b6221235ec8af03b87fde0071b6df7
45 plans, 90 blocks, 24 distinct plan source URLs
metadata.generatedAt: 2026-10-05
```

At that integration, comparison against the saved original snapshot confirmed
that all 31 original plan definitions and all 62 original blocks remained equal
by ID, and the original plan order was preserved. Library metadata was unchanged except for
`generatedAt`, which advances from `2026-08-01` to `2026-10-05`.

The 14 additions are the two Beastmaker presets, four Tension presets, two
Cameron Hörst presets, REI Hangboard Training 101, and five Rock Prodigy presets.
Their source URLs, prescriptions, adaptation choices, and manual-selection
disclosures are retained from main and documented in the
[2026-10-05 training-plan source audit](../TRAINING_PLAN_SOURCE_AUDIT_2026-10-05.md).
This integration introduces no further prescription changes. JSON remains the
authoring source; Swift seed definitions and the standalone exporter stay retired.

The current chooser integration retains main
`f7d113822c6345a1c37421b75851c94870949a3f` byte for byte:

```text
1,306,373 bytes
SHA-256: 1e102f27e36630bf4901c5344bf50b985acbf7c6ae6e00159435c8e353eb5757
45 plans, 90 blocks, 24 distinct plan source URLs
19 added optional plan metadata.focus fields
```

Removing exactly those 19 newly added `focus` fields makes the complete parsed
document equal to the prior 45-plan source. All 90 blocks, plan order, library
metadata, source URLs, prescriptions, and adaptation disclosures are unchanged.
All 19 additions occur among the original 31 plans; those original definitions
remain deeply equal to their saved snapshot after excluding only the added
focus fields, and all 62 original blocks remain equal.

The classifications are the explicit editorial adaptations documented in the
[workout chooser classification audit](../WORKOUT_CHOOSER_CLASSIFICATION_AUDIT_2026-10-05.md).
They introduce no exercise or prescription changes. Author optional focus in
canonical JSON; the retired Swift label authoring helper stays removed.
The workspace-owned comparison receipt is
`.context/mad-tiger-linux-port/mad-tiger-chooser-main-source-receipt.json`.

The merged chooser passed 312 plan, filter, and board package unit tests and
all six chooser UI tests on iOS 26.5 with the complete Linux-generated catalog;
one existing historical-audit test remained skipped. All 159 source hashes and
156 Linux asset hashes matched the build receipt. The source, built bundle, and
installed app carried identical canonical JSON. The temporary Simulator and
DerivedData were deleted, and exact registration and filesystem deletion were
independently verified.

Future plan changes must edit this canonical JSON and retain a source audit for
each changed field, as described in [Adding a training routine](../ADDING_A_ROUTINE.md).
