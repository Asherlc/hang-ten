# Replace Raster Board Presentations with Supplied 3D Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raster presentations for the two supplied catalog boards with the matching downloaded 3D models.

**Architecture:** Preserve each board’s existing ID, logical hold inventory, metadata, and workout target identities. Convert the supplied Blender source into the repository’s model-only package contract (`primary.usdz` plus generated `primary.model.json`), bind every mesh explicitly to the existing logical hold IDs, and make the model presentation the sole rendering, highlighting, picking, and matching geometry.

**Tech Stack:** Blender/USDZ, the existing model-package compiler and validators, schema-v2 board packages, Swift/SceneKit runtime, and Python/XCTest package tests.

**Spec:** `docs/superpowers/specs/2026-09-10-import-hangboard-model-packages-design.md` (scoped to the two supplied directories actually present in `/Users/asherlc/Downloads/models`).

## Global Constraints

- Migrate only `metolius.simulator-3d` and `soill.training-tiles`; no other board is in scope.
- Preserve existing board IDs, existing logical hold IDs and order, metadata, equipment, positions, transitions, and training behavior; add only the two source-backed Metolius #2 flat-sloper IDs required to represent supplied selectable contacts.
- Each migrated package contains exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; no PNG, raster presentation, canonical 2D `holdGeometry`, duplicate model resource, or undeclared asset remains.
- The downloaded Blender files are source inputs; the shipped USDZ and descriptor must be generated and hash-bound in the repository’s `hang-ten-board-v1` coordinate frame.
- Mesh-to-hold mappings are explicit and identity-based. Do not infer tags from pixels, positions, contours, or the old raster paths.
- Preserve source model object names and assign every body/hold mesh a validated role; allow one or more body meshes in the model descriptor/runtime and keep all body geometry nonselectable.
- Omit mounting hardware/holes and unsupported physical claims from package metadata unless already represented by the existing board metadata; this is display geometry, not manufacturing CAD.
- Keep temporary source copies, generated reports, renders, and validation artifacts below `.context/replace-rasters-with-3d-models/`; do not add them to shipped package roots.
- Do not start an HTTP server.

## File Structure

| Path | Responsibility |
| --- | --- |
| `Hangboards/metolius-simulator-3d/board.json` | Existing Metolius logical metadata plus one model-only presentation. |
| `Hangboards/metolius-simulator-3d/assets/` | Exact shipped Metolius USDZ and generated descriptor. |
| `Hangboards/soill-training-tiles/board.json` | Existing Training Tiles logical metadata plus one model-only presentation. |
| `Hangboards/soill-training-tiles/assets/` | Exact shipped Training Tiles USDZ and generated descriptor. |
| `Tools/HangboardPackages/tests/test_approved_board_packages.py` | Package-level regression coverage for the two promoted model packages, if existing assertions need extension. |
| `HangTenTests/BoardModelTests.swift` | Runtime routing/identity regression coverage for the two migrated boards, if existing assertions need extension. |
| `docs/source-audits/2026-09-11-replace-rasters-with-3d-models.md` | Source paths, hashes, explicit mapping tables, omissions, and validation evidence. |
| `.context/replace-rasters-with-3d-models/` | Owned temporary conversion inputs, outputs, reports, and cleanup records; not shipped. |

### Task 1: Convert and promote the two supplied model packages

**Files:**
- Modify: `Hangboards/metolius-simulator-3d/board.json`
- Modify: `Hangboards/soill-training-tiles/board.json`
- Modify if needed: `Tools/HangboardModels/compile_model_package.py`, `Tools/HangboardModels/model_descriptor.py`, `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`, and focused model tests to support multiple body meshes without making them selectable
- Create: `Hangboards/metolius-simulator-3d/assets/primary.usdz`, `Hangboards/metolius-simulator-3d/assets/primary.model.json`
- Create: `Hangboards/soill-training-tiles/assets/primary.usdz`, `Hangboards/soill-training-tiles/assets/primary.model.json`
- Delete: `Hangboards/metolius-simulator-3d/assets/primary.png`, `Hangboards/soill-training-tiles/assets/primary.png`
- Modify if needed: `Tools/HangboardPackages/tests/test_approved_board_packages.py`, `HangTenTests/BoardModelTests.swift`
- Create: `docs/source-audits/2026-09-11-replace-rasters-with-3d-models.md`
- Create: owned temporary artifacts below `.context/replace-rasters-with-3d-models/`

