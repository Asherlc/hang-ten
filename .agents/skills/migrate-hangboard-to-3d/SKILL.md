---
name: migrate-hangboard-to-3d
description: Use when migrating an existing Hang Ten hangboard to an interactive 3D display model, or refining its geometry, exported materials, picking, or app integration.
---

# Migrate a hangboard to 3D

Deliver a faithful model-only schema-v3 package with selectable physical
contacts. The USDZ and hash-bound descriptor are the sole sources of rendering,
highlighting, hit testing, and resolved spatial geometry. Do not retain raster
media, canonical paths, cached frames, or fallback geometry in a model package.
Preserve contact identity and source-backed factual metadata exactly.

**REQUIRED SUB-SKILL:** Use `audit-3d-hangboard-suspension` when a portable
model has, needs, or is suspected to be missing a cord. Read
[`3D suspension and ODR`](../../../docs/3D_SUSPENSION_AND_ODR.md) before
changing suspension metadata or diagnosing Apple offline/On-Demand Resource
caching. The USDZ is the only ODR asset; cords are metadata-driven transient
geometry.

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

Read the live schema-v3 `board.json` and use `contacts[].id` as the only logical
identity inventory. A model presentation owns one USDZ and one descriptor. Its
descriptor binds importer-visible nodes to physical contact IDs; disconnected
mesh pieces may share a contact ID. Model packages are model-only and
read-only in the apps. Remote model editing is unsupported.

Use only the retained native tools:

- `Tools/HangboardModels/contact_model_descriptor.py` validates and compiles
  descriptor-v1 contact bindings and read-only mesh-derived bounds.
- `Tools/HangboardModels/contact_model_package.py` transports deliberately
  tagged Blender geometry into a deterministic USDZ and descriptor. It reads
  only schema-v3 `contacts[]`.
- `Tools/HangboardModels/import_contact_model_source.py` imports a reviewed
  source model using an explicit contact mapping; it does not infer bindings.
- `Tools/HangboardModels/verify_yy_baguette_evo.py` verifies the shipped YY
  Baguette Evo package’s exact model, descriptor, bindings, and hashes.
- `Tools/HangboardCAD/compile_board.py` compiles a native FreeCAD source
  (`Hangboards/<slug>/<slug>.FCStd`) directly into the USDZ and descriptor. For
  such a package, `board.json` is generated from the FCStd's embedded
  `HangTenBoardManifest` at build time and is not committed: embed the reviewed
  `board.json` with `set_board_manifest.py`, then `git rm` it and add its path
  to `.gitignore`. Follow
  `docs/freecad-authoring-migration.md` and "Authoring a new CAD board" in
  `Tools/HangboardCAD/README.md`; any authoring script is a throwaway under
  `.context/`, and its provenance goes in a dated `docs/source-audits/` record.

Do not recreate removed schema-v2 compilers, migration manifests, baseline
wrappers, gallery generators, raster converters, or compatibility aliases.

## Geometry authoring and export

Use Astra only for authoritative final shape generation or difficult physical
shape judgment after the evidence gate. Lower-cost workers may handle schemas,
deterministic tooling, validation, packaging, and app integration. Directly
author analytic silhouettes, sections, recesses, and symmetric counterparts;
never trace, segment, vectorize, crop, register, or infer geometry from pixels.

The compiler transports authored geometry and must not repair shapes,
materials, names, or topology. Tag every source mesh explicitly as body,
attachment, or contact. Keep source-to-imported node correspondence through
export. Reimport the actual USDZ from an empty scene and rebuild the descriptor
from importer-visible triangles. Validate exact assets, hashes, materials,
dimensions, contact inventory, bindings, and sorted canonical descriptor data.
Derived centers and bounds are read-only mesh outputs, never authored facts.

Blender entrypoints must bootstrap sibling imports from `__file__` and use
workspace-owned config/cache/temp/output. If Blender fails before Python in the
managed sandbox, compare one minimal host-context invocation when authorized;
do not attribute an environment boundary failure to geometry.

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
promoted USDZ and descriptor hashes unless audited geometry work explicitly
authorizes a new promotion. Put generated artifacts under the workspace-owned
`.context` directory, install exact cleanup traps for external resources, and
verify cleanup before reporting completion.
