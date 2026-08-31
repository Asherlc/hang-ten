# Hangboard package validator

This package provides fail-closed schema validation and direct discovery for
the repository's canonical hangboard packages. It is read-only: it validates
package bytes and reports inventory metadata without changing any package.

## Package contract

Each direct child of `Hangboards/` is either a complete package or an exact
primary-only draft. A complete package has this shape:

```text
Hangboards/<package>/
  board.json
  assets/
    primary.png
```

`board.json` contains the board identity, sourced physical facts, and exact
normalized hold geometry. The validator rejects unknown package entries,
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
  --final-validation
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

Ledger boards in `reviewedBoardIDs` retain the complete contract: every hold
must have one outcome for each supported metadata field. Boards in the
disjoint `sloperOnlyBoardIDs` scope must instead have exactly one `sloper`
outcome for every hold and may not have records for unrelated fields. This
supplemental scope records a complete sloper audit without claiming that the
board's other metadata fields have been source-audited.

The current repository inventory contains 61 complete packages and zero
drafts.
