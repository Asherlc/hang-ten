# Hang Ten model package tooling

This directory contains the evidence-packet validator and the deterministic
USDZ-to-descriptor compiler for the schema-v2 board package contract. The
completed inventory contains 58 raster v2 packages and three model-only
packages: Beastmaker 1000, Metolius Wood Grips Compact II, and Tension Flash
Board. The three promoted model package trees contain `board.json`, `assets/primary.usdz`, and
`assets/primary.model.json`; model media is read-only. This tooling documents
demonstrated package validation and staging, not remote model sync or model
editing.

## v2 logical and presentation contract

`board.json` has `schemaVersion: 2`. Board identity, sourced physical facts,
equipment, positions, transitions, and logical hold metadata remain in the
document. Hold records contain no spatial geometry or presentation ownership.
Each presentation owns one tagged media payload:

- `raster` has `assetPath` beneath `assets/` and a non-empty
  `holdGeometry` map of normalized path pieces. Only raster presentations may
  be derived or inverted, and canonical raster presentations collectively own
  every logical hold ID exactly once, forming an exact, single-owner partition.
- `model` has a `.usdz` `assetPath`, a generated `.model.json` `descriptorPath`,
  and `display.camera` with an orthographic type, finite non-zero
  `viewDirection` and `up` vectors, and positive `fitPadding`.

Model media is model-only: a package may not mix model and raster
presentations, and a model presentation may not be derived or inverted. Its
descriptor hash must match the exact USDZ bytes and its node/hold inventory
must equal the logical inventory. Staging copies declared package files
byte-for-byte; it does not synthesize a raster fallback or substitute a model
resource. Remote GitHub model-package sync is deferred/unsupported by the
current PNG/default-oriented GitHub sync. Workbench model editing is
read-only/unavailable; raster Workbench editing remains supported.

## Extracted verification and migration bookkeeping

The shared verifier is the preservation boundary for the shipped model
packages. `model_verification.ModelVerificationConfig` carries the expected
ordered logical IDs, exact package asset set, role/material policy, triangle
ceiling, and additive board probes. Call
`model_verification.verify_model_package(package, config, render=False)` for
the common package, descriptor, material, imported-node, triangle, and
regenerated-descriptor checks. The board-specific wrappers remain the public
CLI compatibility layer:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/verify_beastmaker_1000.py -- \
  --output .context/OWNER-beastmaker-1000/package --skip-renders
```

The wrapper's `beastmaker_config()` and Compact II's
`compact_ii_config()` supply the shared `ModelVerificationConfig` when these
documented Blender entrypoints run.

Compact II uses `compact_ii_config()` and retains its fixed 19-ID inventory,
150,000-triangle ceiling, exact two-asset package, and `--skip-renders`
compatibility mode. Beastmaker retains its fixed 22-ID inventory and authored
rim/nearest-hit probe. Do not use these adapters to infer identity from
imported names. `verify_tension_flash_board.py` remains a separate Flash
verifier and baseline: its package, generator, and two-branch presentation are
not part of this shared route until separately approved.

Capture a pre-extraction record with
`model_characterization.capture_model_baseline(package, board_json)` and
compare it with `assert_baseline_matches(actual, expected)`. The record
preserves exact regular-file asset inventory, model and descriptor SHA-256
values, descriptor data, and logical hold order. The staging contract remains
`scripts/stage-board-packages.py`'s recursive copy of parser-approved regular
files; the staging tests compare every staged file's bytes with its source.
No model resource is synthesized, renamed, substituted, or synchronized to a
remote service.

Migration bookkeeping is a closed document. Validate an actual manifest with
`migration_manifest.load_migration_manifest(path)`; the checked-in
`migration-manifest.example.json` contains placeholders and is not itself a
verified board record. After verification, the fixed-view gallery interface
can be called as follows (the output must be a direct, owner-prefixed child of
the canonical workspace `.context`):

```python
from pathlib import Path
from migration_manifest import load_migration_manifest
from render_model_gallery import render_model_gallery

