# Hangboard package validator

This package provides fail-closed, read-only validation and direct discovery
for the repository's schema-v3 hangboard packages.

## Package contract

Every catalog board retains one flat `Hangboards/<slug>.FCStd`; its generated
package is the adjacent `Hangboards/<slug>/` directory. Discovery starts from
the flat source files, so a fresh source-only checkout need not contain package
directories. USDZ, `*.model.json`, optional `*.physics.json`, and
`assets/suspension.json` files in those directories are ignored build outputs.
Run `scripts/build-board-assets.sh` before validation
to compile them from the sources using pinned FreeCAD 1.1.3/OpenUSD 26.8.

The board document is generated in memory from the FCStd's
`HangTenBoardManifest` and validated generated `assets/suspension.json`
(`hangboard_packages.cad_source`; see [the CAD guide](../HangboardCAD/README.md)).
There is **no** on-disk `board.json` in a native package: the validator rejects
one as a stale hand edit. Use `board_catalog.read_board_json(package_root)` or
`BoardPackage.generated_board_json`. Cord/simulation authoring lives in the
document-level string properties `HangTenSuspensionAuthoring` and
`HangTenRopePhysics`; hashes, settled heights, and routes are generated outputs.
The package generator rejects absent/stale suspension artifacts and authoring
payload mismatches. Staging writes the same generated document
into iOS and Android packages. A package may have several presentations, with
exactly one default. Existing manifest-only legacy suspensions do not require
a separate artifact; the [CAD guide](../HangboardCAD/README.md) lists those
retained packages. An artifact is required for embedded
`HangTenSuspensionAuthoring`, not for a source with no such property.

`contacts[]` is the only physical-fact inventory. Each contact has a stable ID,
an equipment object, a sourced name and kind, and only those optional facts that
the cited evidence supports. Contacts do not own presentation geometry.

The schema also supports raster presentations that declare a PNG and canonical
normalized paths under
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
rtk proxy bash scripts/build-board-assets.sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
```

`validate` and `status` print the discovered complete packages and draft paths;
add `--final-inventory` to reject
any primary-only draft:

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

The read-only CLI also supports explicit author-provided audit inputs:

```sh
rtk scripts/hangboard-packages.sh audit-metadata --root Hangboards --ledger <ledger.json>
rtk scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest <cord-audit.json>
rtk scripts/hangboard-packages.sh audit-presentations --root Hangboards --manifest <presentation-audit.json>
```

These commands validate their respective closed audit schemas. A package's
`assets/suspension.json` is generated runtime metadata, not a cord-audit manifest.
Historical catalog-wide audit inputs are not supplied by this package; use current retained
source evidence and an explicit manifest when running an audit command.
Run `rtk scripts/hangboard-packages.sh <command> --help` for its options.

## Model workflow

A package's native source is compiled by
`Tools/HangboardCAD/compile_board.py`. The shared producer compiles every declared
model presentation, verifies model/descriptor/physics hash bindings, checks
embedded suspension authoring against the generated routes and new exports,
and installs the generated files at their existing ignored runtime paths:

```sh
rtk git lfs pull
rtk proxy bash scripts/build-board-assets.sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

The compiler derives descriptor bounds and bindings from its exact exported
meshes. The FCStd remains the geometry and embedded metadata source; there is
no Blender board compiler/importer or per-board Python build input.

For a complete fresh-checkout app build, use `scripts/build-runtime-assets.sh`,
which also exports the grip hand mesh and plan library. CI's
`compile-board-assets` action produces the runtime artifact that consumer jobs
download before validation or Xcode staging. See
[generated artifacts](../../docs/GENERATED_ARTIFACTS.md).