**Interfaces:** Consume `/Users/asherlc/Downloads/models/Metolius-Simulator-3D/Metolius-Simulator-3D.blend` and `/Users/asherlc/Downloads/models/Training-Tiles/Training-Tiles.blend`, their README/hold-map/validation evidence, the existing board JSON logical inventories, and the repository’s compiler/parser/runtime model contract. Produce model-only schema-v2 packages with exact `assets/primary.usdz` and generated `assets/primary.model.json` paths.

- [ ] Record source file SHA-256 values, source README/hold-map/validation hashes, source coordinate frames, and the explicit source-object-to-logical-ID mappings in the audit. The Metolius mapping must cover `hold_01_left`, `hold_01_right`, through `hold_18_center`, including new source-backed `flat-sloper-2-left` and `flat-sloper-2-right` IDs for #2; Training Tiles must cover every `hold-L-*` and `hold-R-*` mesh using the existing left/right logical IDs.
- [ ] Validate the source scene inventories and apply only explicit semantic tags in an in-memory or owned temporary copy. Reject unknown, duplicate, missing, non-mesh hold mappings, and unmapped source objects rather than guessing. Extend the compiler/descriptor/parser only as needed to retain multiple explicitly tagged body meshes; add a focused regression proving body meshes remain nonselectable.
- [ ] Compile each tagged Blender source through the documented model compiler into the exact package layout. Preserve source object names, produce descriptors from actual imported USDZ vertices, and ensure descriptor hashes match the shipped USDZ bytes.
- [ ] Update each `board.json` presentation to `media.type: "model"` with `assetPath: "assets/primary.usdz"`, `descriptorPath: "assets/primary.model.json"`, an orthographic camera, and no raster geometry or derivation. Preserve all existing logical holds and append only `flat-sloper-2-left` and `flat-sloper-2-right` with the supplied 55 mm flat-sloper metadata.
- [ ] Remove only the two migrated PNG assets after descriptor bindings cover every logical hold. Ensure each migrated package root has exactly the declared three files.
- [ ] Add or update focused package/runtime assertions for model routing, stable hold IDs/order, no PNG/image URL, descriptor/model URL resolution, complete descriptor inventory, and no regression to unrelated raster/model boards.
- [ ] Run the relevant Python package tests, the package validator with final inventory, `git diff --check`, and the focused Swift model tests/build if available. Record exact commands and results in the source audit and owned report.
- [ ] Commit the implementation and push the current branch to its remote.

**Review gate:** An independent reviewer verifies the two package inventories, exact logical identity preservation, explicit mesh mappings, descriptor/USDZ hash binding, model-only media contract, absence of raster fallback, and the reported validation evidence.

### Task 2: Final independent verification and handoff

**Files:**
- No product files unless Task 1 review identifies a concrete defect.
- Read: Task 1 source audit, package JSON/assets, test reports, and git diff.
- Create: `.context/replace-rasters-with-3d-models/final-verification.json` (owned, untracked)

**Interfaces:** Consume Task 1’s promoted packages and audit. Do not redesign geometry or alter logical metadata during verification.

- [ ] Re-run package discovery and assert both migrated packages contain exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`, with no PNG or raster media.
- [ ] Re-run model descriptor/hash/inventory validation and relevant Python tests; inspect the actual diff for unrelated board changes.
- [ ] Run the focused Swift model/package tests or the narrowest available Xcode build check and record whether the two boards resolve through `BoardModelView` without raster fallback.
- [ ] Dispatch the final whole-branch reviewer with the plan, source audit, verification report, and full branch diff; address any Critical/Important finding through a fresh implementation agent and scoped re-review.
- [ ] Push any final reviewed commit and report the pushed commit SHA.

**Review gate:** Verification evidence is fresh, the final review is clean or all residual findings have an explicit ruling, and the user receives only the requested migration result plus any concrete limitations.
