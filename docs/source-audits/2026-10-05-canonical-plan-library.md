# Canonical plan library migration

`HangTen/Resources/PlanLibrary.json` becomes the checked-in plan source shared
by iOS and Android. This migration changes storage and loading, without changing
training content.

Before removing the Swift authoring catalog, the existing
`scripts/export-plan-library.sh --check` completed successfully: its fresh export
of all 31 plans matched the retained JSON byte for byte. The original document
and parsed snapshot were saved in workspace-owned
`.context/mad-tiger-linux-port/PlanLibrary.original.json` and
`PlanLibrary.original.parsed.json` before editing production code.

The canonical document retains exactly those 823,585 bytes:

```text
SHA-256: 2c2ecd7ae62de57928c9434029a812dfae4043fa17b071408b6ee22c5aa481d1
31 plans, 62 blocks, 18 distinct plan source URLs
```

Byte equality and parsed-document equality cover every metadata field, source
URL, provenance value, block reference, repetition count, step ID and order,
duration, segment, hand target, grip and finger cue, instruction, accessory,
note, and workout label. Their existing source links and audited adaptations
remain the authority for those fields; this migration introduces no new
prescription or source claim.

`PlanStorage.swift` continues to decode, validate, and resolve the same document.
Missing or invalid bundled data now fails explicitly, with no Swift source
fallback. The Swift seed catalog, its task migration and label assignments, the
DEBUG seed comparison, and the standalone exporter are removed. Plan source
tests read the canonical JSON at the original step boundary before runtime
segment expansion, retaining the source-prescription assertions.

The retired catalog's named seeds exposed legacy contact requirements or a
self-selected target, while its `.all` export already converted these into
canonical per-hand tasks. The unchanged JSON retains that shipped task format.
Tests now assert the exact hand targets, counts, sides, grip/finger cues, and
timing in the canonical source and resolve contact assignments through the
task-aware API. Athlete-selected work remains a task with no contact predicates.
Legacy selection compatibility tests retain explicit requirement fixtures,
including rejection of ambiguous bilateral pairs, rather than flattening hand
tasks and losing their simultaneous assignment semantics.

Focused Simulator validation passed 585 unit tests and the Mini Bar two-board
UI regression, with no failures and one existing historical-audit skip. This
includes all 11 adapted canonical-source cases and the complete built-in catalog
comparison against independently expanded canonical fixtures.

Future plan changes must edit this canonical JSON and retain a source audit for
each changed field, as described in [Adding a training routine](../ADDING_A_ROUTINE.md).