manifest = load_migration_manifest(Path("PATH/migration-manifest.json"))
artifacts = render_model_gallery(
    Path(".context/OWNER-beastmaker-1000/package"),
    manifest,
    Path(".context/OWNER-beastmaker-1000-gallery"),
)
```

The gallery imports only the verified USDZ, records fixed-view PNG hashes and
provenance, and requires explicit cleanup of the owned output directory. It
does not open source blends/images or edit model geometry. The Swift
single-cord runtime boundary is `SuspensionProfileSolver.solveSingle` behind
`SuspendedBoardPresentation`; keep the cord transient, invisible-anchor,
non-pickable, and unavailable-on-invalid-input behavior. Two-branch solving
and Flash adoption remain separately gated and unsupported here.

## Stage 0 evidence packets

For any future model migration, retain at least two complete exact-revision
visual images per board under the packet directory: one manufacturer-published
image and, where available, a materially different oblique/side/back/profile
view. Record each image's pixel dimensions, retrieval date/locale, exact angle,
page linkage, source tier, SHA-256, and the geometric facts that view can and
cannot support. Authorized retailer/distributor images fill only a documented
manufacturer gap and are labeled commerce-gap evidence. Crops, duplicates,
search thumbnails, reviews/forums, generated renders, and ambiguous revision
media do not satisfy the gate; diagrams supplement but do not count as a
distinct-angle photograph unless they expose side/profile geometry. Retain
exact manufacturer evidence (and only documented commerce gap evidence where
necessary) under the packet directory.
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
Human visual review of the display geometry was completed before the two model
packages entered the live inventory. The shared warm-white/light-neutral
fallback and final front lighting were subsequently reviewed in the actual app
renderer and human-approved. Package-local descriptors are generated from
actual exports and remain read-only.

## Canonical wood display material

Every shipped wood display model uses the one committed original source
`assets/canonical-neutral-wood.png`: light neutral, low-to-moderate fine grain,
and no species-match, logo, knot, stain, or board-color claim. The PNG declares
its encoded color explicitly with standard-sRGB `sRGB`, `gAMA`, and `cHRM`
chunks so the source and self-contained USDZ payload do not depend on a
decoder's unprofiled-image default. The deterministic v5 generator, its
color-profile intent, and the SceneKit-calibrated light-tan albedo are in
`canonical_neutral_wood.py`; regenerate the asset
only with:

```sh
rtk python3 -B Tools/HangboardModels/canonical_neutral_wood.py
```

The approved canonical PNG SHA-256 is
`fdab3b78ce575a0dbf90b300db4d52438cb94f7e71cd6d589d56a044de97ec0a`.
The final packages and generated descriptors are:

| package | USDZ SHA-256 | descriptor SHA-256 | inventory |
| --- | --- | --- | --- |
| Beastmaker 1000 | `19fb5895575792fb69e82aa3c8a04fa14a6bd40a8a97f486bc16be014e546f3d` | `ee095c463804312cbd6ed08f5113019793b934ab6806a6fb343be939ff8a68d3` | 22 holds / 23 nodes |
| Compact II | `addf2cd2ddd34f18f311ccc1413ca94644df0d2f3d56020b68edf25625bc664a` | `a652b1a184ec15432126502514d11db2b02768df7c3c0a892c62031f381c0c7f` | 19 holds / 20 nodes |

Each exporter loads and packs those exact bytes, so its USDZ remains
self-contained/offline while both packages embed the same stable
`textures/canonical-neutral-wood.png` member. After changing that source, run
the complete discovered-model rebuild. It provisions disposable compiler
sources from the checked-in board generators in an owned temporary directory;
it never reads or mutates durable `.context` `.blend` files. It refuses
incomplete builder coverage and rejects descriptor geometry/inventory drift
before promotion:

```sh
rtk python3 -B Tools/HangboardModels/rebuild_all_wood_models.py
```

Then run the actual-package material regression. It cleanly reimports every
shipped model USDZ and requires the byte-identical embedded canonical PNG plus
the exact standard-sRGB metadata, positive loaded image dimensions, and image
material bindings on every mesh. Blender reimport/render verifies the Blender
side only; a controlled app-renderer comparison remains required after a
texture or exported-material change because USD color-space tags do not by
themselves establish bridge decoding behavior:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/test_canonical_wood_material.py
```

For albedo calibration, keep camera, lighting, geometry, and material settings
fixed and capture at least two source-albedo samples through the actual app
renderer. Compare matched board pixels, solve the observed response toward a
declared exposed-face target, and validate the chosen source in the app again.
Do not tune from Blender's color-managed review alone.

The retained final actual-app review is
`.context/shaky-rat-warm-white-lighting-review/review-report.md`; its approved
normal-state renders are
`.context/shaky-rat-warm-white-lighting-review/beastmaker-1000-normal-portrait.png`
and
`.context/shaky-rat-warm-white-lighting-review/compact-ii-normal-portrait.png`.
The focused SceneKit key-direction and complete migrated-package model checks
passed on the exact owned Simulator used by that report. This is Simulator
integration evidence, not a claim of physical-device PBR pixel parity:
SceneKit can fall back from physically based shading where Metal is
unavailable.

## Actual-export verifiers

Board-specific verifiers are a second check of the compiler's actual USDZ
bytes. They start with an empty Blender scene, reimport only
`assets/primary.usdz`, verify image materials, explicit triangles, tagged
body/hold bindings, and the generated descriptor's exact hash-bound contents.
They do not open, save, repair, or triangulate an authored `.blend`.

For Beastmaker 1000, run the verifier against an already compiler-produced
directory after the approved source and package compilation have completed:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/verify_beastmaker_1000.py -- \
  --output .context/OWNER-beastmaker-1000/package
```

The Beastmaker report requires its fixed 22-ID logical inventory and zero
hardware meshes, as well as the runtime reimport checks. Its review renders
and `export-verification.json` are evidence beside the compiler output, not
additional files inside the compiler package directory.

The checked Beastmaker source also retains a documented compiler-input
transport copy. A read-only audit verifies all 23 mesh names, roles, hold IDs,
material slots, local vertex hashes, and topology hashes are identical to the
approved editable source; every scene matrix is only the fixed rigid axis
transport. Compile that emitted input for the current generic compiler. A
direct compile of the editable source produces a 580 × 58 × 150 mm axis order
and is rejected by the verifier, whereas the audited transport output is
580 × 150 × 58 mm in `hang-ten-board-v1`. Reconciling the brief's editable
source command with the compiler's Blender-native axis expectation remains a
separate specification decision; do not repair geometry to work around it.

The Compact II verifier similarly accepts only the compiler package layout;
it no longer reads legacy root-level GLB/USDZ files or derives identities from
mesh names:

```sh
rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/verify_wood_grips_compact_ii.py -- \
  --format usdz --skip-renders .context/OWNER-wood-grips-compact-ii/package
```

Compact II's evidence does not establish a whole-board depth. Its verifier
therefore compares the actual imported USDZ to the generated descriptor and
does not assert a 56 mm overall-body dimension. The promoted Compact II
package uses the approved tagged source and actual export. Do not infer tags
from imported names or add them during verification.

Remote GitHub model sync and model editing remain outside this tooling's
demonstrated contract.

The Blender-free report checks are available with:

```sh
rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py
```
