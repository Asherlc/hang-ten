# Complete Hangboard Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add all identified fixed and portable hangboard products as complete, source-backed packages with AI-simplified presentation art and correct selectable geometry.

**Architecture:** Introduce schema version 2 presentation surfaces while retaining full version 1 compatibility. A presentation chooses one AI-created simplified image and filters its physical holds; source audits retain the primary manufacturer evidence used for every product, surface, and hold decision. The app and Workbench use the selected presentation consistently, so multi-surface devices never highlight a hold over the wrong orientation.

**Tech Stack:** Python package validation, Swift/SwiftUI, TypeScript/React, XCTest, pytest, Vitest, Image Generation, iOS Simulator.

**Spec:** `docs/superpowers/specs/2026-08-20-complete-hangboard-catalog-design.md`

## Global Constraints

- Use only primary manufacturer sources for identity, inventory, measurements, and geometry decisions; record source URLs and field mappings in an audit.
- Every primary presentation asset is an AI-created simplified PNG; use official imagery only as the image-generation reference and geometry evidence.
- Never generate, detect, vectorize, crop, register, segment, or infer hold geometry from images. Draw and review every canonical path manually.
- Version 1 packages and their bytes remain valid; version 2 packages must declare every image, surface, and hold-to-surface relationship fail-closed.
- A completed package contains a full hold inventory, official-source audit, AI simplified `primary.png`, deliberately authored paths, and no unsupported facts.
- Commit each completed task, push each commit to the current remote branch, and create/update the PR only after the final review passes.

---

## File Map

| Area | Primary files | Responsibility |
| --- | --- | --- |
| Package parser | `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` | Validate and expose v1/v2 presentations and scoped holds. |
| Package tests | `Tools/HangboardPackages/tests/test_board_catalog.py`, `test_approved_board_packages.py` | Lock fail-closed v2 behavior and artifact layout. |
| App decoder | `HangTen/Models/BoardStorage.swift`, `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift` | Decode v2, validate assets, retain presentation ownership. |
| App UI | `HangTen/Views/BoardMapView.swift` and its callers | Select a presentation and draw only matching holds. |
| Workbench | `Tools/HangboardWorkbench/{board_package.py,server.py,src/*}` | Edit one presentation at a time and preserve the rest. |
| New packages | `Hangboards/<slug>/{board.json,assets/*.png}` | Complete product packages and AI illustration assets. |
| Evidence | `docs/source-audits/2026-08-20-complete-hangboard-catalog.md` | Product sources, mappings, art provenance, and visual review. |

