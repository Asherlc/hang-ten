# Tension Whetstone native CAD migration plan

**Goal:** Replace the flat Whetstone presentation with a self-contained native FreeCAD source and selectable 3D contacts.

**Spec:** `.agents/skills/migrate-hangboard-to-3d/SKILL.md`, `AGENTS.md`, and the user-approved evidence in `.context/rugged-chipmunk-whetstone-cad/evidence/review.json`.

**Architecture:** The FCStd owns native geometry and the embedded board manifest. Existing compilation and staging generate an unbound USDZ, hash-bound descriptor, and build-time board.json. Existing renderers consume the package unchanged.

**Tech stack:** Pinned FreeCAD 1.1.3, OpenUSD 26.08, Python package tools, Swift/Xcode.

## Constraints and review focus

Preserve all 12 contact IDs and sourced dimensions/depths; retain approved manufacturer originals, URLs, hashes and field mappings. Label unpublished geometry estimates. No raster fallback, materials, textures, mounting holes, or hardware. Review stepped slot boundaries, incut center, pocket orientation, jug curvature, and selectable contact surfaces.

## Task 1: Native source and geometry

- [x] Retain and obtain approval for front and both oblique manufacturer views.
- [x] Author `Hangboards/tension-whetstone/tension-whetstone.FCStd` with native editable features and embedded model manifest; temporary authoring code stays in `.context`.
- [x] Reopen/recompute and verify bounds, contact identity, depths, surface partition and edit propagation.
- [x] Compile and review front/side/top views beside prior committed image.

## Task 2: Package integration and audit

- [x] Remove old raster and committed board.json; ignore generated board.json.
- [x] Add dated source audit and retained evidence under `docs/source-audits/`.
- [x] Update delivery inventory and hashes; run package validation, staging parity, model/CAD Python tests and reproducibility.

The native and package regression tests live in `Tools/HangboardCAD/tests/test_whetstone_package.py` and `whetstone_native_source_checks.py`. The RealityKit check is added to `HangTenTests/BoardModelRealityTests.swift`, with Whetstone added to the existing CI simulator staging set in `scripts/stage-board-packages.py`.

## Task 3: Native validation and delivery

- [x] Build/test on an exactly registered workspace-owned simulator; inspect Whetstone inactive and jug/deep/shallow highlights.
- [x] Review final diff and source boundaries; fix substantive findings.
- [x] Shut down/delete owned simulator and verify removal; commit and push to the remote branch.

Validation: Python 458 passed / 11 skipped; iOS 1,234 executed / three skipped / zero failures. Native edit propagation, byte-identical recompilation, package catalog, platform staging parity, source boundary manifest and delivery lock passed. App screenshots and selected-ID checks are retained in the dated source audit. All three review simulators were deleted and verified; the final simulator was `F9DDAA30-96E5-4F1A-A07C-89C79E8DC1ED`.
