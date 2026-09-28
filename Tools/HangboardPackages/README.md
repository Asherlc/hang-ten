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
```

`validate` and `status` print the discovered complete packages and draft paths;
add `--final-inventory` to reject
any primary-only draft:

```sh
scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

The historical audit and evidence commands were removed with their source
records; package validation is the supported package check.

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