### Task 1: Define and validate package schema version 2

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`
- Modify: `Tools/HangboardPackages/tests/{conftest.py,test_board_catalog.py,test_approved_board_packages.py,test_board_package_staging.py}`

**Interfaces:**
- Produces a `BoardPresentation(id, name, asset_path, is_default)` value and `BoardHold.presentation_id`.
- Version 1 exposes exactly one implicit `primary` presentation and assigns every hold to it.
- Version 2 requires a nonempty `presentations` array with unique identifiers, exactly one default, a declared asset for every image, and a valid presentation ID for every hold.

- [ ] Write failing parser tests for v1 compatibility, valid multi-presentation v2 documents, duplicate/default/unknown IDs, undeclared assets, and asset-path escape.
- [ ] Implement the smallest fail-closed parser and artifact validator that passes those tests.
- [ ] Update approved-package assertions to accept the declared v2 asset set while retaining the v1 primary-only invariant.
- [ ] Run `rtk pytest Tools/HangboardPackages/tests -q`.
- [ ] Commit and push the task.

### Task 2: Decode and render presentation surfaces in the iOS app

**Files:**
- Modify: `HangTen/Models/{BoardStorage.swift,BoardPackageStore.swift,TrainingModels.swift}`
- Modify: `HangTen/Views/BoardMapView.swift` and affected callers
- Modify: `HangTenTests/{BoardPackageStoreTests.swift,BoardSourceBoundaryTests.swift,BoardMapViewTests.swift}` or create a focused board-presentation test file

**Interfaces:**
- Consumes Task 1’s v2 document shape.
- Produces `TrainingBoard.presentations`, `BoardHold.presentationID`, and `presentationImageURL(for:presentationID:)`.
- `BoardMapView` defaults to the board default presentation and filters both image and tap/highlight paths to it.

- [ ] Write failing XCTest cases for v1 fallback, v2 asset loading, malformed presentation documents, and image/hold filtering.
- [ ] Implement decoding, asset containment/PNG/aspect validation, and presentation-aware model conversion.
- [ ] Add a minimal accessible presentation selector only where a board has multiple presentations; keep current callers source-compatible.
- [ ] Run targeted XCTest and a bounded simulator build.
- [ ] Commit and push the task.

### Task 3: Add presentation-aware Workbench editing

**Files:**
- Modify: `Tools/HangboardWorkbench/{board_package.py,server.py,github_board_store.py}` as required
- Modify: `Tools/HangboardWorkbench/src/{types.ts,WorkbenchApp.tsx,useWorkbench.ts,workbench-client.ts,workbench-controller.ts}` and presentation-related components
- Modify: related Python, Vitest, and React harness tests

**Interfaces:**
- Consumes Task 1’s v2 package format.
- Presents one selectable surface canvas at a time, filters its regions, and creates holds scoped to that surface.
- Saving must preserve the selected surface ID and all unselected holds and assets.

- [ ] Write failing server/controller/UI tests for listing surfaces, switching canvas images, filtering regions, adding a scoped hold, and lossless preservation on save.
- [ ] Implement the focused surface selector and the minimal protocol changes required to support it.
- [ ] Run the affected Python and TypeScript test suites.
- [ ] Commit and push the task.

### Task 4: Package Metolius Foundry Training Board

**Files:**
- Create: `Hangboards/metolius-foundry/{board.json,assets/primary.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`
- Create: focused package test if a model-specific invariant is needed

- [ ] Gather the official product page, front/oblique/hold-depth images, and manual; record each mapping before authoring.
- [ ] Generate and inspect a simplified AI primary illustration using the official front view as a reference input; record its prompt and source role in the audit.
- [ ] Freeze the contact inventory, manually author every path against the accepted illustration and official evidence, and validate the complete package.
- [ ] Add targeted test coverage where ordinary catalog validation cannot protect the model-specific inventory.
- [ ] Commit and push the task.

### Task 5: Package Metolius Prime Rib

**Files:**
- Create: `Hangboards/metolius-prime-rib/{board.json,assets/primary.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`

- [ ] Repeat Task 4’s evidence, AI-primary-art, direct-path, validation, and audit workflow for the three documented edges.
- [ ] Commit and push the task.

### Task 6: Package Metolius Wood Grips II Deluxe

**Files:**
- Create: `Hangboards/metolius-wood-grips-deluxe-ii/{board.json,assets/primary.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`

- [ ] Establish the Deluxe-specific source inventory separately from the existing Compact II package; do not inherit geometry or measurements from Compact.
- [ ] Generate the AI simplified primary, directly author and review complete Deluxe geometry, validate, audit, commit, and push.

### Task 7: Package The Hangboard

**Files:**
- Create: `Hangboards/the-hangboard/{board.json,assets/primary.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`

- [ ] Use the manufacturer’s current product page and gallery as the only evidence; source every labelled edge, jug, and sloper decision.
- [ ] Generate the AI simplified primary, directly author all contacts, validate, audit, commit, and push.

### Task 8: Package Tension Flash Board

**Files:**
- Create: `Hangboards/tension-flash-board/{board.json,assets/*.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`

- [ ] Gather official evidence for each usable cylindrical orientation and map its distinct contacts to v2 presentations.
- [ ] Generate one accepted simplified AI illustration per represented surface, retaining `primary.png` for the default surface.
- [ ] Directly author all documented contacts, validate the v2 package, audit, commit, and push.

### Task 9: Package Metolius Light Rail 2.0

**Files:**
- Create: `Hangboards/metolius-light-rail-2/{board.json,assets/*.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`

- [ ] Use the official reversible-device evidence and manual to identify each usable face, not merely the front marketing shot.
- [ ] Generate surface-specific AI simplified illustrations; directly author and verify every distinct contact per face.
- [ ] Validate, audit, commit, and push.

### Task 10: Package Metolius Rock Rings 3D

**Files:**
- Create: `Hangboards/metolius-rock-rings-3d/{board.json,assets/*.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`

- [ ] Establish separate left/right suspended-device geometry from primary evidence; use only supported symmetry.
- [ ] Generate the AI simplified primary/supplementary surface illustrations, author every contact, validate, audit, commit, and push.

### Task 11: Package YY Vertical portable devices

**Files:**
- Create: `Hangboards/yy-{travelboard,baguette,baguette-evo,penta-evo}/{board.json,assets/*.png}`
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`

- [ ] Treat TravelBoard, The Baguette, Baguette Evo, and Penta Evo as four independent products with source mapping and inventory freeze per model.
- [ ] For each product, generate the required AI simplified primary and additional surface images, then directly author paths and constraints from manufacturer evidence.
- [ ] Validate every package in the final inventory, audit, commit, and push.

### Task 12: Visual review and catalog integration

**Files:**
- Modify: `docs/source-audits/2026-08-20-complete-hangboard-catalog.md`
- Modify: focused package/app tests only if the review reveals a regression

- [ ] Run package final-inventory validation and staging tests.
- [ ] Use `validate-hang-ten-ios` to build, install, launch, and inspect every new presentation on an owned simulator; verify normal, active, and hit-test alignment against the accepted illustration and source audit.
- [ ] Record per-package/per-surface review results and remedy every defect through a scoped follow-up task.
- [ ] Run the complete relevant Python, TypeScript, XCTest, and build verification set.
- [ ] Commit and push any verification-driven fixes.

### Task 13: Whole-branch review and PR

**Files:**
- No planned product changes; reviewer findings determine scoped follow-up files.

- [ ] Dispatch a fresh high-reasoning reviewer with the whole diff, spec, plan, audit, and verification evidence.
- [ ] Resolve every load-bearing finding with one scoped implementation task and re-review.
- [ ] Re-run the final validation set, commit/push the final state, then create or update a GitHub PR for the current branch.
