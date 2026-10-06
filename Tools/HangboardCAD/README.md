# FreeCAD authoring — native source and direct USDZ compiler

The pipeline below is implemented and reproducible for native CAD packages.

## What this provides

One self-contained native FreeCAD document per board, kept directly in the
catalog source root:

    Hangboards/<slug>.FCStd

The FCStd is the source of truth for geometry, board metadata, cord topology,
solver settings, evidence, and optional simulation inputs. One shared command
turns it into ignored runtime files under `Hangboards/<slug>/assets/`
(`*.usdz`, `*.model.json`, optional `suspension.json` and `primary.physics.json`).
The package's `board.json` is generated at build time and never committed (see
[Board metadata](#board-metadata-boardjson-is-generated-at-build-time)).
There is no Blender board compiler/importer, intermediate GLB/STEP/OBJ/STL step,
or board-specific Python program in the build path. Commit the FCStd and source
audits. All runtime exports, including solved suspension, remain ignored.

## Build from a fresh checkout

Fetch the retained Git LFS sources, then compile and install every ignored board
asset before package validation.

On Ubuntu 24.04, install the prerequisites for FreeCAD board builds and the
Blender hand export used by the full runtime build below:
`libegl1 libgl1 libglu1-mesa libopengl0 libxi6 libxfixes3 libxrender1 libsm6 libxxf86vm1 libxkbcommon0 squashfs-tools xz-utils`.
The FreeCAD installer extracts the pinned AppImage and runs its bundled
`freecadcmd` without a FUSE mount.

```sh
rtk git lfs pull
rtk proxy bash scripts/build-board-assets.sh
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

The script uses pinned FreeCAD 1.1.3 and OpenUSD 26.8, runs
`prepare_assets.py` in workspace-owned scratch, and installs outputs into the
existing `Hangboards/<slug>/assets/` paths. It builds every declared model
presentation and invokes `compile_suspension.py` with the embedded authoring
inputs to solve native cord routes. It validates current source, model,
physics, and suspension bindings before publishing the complete package. It
never needs a previous USDZ, descriptor, or solved suspension artifact.
For one board, pass `--package <slug>`; repeated `--package` selects several.
`HANGTEN_FREECAD_CMD` can select the pinned executable and `HANGBOARD_PYTHON`
selects the host Python.

Before Xcode or a full fresh-checkout app build, use
`rtk proxy bash scripts/build-runtime-assets.sh`. It also exports the grip hand
mesh with Blender 5.2.0. Audited plans live in the checked-in canonical
`HangTen/Resources/PlanLibrary.json`. CI's
`.github/workflows/runtime-assets.yml` runs eight stable board shards on
Ubuntu 24.04, with up to eight Linux runners and two independent native processes
per runner. One Linux job assembles the complete catalog and exports the hand
once. Validation and app-build jobs download that catalog before staging.
Automatic releases
reuse the immutable catalog available to the successful main CI attempt;
manual releases invoke the same compiler workflow. Failed-job retries retain
successful shards, and test-only retries retain their catalog producer.
Release selection groups copied job records by execution times and runner to
identify the original producer attempt; it rejects missing or expired catalogs.
See [generated artifacts](../../docs/GENERATED_ARTIFACTS.md).

CI caches each board's complete runtime set against the current FCStd, compiler
inputs, pinned toolchain, and platform. Every hit checks the current presentation
inventory, source/model/physics/suspension bindings, and all output hashes.
Changed or damaged entries rebuild through the native compiler. A complete
cache hit skips FreeCAD download and native dependency installation. Local
builds can opt in with `HANGTEN_CAD_CACHE_DIR` pointing to a workspace-owned
directory under `.context`; omit it for a fresh native build. `--jobs <count>`
sets the number of independent board workers.

## Board metadata: board.json is generated at build time

For a CAD-backed package, `Hangboards/<slug>/board.json` is **not in the
repository**. Host package generation reads the adjacent flat
`Hangboards/<slug>.FCStd` and merges validated generated
`Hangboards/<slug>/assets/suspension.json` into the named model presentations
or equipment instances. An artifact is required when the source declares
`HangTenSuspensionAuthoring`. Source/model hashes and the retained authoring
payload bind the artifact to the current CAD document; missing artifacts, stale hashes, or
changed authoring inputs fail before validation/staging. Neither the FCStd nor
the standalone suspension artifact is staged into the app: its runtime
suspension is already in bundled `board.json`.

The document-level `App::PropertyString` `HangTenSuspensionAuthoring` retains
only authored topology, dimensions, solver settings, evidence, pose rotations
and cameras, and optional horizontal `offsetXZ: [x, z]` (default `[0, 0]`).
It contains no model/source hashes, settled Y translations, `cordContactPoints`,
or `wrappedRoutes`. `compile_suspension.py` reads those inputs, derives the
native collision solid and current model bindings, and solves every canonical
pose with the retained native solvers. The generated artifact supplies runtime
`translation` values and solved routes, as well as `sourceSHA256` and model
hashes. Edit the CAD inputs and rebuild; do not copy solved values into CAD.
The optional `App::PropertyString` `HangTenRopePhysics` retains the native
body/channel feature selections and simulation/topology inputs used to generate
`primary.physics.json`, including the Clavellium live-physics configuration.
Captain Fingerfood POCKET retains its existing suspension in
`HangTenBoardManifest` as an intentional legacy exception, unchanged by source
consolidation. A separate evidence-backed cord revision must use the native
solver contract; this exception does not authorize new hand-authored routes.

Authoring schema 2 may declare `instanceSuspensions`, keyed by the exact
equipment instance IDs in the native manifest. This supports independently
placed copies of one asset; every instance must have a suspension. The generated
artifact adds the hash of the shared asset. Rock Rings use this form with
`threadedLoopCord`:
one branch, two mouths, and an ordered native channel centerline in
`internalLoop.channelPointsByBranchID`. Its hidden length is measured from the
linked `ContinuousCordSpine` of the channel's `Part::MultiFuse`. Run its rope
solve using FreeCAD's Python interpreter for exact solid clearance, including
inside-solid rejection. Unobstructed rising legs are solved from the total loop
length; a collision rejects the route instead of adding manual contacts.

For a schema-2 Rock Ring measurement, select the instance explicitly:

```sh
rtk proxy env HANGTEN_CHANNEL_PACKAGE=metolius-rock-rings-3d \
HANGTEN_CHANNEL_EQUIPMENT_OBJECT_ID=left-ring \
HANGTEN_CHANNEL_FEATURES_JSON='{"left-ring-loop":"ContinuousCordChannel"}' \
HANGTEN_CHANNEL_VERIFY=1 \
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
  Tools/HangboardCAD/measure_channel_spines.py
```

For the other copy, use `right-ring` and `right-ring-loop`. An omitted or
unknown equipment ID fails with the available IDs before measurement.

* the package validator (`hangboard_packages.board_catalog`, used by
  `scripts/hangboard-packages.sh validate` and every package test) validates the
  exact generated bytes, with the same schema and closed-key checks as a
  hand-authored `board.json`;
* `scripts/stage-board-packages.py` writes it into each staged package, for the
  iOS bundle (the Xcode "Stage Board Packages" phase) and for the Android assets
  (the `scripts/stage-board-packages.py --target android` entrypoint); the FCStd itself
  is never staged into either app.

Generation is pure host Python (`hangboard_packages.cad_source`, stdlib only; no
FreeCAD), so it runs in every build and in CI. The scripts here import it
directly; `use_hangboard_packages.py` is the one place that puts
`Tools/HangboardPackages/src` on `sys.path` for them, because they run as plain
scripts under host `python3` and under FreeCAD's `freecadcmd` (which does not
inherit `PYTHONPATH`). `contract.py` holds only the compiler's node role-binding
check; the archive preflight is `cad_source.inspect_archive`. An on-disk `board.json` inside a
CAD-backed package is a validation error (it would be a stale hand edit), and
`.gitignore` covers native packages' `board.json` and generated asset paths.
The schema still supports non-CAD raster packages with hand-authored
`board.json`; the current catalog retains native sources. Because the FCStd is Git LFS,
every checkout that builds or validates packages needs the LFS objects
(`git lfs pull`, or `lfs: true` in CI); an LFS pointer fails generation with a
fetch hint.

Board metadata lives in two document-level string properties of the FCStd:

* `HangTenBoardID` — the board `id`;
* `HangTenBoardManifest` — `board.json` minus `id`, as compact single-line JSON
  in the order `board.json` is emitted, with every number spelled as authored
  (the package validator reads some number lexemes, such as nine-decimal
  instance translations).

Only `id` is derived. `aspectRatio` stays a stored manifest value: it is a
presentation (viewport) fact, not always the single-unit front ratio. Of the
seven CAD boards covered by the aspect-ratio audit, five match the descriptor
`modelBounds` x/y ratio to within
2e-8 relative (float32 export noise against exact ratios such as 5/3 and 12/7),
`metolius-wood-grips-compact-ii` keeps its pre-migration raster value `3.88`
(0.14% from its 610 × 157 mm face), and `metolius-rock-rings-3d` presents two
ring instances while its descriptor bounds cover one ring, so a derived value
would be wrong there. These are the findings of the initial seven-board
aspect-ratio audit.
The eighth CAD board, `soill-iron-palm-2`, was added after that audit and is
not covered by it: its model presentation `aspectRatio` equals its bounds ratio
(`2.3226565483816386`), while its top-level value is `1.5`.
Published grip depths stay because they are sourced product facts (see `AGENTS.md`,
Training-plan Fidelity) that `compile_board.py` validates the geometry against.
The reviewed Beastmaker 1000 metadata correction deliberately preserved its
existing display geometry. Those exact source and contact exceptions are
hash-bound in [display_depth_audits.json](display_depth_audits.json), with the
retained source audit linked there. Source consolidation preserves its exported
geometry and does not turn display extents into product measurements.
Schema-v2 boards (slots, instances, `contactIDsBySlotID`) are carried the same
way, which is why the manifest is one JSON document rather than per-object
properties. Optional cord/simulation inputs live separately in the document's
`HangTenSuspensionAuthoring` and `HangTenRopePhysics` string properties.

`board_manifest.py` is the command line for the same generator (host Python):

    rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug>                   # board.json to stdout
    rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug> --output <path>   # ... to a scratch file
    rtk python3 Tools/HangboardCAD/board_manifest.py --all                              # generate every CAD board
    rtk python3 Tools/HangboardCAD/board_manifest.py --dump --package <slug>            # print the manifest

It refuses to write into the package's own `board.json`.

To change a CAD board's metadata, edit the manifest and embed it (host Python;
source URLs and audit mappings for any changed field are still required, per
`AGENTS.md`), then validate:

    rtk python3 Tools/HangboardCAD/board_manifest.py --dump --package <slug> > .context/<owner>-manifest.json
    # Edit .context/<owner>-manifest.json, retaining source mappings.
    rtk python3 Tools/HangboardCAD/set_board_manifest.py --package <slug> .context/<owner>-manifest.json
    rtk proxy bash scripts/build-board-assets.sh --package <slug>
    rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory

`set_board_manifest.py` rewrites only `Document.xml` inside the archive (it
inserts or replaces the property exactly as FreeCAD writes it) and verifies that
every other member — shapes, element maps, textures — is byte-identical, so a
metadata edit can never perturb the compiled geometry. It deliberately does not
re-save through FreeCAD: a FreeCAD save re-serializes every shape with last-ulp
differences. Editing the property in the FreeCAD GUI is also valid, but then
treat it like any geometry edit (recompile and validate the package). After
either route, commit the changed FCStd; there is no committed `board.json` for
a CAD-backed package.

To inspect and change cord/simulation authoring, dump the chosen property to
workspace scratch, edit the authored inputs with their evidence mappings, and
embed it without re-saving through FreeCAD:

```sh
rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug> \
  --dump-authoring suspension > .context/<owner>-suspension-authoring.json
rtk python3 Tools/HangboardCAD/set_cad_authoring.py --package <slug> \
  --suspension .context/<owner>-suspension-authoring.json
rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug> \
  --dump-authoring rope-physics > .context/<owner>-rope-physics-authoring.json
rtk python3 Tools/HangboardCAD/set_cad_authoring.py --package <slug> \
  --rope-physics .context/<owner>-rope-physics-authoring.json
rtk proxy bash scripts/build-board-assets.sh --package <slug>
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

An absent property dumps as `null`; author a supported JSON object before
embedding it. The editor accepts `--source <path.FCStd>` instead of `--package`,
allows both inputs in one mutation, and preserves the property not selected.
Use `--remove-suspension` or `--remove-rope-physics` for an evidence-backed
removal. Like the manifest editor, it changes only `Document.xml` and verifies
that every other archive member is unchanged. Duplicate, incorrectly typed,
oversized, or malformed authoring properties fail closed. Both editors
invalidate generated source bindings, so always rebuild before validation.

Readable diffs: `.gitattributes` routes `Hangboards/*.FCStd` through the
`hangten-fcstd` diff driver. Enable it once per clone:

    rtk git config diff.hangten-fcstd.textconv "python3 Tools/HangboardCAD/board_manifest.py --dump-file"

`git diff`/`git log -p` then show the HangTen document properties, the
pretty-printed manifest, and one digest line per archive member (so geometry
changes show up as changed `*.brp` digests). The driver resolves Git LFS
pointers from the local LFS object store; without it, the diff shows the LFS
pointer as before.

The one-off migration that moved each committed `board.json` into its FCStd
was applied in commit 3e1653b and then deleted: it cannot run at a later HEAD
because the hand-authored `board.json` files it read are gone. Read it with
`git show 3e1653b:Tools/HangboardCAD/migration/embed_board_manifest.py`. It
required every regenerated `board.json` to be token-identical to the
hand-authored one (only whitespace and string escaping changed, for three
packages). The last committed CAD `board.json` files are byte-identical to what
the build now generates.

## Authoring a new CAD board

There is no per-board authoring program in the repository. Retired migration,
conversion, and archived execution scripts are preserved in Git history;
commit `769817bcc` retains the code that preceded the source-only cleanup.
Their dated source audits remain evidence. The saved FCStd must stand alone
and must not depend on recreating it with an old authoring script.

1. Create the FCStd. Drawing it in the FreeCAD GUI or writing a throwaway script
   under `.context/` (run with `run_freecad.py`) are both fine; the script is
   not committed and the saved document must stand alone. Set the document
   properties and per-object bindings in
   [Source document contract](#source-document-contract).
2. Write the board metadata as a manifest (`board.json` fields minus `id`, or a
   full `board.json`-shaped object whose `id` equals `HangTenBoardID`), with
   source URLs and audit mappings for every field per `AGENTS.md`. Embed it
   (do not create `Hangboards/<slug>/board.json`):

       rtk python3 Tools/HangboardCAD/set_board_manifest.py --package <slug> <manifest.json>

3. Compile with `scripts/build-board-assets.sh --package <slug>`, then run the
   native source checks and package validator. Review front/side/top exports
   alongside the prior source's export for any geometry change.
4. Record the provenance of every authored number (published versus measured,
   tolerances, reference SHAs, source URLs) in a dated provenance record.

For a newly authored or revised cord setup, embed its reviewed authoring inputs
with `set_cad_authoring.py` before compilation. From then on the build generates
runtime assets from the FCStd, and host validation/staging generates
`board.json` from its manifest and validated suspension artifact.

Choose each corded board's solver from its evidenced topology (see
[`docs/HANGBOARD_CORD_AUTHORING.md`](../../docs/HANGBOARD_CORD_AUTHORING.md)).
Connected internal mouth pairs use the channel method below; independent leads,
exterior wraps, and unknown hidden connections use `cadRoutedCord` with
`ropeSolver.method: "nativeRoutes"`. Do not add a hidden join to fit a solver.
For a cord routed through connected `PartDesign::SubtractivePipe` channels,
measure the hidden length from each pipe's Sketcher spine between the two
declared mouth points; a straight `Part::Cylinder` through-bore is measured
along its axis. The result is channel geometry, not a cord mesh. For
the Mini Bar, run:

```sh
rtk proxy env HANGTEN_CHANNEL_PACKAGE=lattice-mini-bar \
HANGTEN_CHANNEL_FEATURES_JSON='{"left-loop":"LeftCordChannel","right-loop":"RightCordChannel"}' \
  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
  Tools/HangboardCAD/measure_channel_spines.py
```

Record the measured length in embedded `HangTenSuspensionAuthoring` under
`internalLoop.channelLengthByBranchID`, using `set_cad_authoring.py`. Run the
same command with `HANGTEN_CHANNEL_VERIFY=1` after editing the property to check
that the declared lengths still match the CAD spines.
For a physics probe, add
`HANGTEN_CHANNEL_SAMPLES_OUTPUT=.context/<workspace-owner>/channel-paths.json`
to export both spine centerlines in model coordinates. The output paths run
from the first to second declared mouth, including both endpoints; they are
derived from CAD and must not be copied into the USDZ.

### Focused cord reproduction

For a bar-shaped board with two connected cord channels, the shared producer
solves visible settled routes from the native wood solid and writes only the
ignored `assets/suspension.json`. Authored inputs remain the mouths, connected
channel lengths, winding, overhead anchor, loop length, pose rotations/cameras,
and horizontal offsets. The build provisions pinned
`rope_solver_requirements.txt` dependencies in temporary scratch and removes
that environment on exit. For focused reproduction, create a retained
workspace-owned virtualenv explicitly. Run these commands from the repository
root with Python 3.11 or 3.12 and an installed FreeCAD 1.1.3 executable;
set `HANGTEN_FREECAD_CMD` if FreeCAD is installed elsewhere:

```sh
rope_owner="${PASEO_WORKTREE_PATH:-$PWD}"
rope_owner="${rope_owner##*/}"
rope_root=".context/$rope_owner/cord-reproduction"
rope_python="$rope_root/rope-venv/bin/python"
freecad_command="${HANGTEN_FREECAD_CMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}"

rtk proxy python3 -m venv "$rope_root/rope-venv"
rtk proxy "$rope_python" -m pip install --disable-pip-version-check --only-binary=:all: \
  -r Tools/HangboardCAD/rope_solver_requirements.txt

rtk proxy bash scripts/build-board-assets.sh --package lattice-mini-bar
rtk proxy env TMPDIR="$rope_root" HANGTEN_ROPE_PACKAGE=lattice-mini-bar \
  HANGTEN_ROPE_SOLID_FEATURE=RightCordChannel \
  HANGTEN_ROPE_SOLID_OUTPUT="$rope_root/lattice-mini-bar-solid.json" \
  python3 Tools/HangboardCAD/run_freecad.py --freecad "$freecad_command" \
  Tools/HangboardCAD/export_rope_collision_solid.py

rtk proxy "$rope_python" \
  Tools/HangboardCAD/solve_threaded_rope.py \
  --package lattice-mini-bar \
  --solid "$rope_root/lattice-mini-bar-solid.json" --check \
  --report "$rope_root/lattice-mini-bar-check.json"
```

For another board, export its selected final native solid, including any
explicit `ropeSolver.collisionFeature`, and pass that board's slug and collider
path. Groove-guided routes also require the retained native groove and bore
feature selections in `HANGTEN_ROPE_GROOVE_FEATURES` and
`HANGTEN_ROPE_BORE_FEATURES` during export. Schema-2 entries require
`--presentation` and, for a reusable-unit entry, `--equipment-object`.
The host virtualenv example supports `twoBranchCord` and `nativeRoutes`;
`threadedLoopCord` requires FreeCAD's interpreter for exact native-solid checks,
as used by the pinned producer.

The solver finds a shortest route in each declared winding direction on a
CAD section offset by the rope radius, moves the board under the fixed anchor
until the longest loop reaches its declared length, and checks the full visible
centerline against the watertight CAD solid every 0.5 mm. It fails on a
missing route, wood penetration, or more than 0.5 mm slack in either loop.
This is a static taut-rope model for approximately extruded bars; it does not
simulate swing, friction, elasticity, or arbitrary travel along the bar.
Review the generated poses next to manufacturer photos before delivery.

## Running it

The pinned toolchain is FreeCAD 1.1.3 (OCCT 7.8.1, Python 3.11.14) with OpenUSD
26.8 supplied to FreeCAD's interpreter out of band. The shared build script
handles this and the launcher's consumed command-line options. For a focused
compiler check, use the retained wrapper:

    rtk python3 Tools/HangboardCAD/run_freecad.py \
      --extra-python-path <directory-containing-pxr> \
      Tools/HangboardCAD/compile_board.py --package lattice-triple-rung --check

Add `--check` to validate and stage without publishing, and `--report <path>` to
write the JSON build report. The command reads the board metadata from the
source's `HangTenBoardManifest` (`--board <path>` overrides it with an explicit
file; a source without a manifest is an error),
validates it and the source archive, reopens and recomputes the document without
modifying its bytes,
extracts the bound components, tessellates at the document's pinned deflection,
partitions the board surface, writes the USDZ directly, reopens the exported
bytes, derives the descriptor from those bytes, and installs the ignored outputs. It never
writes `board.json`.

