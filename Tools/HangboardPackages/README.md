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

Direct discovery sorts complete packages by manufacturer, board name, board
ID, and package path. Exact primary-only directories are reported separately
as drafts. Any other incomplete directory fails validation.

## Commands

Run the repository wrapper from the checkout root:

```sh
scripts/hangboard-packages.sh validate --root Hangboards
scripts/hangboard-packages.sh status --root Hangboards
```

Both commands print the discovered complete packages and draft paths. Add
`--final-inventory` to reject any primary-only draft:

```sh
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

The current repository inventory contains 44 complete packages and zero
drafts.
