# Hangboard Collection Model Imports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the six approved, structurally checked Hangboard Collection GLBs into source-audited, contact-first schema-v3 model-only Hang Ten packages.

**Architecture:** The current `board.json` files remain the physical-contact identity authority. Each task uses an explicit source-node mapping to import one reviewed GLB into a USDZ, compiles the descriptor from the actual reimported USDZ, then replaces its raster presentation without altering source-backed contact facts or saved contact IDs.

**Tech Stack:** Python model importer/compiler, Blender/USDZ, schema-v3 package validator, Swift/SceneKit model runtime, XCTest, Xcode/iOS Simulator.

**Spec:** `docs/superpowers/specs/2026-09-15-import-hangboard-collection-models-design.md`

## Global Constraints

- Scope is exactly Metolius Climber's Edge, Metolius Contact, Metolius Simulator 3-D, So iLL Training Tiles, The Hangboard, and Trango Rock Prodigy Training Center.
- Preserve each `board.json` ID, revision identity, `contacts[].id` inventory and source-backed facts exactly; a source mesh may bind to multiple pieces of one existing contact but never creates or renames a logical contact.
- Retain two materially distinct, audited visual sources per exact revision before promotion; record URLs, publishers, reviewed hashes, supported fields, omissions, and review date in a tracked source audit.
- A delivered package is model-only: exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; no PNG, raster media, canonical paths, cached frames, or fallback geometry remains.
- Model bindings are explicit source-node-to-contact mappings. Do not trace images, infer contacts from position or pixels, or use model-derived facts as training metadata.
- Omit screws and mounting hardware. Tag non-contact model geometry as body or attachment; it is not pickable. Invalid/missing assets fail closed to the runtime unavailable state.
- All generated conversion input/output, evidence copies, reports, screenshots, and simulator manifests belong under `.context/lumpy-liger-hangboard-collection/`; register and clean up owned external resources with exact workspace-name checks.
- Do not start an HTTP server.

## File Structure

| Path | Responsibility |
| --- | --- |
| `Hangboards/<board>/board.json` | Existing factual identity and final model presentation declaration. |
| `Hangboards/<board>/assets/primary.usdz` | Promoted deterministic model export. |
| `Hangboards/<board>/assets/primary.model.json` | Hash-bound descriptor generated from actual USDZ triangles. |
| `.context/lumpy-liger-hangboard-collection/<board>/` | Downloaded-source manifest, explicit mapping, temporary source copy, compiler output, and validation report. |
| `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md` | Cross-board evidence, mapping decisions, omissions, and commands/results. |
| `Tools/HangboardModels/test_*.py` | Existing descriptor/importer regression suite. |
| `Tools/HangboardPackages/tests/test_model_first_packages.py` | Package-boundary and descriptor inventory validation. |
| `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/BoardModelTests.swift` | Runtime package decode, unavailable-state, loading, and picking coverage. |

### Task 1: Audit and migrate Metolius Climber's Edge

**Files:**
- Modify: `Hangboards/metolius-climbers-edge/board.json`
- Create: `Hangboards/metolius-climbers-edge/assets/primary.usdz`, `Hangboards/metolius-climbers-edge/assets/primary.model.json`
- Delete: declared raster media from `Hangboards/metolius-climbers-edge/`
- Create/modify: `.context/lumpy-liger-hangboard-collection/metolius-climbers-edge/*`, `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md`

- [ ] Record the exact source GLB hash, the downloaded source register, and two reviewed visual sources for this revision; stop if the evidence gate is not met.
- [ ] Compare the GLB node inventory with the existing 15-contact inventory and author a reviewed explicit mapping; classify every unbound source node as body or attachment.
- [ ] Run `Tools/HangboardModels/import_contact_model_source.py` with the explicit mapping, reimport the resulting USDZ from an empty scene, and compile the descriptor.
- [ ] Replace the raster presentation only after descriptor contact keys exactly equal the existing contact IDs; remove obsolete raster assets and run focused package/model tests.
- [ ] Commit and push the completed board migration.

**Review gate:** A fresh reviewer verifies evidence traceability, exact contact-ID preservation, complete descriptor bindings, and absence of a raster fallback.

### Task 2: Audit and migrate Metolius Contact

**Files:**
- Modify: `Hangboards/metolius-contact/board.json`
- Create: `Hangboards/metolius-contact/assets/primary.usdz`, `Hangboards/metolius-contact/assets/primary.model.json`
- Delete: declared raster media from `Hangboards/metolius-contact/`
- Create/modify: `.context/lumpy-liger-hangboard-collection/metolius-contact/*`, `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md`

- [ ] Audit and retain the exact-revision evidence and source GLB hash.
- [ ] Explicitly map all 33 existing logical contacts to reviewed importer-visible nodes; keep bore/body nodes nonselectable.
- [ ] Import, export, reimport, and descriptor-validate the USDZ without source materials present.
- [ ] Promote only if descriptor inventory and model hash match, then run focused package/model tests.
- [ ] Commit and push the completed board migration.

**Review gate:** A fresh reviewer verifies the 33-contact mapping, stable metadata, and no fabricated depth/bore facts.

