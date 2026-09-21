# Task 7 report — Batch 04 source-audit documents

## Owned verification resource

- Owner: `learned-giraffe`
- Resource: Task 7 full `Tools/HangboardPackages` pytest process, PID `66762`
- Log: `.superpowers/sdd/2026-09-20-hangboards-batch-04-3d-migration/task-7-full-pytest.log`
- Lifecycle: PID `66762` is absent after exiting without a result; no owned
  pytest process remains.

The first foreground-wrapper background launch (PID `65053`) exited without a
test result because its parent shell closed. It was absent before this retry;
the tracked retry uses `nohup` and replaces the same incomplete log.

## TDD record

RED was observed with the new document-only test before source retention:
`rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch04_source_audit.py -q`
failed with the expected missing source-register/evidence/checksum paths.

GREEN focused result: `7 passed in 0.06s`.

The controller independently completed the required exact full command with a
session-aware runner (this is controller verification, not an implementer log):

```text
rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests -q
650 passed in 137.91s (exit 0)
```

My foreground full-suite attempts were stopped by the local RTK wrapper at
about 30 seconds after 88%+ output, so they are not represented as passing
runs. A bounded non-presentation shard passed `505 passed in 23.80s`; the
controller result above is the definitive complete-suite evidence.

## Retention result

All six delivered GLBs, all twelve delivered source-register/media-manifest
documents, nine batch-supplied originals, and the seven currently exact
approved URL files were retained and hash-verified. The rejected Pivot GLB is
retained as evidence only.

The live Squarespace Light Rail binary returned changed bytes
`7d06ec5f74917b909b031ac72067944f8cf72b14481aa0e31eafc272600c0aea`
(702,408 bytes) and was not retained. The retained exact 848,076-byte
candidate hashes to `93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a`.
It is replayed evidence from
`https://web.archive.org/web/20260129012402id_/https://images.squarespace-cdn.com/content/v1/5b4544e485ede17941bc95fc/452f6e96-37f1-454d-a405-e801658501a5/metolius-light-rail-1.jpg`
at `2026-01-29T01:24:02Z`; no changed live bytes were blessed.

| Retrieved approved file | SHA-256 |
| --- | --- |
| Helium front | `9f5dea470c326d32c6bde1dd5427f2bfb95a81b99ae258c320ae9deec0384a40` |
| Light Rail manufacturer photo | `7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272` |
| Rock Rings manufacturer photo | `d92a0f25dab857eae2ee9b8581651fa9162452c38e32a7955e23c74de4a3d77c` |
| Pivot front | `339f743c7e5fff0b0619314cf6781d8f602c1545975390f4ab4424aa7461bf5d` |
| Pivot dual-board oblique | `e05deb5c0ea6d3361122926d7b3efee6b72bb9aad0a75fc09663bf599731e3e4` |
| Pivot single-board oblique | `7aa2556dec24293e62c2be110fa7dfb6bcf118333ff35693e455a8a7babc67f7` |
| Pivot close-up | `26cf8d599a1a08bbcbbf688e14c9806d5f2381dc2aecdb608998ab22cee2c1b3` |

## Closed-schema implementation-plan discrepancy

`2026-09-13-model-hangboard-cord-audit.json` is intentionally schema-closed
to exactly `schemaVersion` and `records`; its validator additionally requires
the record IDs to exactly equal the current discovered model-media package
inventory. None of the six Batch 04 packages is model-media yet. Adding their
future records now would fail the required full suite with unknown model
package records. Therefore their exact source facts and cord rulings are
retained in the new Batch 04 source register and are summarized in the cord
audit Markdown handoff; each record must enter the closed JSON only with its
own package migration.

`2026-08-30-hangboard-presentation-remediation-manifest.json` is also
schema-closed. A candidate top-level Batch 04 linkage was rejected by the
existing audit test as an unknown manifest key, so it was removed. The source
register is the valid Batch 04 supersession authority; the historical manifest
remains parseable without an unsupported schema extension.
