---
name: add-hangboard
description: Use when adding or refining a physical hangboard or a distinct board revision, correcting its hold inventory or metadata, editing canonical hold paths, preparing its presentation asset, or reviewing highlight alignment in Hang Ten.
---

# Add a hangboard

Read `docs/ADDING_A_BOARD.md` completely. It is the active package, evidence,
geometry, and validation contract.

## Workflow

1. Identify the exact physical revision. Give genuinely different product
   revisions separate packages so one revision never overwrites another's
   identity or saved selection. Keep selectable surfaces, sides, and mounting
   orientations of the same physical product in one package as presentations.
2. Research that revision using official front, oblique, dimensional, and
   hold-guide sources. Record URLs, review date, field mappings, and explicit
   caveats for any archival third-party image in a source audit.
3. Freeze the physical hold inventory. Require `fingerCapacity` (1–4 non-thumb
   fingers per hand) on every contact. Prefer published counts; otherwise review
   the physical hold and document an explicitly labeled estimate with contact
   IDs, reasoning, source URLs, and review date. Do not infer capacity from a
   highlight patch alone. Omit unsupported optional measurements, hand capacity,
   posture, and feature metadata.
4. Create or refine one flat `Hangboards/<slug>.FCStd`, the retained native
   geometry and embedded board/cord/simulation input source. **REQUIRED SUB-SKILL:** Use
   `migrate-hangboard-to-3d` for geometry or model integration work. Embed
   metadata with `Tools/HangboardCAD/set_board_manifest.py`; edit evidenced
   cord/simulation inputs with `Tools/HangboardCAD/set_cad_authoring.py` in
   document-level `App::PropertyString` properties `HangTenSuspensionAuthoring`
   and `HangTenRopePhysics`. Suspension authoring retains topology, dimensions,
   solver settings, evidence, pose rotations/cameras, and optional
   `offsetXZ: [x, z]`. Hashes, settled heights, and solved routes are generated.
   Do not create `board.json` or authored JSON sidecars inside a CAD package.
5. Deliberately author native contact regions. Mirror one reviewed side
   exactly when official evidence shows symmetry, and keep disconnected pieces
   under their physical contact ID. Follow the Trango Rock Prodigy Pivot as a
   structural precedent, without copying its product-specific geometry.
6. Run `rtk proxy bash scripts/build-board-assets.sh --package <slug>` using
   pinned FreeCAD 1.1.3/OpenUSD 26.8 and pinned native solver dependencies.
   Generated USDZ, model descriptors, `assets/suspension.json`, and optional
   physics descriptors remain at ignored `Hangboards/<slug>/assets/` paths.
   The producer solves every declared cord pose from the CAD inputs and actual
   solid; package generation validates the source/model bindings and merges
   solved suspension into bundled `board.json`. Compare front/side/top
   exports against the prior committed source for every geometry change.
7. Run `rtk scripts/hangboard-packages.sh validate --root Hangboards
   --final-inventory` and `rtk scripts/hangboard-packages.sh status --root
   Hangboards`. Inspect normal paths and active/highlight alignment in the app
   on an owned simulator after `rtk proxy bash scripts/build-runtime-assets.sh`.
   Capture representative app-rendered normal and
   active/highlight screenshots and include them in the PR evidence.

## Non-negotiable rules

- Author geometry directly. Do not use or create image-driven detection,
  segmentation, masks, contours, registration/alignment, vectorization,
  automatic simplification/cropping, or proposal/refine/promote tooling.
- For supported raster packages, canonical paths remain the rendering,
  highlighting and hit-testing source; constraints are operator-selected,
  never inferred from pixels.
- Generated board meshes ship unbound, without materials or textures.
- Review each revision's distinguishable shape against primary evidence and a
  comparable catalog product.
- Do not split one physical product into separate catalog packages solely
  because its selectable surface or mounting orientation changes.
- Record provenance and caveats for every non-primary source; never turn an
  unsupported image detail into board metadata or geometry.
- Do not hand-author both sides of a symmetric board unless evidence establishes
  asymmetry.
- Commit flat native sources and evidence. `board.json` is
  generated during validation/staging, and runtime assets stay ignored.
  See `Tools/HangboardCAD/README.md` and `docs/GENERATED_ARTIFACTS.md`.
- Do not finish with missing geometry, extra geometry, unsupported facts, or a
  highlight that drifts from its physical contact surface. Include app-rendered
  normal and highlighted-hold screenshots in PR review evidence.
