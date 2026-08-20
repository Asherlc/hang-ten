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
metadata, and invalid frames or shapes.

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

The current repository inventory contains eight complete packages and zero
drafts.
