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
symlinks, malformed JSON or PNG data, opaque primary images, duplicate
identifiers, unsupported hold metadata, and invalid frames or shapes. A
primary PNG must contain at least one pixel whose alpha value is exactly zero;
the validator checks decoded PNG samples with the Python standard library so
the bare build-time interpreter does not need Pillow.

## Removing white source backdrops

The maintained migration tool uses the pinned `rembg` U-2-Net model to segment
every primary PNG, including primaries that already have alpha. It writes only
the model's mask into the alpha channel while retaining every decoded source
RGB sample and the original pixel dimensions. The first run downloads the
checksum-verified model into `.context/hangboard-rembg-models`; later runs
reuse it and create one model session for the complete sorted inventory.

Install the backdrop-removal dependency, then run the tool from the repository
root:

```sh
.context/hangboard-packages-venv/bin/python -m pip install \
  -e 'Tools/HangboardPackages[backdrop]'
.context/hangboard-packages-venv/bin/python \
  Tools/HangboardPackages/scripts/remove_primary_backdrops.py --root Hangboards
```

The script fails rather than writing an all-opaque or all-transparent result.
Generated output files are temporary and atomically replaced.

For the few reviewed source photos where U-2-Net retains white background in an
enclosed through-hole, the script has a tightly bounded seed map. It clears
only four-connected pixels within 12 RGB levels of the reviewed source sample,
with a 100,000-pixel ceiling; it does not run a broad white-pixel cleanup. ONNX
Runtime telemetry is disabled before the model loads, so its session sidecar is
not created in the repository root.

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
```

Both commands print the discovered complete packages and draft paths. Add
`--final-inventory` to reject any primary-only draft:

```sh
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

`audit-metadata` requires a complete final package inventory, cross-checks a
source-audited ledger against its hold metadata, and prints a sorted coverage
report. Like the other package commands, it is source-only and read-only: it
does not alter packages or the ledger.

The current repository inventory contains 44 complete packages and zero
drafts.
