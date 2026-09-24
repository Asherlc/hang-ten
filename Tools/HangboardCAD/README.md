# FreeCAD authoring — native source and direct USDZ compiler

**Status: 6 of the 46 model-media boards are migrated** (those with a committed
`Hangboards/*/*.FCStd` source; the delivery lock lists 46 model packages). The
pipeline below is implemented, executed, and reproducible. Do not read this as a
finished catalogue migration.

## What this provides

One self-contained native FreeCAD document per board, kept inside the board's own
package:

    Hangboards/<package-directory>/<package-directory>.FCStd

plus the existing logical metadata at `Hangboards/<package-directory>/board.json`.
One shared command turns those two inputs into the existing runtime pair
(`assets/primary.usdz` and `assets/primary.model.json`). There is no required
Blender, GLB, STEP, OBJ, or STL step, and no board-specific Python program in the
build path.

## Running it

The pinned toolchain is FreeCAD 1.1.3 (OCCT 7.8.1, Python 3.11.14) with OpenUSD
26.08 supplied to FreeCAD's interpreter out of band, because FreeCAD's launcher
does not inherit `PYTHONPATH`:

    HANGTEN_CAD_PYTHONPATH=<dir containing pxr> \
      /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
      Tools/HangboardCAD/compile_board.py --package lattice-triple-rung

Add `--check` to validate and stage without publishing, and `--report <path>` to
write the JSON build report. The command validates `board.json` and the source
archive, reopens and recomputes the document without modifying its bytes,
extracts the bound components, tessellates at the document's pinned deflection,
partitions the board surface, writes the USDZ directly, reopens the exported
bytes, derives the descriptor from those bytes, and publishes the pair.

## Source document contract

Document properties: `HangTenBoardID`, `HangTenPresentationID`,
`HangTenSchemaVersion` (1 or 2), `HangTenSourceKind`,
`HangTenCoordinateFrame` (`freecad-mm-z-up-front-negative-y`), and
`HangTenTessellationDeflection`.

Every exported object carries `NodeID`, `NodeRole` (`body`, `contact`,
`attachment`), `ContactID` (or `ContactSlotID`), `MaterialName`, `BaseColor`,
`Roughness`, `Metallic`, and optionally an embedded `TextureFile`. Objects
without `NodeID` — sketches, datums, construction features — are never exported.
The `NodeID` becomes the USD mesh prim name, which is what the application binds
against.

Coordinate conversion is applied exactly once: native millimetres
(+X right, +Z up, front -Y) to runtime metres (+X right, +Y up, front +Z) as
`(x, y, z) -> (x/1000, z/1000, -y/1000)`.

## Surface partition

The approved runtime contract partitions the board surface: the body node holds
the surface *minus* the contact regions, and each contact node holds its region.
The compiler assigns every tessellated body triangle to exactly one node using
the contact regions built from the source document's own sketch edges, so the
result has no duplicated coplanar geometry and no z-fighting. Verified on the
pilot: 390 body triangles plus 122 / 82 / 82 contact triangles, with each contact
region matching the approved reference to 0.0000 mm in both directions.

## Pilot: lattice-triple-rung

`Hangboards/lattice-triple-rung/lattice-triple-rung.FCStd` is a native PartDesign body: one fully
constrained 170-vertex Sketcher profile and a symmetric 550 mm pad. The three
grip regions are `PartDesign::SubShapeBinder` runs of the profile's own sketch
edges, extruded with a length expression on the pad.

Provenance of the authored numbers. There is deliberately no per-board
provenance sidecar; these facts live here instead.

* Published facts come from `board.json`: overall 550 x 130 x 50 mm and grip
  depths 45 / 20 / 10 mm. Cross-reference those (and product identity) against
  manufacturer / product pages before treating them as settled; web search is a
  required check, not a geometry source — see
  `docs/freecad-authoring-migration.md` procedure step 3.
