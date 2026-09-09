# Hangboard package validator

This package provides fail-closed schema validation and direct discovery for
the repository's canonical hangboard packages. It is read-only: it validates
package bytes and reports inventory metadata without changing any package.

## Package contract

Each direct child of `Hangboards/` is either a complete package or an exact
primary-only draft. A complete raster package has this shape:

```text
Hangboards/<package>/
  board.json
  assets/
    primary.png
```

A complete model package has the same `board.json` root and instead declares:

```text
Hangboards/<package>/
  board.json
  assets/
    primary.usdz
    primary.model.json
```

`board.json` uses schema version 2: board identity and sourced physical facts
remain logical, while each presentation owns typed raster or model media. A
raster presentation stores exact normalized hold geometry in
`media.holdGeometry`; a model presentation stores a confined USDZ,
`descriptorPath`, and orthographic display configuration. Logical hold records
contain no presentation ownership or spatial fields. Derived presentations are
raster-only; model media cannot be derived or inverted, and a model package may
not carry a raster fallback. The validator rejects unknown package entries,
symlinks, malformed JSON or PNG data, duplicate identifiers, unsupported hold
metadata, and invalid frames or shapes. Primary PNGs may use either transparent
or fully opaque backgrounds; the validator checks decoded primary image data
with the Python standard library so the bare build-time interpreter does not
need Pillow.

Direct discovery sorts complete packages by manufacturer, board name, board
ID, and package path. Exact primary-only directories are reported separately
as drafts. Any other incomplete directory fails validation.

## Commands

Run the repository wrapper from the checkout root:

```sh
scripts/hangboard-packages.sh validate --root Hangboards
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

Preflight validates the 20 exact canvas classes, 22 disposable behavior probes,
and capability-artifact deletion/production-disjointness. Partial mode validates
truthful intermediate package bytes and may select one declared `--batch-id`.
Final mode accepts no batch or transient files and requires the complete terminal
catalog. Repeated `--source-file SHA256 PATH` and `--candidate-file SHA256 PATH`
pairs are accepted only in preflight or partial mode and only for declarations
owned by that lifecycle; duplicate SHA keys and cross-lifecycle reuse fail closed.

The current repository inventory contains 61 complete packages and zero drafts.
All 61 live packages are raster v2 at this checkpoint; no package currently
declares `media.type: "model"`. Model schema support and compiler tooling are
available for a later explicitly scoped geometry migration, but this plan does
not migrate a board or author geometry.

## Schema migration

The one-way migration utility discovers direct-child packages at execution
time. It preserves legacy raster scalars, hold ordering, and path command
ordering while moving geometry into typed raster media. Run a write followed by
the idempotent check before committing package changes:

```sh
python3 Tools/HangboardPackages/scripts/migrate_to_schema_v2.py \
  --root Hangboards --write
python3 Tools/HangboardPackages/scripts/migrate_to_schema_v2.py \
  --root Hangboards --check
```

After migration, both the Python catalog parser and the iOS loader require
`schemaVersion: 2`; unversioned v1 documents are intentionally rejected.

## Model tooling boundary

The Stage 0 evidence packet is validated before any future model work. The
packet contains source provenance and logical inventory only; it contains no
coordinates, contours, masks, vectors, alignment, or numeric shape
prescriptions:

```sh
python3 -B Tools/HangboardModels/validate_evidence_packet.py PATH
```

The later compiler consumes a reviewed Blender file and the logical inventory,
then emits exactly `assets/primary.usdz` and
`assets/primary.model.json`:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/compile_model_package.py -- \
  --blend PATH/board.blend --board-json Hangboards/SLUG/board.json \
  --output-directory PATH/compiled-package
```

The descriptor is generated from the actual reimported USDZ, rounded to nine
decimal places, and hash-bound to its exact bytes. The compiler never repairs
or redesigns shape. See `Tools/HangboardModels/README.md` for the descriptor
fields and model-only package rules.
