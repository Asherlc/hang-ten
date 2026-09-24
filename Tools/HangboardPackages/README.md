# Hangboard package validator

This package provides fail-closed, read-only validation and direct discovery
for the repository's schema-v3 hangboard packages.

## Package contract

Every completed package is a direct child of `Hangboards/` containing exactly
`board.json` and its declared files below `assets/`. A model package with a
native CAD source instead contains `<package-directory>.FCStd` and its assets,
and **no** `board.json`: its board document is generated from the FCStd's
`HangTenBoardManifest` at build time (`hangboard_packages.cad_source`; see
`Tools/HangboardCAD/README.md`). The validator validates the exact generated
bytes with the same checks as a committed `board.json`, and rejects an on-disk
`board.json` in a CAD-backed package as a stale hand edit. Use
`board_catalog.read_board_json(package_root)` (or `BoardPackage.generated_board_json`)
rather than reading `board.json` from disk. A package may contain one or more
presentations, but exactly one is the default.

`contacts[]` is the only physical-fact inventory. Each contact has a stable ID,
an equipment object, a sourced name and kind, and only those optional facts that
the cited evidence supports. Contacts do not own presentation geometry.

Each raster presentation declares a PNG and canonical normalized paths under
`media.contactGeometry`, keyed by contact ID. Each geometry piece contains its
frame, closed shape, treatment, and optional operator-selected constraint.
Each model presentation instead declares a confined USDZ, hash-bound contact
descriptor, and orthographic display configuration. Model packages contain no
raster stand-in or fallback geometry.

The validator rejects older or unversioned schemas, unknown package entries,
symlinks, undeclared or missing assets, malformed JSON or PNG data, duplicate
identifiers, unsupported factual fields, invalid contact references, and
invalid frames or paths. It never upgrades or writes a package.

## Commands

From the repository root:

```sh
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
scripts/hangboard-packages.sh status --root Hangboards
scripts/hangboard-packages.sh audit-metadata --root Hangboards \
  --ledger docs/source-audits/2026-08-25-hangboard-metadata-ledger.json
scripts/hangboard-packages.sh audit-presentations --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --phase2-preflight
```

`validate` and `status` print the discovered complete packages and draft paths;
`audit-metadata` prints its coverage report. Add `--final-inventory` to reject
any primary-only draft:

```sh
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

`audit-metadata` requires a complete final package inventory, cross-checks a
source-audited ledger against its hold metadata, and prints a sorted coverage
report. Like the other package commands, it is source-only and read-only: it
does not alter packages or the ledger.

`audit-cords` requires one closed record for every discovered model package.
Each evidence entry must retain `exactRevisionID`, a controlled `sourceTier`,
`snapshotSHA256`, and a relative `snapshotPath` to a retained source response
or media file. Snapshot paths and SHA-256 values must be distinct for every
distinct evidence view in a represented record; markdown audit ledgers are
rejected as snapshots. Every record must also carry the independent
source-fact field `sourceFact`: `documentedSuspension` for a source-documented
suspended presentation or `noDocumentedSuspension` when the reviewed evidence
does not document one. Both represented and excluded records require retained
source evidence; an excluded record with `documentedSuspension` is rejected
even if its package suspension metadata has been removed. Every record must
also contain an explicit approved `humanApproval` object with reviewer, date,
and notes. Incomplete provenance or approval is rejected before topology
coverage is checked. Optional rope or bungee evidence supports a documented
presentation without claiming that an accessory is supplied or integral.

Ledger boards in `reviewedBoardIDs` retain the complete contract: every hold
must have one outcome for each supported metadata field. Boards in the
disjoint `sloperOnlyBoardIDs` scope must instead have exactly one `sloper`
outcome for every hold and may not have records for unrelated fields. This
supplemental scope records a complete sloper audit without claiming that the
board's other metadata fields have been source-audited.

`audit-presentations` requires a complete final inventory and cross-checks the
closed remediation manifest against every declared presentation's package ID,
asset path, PNG hash, and dimensions. It prints a sorted decision report. A
repeatable `--package-id BOARD_ID` selects a validation lane for required
presentation coverage and report counts; the manifest's root `packageIDs` must
still cover the entire inventory, and every record it does contain is still
fully validated against real package assets.

Use `--final-validation` only for the completed Phase 1 ledger. It rejects lane
selection and requires all four root `phase1Checks` entries to be
`passed` with their exact non-empty commands; omit it for skeleton and
intermediate-lane validation while those checks are still pending.

Schema 2 uses three mutually exclusive lifecycle modes:

```sh
scripts/hangboard-packages.sh audit-presentations --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --phase2-preflight
scripts/hangboard-packages.sh audit-presentations --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --phase2-partial --batch-id nonwood-fixed
scripts/hangboard-packages.sh audit-presentations --root Hangboards \
  --manifest docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json \
  --phase2-final
```

`--final-inventory` rejects incomplete direct children. The metadata and
presentation audits cross-check tracked source decisions and declared asset
hashes without changing either input.

## Model workflow

A package with a native FreeCAD source is compiled by
`Tools/HangboardCAD/compile_board.py`; see `Tools/HangboardCAD/README.md`.
Otherwise the model compiler is contact-native. It consumes a human-reviewed
Blender file and the exact `contacts[]` inventory, then writes only a USDZ and
its hash-bound contact descriptor:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/contact_model_package.py -- \
  --blend PATH/board.blend --board-json Hangboards/SLUG/board.json \
  --output-directory PATH/compiled-package
```

`import_contact_model_source.py` performs the reviewed source import, and the
board-specific Baguette verifier checks the shipped promotion. No raster/contact
migration utility or older-schema reader/writer is supported.