* The cross-section is **measured** from the approved reference asset at the
  pre-migration commit, as an ordered end-cap boundary loop. It is a measured
  approximation of a display mesh, **not recovered manufacturing geometry**.
* The 267 measured points were reduced to 170 authored vertices, with a maximum
  deviation of 0.1899 mm. `include/tolerance` details are in the migration
  script, which records the reduction criterion.
* The reference is resolved from commit `6b828e15`
  (`Tools/HangboardCAD/reference.py`), never from the live runtime path.

## In-app verification

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
``Tools/HangboardModels/mounting_bore_repairs.json`` (x = +/-75 mm and
+/-225 mm at y = 14 mm, and x = +/-225 mm at y = 96 mm). They are essentially
flush with the surrounding surface - the two-way sampled deviation is 0.21 mm
worst case - but the rim crease is visible. The migrated asset has a continuous
surface there, so those seams are gone, consistent with the repository
screw-hole/hardware omission policy.

Not verified in the app: suspension and cord clearance, accessibility, and
performance. Those remain open.

## Known limitations and open interface question

* **6 of 46 model-media boards are migrated.** The other 40 still ship their
  existing runtime assets, which are unchanged by this work.
* `HangTenSourceKind` distinguishes `native-parametric-measured-profile` from
  `faceted-import`. A mesh imported as B-rep must be labelled `faceted-import`
  and must not be presented as recovered parametric history.
* The compiler refuses a source it cannot recompute cleanly, a contact region
  whose depth disagrees with the published grip depth in `board.json`, a body
  triangle claimed by two contact regions, a region that claims more body
  surface than its own exported surface, and a document labelled
  `faceted-import` unless `--allow-faceted-import` acknowledges it. Each guard
  has a failing test.
* FreeCAD's Sketcher `DistanceX`/`DistanceY` against an axis solve to the negated
  value in this pinned build. The authored sketch stores negated local
  coordinates with positive driving dimensions and negates them back through an
  explicit sketch placement; the pad's world bounding box is asserted, so any
  change in that behaviour fails the build rather than silently mirroring.
* Binding contact regions to the pad's **faces** was tried and rejected: FreeCAD
  lost the face element map after a profile edit and unrelated contact regions
  silently moved to different faces. The sketch-edge binding is used instead, and
  the native checks fail if any region's depth changes after an unrelated edit.
* CPU previews are neutral geometry renders with an explicit planar UV
  projection. They are not native SceneKit screenshots and do not establish
  native materials, picking, accessibility, suspension, or performance.
* The migrated asset was validated in the iOS simulator board-detail route (see
  above). Suspension, accessibility, and performance checks were not run, so this
  is not complete native acceptance.

## Tests

    .context/organic-shark/venv/bin/python -m pytest Tools/HangboardCAD/tests -q

* `test_contract.py` — archive preflight: traversal, case collisions, duplicate
  members, unsupported object types, external links, missing embedded files,
  LFS pointers, and binding completeness.
* `test_usdz_writer.py` — real round trips including an asymmetric basis fixture
  that catches scale, reflection, and axis-swap errors, embedded textures,
  normals and UVs, and byte reproducibility.
* `test_pilot_native.py` — runs the native checks and the compiler under the
  pinned FreeCAD build as subprocesses; skipped, not silently passed, when that
  toolchain is absent. The reference comparison resolves the pre-migration asset
  from Git via `Tools/HangboardCAD/reference.py`, so no copy of it is kept in the
  working tree.
* `tests/native_source_checks.py` — genuine native reopen, recompute, and edit
  checks: pad length 550 -> 620 mm propagating to every contact, and a profile
  dimension 50 -> 56 mm moving the edge-45 contact from 45.00 to 55.98 mm while
  the unrelated contacts keep their measured depth.
* `tests/compare_exports.py` — sampled two-way point-to-triangle distance against
  the approved reference (0.21 mm worst case, limit 0.5 mm). A sampled bound, not
  an exact Hausdorff distance and not a product accuracy claim.
