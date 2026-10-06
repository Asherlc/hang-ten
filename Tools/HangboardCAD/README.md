# FreeCAD authoring and runtime export

Each catalog board retains one self-contained native source:
`Hangboards/<slug>.FCStd`. It owns geometry, board metadata, cord authoring, and
optional simulation inputs. The shared compiler generates ignored runtime files
under `Hangboards/<slug>/assets/`: USDZ models, `*.model.json` descriptors,
optional `*.physics.json`, and solved `suspension.json`. Validation and app
staging generate `board.json` from those inputs; it is never committed.

Commit the FCStd and its source evidence. The saved document must stand alone:
there is no board-specific program, Blender board compiler, or intermediate mesh
conversion in the build path. Both apps consume bundled generated packages.

## Build from a fresh checkout

Run from the repository root. On Ubuntu 24.04, install the runtime and
extraction prerequisites for FreeCAD and the full build's Blender hand export:
`libegl1 libgl1 libglu1-mesa libopengl0 libxi6 libxfixes3 libxrender1 libsm6 libxxf86vm1 libxkbcommon0 squashfs-tools xz-utils`.
The FreeCAD installer extracts the pinned AppImage and runs its bundled
`freecadcmd` without a FUSE mount.

```sh
rtk git lfs pull
rtk proxy bash scripts/build-board-assets.sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Before Xcode or a full app build, use
`rtk proxy bash scripts/build-runtime-assets.sh`; it also exports the grip hand
with Blender 5.2.0. Audited plans live in the checked-in canonical
`HangTen/Resources/PlanLibrary.json`. See
[generated artifacts](../../docs/GENERATED_ARTIFACTS.md) for CI production,
caching, staging, and release consumption.

The board producer uses pinned FreeCAD 1.1.3 and OpenUSD 26.8. It builds every
model presentation, solves declared suspension against the native solid, checks
source/model/physics/suspension bindings, and installs complete packages. It
needs no previous export. Its temporary toolchain and scratch resources are
owned by the workspace and cleaned on exit. CI runs eight stable board shards
on Ubuntu 24.04 and assembles one complete catalog for its consumers.

For a selected board, use `--package <slug>`; repeat `--package` for several.
`--jobs <count>` controls independent board workers. `HANGTEN_FREECAD_CMD`
selects the pinned executable and `HANGBOARD_PYTHON` selects host Python.
`HANGTEN_CAD_CACHE_DIR` enables validated reuse when it points to a
workspace-owned directory under `.context`; omit it for a fresh native build.
Every checkout that builds, validates, or stages packages needs the Git LFS
objects. LFS pointers are rejected with a fetch hint.

## Board metadata: board.json is generated at build time

The FCStd document stores these `App::PropertyString` values:

| Property | Authored contents |
| --- | --- |
| `HangTenBoardID` | Board `id` |
| `HangTenBoardManifest` | `board.json` fields minus `id`, as compact JSON |
| `HangTenSuspensionAuthoring` | Optional topology, dimensions, solver settings, evidence, pose rotations/cameras, and `offsetXZ: [x, z]` |
| `HangTenRopePhysics` | Optional native feature selections and simulation inputs |

`aspectRatio` remains an authored presentation value: an instance layout need
not have the aspect ratio of its shared model. Grip depths remain sourced
product facts. Preserve numeric spelling, including the nine-decimal instance
translations required by the package contract.

Host generation lives in
[`hangboard_packages.cad_source`](../HangboardPackages/src/hangboard_packages/cad_source.py)
and requires no FreeCAD. It validates generated suspension against the current
FCStd, authoring inputs, and model descriptors, then merges runtime suspension
into each named presentation or equipment instance. A source declaring
`HangTenSuspensionAuthoring` requires a current `assets/suspension.json` before
package validation or staging. Source/model hashes, settled translations,
`cordContactPoints`, and `wrappedRoutes` belong only in that generated artifact.

An on-disk `Hangboards/<slug>/board.json` is rejected for a CAD-backed package.
Neither the FCStd nor the standalone suspension artifact is staged into an app;
suspension is already present in bundled `board.json`. Only USDZ is an Apple
On-Demand Resource. See
[suspension and ODR](../../docs/3D_SUSPENSION_AND_ODR.md).

### Inspect or edit metadata

Replace `<slug>` and `<owner>` in the examples. Derive `<owner>` from the final
path component of `${PASEO_WORKTREE_PATH:-$PWD}` and keep generated diagnostics
under workspace-owned `.context` paths.

```sh
rtk mkdir -p .context/<owner>/cad-authoring
rtk python3 Tools/HangboardCAD/board_manifest.py --dump --package <slug> \
  > .context/<owner>/cad-authoring/manifest.json