**Without the pinned toolchain.** A USDZ compiled with another OCCT version may
not reproduce the approved export bytes. Use the pinned toolchain before
staging or reviewing a changed export. `prepare_assets.py` rebuilds from the
source, derives a new descriptor, checks source immutability and the authored
generated suspension source/model bindings, and fails if those boundaries
disagree. Review source changes
and their generated USDZ/descriptor together; commit only authoring inputs and
evidence.

## Source document contract

Document properties: `HangTenBoardID`, `HangTenBoardManifest`, optional
`HangTenSuspensionAuthoring` and `HangTenRopePhysics` (all document-level
`App::PropertyString`; see above),
`HangTenPresentationID`, `HangTenSchemaVersion` (1 or 2), `HangTenSourceKind`,
`HangTenCoordinateFrame` (`freecad-mm-z-up-front-negative-y`), and
`HangTenTessellationDeflection`.

Every exported object carries `NodeID`, `NodeRole` (`body`, `contact`,
`attachment`), and `ContactID` (or `ContactSlotID`). `MaterialName`,
`BaseColor`, `Roughness`, `Metallic`, and `TextureFile` are optional
compile-time metadata (see **Material policy** below).
Optionally, `HangTenCurvedRegionPartition` (`App::PropertyBool`) opts a
document into the curved-region partition described below; documents without it
compile exactly as before. Objects
without `NodeID` — sketches, datums, construction features — are never exported.
The `NodeID` becomes the USD mesh prim name, which is what the application binds
against.

