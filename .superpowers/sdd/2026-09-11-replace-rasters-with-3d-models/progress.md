# SDD ledger — plan: docs/superpowers/plans/2026-09-11-replace-rasters-with-3d-models.md

## Preflight scan

| Task | Shared files/interfaces | Finding | Ruling |
| --- | --- | --- | --- |
| Task 1 ↔ Task 2 | Task 1 produces the two model-only packages and audit; Task 2 consumes them for final verification. | No contradiction; Task 2 must not alter package content except through a reviewed fix agent. | Proceed in order. |
| Task 1 | Board JSON, model assets, package/runtime tests, source audit. | Requirements agree: preserve logical IDs while replacing presentation-owned raster media with model media and generated descriptors. | Use explicit source-object mappings and existing compiler/parser contracts. |
| Task 2 | Final verification report and Task 1 outputs. | Requirements agree: verification is read-only unless a review finding requires a fresh implementation fix. | Re-run validators/tests and inspect the full branch diff. |

Ruling: the Downloads directory currently contains exactly two usable migrated-board directories, Metolius Simulator 3D and Training Tiles; — scope is limited to those two exact catalog matches because no third supplied board model is present — cost if wrong: another intended model would remain raster until a later migration.

Ruling: baseline Python package tests cannot run in the current environment because `pytest` is not installed — proceed with implementation and run all available repository-native checks, recording the missing dependency — cost if wrong: Python regressions may require dependency installation or CI verification.

Ruling: add `flat-sloper-2-left` and `flat-sloper-2-right` as source-backed Metolius logical holds using the supplied 55 mm flat-sloper evidence, and generalize the model body contract from exactly one body mesh to one-or-more explicit body meshes — this preserves all 31 selectable Metolius contacts and both Training Tiles body objects without collapsing, dropping, or inventing geometry — cost if wrong: the catalog inventory and model parser contract gain two IDs and a broader body-node invariant that would need a follow-up migration if the product intentionally wants a single-body-only schema.

Ruling: use the supplied manufacturer-supported Training Tiles inventory of 16 contacts, remove `top-pocket-inner-left/right` and `top-jug-left/right` from active selectable metadata, and record those four IDs as deprecated/unverified in the migration audit; no saved workout/history data in the repository references them — this preserves the model-only completeness contract without inventing geometry — cost if wrong: an external user data store may later need an explicit deprecated-ID compatibility migration.

## Task tracking

- Task 1: complete
- Task 2: complete

## Completion evidence

- Implementation commits: `0ed928be`, `9c9e9078`, `2a082779`.
- Review approved with no Critical or Important findings.
- Final package validator passed; focused model unittest passed.
- Exact package-tree, inventory, and hash semantic checks passed.
- `pytest` was unavailable in this environment; simulator XCTest stalled before build and was cleaned up.