# Edit the scratch manifest, retaining source URLs and field audit mappings.
rtk python3 Tools/HangboardCAD/set_board_manifest.py --package <slug> \
  .context/<owner>/cad-authoring/manifest.json
rtk proxy bash scripts/build-board-assets.sh --package <slug>
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

`set_board_manifest.py` accepts a manifest or a full board-shaped JSON object
whose `id` equals `HangTenBoardID`. It rewrites only `Document.xml` and verifies
that every other archive member is unchanged. A metadata-only edit therefore
uses this editor rather than re-saving through FreeCAD, which can reserialize
shape data. Both routes change the source binding and require rebuilding.

To inspect generated runtime metadata after building:

```sh
rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug>
rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug> \
  --output .context/<owner>/cad-authoring/generated-board.json
```

`--all` generates every CAD board; `--dump` reads the embedded manifest without
requiring runtime artifacts. The command refuses to write the package's own
`board.json`.

Enable readable FCStd diffs once per clone:

```sh
rtk git config diff.hangten-fcstd.textconv "python3 Tools/HangboardCAD/board_manifest.py --dump-file"
```

The diff shows document properties, authored JSON, and a digest for each archive
member. Git LFS pointers resolve through the local LFS object store when present.

### Edit cord and simulation inputs

Dump the chosen property, edit its source-backed inputs, and embed it:

```sh
rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug> \
  --dump-authoring suspension > .context/<owner>/cad-authoring/suspension.json
rtk python3 Tools/HangboardCAD/set_cad_authoring.py --package <slug> \
  --suspension .context/<owner>/cad-authoring/suspension.json
rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug> \
  --dump-authoring rope-physics > .context/<owner>/cad-authoring/rope-physics.json
rtk python3 Tools/HangboardCAD/set_cad_authoring.py --package <slug> \
  --rope-physics .context/<owner>/cad-authoring/rope-physics.json
rtk proxy bash scripts/build-board-assets.sh --package <slug>
```

An absent property dumps as `null`; author a supported JSON object before
embedding it. The editor accepts `--source <path.FCStd>` instead of `--package`,
allows both input files in one mutation, preserves the unselected property,
and supports `--remove-suspension` / `--remove-rope-physics` for evidence-backed
removals. It also changes only `Document.xml` and verifies all other members.

Follow [cord authoring](../../docs/HANGBOARD_CORD_AUTHORING.md) for topology,
channel measurements, native route selection, and validation. Connected internal
mouth pairs use `twoBranchCord` or `threadedLoopCord` with `internalLoop`;
independent visible leads, exterior wraps, or unknown hidden connections use
`cadRoutedCord` with `ropeSolver.method: "nativeRoutes"`. Preserve the evidenced
connection graph. Never invent a hidden join or copy solved routes into CAD.
Schema-2 instance authoring must name the exact equipment IDs, with one
suspension for each instance.

Existing legacy manifest-only suspensions remain in
`captain-fingerfood-pocket`, `j-bryant-ftg-32`, `lattice-mxedge-lift-large`,
`lattice-mxedge-lift-small`, and `metolius-light-rail-2`. Each retains
`pairedLeadCord` in `HangTenBoardManifest` without `HangTenSuspensionAuthoring`.
New or revised cord authoring must use evidence-backed native inputs and
computed routes; these retained manifest routes do not authorize new
hand-authored suspension.

## Source document contract

Required document properties:

