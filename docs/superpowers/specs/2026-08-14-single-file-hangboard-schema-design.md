# Single-File Hangboard Schema Design

## Decision

Every direct child of `Hangboards/` is a complete app board package with exactly:

```text
manufacturer-model/
  board.json
  assets/
    primary.png
```

No incomplete board directory is committed. `board.json` is the only structured
package document.

## Physical board document

`board.json` contains product identity and physical holds. Each hold requires a
stable `id`, human-readable `name`, one of `jug`, `edge`, `pocket`, `pinch`, or
`sloper`, and one or more normalized geometry pieces. Each piece has a finite
frame and a supported closed shape. The union of a hold's pieces supplies its
runtime bounds, and those same paths draw normal contact, active contact, and
hit-testing geometry.

Measurements, depth ranges, finger capacity, grip posture, and physical feature
tags are optional. Unknown values are omitted. Coaching copy, palettes, and
routine semantics are not board-package fields.

`aspectRatio` is the presentation canvas width divided by height and must match
the decoded dimensions of `assets/primary.png` within the validator tolerance.

## Direct authoring

An operator freezes the physical inventory from primary manufacturer sources,
authors every closed path directly, and reviews it in Workbench. Exact mirroring
is used when the product is actually symmetric. When supported, a constraint may
be selected manually for a genuinely regular shape; irregular contacts remain
freeform. The constraint never replaces the canonical path.

## Discovery and validation

The validator, staging script, and iOS loader enumerate complete direct-child
packages and sort them by manufacturer, name, ID, and path. Duplicate IDs,
unsafe paths, symlinks, malformed documents, missing presentation images,
unknown keys, invalid geometry, and hold/geometry mismatches fail closed.

The final inventory command rejects every incomplete direct child:

```sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```
