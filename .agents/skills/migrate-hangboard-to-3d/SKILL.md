---
name: migrate-hangboard-to-3d
description: Use when migrating an existing Hang Ten hangboard to native CAD, refining its 3D geometry, or reviewing unbound exports, picking, or app integration.
---

# Migrate a hangboard to 3D

Deliver a faithful model-only schema-v3 package with selectable physical
contacts. Retain one flat `Hangboards/<slug>.FCStd` as the geometry and embedded
board/cord/simulation input source. Its generated USDZ and hash-bound descriptor drive rendering,
highlighting, hit testing, and resolved spatial geometry. Do not retain raster
media, canonical paths, cached frames, or fallback geometry in a model package.
Preserve contact identity and source-backed factual metadata exactly.

**REQUIRED SUB-SKILL:** Use `audit-3d-hangboard-suspension` when a portable
model has, needs, or is suspected to be missing a cord. Read
[`3D suspension and ODR`](../../../docs/3D_SUSPENSION_AND_ODR.md) before
changing suspension metadata or diagnosing Apple offline/On-Demand Resource
caching. The USDZ is the only ODR asset; cords are metadata-driven transient
geometry. For connected passages or a mesh-derived bearing route, read
[`CAD cord authoring`](../../../docs/HANGBOARD_CORD_AUTHORING.md) before
authoring topology or selecting a solver. A board migrated to CAD preserves
its evidenced connection graph and replaces hand-authored leads with native
solver-generated routes. Connected internal mouth pairs use the standard CAD
void, measured channel and `internalLoop` method; source-backed independent
leads, exterior wraps and unknown interior joins use `cadRoutedCord` with
`ropeSolver.method: "nativeRoutes"`. Never infer hidden connectivity. Generate
every canonical pose through `scripts/build-board-assets.sh` and
`compile_suspension.py`, reproduce the generated artifact with
`solve_threaded_rope.py --check`, and retain native-solid clearance, length,
tube and topology checks. Change CAD inputs and rebuild; solved heights and
routes never become source metadata. POCKET's pre-existing manifest suspension
remains the documented legacy exception pending a separate evidence-backed
revision; consolidation does not infer new threading for it.
The cord route is not live physics; document its mesh and topology assumptions.

## Evidence and scope

Identify the exact product revision and read the package source audit. Reuse
verified manufacturer references and research only missing evidence. Before
geometry work, retain at least two materially distinct visual sources for that
revision, record each source URL/publisher/hash and what it supports, and obtain
human approval of the exact set. Manufacturer evidence is preferred; clearly
labeled commerce evidence may fill a documented missing angle. Search
thumbnails, generated renders, legacy raster assets, and ambiguous revisions do
not satisfy this gate.

Separate sourced dimensions and contact facts from estimated display geometry.
Never derive training prescriptions from a model. Omit mounting holes, screws,
and mounting hardware from display models and document those omissions without
implying the physical product lacks them.

## Contact-first package contract

Read the generated schema-v3 document with
`rtk python3 Tools/HangboardCAD/board_manifest.py --package <slug>` and use
`contacts[].id` as the only logical identity inventory. A model presentation
declares one generated USDZ and descriptor. Its
descriptor binds importer-visible nodes to physical contact IDs; disconnected
mesh pieces may share a contact ID. Model packages are model-only and
read-only in the apps. Remote model editing is unsupported.

Use only the retained native tools:

- `Tools/HangboardModels/contact_model_descriptor.py` validates and compiles
  descriptor-v1/v2 bindings and read-only mesh-derived bounds.
