---
name: add-hangboard
description: Use when adding or refining a physical hangboard, correcting its hold inventory or metadata, editing canonical hold paths, or reviewing highlight alignment in Hang Ten.
---

# Add a hangboard

Read `docs/ADDING_A_BOARD.md` completely. It is the active package, evidence,
geometry, and validation contract.

## Workflow

1. Research the exact product using official front, oblique, dimensional, and
   hold-guide sources. Record URLs and field mappings in a source audit.
2. Freeze the physical hold inventory. Omit optional measurements, capacities,
   posture, and feature metadata that the sources do not support.
3. Create the flat `Hangboards/<slug>/board.json` plus
   `assets/primary.png`. Use the Trango Rock Prodigy Pivot only as a structural
   and path-style precedent; do not copy its product-specific geometry.
4. Deliberately author each normalized closed path, then refine it directly in
   Workbench. Mirror one reviewed side exactly when official evidence shows
   symmetry. Keep one logical hold with multiple pieces when a single physical
   contact is visually disconnected.
5. If the checked-out schema supports shape constraints, select one manually
   for a genuinely regular hold; otherwise use a freeform path. The canonical
   path is always the rendering, highlighting, and hit-testing truth.
6. Run `rtk scripts/hangboard-packages.sh validate --root Hangboards
   --final-inventory` and `rtk scripts/hangboard-packages.sh status --root
   Hangboards`. Inspect normal paths in Workbench; inspect active/highlight
   alignment in the app on an owned simulator.

## Non-negotiable rules

- Author paths directly. Do not use or create image-driven detection,
  segmentation, masks, contours, registration/alignment, vectorization,
  automatic simplification/cropping, or proposal/refine/promote tooling.
- Shape constraints are operator-selected, never inferred from pixels.
- The same saved path must drive normal rendering, active rendering, and hit
  testing.
- Do not hand-author both sides of a symmetric board unless evidence establishes
  asymmetry.
- Do not finish with missing geometry, extra geometry, unsupported facts, or a
  highlight that drifts from its physical contact surface.
