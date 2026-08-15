# Single-File Hangboard Schema Design

## Decision

Every direct child of `Hangboards/` that contains `board.json` is an app board.
There is no root catalog and no package-side artwork, semantics, or evidence
document. A finished board directory contains exactly:

```text
manufacturer-model/
  board.json
  assets/
    primary.png
```

Primary-only directories remain non-runtime drafts during migration. Final
inventory validation requires every board directory to contain `board.json`.

## Physical board document

`board.json` contains product identity plus physical holds. Each hold requires
a stable ID, a human-readable physical name, one of `jug`, `edge`, `pocket`,
`pinch`, or `sloper`, and one or more normalized geometry pieces. A reviewed
photo/spec inspection may classify `kind`.

Exact measurements, depth ranges, finger capacity, grip posture, and physical
feature tags are optional. Unknown values are omitted and remain unknown at
runtime; the loader must not manufacture defaults.

Each geometry piece contains its normalized frame, shape, and optional physical
profile. The union of those pieces supplies the runtime hold bounds. The same
piece paths draw normal contact, active contact, and hit-testing geometry.

`cueStyle`, `shortLabel`, coaching detail, palettes, colors, shadows, and
gradients are app presentation concerns and are not board fields. The app owns
all styling. Board-specific routine semantics are training-plan concerns and
do not live in a board package.

## Discovery and validation

The repository validator, staging script, and iOS loader enumerate direct
children rather than reading `catalog.json`. Packages are sorted by
manufacturer, name, then ID. Duplicate IDs, unsafe paths, symlinks, malformed
documents, missing primary images, unknown keys, invalid normalized geometry,
or model/geometry mismatches fail closed.

During migration, a direct child containing only `assets/primary.png` is
ignored by runtime staging. After all authoring batches, the final inventory
test rejects any remaining primary-only directory.

## Migration and delivery

The current Compact II package migrates first and proves the schema end to end.
Its existing physical hold data and vector paths are combined into one board
document; its semantics and evidence are not carried forward. The remaining
boards are then authored in small image-audited batches. Each batch verifies
model hold IDs equal geometry hold IDs and inspects inactive and active paths
in portrait and landscape.
