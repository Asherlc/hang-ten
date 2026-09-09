# Hang Ten model package tooling

This directory contains the evidence-packet validator and the deterministic
USDZ-to-descriptor compiler for the schema-v2 board package contract. The
tooling is ready for a later, explicitly scoped model migration. At the
current checkpoint all 61 live `Hangboards/*/board.json` packages are raster
v2 packages; none declares `media.type: "model"`. The current model-first
schema/compiler plan does not author or migrate board geometry.

## v2 logical and presentation contract

`board.json` has `schemaVersion: 2`. Board identity, sourced physical facts,
equipment, positions, transitions, and logical hold metadata remain in the
document. Hold records contain no spatial geometry or presentation ownership.
Each presentation owns one tagged media payload:

- `raster` has `assetPath` beneath `assets/` and a non-empty
  `holdGeometry` map of normalized path pieces. Only raster presentations may
  be derived or inverted, and a canonical raster presentation must own every
  logical hold exactly once.
- `model` has a `.usdz` `assetPath`, a generated `.model.json` `descriptorPath`,
  and `display.camera` with an orthographic type, finite non-zero
  `viewDirection` and `up` vectors, and positive `fitPadding`.

Model media is model-only: a package may not mix model and raster
presentations, and a model presentation may not be derived or inverted. Its
descriptor hash must match the exact USDZ bytes and its node/hold inventory
must equal the logical inventory. Staging and sync copy declared package files
byte-for-byte; they do not synthesize a raster fallback or substitute a model
resource.

## Stage 0 evidence packets

Before any future geometry work, retain exact manufacturer evidence (and only
documented commerce gap evidence where necessary) under the packet directory.
The packet validator requires HTTPS source URLs, retained regular files beneath
the packet directory, matching SHA-256 values, a board revision/date and
locale, source-backed logical inventory, conflicts and rulings, qualitative
unknowns, material fidelity, deliberate omissions, and the required `front`,
`three-quarter`, and `clay-detail` review views. It requires `screw holes` and
`mounting hardware` as deliberate display omissions.

Start from `evidence-packet-template.json`, fill its placeholders, then run:

```sh
python3 -B Tools/HangboardModels/validate_evidence_packet.py PATH
```

This contract rejects geometry proposals and image-derived geometry fields:
coordinates, contours, masks, vectors, tracing, alignment, and numeric shape
prescriptions. Measurements are allowed only as cited source-backed claims or
metadata. The packet prepares evidence and logical identity; it does not
decide, generate, or refine geometry.

## Deterministic compiler and generated descriptor

After a separate geometry-authoring and review step, compile a tagged Blender
scene with Blender 5.2:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/compile_model_package.py -- \
  --blend PATH/board.blend --board-json Hangboards/SLUG/board.json \
  --output-directory PATH/compiled-package
```

Every authored mesh must carry `role` equal to `body` or `hold`; hold meshes
also carry a `hold_id` present in the board's logical inventory. The compiler
rejects missing or unknown tags, non-mesh authored objects, empty or unbound
geometry, inventory mismatches, missing materials/images after reimport,
changed node bindings, and physical-bounds drift. It makes disposable export
copies and triangulates only those copies. It then reimports the actual USDZ
and fails rather than repairing or redesigning a shape.

A successful output directory contains exactly:

```text
assets/primary.usdz
assets/primary.model.json
```

There is no hand-authored or standalone descriptor CLI. The compiler generates
the descriptor only after validating the actual reimported USDZ. Descriptor v1
contains `schemaVersion`, `coordinateFrame`, `modelSHA256`, `modelBounds`,
sorted `nodes`, and sorted logical `holds`; model bounds and each hold's
normalized face-plane AABB and center are derived from imported vertices and
rounded to nine decimal places. The coordinate frame is
`hang-ten-board-v1`: metres, right-handed, origin at back-bottom-left, `+X`
right, `+Y` up, and `+Z` toward the climber.

The compiler is package/tooling support, not a geometry authoring workflow.
Human visual review remains required before a future model package enters the
live inventory.