| Property | Value |
| --- | --- |
| `HangTenBoardID` / `HangTenBoardManifest` | Identity and embedded metadata as above |
| `HangTenPresentationID` | Default declared model presentation |
| `HangTenSchemaVersion` | Descriptor binding schema `1` or `2` (distinct from board schema `3`) |
| `HangTenSourceKind` | `native-parametric-measured-profile`, or explicitly labeled `faceted-import` |
| `HangTenCoordinateFrame` | `freecad-mm-z-up-front-negative-y` |
| `HangTenTessellationDeflection` | Authored linear tessellation deflection in millimetres |

The archive preflight rejects unsupported object types, executable Python
properties, external document references, missing embedded files, and malformed
archives. Built-in sketches, features, and internal links must form a
self-contained document that reopens and recomputes cleanly.

Every exported object has `NodeID` and `NodeRole` (`body`, `contact`, or
`attachment`). Contacts bind with `ContactID` in schema 1 or `ContactSlotID` in
schema 2. Objects without `NodeID`, including construction sketches and datums,
are not exported. `NodeID` becomes the USD mesh prim name used by the app.
Attachments participate in surface partitioning but are not pickable or
highlightable.

For reusable instances, author one unit and use generic slots mapped through
each instance's `contactIDsBySlotID`. Slot inventories must agree with the
manifest, and every instance of a slot must agree on its declared scalar grip
depth. The descriptor uses `contactSlots` for schema 2.

A schema-1 contact can declare `AdditionalContactIDs` as a nonempty, sorted,
unique `App::PropertyStringList` of other board contacts sharing its surface.
The primary ID remains the picking identity; all memberships highlight the one
exported mesh. Shared contacts derive bounds and depths from their member
meshes and cannot supply an outline.

Optional `HangTenHoldOutline` and `HangTenHoldFloorOutline` string properties
contain ordered `[x, z]` native-millimetre points. They describe deliberately
authored front-plane contact outlines; the compiler normalizes them into the
descriptor. A front outline also supplies `facePlaneAABB` and `center`.

Coordinates convert once from native millimetres (+X right, +Z up, front -Y)
to runtime metres (+X right, +Y up, front +Z):

```text
(x, y, z) -> (x/1000, z/1000, -y/1000)
```

Normals receive the rotation without the scale factor. All generated USDZ
meshes are unbound and ship without materials or textures. The compiler ignores
retained `MaterialName`, `BaseColor`, and other legacy material metadata.

## Surface partition

The body node carries the board surface minus the contact and attachment
regions. Each region normally exports its own native Shape. Its boundary must
match the surface removed from the body. Author live contact surfaces from the
same sketch edges, cutters, or native body faces; a capped pocket tool is not a
contact surface. Split large body faces at contact boundaries rather than
placing a coincident overlay on them. See
[geometry precautions](../../docs/freecad-authoring-lessons.md) for construction
and binding checks.

The default partition assigns a body triangle whose centroid lies on a region.
For curved contact faces, set document `HangTenCurvedRegionPartition`
(`App::PropertyBool`): chord triangles are also assigned when all vertices lie
on the region, the centroid is within the tessellation deflection, and the
normal agrees. This avoids duplicated curved geometry. It is an authored opt-in
that changes the exported partition and requires review.

`HangTenUseBodyTriangles = true` is supported only on a native
`PartDesign::SubShapeBinder` contact. It exports the contact's validated assigned
body triangles to share an exact seam. Native source, face-membership, partition,
and depth checks still apply.

## Surface normals

Default shading clusters incident triangles by crease angle and averages their
normals. Document `HangTenSurfaceNormals` (`App::PropertyBool`) instead uses the
analytic B-rep surface normal at each vertex. This can avoid a shaded band on a
large planar face beside a tangent fillet.

Optional `HangTenUVNodeSurfaceNormals` (`App::PropertyBool`) requires
`HangTenSurfaceNormals`. It uses native face UV nodes for unambiguous tessellated
facets and falls back to the original surface evaluator for missing APIs,
ambiguous ownership/vertices, or internal non-smooth B-spline knots. Exact facet
ownership can select a different analytic face from the legacy centroid
heuristic; review such normal changes against the actual native face. These
options preserve positions, triangle order, and node identities but require
review of the exported appearance.