- `Tools/HangboardCAD/compile_board.py` compiles a native FreeCAD source
  (`Hangboards/<slug>.FCStd`) directly into the USDZ and descriptor. For
  such a package, `board.json` is generated from the FCStd's embedded
  `HangTenBoardManifest` and validated generated `assets/suspension.json` at
  build time and is not committed. Embed reviewed board metadata with
  `set_board_manifest.py` and cord/simulation inputs with `set_cad_authoring.py`
  in document-level `App::PropertyString` `HangTenSuspensionAuthoring` and
  `HangTenRopePhysics`. Suspension authoring retains topology, dimensions,
  solver settings, evidence, pose rotations/cameras, and optional
  `offsetXZ: [x, z]`. Source/model hashes, settled heights, and solved routes
  belong in the generated artifact. Missing/stale artifacts and changed
  authoring payloads fail package validation. Follow
  "Authoring a new CAD board" in `Tools/HangboardCAD/README.md`; any authoring
  script is a throwaway under
  `.context/`, and its provenance goes in a dated `docs/source-audits/` record.
- `scripts/build-board-assets.sh --package <slug>` builds ignored runtime
  outputs using pinned FreeCAD 1.1.3/OpenUSD 26.8. Run it before validation;
  run `scripts/build-runtime-assets.sh` before a fresh-checkout app build.
- `Tools/HangboardModels/verify_owl_climb_poker.py` and the native Training
  Center verifier retain actual-export regressions for those boards.

Commit the flat FCStd and evidence; keep USDZ, `*.model.json`, `*.physics.json`,
`assets/suspension.json`, and generated `board.json` out of Git. Runtime assets
retain their existing `Hangboards/<slug>/assets/` paths. Do not recreate retired
Blender board compilers/importers, per-board authors, mesh cleanup/simplification,
raster converters, or compatibility aliases.

## Geometry authoring and export

Use Astra only for authoritative final shape generation or difficult physical
shape judgment after the evidence gate. Lower-cost workers may handle schemas,
deterministic tooling, validation, packaging, and app integration. Directly
author analytic silhouettes, sections, recesses, and symmetric counterparts;
never trace, segment, vectorize, crop, register, or infer geometry from pixels.

The compiler transports authored geometry and must not repair shapes,
materials, names, or topology. Bind each exported native object explicitly with
`NodeID`, `NodeRole`, and `ContactID` or `ContactSlotID`. Reopen the actual USDZ
with the retained native reader and rebuild its descriptor from exported
triangles. Validate exact assets, hashes, unbound material policy,
dimensions, contact inventory, bindings, and sorted canonical descriptor data.
Derived centers and bounds are read-only mesh outputs, never authored facts.

Use `run_freecad.py` or the shared build script to handle FreeCAD launcher
arguments and its extra Python path. Generated diagnostics belong under a
workspace-owned `.context` path. Blender 5.2.0 is retained for grip hand export,
not board authoring or compilation.

## Runtime integration

Inspect package loading, `BoardModelView`, staging, and model tests before
editing. Extend the existing renderer and identity bridge. Keep asynchronous
cached loading, cloned materials, scene/camera rebinding, accessibility, and
on-demand rendering. Gate the model to its exact package revision. Missing or
invalid assets fail closed to the explicit unavailable state; never substitute
a raster or inferred shape.

For suspended presentations, author only explicit source-backed attachment
facts and clearly labeled pose/cord display estimates. Passage and attachment
nodes must bind to importer-visible body or attachment nodes, never contact
nodes. Validate finite canonical poses, cord dimensions, clearance,
self-intersection, and non-pickability. Unsupported or invalid suspension data
must enter the model-unavailable state without a visible stand-in or fallback.

## Verification and cleanup

Run retained model-tool pytest collection, package validation, staging parity,
native model/picking tests, full Swift tests/build, and hard-cut scans. Preserve
generated USDZ and descriptor hashes for metadata-only changes. For geometry
changes, build from both prior and changed FCStd sources and present
front/side/top previews before completion. Hash-bound depth exceptions in
`Tools/HangboardCAD/display_depth_audits.json` retain specific reviewed source
facts; they do not authorize geometry changes. Put diagnostic artifacts under
the workspace-owned `.context` directory, install exact cleanup traps for external resources, and
verify cleanup before reporting completion.
