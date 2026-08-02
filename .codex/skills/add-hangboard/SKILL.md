---
name: add-hangboard
description: Add or refine a physical hangboard in Hang Ten with audited hold metadata, deterministic normalized vector artwork, semantic routine targets, and exact-path highlights. Use for new board models, board fidelity fixes, hold-map corrections, highlight alignment, or reusable board-design work.
---

# Add a hangboard

Read `docs/ADDING_A_BOARD.md` completely before changing files. Follow its
source, metadata, geometry, and validation contract.

## Workflow

1. Inspect `BoardCatalog`, `BoardDesignLanguage.swift`, the existing bespoke
   designs, and the target board's official manufacturer sources.
2. Record front, oblique, dimensional, and hold-depth evidence. Do not infer a
   hold semantic when a manufacturer diagram exists.
3. Add stable `TrainingBoard` and `BoardHold` metadata first, including truthful
   `GripType` and `HoldFeature` values.
4. Build normalized vector geometry from silhouette to planes to contact
   shapes. Define paired geometry once and mirror it.
5. Register the design and keep the model and rendered hold-ID sets identical.
6. Add the board's versioned semantic mapping, regenerate `PlanLibrary.json`,
   and verify it with `scripts/export-plan-library.sh --check`.
7. Resolve representative routines and ensure every requested feature maps to
   a factual hold.
8. Use the dedicated-simulator workflow to inspect inactive and active surface,
   shelf, deep-recess, and shallow-recess states in portrait and landscape.

## Non-negotiable rules

- A raster may be a temporary calibration reference, never the highlight or
  hit-testing source.
- The same `BoardHoldPiece` path must draw normal contact, active contact, and
  interaction geometry.
- Do not add bolts, branding, photographic texture, or fake protrusions to the
  shared design language.
- Do not hand-enter both sides of a symmetric board unless official evidence
  establishes asymmetry.
- Do not call the work complete while a model hold lacks artwork, artwork has
  no model hold, or a highlighted screenshot drifts from its cavity.