## Grip depth and model presentations

The compiler derives published scalar grip depths from the manifest. A contact's
`HangTenDepthAxis` selects native `x`, `y`, or `z`; omitted means `y`. By default
it measures the contact's extent along that axis. When a nominal published depth
exceeds the body's extent, the contact must span the full body extent instead.
Reviewed display-depth exceptions are bound to the exact source and labels in
[display_depth_audits.json](display_depth_audits.json); a changed source or label
requires a new audit.

For a stepped lip whose grip depth is not an axis-aligned extent, author both
`HangTenGripDepthStart` and `HangTenGripDepthEnd` as native-millimetre vector
properties. Each witness must lie on the contact surface within 0.25 mm; their
distance is the measured depth. Bind them to live native dimensions when those
can change. An incomplete pair fails compilation. A published depth range is
not a scalar gate: deliberately check its source-backed endpoints.

When a real accessory changes the solid, tag its bound features with
`HangTenPresentationID` and give every model presentation unique asset and
descriptor names. Untagged features belong to the document's default
presentation. `prepare_assets.py` builds every declared model configuration.
Position `effectiveDepths` carries source-backed configured grip depths.

## Authoring a new CAD board

1. Inspect primary manufacturer evidence and record source URLs, field mappings,
   published facts, display estimates, uncertainties, and source conflicts. Use
   the Trango Rock Prodigy Pivot package as the structural precedent. Preserve
   exact left/right mirroring when the real product is symmetric.
2. Author native sketches and features in `Hangboards/<slug>.FCStd`, with the
   document properties and live contact bindings above. A temporary authoring
   script may live under `.context` and run through `run_freecad.py`; the saved
   document must stand alone.
3. Embed the sourced manifest with `set_board_manifest.py` and any reviewed cord
   or simulation inputs with `set_cad_authoring.py`. Keep generated hashes,
   translations, and routes out of authored properties.
4. Build with `scripts/build-board-assets.sh --package <slug>`, run the relevant
   native checks and package validation, then review exported geometry and
   selected contacts in the app.

Follow [AGENTS.md](../../AGENTS.md) and the
[geometry precautions](../../docs/freecad-authoring-lessons.md). Direct native
authoring and human review are required. Measuring an approved display mesh's
cross-section as an ordered boundary loop for a deliberately authored Sketcher
profile is permitted; it is a display approximation with recorded provenance,
not recovered manufacturing geometry. Image-driven geometry inference and
vectorization are prohibited.

## Review and verification

Before a geometry edit, build the unchanged prior committed source and preserve
its exported model in workspace-owned scratch. Record its source revision,
FCStd SHA-256, and export SHA-256. If editing has begun, export that prior source
from an isolated workspace-owned checkout. Rebuilding the edited source cannot
supply the baseline.

`preview.py` needs host `numpy`, `Pillow`, and `usd-core==26.8`. After rebuilding,
render front, side, and top previews of both exports:

```sh
rtk python3 Tools/HangboardCAD/preview.py --package <slug> \
  --reference .context/<owner>/prior/<slug>/primary.usdz \
  --out .context/<owner>/previews
```

For a non-default model, pass its path with `--asset`. The tool writes candidate
and reference PNGs for all three views. Present those images together before
reporting any geometry change complete. Review primary evidence beside them and
check selected-contact highlighting and picking in the app. Use
[isolated iOS validation](../../docs/IOS_SIMULATOR_VALIDATION.md) for app review.
`tests/compare_exports.py` supplies optional sampled distance evidence; its result
is not a product-accuracy measurement or a replacement for visual review.

Use the applicable modules in `Tools/HangboardCAD/tests`, including each board's
native reopen/recompute and edit-propagation checks. The pilot's
`tests/native_source_checks.py` expects its specific sketch-and-pad source and
is not a universal checker. Native integration tests skip when the toolchain is
absent; a skip is not native verification. After building the required assets,
run `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`.

