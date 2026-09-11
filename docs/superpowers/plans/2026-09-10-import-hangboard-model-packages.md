# Import Hangboard Model Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the four supplied 3D hangboard packages, replace the raster presentations for the three exact catalog matches, add the standard Nature Stone Hanger as a new model-only board, and integrate the requested two-branch cord support.

**Architecture:** Keep logical board metadata in `board.json` and make each migrated package model-only with one USDZ and one generated descriptor. Reuse the existing model-first compiler/parser/SceneKit bridge, selectively port the hardened suspension contract and solver from `origin/load/3d-hangboard-models`, and bind package mesh names to stable app hold IDs through explicit mappings.

**Tech Stack:** Blender/USDZ, Python package validators and compiler, Swift/SceneKit/XCTest, existing board staging scripts, and the supplied ZIP evidence/manifests.

**Spec:** `docs/superpowers/specs/2026-09-10-import-hangboard-model-packages-design.md`

## Global Constraints

- Three replacements preserve their existing board IDs, hold IDs, metadata, and saved workout target identities.
- The Nature package is a new `nature-stone-hanger` board; it must not overwrite Stoak Board III or either Stone Hanger Mini package.
- Every migrated package contains exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; no PNG, canonical 2D `holdGeometry`, duplicate app resource, or undeclared asset remains.
- Supplied GLB/Blend files are source inputs; shipped USDZ bytes and descriptors are generated/validated in the repository’s `hang-ten-board-v1` frame with exact hash binding.
- Mesh-to-hold mappings are explicit and reviewed. No image tracing, segmentation, automatic contouring, positional inference, or 2D-path reuse is allowed.
- Nature uses the supplied eight contact IDs and two cord-passage markers. Hidden cord routing, hardware, mounting holes, logos, and unsupported physical claims remain omitted or explicitly unknown.
- Cord support is selectively ported from `origin/load/3d-hangboard-models`; unrelated Flash Board geometry/content is not imported.
- Owned generated output, source archives, reports, renders, and simulator resources live below `.context/import-hangboard-model-packages/`; every external resource has an owner record and cleanup trap.
- Do not start an HTTP server.

## File Structure

| Path | Responsibility |
| --- | --- |
| `.context/import-hangboard-model-packages/` | Owned ZIP extracts, source manifests, mappings, conversion output, reports, renders, and cleanup records. |
| `Tools/HangboardModels/import_model_package.py` | Deterministic manifest-driven source-package import/conversion entry point wrapping the existing compiler. |
| `Tools/HangboardModels/verify_imported_model_packages.py`, `test_import_model_package.py` | Validate ZIP mapping, exact export inventory, material/bounds/hash contracts, and actual USDZ reimport. |
| `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` | Parse/validate any Nature suspension metadata and model-only package inventory. |
| `HangTen/Models/TrainingModels.swift` | Model/suspension value types and stable board identity routing. |
| `HangTen/Models/BoardPackageStore.swift` | Swift package decode/validation for model and two-branch suspension metadata. |
| `HangTen/Views/BoardModelView.swift`, `HangTen/Views/BoardMapView.swift`, `HangTen/Views/SuspendedBoardPresentation.swift` | Model rendering, highlighting, and transient two-branch cord presentation. |
| `HangTenTests/*`, `Tools/HangboardPackages/tests/*` | Cross-language parser, runtime, picking, and package-boundary regressions. |
| `Hangboards/metolius-simulator-3d/`, `Hangboards/soill-training-tiles/`, `Hangboards/yy-baguette-evo/`, `Hangboards/nature-stone-hanger/` | Final model-first board packages. |
| `docs/source-audits/2026-09-10-imported-model-packages.md` | Source ZIP hashes, explicit mappings, omissions, unresolved claims, and validation evidence. |