For a contact that declares `HangTenGripDepthMm`, optional string property
`HangTenDepthAxis` selects the native measurement axis (`x`, `y`, or `z`).
Omitting it retains the original Y-axis behavior. The compiler validates the
declared depth against that axis's exported contact bounds.

A schema-v1 contact mesh may also declare `AdditionalContactIDs` as a nonempty,
sorted, unique `App::PropertyStringList` of other logical contacts that use that
same physical surface. The primary `ContactID` remains the picking identity;
the descriptor includes the mesh in every declared contact's `nodeIDs`, and the
app highlights it when any membership is selected. The surface is exported once.
Secondary IDs must belong to the board and must not repeat the primary ID.
Shared contacts derive their bounds from all member meshes and cannot supply an
outline. Their published depth is measured across those members using the
primary contact object's axis or witness pair; unrelated contacts retain their
individual depth checks. For example, The NUG's upper jug surface also belongs
to its 60 mm pinch, measured between the upper and lower surfaces along native Z.

Coordinate conversion is applied exactly once: native millimetres
(+X right, +Z up, front -Y) to runtime metres (+X right, +Y up, front +Z) as
`(x, y, z) -> (x/1000, z/1000, -y/1000)`.

**Material policy.** Generated USDZ models ship without materials or textures.
The compiler produces unbound meshes — objects without `MaterialName` are
exported without material bindings. The FreeCAD source may still carry
`MaterialName`, `BaseColor`, etc. as compile-time metadata, but those
properties are not required and do not affect the shipped appearance.