For a focused compiler check with an installed pinned toolchain:

```sh
rtk mkdir -p .context/<owner>/cad-authoring
rtk proxy env TMPDIR=.context/<owner>/cad-authoring \
  python3 Tools/HangboardCAD/run_freecad.py \
  --extra-python-path <directory-containing-pxr> \
  Tools/HangboardCAD/compile_board.py --package <slug> --check
```

The wrapper handles FreeCAD's consumed command-line flags and extra Python
paths. `--check` validates and stages without publishing; `--report <path>`
writes a build report. The compiler reopens/recomputes without changing source
bytes, tessellates, partitions, writes the USDZ, and derives the descriptor from
the exported bytes. Use the shared board producer for complete delivery,
including cord and physics outputs.

### Focused cord reproduction

The shared producer provisions the pinned rope dependencies automatically.
For an isolated `twoBranchCord` or `nativeRoutes` check, the following example
builds the Mini Bar and verifies its generated suspension against the selected
native solid. It uses Python 3.11 or 3.12 and installed FreeCAD 1.1.3. All
temporary diagnostics and the virtualenv are removed on exit:

```sh
rtk proxy bash <<'SH'
set -euo pipefail
rope_owner="${PASEO_WORKTREE_PATH:-$PWD}"
rope_owner="${rope_owner##*/}"
rtk mkdir -p .context
rope_root="$(rtk proxy mktemp -d "$PWD/.context/$rope_owner-cord-check.XXXXXX")"
rtk proxy printf '%s\n' "$rope_root" > "$rope_root/owned-resources"
trap 'rtk proxy rm -rf -- "$rope_root"; rtk proxy test ! -e "$rope_root"' EXIT
rope_python="$rope_root/venv/bin/python"
freecad_command="${HANGTEN_FREECAD_CMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}"

rtk proxy python3 -m venv "$rope_root/venv"
rtk proxy "$rope_python" -m pip install --disable-pip-version-check --only-binary=:all: \
  -r Tools/HangboardCAD/rope_solver_requirements.txt
rtk proxy bash scripts/build-board-assets.sh --package lattice-mini-bar
rtk proxy env TMPDIR="$rope_root" HANGTEN_ROPE_PACKAGE=lattice-mini-bar \
  HANGTEN_ROPE_SOLID_FEATURE=RightCordChannel \
  HANGTEN_ROPE_SOLID_OUTPUT="$rope_root/solid.json" \
  python3 Tools/HangboardCAD/run_freecad.py --freecad "$freecad_command" \
  Tools/HangboardCAD/export_rope_collision_solid.py
rtk proxy "$rope_python" Tools/HangboardCAD/solve_threaded_rope.py \
  --package lattice-mini-bar --solid "$rope_root/solid.json" --check
SH
```

For another board, select its final native collision solid, honoring
`ropeSolver.collisionFeature`. Groove-guided routes also require the retained
`HANGTEN_ROPE_GROOVE_FEATURES` and `HANGTEN_ROPE_BORE_FEATURES` selections during
export. Schema-2 entries select `--presentation` and, for reusable units,
`--equipment-object`. `threadedLoopCord` needs FreeCAD's interpreter for exact
native-solid checks, as used by the pinned producer. See
[cord authoring](../../docs/HANGBOARD_CORD_AUTHORING.md) for the supported
solvers, limitations, and channel measurement commands.

## Lattice Triple Rung profile provenance

The [manufacturer product page](https://latticetraining.com/product/triple-rung-wooden-hangboard/)
is the product source recorded in the embedded manifest: 550 × 130 × 50 mm,
with upper/middle/lower grip depths 45 / 10 / 20 mm. The native profile was
measured as an ordered end-cap boundary of the approved display reference at
revision `6b828e15`. Its 267 measured points became 170 deliberately authored
vertices with a maximum recorded deviation of 0.1899 mm. These are display-mesh
measurements, not manufacturer CAD or manufacturing tolerances. This source note
retains the board's profile provenance, which has no separate provenance sidecar.