### Task 1: Port and characterize the requested two-branch cord contract

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`, `HangTen/Models/TrainingModels.swift`, `HangTen/Models/BoardPackageStore.swift`
- Modify: `HangTen/Views/BoardModelView.swift`, `HangTen/Views/BoardMapView.swift`
- Create or modify: `HangTen/Views/SuspendedBoardPresentation.swift`, `HangTenTests/SuspendedBoardPresentationTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`, `Tools/HangboardPackages/tests/test_model_first_packages.py`

**Interfaces:** Port only the reusable contract and solver behavior from `origin/load/3d-hangboard-models` at commits `b488bab3` through `d925e863`, preserving the current branch’s model-only behavior and existing single-cord compatibility. The two-branch type must represent two named passage pairs, ordered branch paths, one shared invisible anchor, finite canonical poses, and explicit unavailable-state errors.

- [ ] Inspect the remote branch diff and identify the smallest commit/file set that supplies parser parity, deterministic solving, branch closure/self-intersection validation, and SceneKit cord rendering.
- [ ] Add characterization fixtures for repeated endpoints, non-closure paths, invalid branch order, impossible lengths, nonfinite values, self-intersection, and one valid two-branch package.
- [ ] Port the contract and solver without importing Flash Board board IDs, geometry, assets, or unrelated plan content.
- [ ] Run focused Python and Swift tests; record exact results in `.context/import-hangboard-model-packages/cord-contract-report.json`.
- [ ] Commit and push: `feat: support two-branch hangboard cords`.

**Review gate:** A fresh reviewer confirms that single-cord/model-only packages remain unchanged, the strict two-branch contract rejects malformed data, and no Flash Board-specific resource was imported.

### Task 2: Import, convert, and verify the four supplied model sources

**Files:**
- Create: `Tools/HangboardModels/import_model_package.py`
- Create: `Tools/HangboardModels/verify_imported_model_packages.py`, `Tools/HangboardModels/test_import_model_package.py`
- Create: `.context/import-hangboard-model-packages/source-manifest.json`, `mappings/*.json`, `converted/*`, `reports/*`

**Interfaces:** Consume the four ZIP files in `/Users/asherlc/Downloads/models`. Produce deterministic USDZ/descriptor candidates and explicit mesh-to-logical-ID mappings for Metolius, Training Tiles, Baguette Evo, and Nature Stone Hanger. Preserve package object names and reject unknown or duplicate mappings.

- [ ] Record each ZIP SHA-256, retained README/manifest/hold-map/integration hashes, source model file, coordinate frame, and package validation result under the owned context directory.
- [ ] Exercise the existing Blender compiler against each supplied `.blend` source, then implement the manifest-driven adapter as a thin self-bootstrapping wrapper around the compiler. The wrapper must fail with a named mapping error when a source scene lacks the required tags; it must not infer tags from pixels or positions.
- [ ] Write explicit mappings: Metolius `hold_01_*`–`hold_18_center` to current `jug-*`, `round-sloper-*`, `edge-*`, and `pocket-*`; Training Tiles `hold-L/R-*` to current left/right logical IDs; Baguette IDs to existing `edge-*`/`rounded-tray`; Nature eight supplied contact IDs to its new board IDs.
- [ ] Validate actual USDZ reimport with source images/materials removed, all meshes assigned to body/hold/attachment roles, descriptor hash/bounds/centers, positive triangles, and native material payloads. Keep cord passages nonselectable.
- [ ] Run focused importer/verifier tests and retain reports/renders; do not promote a candidate with incomplete mapping or unavailable native material data.
- [ ] Commit and push: `feat: import supplied hangboard model packages`.

**Review gate:** Reviewer checks every ZIP field is preserved or explicitly rejected, mappings are identity-based rather than positional, and actual exports—not only source Blend/GLB files—pass inventory and material checks.

### Task 3: Create the four final model-only board packages and source audit

**Files:**
- Modify: `Hangboards/metolius-simulator-3d/board.json`, `Hangboards/soill-training-tiles/board.json`, `Hangboards/yy-baguette-evo/board.json`
- Create: `Hangboards/nature-stone-hanger/board.json`
- Create: each package’s `assets/primary.usdz` and `assets/primary.model.json`
- Delete: the three migrated packages’ `assets/primary.png` and any migrated canonical 2D geometry members
- Create/modify: `docs/source-audits/2026-09-10-imported-model-packages.md`

**Interfaces:** Consume Task 2’s verified exports/mappings and preserve the existing logical hold metadata for the three replacements. The Nature board uses its package-backed identity, `105 × 105 × 35 mm`, oak/granite material notes, eight edge contacts, two cord markers, and explicit display-estimate/unknown boundaries.

- [ ] Build each `board.json` as schema v2 with one original model presentation, orthographic camera, descriptor path, and no raster media. Preserve logical order and IDs exactly for the three replacements.
- [ ] Add Nature’s eight logical holds and two nonselectable passage metadata entries through the established suspension contract; do not create unsupported extra pinch/jug/hold IDs.
- [ ] Copy only the exact verified USDZ and generated descriptor into each `assets/` directory; ensure package roots contain no source, render, evidence, or ZIP files.
- [ ] Remove legacy PNGs and 2D geometry only after descriptor bindings cover every logical hold; do not delete unrelated presentations from other boards.
- [ ] Record source URLs/hashes from the ZIP evidence, model hash, mapping table, deliberate omissions, and unresolved source claims in the audit.
- [ ] Run `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` and the model package tests.
- [ ] Commit and push: `feat: promote imported boards to model packages`.

**Review gate:** Reviewer verifies exact package trees, no raster/model mixing, stable IDs/order, complete descriptor bindings, and no source-backed claim copied from another Nature product.

### Task 4: Integrate Nature’s suspended presentation and preserve app routing

**Files:**
- Modify: `HangTenTests/BoardModelTests.swift`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:** Wire the new Nature ID and two-branch profile into existing board lookup and model presentation. The cord is transient display geometry, does not become a selectable node or accessibility element, and uses the package’s two external passage branches with unknown hidden route.

- [ ] Add focused tests for catalog lookup, default model presentation, stable hold identity, native highlighting/clear behavior, passage nonselectability, and explicit unavailable state in `HangTenTests/BoardModelTests.swift`.
- [ ] Consume Task 1's deterministic canonical pose/camera contract and add Nature-specific catalog assertions without duplicating solver tests.
- [ ] Confirm board-specific workout plans continue resolving existing Metolius and Baguette/Training Tiles hold IDs; no training prescription is invented for Nature.
- [ ] Run the focused XCTest/build checks and fix only integration defects, routing geometry/fidelity issues back to the geometry/package task.
- [ ] Commit and push: `feat: integrate Nature suspended model presentation`.

**Review gate:** Reviewer checks identity changes, accessibility/picking boundaries, no raster fallback, and no regression in existing model/raster board routing.

### Task 5: Final validation, visual review, and handoff

**Files:**
- Modify: `docs/source-audits/2026-09-10-imported-model-packages.md`, `Tools/HangboardModels/verify_imported_model_packages.py`
- Create: `.context/import-hangboard-model-packages/final-report.json`, visual review images, and command logs

- [ ] Run the package validator, Python model/compiler tests, Swift model/package tests, and a bounded iOS simulator build using the repository’s isolated-device validation workflow.
- [ ] Reimport every shipped USDZ, verify exact descriptor hash, body/hold/material inventory, nearest-triangle picking, and explicit absence of 2D fallback assets.
- [ ] Review front, oblique, clay/detail, and selected-highlight renders for all four boards. Record any material or framing issue; route physical-fidelity defects to the geometry owner rather than masking them with camera/light changes.
- [ ] Review the final diff against this plan and spec, run `git diff --check`, and ensure owned generated resources have cleanup records and no shared resource was removed.
- [ ] Commit and push final audit/test adjustments: `test: validate imported hangboard model packages`.

**Review gate:** Dispatch the broad final reviewer with the spec, plan, base SHA, and final SHA. Resolve all critical/important findings before claiming completion.
