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
3. Freeze the physical hold inventory. Omit optional measurements, capacities,
   posture, and feature metadata that the sources do not support.
4. Create the flat `Hangboards/<slug>/board.json` plus the PNG assets declared
   by its presentations. Use a clean, simplified, straight-on presentation
   render that preserves the revision's distinguishable layout; use source
   photos as evidence, not as the primary asset. Match the established catalog
   material/render style for the real product: wood boards use pale timber,
   realistic recesses, soft studio lighting, and an off-white background;
   non-wood boards use a comparable style for their actual material. Before PR
   submission, compare the asset side by side with a similar existing catalog
   board that matches the product's material and form factor. Use the Trango
   Rock Prodigy Pivot only as a structural and path-style precedent; do not
   copy its product-specific geometry.
5. Deliberately author each normalized closed path, then refine it directly in
   Workbench. Mirror one reviewed side exactly when official evidence shows
   symmetry. Keep one logical hold with multiple pieces when a single physical
   contact is visually disconnected.
6. If the checked-out schema supports shape constraints, select one manually
   for a genuinely regular hold; otherwise use a freeform path. The canonical
   path is always the rendering, highlighting, and hit-testing truth.
7. Run `rtk scripts/hangboard-packages.sh validate --root Hangboards
   --final-inventory` and `rtk scripts/hangboard-packages.sh status --root
   Hangboards`. Inspect normal paths in Workbench and active/highlight alignment
   in the app on an owned simulator. Capture representative app-rendered normal
   and active/highlight screenshots and include them in the PR evidence.

## Non-negotiable rules

- Author paths directly. Do not use or create image-driven detection,
  segmentation, masks, contours, registration/alignment, vectorization,
  automatic simplification/cropping, or proposal/refine/promote tooling.
- Shape constraints are operator-selected, never inferred from pixels.
- The same saved path must drive normal rendering, active rendering, and hit
  testing.
- Keep each revision's presentation asset head-on and visually distinguishable;
  do not substitute an angled archival photograph for the rendered asset.
- Match each presentation asset to the catalog render style for the product's
  actual material and form factor, and side-by-side review it against a
  comparable existing catalog board before PR submission.
- Do not split one physical product into separate catalog packages solely
  because its selectable surface or mounting orientation changes.
- Record provenance and caveats for every non-primary source; never turn an
  unsupported image detail into board metadata or geometry.
- Do not hand-author both sides of a symmetric board unless evidence establishes
  asymmetry.
- Do not finish with missing geometry, extra geometry, unsupported facts, or a
  highlight that drifts from its physical contact surface. Include app-rendered
  normal and highlighted-hold screenshots in PR review evidence.