## Surface partition

The approved runtime contract partitions the board surface: the body node holds
the surface *minus* the contact regions, and each contact node holds its region.
The compiler assigns every tessellated body triangle to exactly one node using
the contact regions built from the source document's own sketch edges, so the
result has no duplicated coplanar geometry and no z-fighting. A body triangle
is assigned by its centroid lying on the region surface. That rule cannot see a
chord triangle of a *curved* face (arc, B-spline), whose centroid sits up to the
deflection inside the surface, so the body would keep a duplicate of every
curved hold. With `HangTenCurvedRegionPartition` set, such a triangle is also
assigned when all three vertices lie on the region, the centroid is within the
deflection, and its normal agrees with the surface normal (so an end-cap
triangle touching the region's boundary edge is never claimed). It is opt-in
because it changes existing output, and older sources must keep reproducing
their approved export bytes until they are deliberately rebuilt. `metolius-prime-rib`
and the vector `metolius-rock-rings-3d` source opt in. Verified on the
pilot: 390 body triangles plus 122 / 82 / 82 contact triangles, with each contact
region matching the approved reference to 0.0000 mm in both directions.

`metolius-wood-grips-deluxe-ii` also sets `HangTenCurvedRegionPartition`: its
holds are sketched capsules pocketed into the body, so their walls are true
cylinders and their mouth and floor chamfers are cones.

`beastmaker-1000` sets it too: its top holds are ruled lofts between Bézier
sections, and its cavities are ruled capsule lofts (planes, cylinders, and
cones) cut from the body. See
`docs/2026-09-25-beastmaker-1000-cad-provenance.md`.

`target10a-linebreaker-base` sets it as well: its cavity walls are cylinders,
its chamfers are cones, and its rim rounds are cylinders. See
`docs/2026-09-25-target10a-linebreaker-base-cad-provenance.md`.

`beastmaker-2000` sets it as well: its front-top rounds are cylinders and its
cavity chamfers are cones. See
`docs/2026-09-25-beastmaker-2000-cad-provenance.md`.

`trango-rock-prodigy-pivot` sets it too. Its wing is a smooth loft, and its
sloped crimps and two-finger pocket are ruled lofts. It is also the first
source re-authored from manufacturer evidence rather than from the
pre-migration mesh: the front view comes from Trango's top-down photograph
(bolt-seat scale) and every depth from Trango's depth guide. See
`docs/2026-09-25-trango-rock-prodigy-pivot-cad-provenance.md`.
The initial authoring diagnostics are historical evidence; their scripts are
retired. Current review uses native front/side/top previews alongside primary
manufacturer evidence.

`trango-rock-prodigy-natural` follows the same manufacturer-photo approach.
Its two halves are exact mirrors, with rounded rail and pocket mouths, sloped
rail floors, and a side-profiled jug. The 14 contact node IDs are retained; the
two prior body nodes and bottom-edge body patches are consolidated into one
body node. See
[`docs/2026-09-29-trango-rock-prodigy-natural-cad-provenance.md`](../../docs/2026-09-29-trango-rock-prodigy-natural-cad-provenance.md)
for the photo hashes, display estimates, and the unresolved front-tier step.

`tension-grindstone` sets it too: its top slots have stadium ends. It is the
first CAD board with no prior 3D asset (it was raster-only), so there is no
reference mesh. See
`docs/2026-09-26-tension-grindstone-cad-provenance.md`.

`metolius-light-rail-2` sets it too: its jugs include cylindrical round-overs,
its cord wells are cones and cylinders, and its pocket corners are ruled
B-spline walls. See
`docs/2026-09-26-metolius-light-rail-2-cad-provenance.md`.

`moon-armstrong` sets it too: every hold mouth, tile, rail and bar edge is a
ruled loft of rounded-rectangle sections (cones and planes). Its contact
regions are copies of the compiled body's own faces, selected by lying on each
cutter or rail surface, so the partition is exact. Like the Pivot, it was
re-authored from manufacturer photos rather than traced from its reference. See
`docs/2026-09-26-moon-armstrong-cad-provenance.md`.

`nature-stoak-board-iii` sets it too: its pocket and slot ends are cylinders
and every hold mouth has a 2 mm round-over. Its gradient edge is a channel whose
back wall slants from 10 mm deep at the board end to 25 mm inboard. The compiler
gates only scalar depths, so the authoring script checked the range ends. See
`docs/2026-09-27-nature-stoak-board-iii-cad-provenance.md`.

`dewoodstok-woodbord` sets it too: its 16 pockets are stadiums whose 3 mm
mouth round-overs are ruled lofts through quarter-round stations (planes and
cones), which keeps the asset at 32k triangles instead of the 147k a toroidal
`Part::Fillet` produced. It was re-authored from deWoodstok's straight-on
media-kit photo. See
`docs/2026-09-27-dewoodstok-woodbord-cad-provenance.md`.

`the-hangboard` sets it too: its full-round jug tops, sloper crest and profile
corners are cylinders, and each of its 12 edge segments has a 3 mm mouth
round-over built as a ruled loft through quarter-round stations (planes and
cones). Each segment is its own cutter, so the faces split where one edge depth
steps to the next. It was re-authored from The Hangboard's straight-on product
photo and end-profile render. See
`docs/2026-09-27-the-hangboard-cad-provenance.md`.

`frictitious-megalith` sets the same analytic-normal option. Its round-overs are
cylinders, and each of its 14 edge segments and 2 pocket spans is its own
section cutter. It was re-authored from Frictitious's front and end-grain
photographs. See
`docs/2026-09-28-frictitious-megalith-cad-provenance.md`.

`crimptonite-helium-mobile` sets both options too: its ends and round-overs
are cylinders and tori, and its cavity mouths are ruled stadium chamfers
(planes and cones). Each cavity is a shallow mouth at the lower-lip depth with
a deeper slot sharing its top wall at the upper-lip depth, so both published
lips of a cavity are exact. Each cord hole is a `Part::Cylinder` through-bore
(`LeftCordChannel`, `RightCordChannel`) whose axis is the measured channel
spine; one loop of cord runs through both, and its routes are solved with
`ropeSolver.sectionPlane: "anchor"` (see
[`docs/HANGBOARD_CORD_AUTHORING.md`](../../docs/HANGBOARD_CORD_AUTHORING.md)).
It was re-authored from Crimptonite's product photographs; its provenance is
in the source history and board audit records.

The Metolius Foundry is a native measured-profile source with a deliberately
drawn, exactly symmetric front boundary and continuous side/top depth profiles.
Ordered sections from the superseded display asset were only a qualitative
station guide for the operator-authored macro profile; Metolius's front and
depth images govern the topology and correct the reference's center-crown
conflict. Its fully constrained Sketcher profiles feed native lofts, booleans
and live semantic binders. The 578 x 216 mm published envelope, numbered hold
inventory, and published 15 / 16 / 21 / 22 / 23 / 30 / 32 / 53 mm grip
dimensions are frozen in the source manifest and semantic regions. Unpublished
shell relief, aperture sizes, and jug/pinch display depths remain documented
estimates. See
[`docs/2026-09-28-metolius-foundry-cad-provenance.md`](../../docs/2026-09-28-metolius-foundry-cad-provenance.md).

## Surface normals

By default the compiler clusters each vertex's incident triangles by crease
angle and averages their normals. Where a large planar triangle meets the many
small triangles of a tangent fillet, that average tilts, and the flat face
shades a visible band. A document that sets `HangTenSurfaceNormals`
(`App::PropertyBool`) instead shades each triangle with the analytic normal of
the B-rep face it tessellates: the triangle's face is the one whose surface
holds its centroid (within the deflection, inside the face domain), vertices
are split per face, and each carries that face's normal at its position. A face
then shades smoothly, a tangent seam is continuous, and every edge that is not
tangent stays crisp. The sign follows the triangle winding. It is opt-in so
existing sources keep reproducing their approved export bytes. `metolius-light-rail-2`,
`moon-armstrong`, `nature-stoak-board-iii`, `dewoodstok-woodbord`,
`the-hangboard`, `metolius-climbers-edge`, `frictitious-megalith` and
`metolius-foundry` set it.

`HangTenUVNodeSurfaceNormals` is a separate optional `App::PropertyBool`,
defaulting to false and requiring `HangTenSurfaceNormals` to be true. It speeds
up analytic normal evaluation by using cached native face UV nodes only when
an exported triangle exactly matches a tessellated facet of one unique face
and every vertex has one UV evaluation within 0.00002 mm. UV-node order is
not assumed to match tessellation vertex order. Missing APIs, ambiguous owners,
unmatched/ambiguous UV vertices, or vertices at internal non-smooth B-spline
knots retain the original surface-inverse
evaluator. Winding still determines normal sign; positions, triangle order,
node identity, material policy and pinned tessellation settings are unchanged.
For an unambiguous native facet, its exact owning face takes precedence over
centroid-distance ownership. Near adjacent surfaces, the legacy heuristic can
select a different face even though the facet belongs uniquely to the first;
opt-in normals can therefore differ from legacy normals in that case. Validate
such differences against the actual owner's analytic normal and exact facet
identity, rather than treating legacy agreement as the sole correctness test.
The internal non-smooth-knot fallback remains necessary when derivative side
is ambiguous on the same face. Sources without this flag use the original code
path and retain their bytes.

## Published depth deeper than the board

The published-depth gate compares a region's extent on its selected native
axis with its published grip depth. `HangTenDepthAxis` selects X, Y, or Z;
omitting it retains the original Y-axis behavior. A region cannot be deeper
than the body on that axis, so when a published depth exceeds the body's
extent there (a nominal label, such as the Light Rail's "40 mm" jugs across a
38 mm rail), the region must instead span the body's full extent on that axis.
Every other region still has to match its published depth.

## Pilot: lattice-triple-rung

`Hangboards/lattice-triple-rung.FCStd` is a native PartDesign body: one fully
constrained 170-vertex Sketcher profile and a symmetric 550 mm pad. The three
grip regions are `PartDesign::SubShapeBinder` runs of the profile's own sketch
edges, extruded with a length expression on the pad.

Provenance of the authored numbers. There is deliberately no per-board
provenance sidecar; these facts live here instead.

* Published facts come from the board manifest (the build-time `board.json`): overall
  550 x 130 x 50 mm and grip depths 45 / 20 / 10 mm. Cross-reference those (and
  product identity) against manufacturer / product pages before treating them as
  settled; web search is a required check, not a geometry source — see
  `docs/freecad-authoring-migration.md` procedure step 3.
* The cross-section is **measured** from the approved reference asset at the
  pre-migration commit, as an ordered end-cap boundary loop. It is a measured
  approximation of a display mesh, **not recovered manufacturing geometry**.
* The 267 measured points were reduced to 170 authored vertices, with a maximum
  deviation of 0.1899 mm. The reduction criterion and tolerance from the retired
  authoring script are preserved in
  the corresponding authoring notes.
* The initial migration's reference came from commit `6b828e15`, not from a
  live runtime path. Its historical resolver and authoring code remain in Git
  history; they are not current build inputs.

## Vector profile: metolius-prime-rib

`Hangboards/metolius-prime-rib.FCStd` is the first source
whose profile is authored from vector primitives rather than measured vertices:
one fully constrained Sketcher profile of 11 lines, 12 tangent arcs and two
cubic Bezier spans (Sketcher B-splines with dimensioned poles), a symmetric
508 mm pad, and a 1.2 mm `PartDesign::Fillet` round-over on both end
perimeters. Every joint is tangent (G1), and the profile carries named driving
dimensions (`BoardThickness` 38.1, `BoardHeight` 106.68, `Edge15Depth` 15,
`Edge23Depth` 23, ledge/slot heights, and one named radius per arc).

* Published facts: 20 x 4.2 x 1.5 in and edge depths 38 / 23 / 15 mm, from the
  manufacturer page and the board manifest. The 38 mm edge is the full 1.5 in
  (38.1 mm) thickness.
* The primitives were recovered from the pre-migration reference's end-cap
  loop, which is exactly lines, arcs and two Beziers with round-number values;
  the retired authoring script re-measured the reference and refused to save if
  any of its 291 profile vertices was more than 0.01 mm from the sketch
  (achieved 0.00006 mm). No polyline is used.
* The source sets `HangTenCurvedRegionPartition` (see the partition section
  above), as does `metolius-wood-grips-deluxe-ii`.
* Contacts are sketch-edge runs extruded over the prismatic span
  (`Pad.Length - 2 * EndRoundover.Radius`); a concave slot fillet in a run is
  reversed with `Part::Reverse` and combined with `Part::Compound`, so every
  hold face points out of the board.
* Provenance, field mappings, and the retired authoring script's recovery
  commit: `docs/2026-09-24-metolius-prime-rib-cad-provenance.md`.

## Historical pilot app verification

The initial pilot review below predates the current unbound material policy.
It records that migration's evidence. Use
[isolated Simulator validation](../../docs/IOS_SIMULATOR_VALIDATION.md) for
current-source reviews.

Built for the iOS simulator (Debug, `iPhone 17 Pro`) and launched through the
repository's board-detail review route
(`HANGTEN_REVIEW_BOARD_ID=lattice-triple-rung`, `HANGTEN_REVIEW_BOARD_DETAIL=1`).
The app loads the migrated USDZ and descriptor, renders the board with its wood
texture, and selects and highlights the `45 mm upper edge` contact, so the
descriptor's node IDs resolve to the exported meshes and the contact hit-testing
works. The reference asset was staged by a second build and captured the same
way, so that comparison is a real staged A/B rather than a swapped file (the
illustrative images live in the build session's scratch, not in this repository).

The migrated asset renders a smoother surface than the reference, which shows
banding and shading artifacts. Those artifacts are the residue of the earlier
mounting-bore removal: the reference still carries six flat circular cap patches
at exactly the positions recorded in
``docs/2026-09-22-mounting-bore-repairs.json`` (x = +/-75 mm and
+/-225 mm at y = 14 mm, and x = +/-225 mm at y = 96 mm). They are essentially
flush with the surrounding surface - the two-way sampled deviation is 0.21 mm
worst case - but the rim crease is visible. The migrated asset has a continuous
surface there, so those seams are gone, consistent with the repository
screw-hole/hardware omission policy.

Not verified in the app: suspension and cord clearance, accessibility, and
performance. Those remain open.

## Tests

Native packages can declare several model presentations when a real accessory
changes the solid. Tag each bound feature with `HangTenPresentationID`, keep
each presentation's asset/descriptor names unique in the embedded manifest,
and compile it with `--presentation <id>`. Untagged legacy features belong to
the document's default presentation. `prepare_assets.py` covers every declared asset pair. The former global delivery
lock and reproduction checker were retired on Main; prior exact checks remain
historical evidence. Plateau uses this for
its 18/15/10 mm spacer configurations while retaining one physical contact ID;
position `effectiveDepths` records each actual configured depth.

For a stepped lip where an axis-aligned region extent is not grip depth, a
contact feature may carry both native-millimetre vector properties
`HangTenGripDepthStart` and `HangTenGripDepthEnd`. Both must lie on its native
contact shape within 0.25 mm; their distance is the depth witness. Audit the
specific lip and floor used, and bind the witnesses to native dimensions when
they can change. An incomplete pair fails compilation.

`HangTenUseBodyTriangles = true` is available only on a native
`PartDesign::SubShapeBinder` contact. It exports that contact's already-validated
assigned body triangles to share an exact seam, rather than independently
tessellating the same curved face. It does not bypass native source, depth,
face-membership, contact-partition or material validation.

    rtk python -m pytest Tools/HangboardCAD/tests -q   # in a venv with Tools/HangboardPackages[dev], numpy, usd-core==26.8

* `test_contract.py` — archive preflight (`cad_source.inspect_archive`):
  traversal, case collisions, duplicate members, unsupported object types,
  external links, missing embedded files, LFS pointers; and binding
  completeness (`contract.validate_bindings`).
* `test_board_manifest.py` — the board manifest: round trip to byte-exact
  `board.json`, geometry members untouched by an embed (and the file mode
  kept), in-place replacement, a schema-v2 (slots/instances) board,
  number-spelling preservation, duplicate-key rejection, refusal to write the
  package's own `board.json`, no committed CAD `board.json`, corrupt sources and
  LFS pointers, and the textconv rendering. This and `test_contract.py` run in
  CI's Linux Python job, next to `board_manifest.py --all` and both staging
  targets. The validator side (generated document validated, on-disk
  `board.json` rejected, `.gitignore` coverage) is in
  `Tools/HangboardPackages/tests/test_board_catalog.py` and
  `test_board_package_staging.py`.
* `test_usdz_writer.py` — real round trips including an asymmetric basis fixture
  that catches scale, reflection, and axis-swap errors, embedded textures,
  normals and UVs, and byte reproducibility.
* `test_pilot_native.py` — runs the native checks and the compiler under the
  pinned FreeCAD build as subprocesses; skipped, not silently passed, when that
  toolchain is absent. Its historical pre-migration artifact comparison was
  retired; native source, recompute-failure, and compiler checks remain.
* `tests/native_source_checks.py` — genuine native reopen, recompute, and edit
  checks: pad length 550 -> 620 mm propagating to every contact, and a profile
  dimension 50 -> 56 mm moving the edge-45 contact from 45.00 to 55.98 mm while
  the unrelated contacts keep their measured depth.
* `test_prime_rib_native.py` / `tests/prime_rib_native_source_checks.py` —
  the vector-profile source: primitive inventory, named dimensions, published
  envelope and depths, regions on the body surface, a pad-length edit and an
  `Edge23Depth` 23 -> 26 mm edit that moves only edge-23. `HANGTEN_FREECAD_CMD`
  points it at a non-default `freecadcmd`.
* `tests/compare_exports.py` — sampled two-way point-to-triangle distance between
  reviewed exports. The initial pilot comparison recorded 0.21 mm worst case
  against a 0.5 mm limit. A sampled bound, not
  an exact Hausdorff distance and not a product accuracy claim.