### Task 3: Audit and migrate Metolius Simulator 3-D

**Files:**
- Modify: `Hangboards/metolius-simulator-3d/board.json`
- Create: `Hangboards/metolius-simulator-3d/assets/primary.usdz`, `Hangboards/metolius-simulator-3d/assets/primary.model.json`
- Delete: declared raster media from `Hangboards/metolius-simulator-3d/`
- Create/modify: `.context/lumpy-liger-hangboard-collection/metolius-simulator-3d/*`, `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md`

- [ ] Audit evidence and map the 29 existing contacts to exact source nodes, documenting intentional multi-piece mappings if present.
- [ ] Compile/reimport/verify the actual USDZ and descriptor, including material and body-node validation.
- [ ] Promote the model-only presentation only when every existing contact has a binding and the descriptor hash is exact.
- [ ] Run package/model tests and commit/push the completed board migration.

**Review gate:** A fresh reviewer checks node/contact cardinality decisions and saved-contact identity preservation.

### Task 4: Audit and migrate So iLL Training Tiles

**Files:**
- Modify: `Hangboards/soill-training-tiles/board.json`
- Create: `Hangboards/soill-training-tiles/assets/primary.usdz`, `Hangboards/soill-training-tiles/assets/primary.model.json`
- Delete: declared raster media from `Hangboards/soill-training-tiles/`
- Create/modify: `.context/lumpy-liger-hangboard-collection/soill-training-tiles/*`, `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md`

- [ ] Audit exact board evidence and source hash, including the paired-board arrangement and any model caveats.
- [ ] Map all 20 existing contacts explicitly; ensure left/right counterparts and multi-part upper pockets/jugs bind correctly without adding IDs.
- [ ] Import and verify the USDZ/descriptor from actual importer-visible triangles.
- [ ] Promote the model-only package, remove raster assets, run focused tests, and commit/push.

**Review gate:** A fresh reviewer verifies bilateral mapping and the exclusion of unverified logos, hardware, and inferred geometry.

### Task 5: Audit and migrate The Hangboard

**Files:**
- Modify: `Hangboards/the-hangboard/board.json`
- Create: `Hangboards/the-hangboard/assets/primary.usdz`, `Hangboards/the-hangboard/assets/primary.model.json`
- Delete: declared raster media from `Hangboards/the-hangboard/`
- Create/modify: `.context/lumpy-liger-hangboard-collection/the-hangboard/*`, `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md`

- [ ] Audit evidence and source hash; preserve the 15 existing contacts and all supported dimensions/facts.
- [ ] Author the direct source-node mapping, classify unselectable model elements, and compile/reimport the package.
- [ ] Validate exact descriptor inventory/hash, replace raster declarations/assets, and run focused tests.
- [ ] Commit and push the completed board migration.

**Review gate:** A fresh reviewer verifies central sloper and bilateral edge identities are neither merged nor invented.

### Task 6: Audit and migrate Trango Rock Prodigy Training Center

**Files:**
- Modify: `Hangboards/trango-rock-prodigy-training-center/board.json`
- Create: `Hangboards/trango-rock-prodigy-training-center/assets/primary.usdz`, `Hangboards/trango-rock-prodigy-training-center/assets/primary.model.json`
- Delete: declared raster media from `Hangboards/trango-rock-prodigy-training-center/`
- Create/modify: `.context/lumpy-liger-hangboard-collection/trango-rock-prodigy-training-center/*`, `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md`

- [x] Audit the exact Training Center revision against its existing Trango source audit and the model evidence; do not use Forge, Natural, or Pivot facts as substitutes.
- [x] Map the current 24 contacts to reviewed source nodes and explicitly retain separate pockets, pinches, and bilateral contacts.
- [x] Compile/reimport/descriptor-validate the USDZ and promote it only when all contacts bind.
- [x] Remove raster media, run focused tests, and commit/push the completed board migration.

**Review gate:** A fresh reviewer checks revision isolation and one-to-one identity coverage of the full 24-contact inventory.

### Task 7: Run final package, runtime, and iOS visual validation

**Files:**
- Modify: `docs/source-audits/2026-09-15-hangboard-collection-model-imports.md`
- Create: `.context/lumpy-liger-hangboard-collection/final-validation.json` and temporary review screenshots

- [ ] Run `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, `rtk scripts/hangboard-packages.sh status --root Hangboards`, retained model-tool pytest collection, and focused Swift model/package tests.
- [ ] Build and validate with the isolated-simulator workflow in `docs/IOS_SIMULATOR_VALIDATION.md`; inspect all six normal and selected-contact states, model-unavailable behavior, and picking alignment.
- [ ] Record commands, results, model/descriptor hashes, screenshots reviewed, omissions, and cleanup verification in the audit; clean all owned resources/artifacts.
- [ ] Run `rtk git diff --check`, request the final broad review against this plan/spec, resolve all critical or important findings, then commit and push validation adjustments.

**Review gate:** Final reviewer must confirm the six-package scope, descriptor integrity, source boundaries, runtime behavior, test evidence, and exact owned-resource cleanup.
