# Lean Parallel Two-Board 3D Delivery Delta Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Amend the three existing 2026-09-08 model-first plans into a parallel delivery that keeps both target boards, completes the generic bundled 3D runtime and two-board model migration, and leaves only remote sync and editor support as explicit follow-up work.

**Architecture:** Treat the existing schema/compiler/parser contracts and runtime media-aware matching (runtime Task 1) as the baseline. Run the generic runtime scene/cache and unavailable-state work (Tasks 2 and 3) concurrently with Luna’s two-board evidence lane and Astra’s Beastmaker/Compact geometry lane; converge at package promotion, exact native contract checks, focused simulator validation, and documentation. This is a delta plan: the three 2026-09-08 plans remain intact historical plans and this file records their approved scope/order amendment.

**Tech Stack:** Swift/SwiftUI, SceneKit, Foundation/CryptoKit, XCTest, Python package validators, Blender 5.2 compiler/exporter, USDZ, Xcode iOS Simulator, existing package staging scripts, and source-audit documentation.

**Spec:** `docs/superpowers/specs/2026-09-08-beastmaker-1000-3d-design.md`

## Global Constraints

- Keep exactly `beastmaker-1000` and `metolius.wood-grips-compact-ii`; do not migrate another board.
- Preserve every existing logical board/hold ID, logical metadata, equipment, positions, transitions, and training behavior. `BoardHold` remains logical; render geometry never moves into hold metadata.
- Use schema v2 tagged media and descriptor v1 from the completed schema/compiler work: `media.type`, `assetPath`, `descriptorPath`, `modelSHA256`, `hang-ten-board-v1`, and `facePlaneAABB` retain their exact meanings.
- A model is the sole source of rendering, highlighting, picking, and display-derived matching geometry. Cache keys are `(boardID, presentationID, modelSHA256)`; USDZ node matching is exact and body nodes are not selectable.
- Model failure is fail-closed generic unavailable UI with no PNG/raster fallback, inferred scene, partial interaction, axis guessing, node-name normalization, derived model, or inverted model presentation.
- Use primary manufacturer evidence first. Authorized commerce evidence can fill a documented first-party gap only; search snippets, reviews, forums, and AI summaries are discovery/corroboration, never sole authority.
- Human approval of both evidence briefs precedes geometry. Astra alone authors or corrects physical geometry; lower-cost workers may compile, package, integrate, test, and document but must route visual-fidelity defects to Astra.
- Geometry is display geometry, not manufacturing CAD. Use generic original wood where approved; omit screws, mounting holes, countersinks, hardware, logos, and other non-contact decorations. Do not trace, segment, vectorize, align, crop, or extrude raster paths.
- Keep all durable evidence, source snapshots, hashes, `.blend` files, review renders, and reports under owned `.context/shaky-rat-*` directories. Do not commit those generated evidence directories. Clean only exact ephemeral resources created by the owning worker.
- The active implementation must preserve unrelated worktree edits. At planning time `HangTen/Views/BoardModelView.swift` and `HangTenTests/BoardModelTests.swift` are modified; implementation workers must inspect and integrate those changes rather than overwrite them.

## Scope amendment and deferred backlog

Both target boards remain in scope. “Deferred” means the work is not deleted from the original runtime plan; it is retained as a named follow-up backlog item and is not a prerequisite for this delivery.

| Original runtime task | Decision now | Explicit limitation in this delivery |
| --- | --- | --- |
| Task 4 — GitHub in-app package sync | Defer | `GitHubBoardSyncService` continues to be PNG/default-asset oriented. The completed feature does not pull remote USDZ/descriptor assets or claim remote model packages are supported. Bundled and locally staged package assets are the supported source. |
| Task 5 — iOS editor support | Defer | No iOS model editing, model-to-raster reconstruction, or model-package writer support is added. Existing raster editing remains the editable path; model packages are display/runtime content only for this delivery. |
| Task 6 — Workbench editor support | Defer | No Workbench model editor, USDZ import, or generated 2D paths is added. Workbench’s existing raster workflow remains the editable path; model editing is explicitly unavailable until the follow-up. |

The deferred tasks retain their original file/interface proposals for a later plan. Do not delete them from `docs/superpowers/plans/2026-09-08-package-driven-3d-runtime-and-tools.md` or rewrite the two other 2026-09-08 plans to hide the deferral.

## Completed baseline and dependency graph

The following are prerequisites, not new work in this delta:

- Schema/compiler plan contracts and their parser/package work are in git history, including schema v2 typed raster/model media, descriptor v1, exact declared-asset validation, and byte-preserving staging behavior.
- Runtime Task 1, `BoardHold.resolvedFrame(in:)` and media-aware workout matching, is complete and approved by `5edccbf4` (`docs: approve runtime task 1`) after `e1e53c19` (`feat: resolve board matching geometry from media`). Do not reimplement it or turn it back into a sequential dependency on the editor/sync tasks.
- Target package promotion and generated model artifacts are not assumed complete. The implementation must prove them during the model lane and convergence gates below.

The amended graph is:

```
Completed schema/compiler/parser baseline + runtime Task 1
             |
       +-----+----------------------------------+
       |                                        |
       v                                        v
R2 generic SceneKit model/cache          E1 Luna evidence packets
       |                                        |
       v                                        v
R3 exhaustive map/unavailable UI       human evidence approval
       |                                        |
       +--------------------------+             v
                                  |      G1 Astra Beastmaker +
                                  |         Compact reuse gate
                                  |             |
                                  +-------------v
                                  M1 compile/reimport/package both
                                  |
                                  v
                         R7 native runtime contract
                                  |
                                  v
                   V1 focused build/simulator visual interaction
                                  |
                                  v
                         D1 docs/source audit/skill
```

R2 and R3 are the active runtime core (original Tasks 2 and 3) and run in parallel with E1 and G1/M1. R3 depends on R2. M1 can compile/package as soon as evidence approval and geometry/source gates pass; it does not wait for the deferred sync or editors. R7 waits for R2, R3, M1, and the parser baseline because it verifies the actual two-board package assets. V1 and D1 are convergence work.

## File and interface map

The original plans remain the detailed historical source. The following map narrows the active delta to exact files and contracts.

### Runtime lane (original Tasks 2, 3, and 7; Task 1 complete)

| Slice | Files | Required interfaces and behavior |
| --- | --- | --- |
| R2 — generic model scene/cache | Modify `HangTen/Views/BoardModelView.swift`; test `HangTenTests/BoardModelTests.swift` | Provide `BoardModelKey(boardID: String, presentationID: String, modelSHA256: String)`, `BoardModelAsset.load(media: BoardModelMedia, packageURL: URL) -> SCNScene?`, `BoardModelScene.init?(source:descriptor:)`, `BoardModelScene.geometryNodes`, `BoardModelLoader.load(board:presentation:store:)`, and `.loading/.ready/.unavailable` surface states. Bind exact descriptor node IDs, clone scene/materials per view, reject missing materials/unbound geometry/body selection, preserve native `SCNTransaction.flush()` picking, and remove board registries/static model paths. |
| R3 — map/unavailable state | Modify `HangTen/Views/BoardMapView.swift` and `HangTen/Views/BoardModelView.swift`; test `HangTenTests/BoardModelTests.swift` and `HangTenUITests/OwlClimbPokerBoardMapInteractionUITests.swift` | Exhaustively switch `BoardPresentationMedia`: existing raster surface for raster; generic SceneKit surface for valid model; `BoardModelUnavailableView` with accessibility identifier `boardModel.unavailable` and no selectable elements for invalid/missing model. Never pass an image/raster closure into the model failure branch. |
| R7 — integration/native contract | Modify `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`, and, only when tracked paths change, `HangTenTests/BoardSourceBoundaryTrackedPaths.txt` | Exercise package-local USDZ + descriptor, exact hash, exact node inventory, all 22/19 logical contacts, native nearest-hit rays, body nil-hit, material presence, cache separation by SHA, scene/camera rebind, unavailable state, and no model image URL. No board-specific renderer branch or standalone `HangTen/Resources/BoardModels` dependency. |

### Two-board evidence/geometry/package lane

| Slice | Files/artifacts | Required interfaces and behavior |
| --- | --- | --- |
| E1 — evidence | Create owned `.context/shaky-rat-beastmaker-1000/{ownership.json,evidence-packet.json,evidence-brief.md,astra-handoff.md,references/*}` and `.context/shaky-rat-metolius-wood-grips-compact-ii/{ownership.json,evidence-packet.json,evidence-brief.md,references/*}`; modify `docs/source-audits/2026-08-12-beastmaker-board-packages.md` | Produce packets accepted by `validate_evidence_packet.py`. Record exact manufacturer URLs/snapshots/hashes, revision/date/locale, source-backed logical inventory (22 and 19), qualified conflicts, unknowns, omissions, material fidelity, and required front/three-quarter/clay-detail views. No geometry proposals or image-derived contours. Stop for human approval of both briefs/media before G1. |
| G1 — geometry | Create `Tools/HangboardModels/beastmaker_1000.py` and owned Beastmaker `.blend`/renders/reports; use `Tools/HangboardModels/wood_grips_compact_ii.py` unchanged unless approved visual-fidelity review identifies a defect | Astra alone authors authoritative Beastmaker geometry in `hang-ten-board-v1`, preserving all 22 IDs, sourced 580 × 150 mm face, qualified 58 mm depth, generic pale wood, and no hardware. Reuse the existing Compact II source for its 19 IDs; only an observed physical-fidelity defect is sent to Astra, who alone corrects it. Human visual approval is mandatory; inventory approval is not fidelity approval. |
| M1 — compile/package/promote | Create/modify `Tools/HangboardModels/verify_beastmaker_1000.py`, `Tools/HangboardModels/verify_wood_grips_compact_ii.py`, `Tools/HangboardModels/test_model_reports.py`, `Tools/HangboardModels/README.md`; modify both target `board.json`; create both target `assets/primary.usdz` and `assets/primary.model.json`; delete both target `assets/primary.png` and `HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz`; modify `HangTen.xcodeproj/project.pbxproj` and `HangTenTests/BoardSourceBoundaryTrackedPaths.txt` if required | Lower-cost compiler/package workers consume only approved source and current logical inventory. Reimport actual exports; verify bounds, triangles, materials, exact node IDs, 22/19 bindings, generated descriptor hash, and no hardware. Promote exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json` per target; remove the standalone Compact resource/reference only when no tracked member remains. Do not hand-edit descriptors or redesign shape. |

### Convergence documentation lane

D1 modifies `docs/source-audits/2026-08-12-beastmaker-board-packages.md`, `Tools/HangboardModels/README.md`, and `README.md` for final provenance, package shape, hashes, approval, and limitations. It modifies `.codex/skills/migrate-hangboard-to-3d/SKILL.md` last, only to codify behavior demonstrated by the completed delivery. It must not describe deferred sync/editor behavior as implemented.

## Executable task gates

### Task R2: generic SceneKit model scene and cache

**Files:** `HangTen/Views/BoardModelView.swift`; `HangTenTests/BoardModelTests.swift`.

**Interfaces:** `BoardModelKey`, `BoardModelAsset.load`, `BoardModelScene.init?(source:descriptor:)`, `BoardModelLoader.load(board:presentation:store:)`, and `BoardModelSurface` states as listed in the runtime map.

- [ ] Write failing tests for exact descriptor node binding, cache-key separation by SHA, body non-selection, material cloning, and an invalid model producing `.unavailable`.
- [ ] Run `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests`; expected failure is absent generic binding/cache behavior, not a fixture that bypasses package loading.
- [ ] Implement only generic package-owned loading. Obtain URLs through `BoardPackageStore`; traverse exact ancestor names joined by `/`; require descriptor/model node-set equality, hold IDs, materials, vertex sources, and nonselectable body; preserve `SCNTransaction.flush()` before native picking and current highlight restoration/accessibility behavior.
- [ ] Re-run the focused test target and require PASS for exact IDs, cache isolation, all semantic states, and nearest-hit behavior. Commit with `feat: render package-owned board models`; a fresh review gate rejects any board ID conditional, fallback asset, name normalization, or compiler-side shape repair.

### Task R3: exhaustive media map and unavailable UI

**Files:** `HangTen/Views/BoardMapView.swift`, `HangTen/Views/BoardModelView.swift`, `HangTenTests/BoardModelTests.swift`, `HangTenUITests/OwlClimbPokerBoardMapInteractionUITests.swift`.

**Interfaces:** `BoardPresentationMedia`, `BoardModelSurface`, and `BoardModelUnavailableView` with accessibility identifier `boardModel.unavailable` and `permitsHoldSelection == false`.

- [ ] Add failing assertions that invalid model media selects `.unavailable`, exposes no selectable holds, and never evaluates a PNG/image fallback.
- [ ] Run the focused BoardModel XCTest command from R2; expected failure is the missing unavailable state.
- [ ] Implement the exhaustive raster/model switch. Keep raster rendering/taps unchanged, route valid model media to R2, and render generic unavailable text for missing/invalid model media without an image URL or raster callback.
- [ ] Run `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenUITests/OwlClimbPokerBoardMapInteractionUITests`; require PASS. Review verifies display-only model surfaces do not intercept parent touches and invalid models are never partially interactive. Commit with `feat: surface unavailable package models`.

### Task E1: Luna primary-source evidence and human approval

**Files:** owned packet trees listed above; `docs/source-audits/2026-08-12-beastmaker-board-packages.md`.

**Interfaces:** `validate_evidence_packet(packet_path: Path) -> EvidencePacket` and the exact packet fields `boardRevision`, `boardRevisionDate`, `locale`, `primarySources`, `commerceSources`, `logicalInventory`, `sourcedClaims`, `conflictsAndRulings`, `unknownsForAstra`, `deliberateOmissions`, `materialFidelity`, and `requiredReviewViews`.

- [ ] Write negative packet fixtures at `.context/shaky-rat-beastmaker-1000/rejected-snippet-packet.json` and `.context/shaky-rat-metolius-wood-grips-compact-ii/rejected-retailer-packet.json`; run `rtk proxy python3 -B Tools/HangboardModels/validate_evidence_packet.py .context/shaky-rat-beastmaker-1000/rejected-snippet-packet.json` and the equivalent Compact path, requiring exit 1 with the source-snapshot error.
- [ ] Gather and hash actual manufacturer pages/media for both boards, record authorized-commerce gaps only when needed, validate both approved packets with two explicit CLI invocations, and require exit 0 for each.
- [ ] Record Beastmaker’s sourced 580 × 150 mm face, qualified 58 mm depth ruling and current Tulipwood `5 mm` conflict; record Compact’s current Metolius evidence, 610 × 157 mm dimensions, lower Compact diagram, and qualified 56 mm display thickness. Keep all 22/19 stable IDs and explicitly omit hardware.
- [ ] Present both briefs and matched official media for human evidence approval. Do not dispatch G1 before approval. Commit only the source audit with `docs: record model migration evidence rulings`; fresh Sol review checks every source claim has an actual retained snapshot/hash and neither packet nor handoff proposes geometry.

### Task G1: Astra geometry and lower-cost source reuse gate

**Files:** `Tools/HangboardModels/beastmaker_1000.py`; owned Beastmaker `.blend`, source/estimate report, front/three-quarter/clay-detail renders; existing `.context/shaky-rat-metolius-wood-grips-compact-ii/wood-grips-compact-ii.blend`; `Tools/HangboardModels/wood_grips_compact_ii.py` only for an approved physical defect.

**Interfaces:** Astra consumes only the human-approved Beastmaker packet/brief and logical inventory; it emits tagged `role=body`/`role=hold` meshes with canonical `hold_id` values. Compact emits the existing approved tagged source unless visual review proves a physical defect.

- [ ] Write the geometry/report expectations before authoring: Beastmaker 22 IDs, exact frame, no hardware, source-versus-estimate separation, and required review views.
- [ ] Run the existing negative compiler fixture to prove unknown IDs are rejected before any export; do not retain a proposed shape as evidence.
- [ ] Have Astra directly author Beastmaker’s display silhouette, recesses, jugs, and slopers from approved evidence; use symmetry only where physically present, generic pale wood, and no raster tracing. Reuse Compact source unchanged unless a human-approved comparison identifies a physical defect, then route only that correction to Astra.
- [ ] Render front, three-quarter, clay-detail, and contact overview views; record human approval or a concrete defect in the owned source-versus-estimate report. A fresh reviewer checks that lower-cost workers did not author or alter physical shape.

### Task M1: compile, reimport, package, and promote both targets

**Files:** exact M1 file set in the file map.

**Interfaces:** `compile_model_package(blend_path, board_json_path, output_directory) -> ModelDescriptorV1`; `verify_beastmaker_1000.py`; `verify_wood_grips_compact_ii.py`; package media fields `assetPath: "assets/primary.usdz"`, `descriptorPath: "assets/primary.model.json"`, `derivation.type: "original"`, and orthographic `display.camera`.

- [ ] Add failing report assertions for 22/19 hold IDs, no hardware meshes, exact node bindings, material presence, and descriptor SHA-256 equality.
- [ ] Run `rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py`; expected failure is missing target report registration before implementation.
- [ ] Compile/reimport Beastmaker from the approved `.blend`, requiring 580 × 150 × 58 mm display bounds within 0.000001 m, exact 22 IDs, explicit triangles, materials, and no hardware. Compile/reimport Compact from the existing source, requiring exact 19 IDs and the same checks; if and only if visual fidelity fails, return to G1/Astra.
- [ ] Promote generated bytes to both package-local `assets/` directories, update only presentation media while preserving logical metadata, remove both PNGs and the standalone Compact USDZ/resource reference, and validate exact package trees with `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`.
- [ ] Run focused model report/package tests, commit with `feat: migrate Beastmaker and Compact packages to models`, and use a fresh Sol review gate to verify descriptors are generated, hashes bind actual bytes, and no fallback survives.

### Task R7: actual package runtime integration and native contract verification

**Files:** `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`, and source-boundary manifest only if needed.

**Interfaces:** `BoardPackageStore.presentationAssetURL(for:presentationID:)`, `presentationDescriptorURL(for:presentationID:)`, `BoardModelLoader.load`, `BoardHold.resolvedFrame(in:)`, and actual package-local USDZ/descriptor bytes.

- [ ] Add tests that load both target packages through the generic store, assert descriptor hash equality, set equality of descriptor nodes and logical IDs (22 + 19), material presence, body nil-hit, and nearest-hit for every contact after `SCNTransaction.flush()`.
- [ ] Add negative tests for stale/missing descriptor and missing model bytes; require `boardModel.unavailable`, no image URL, and no selectable elements. Add cache separation for same board/presentation with different model SHA and scene/camera rebind.
- [ ] Run `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests`; require PASS on actual package assets, not fake node-name fixtures.
- [ ] Run `rtk scripts/verify-board-source-boundary-manifest.sh`; commit with `test: verify package-driven model runtime`. Fresh Terra review rejects a standalone resource, board-specific branch, or model-to-PNG fallback.

### Task V1: focused build and simulator visual interaction validation

**Files:** generated then cleaned simulator manifests, `.context/DerivedData`, screenshots/validation report under owned `.context`; modify `docs/IOS_SIMULATOR_VALIDATION.md` only if a demonstrated route changes.

**Interfaces:** exact `Hang Ten Paseo shaky-rat Review` simulator UUID in `HANG_TEN_TEST_DEVICE_UDID`; package-local model presentation and `boardModel.unavailable` accessibility state.

- [ ] Read `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` to EOF before simulator work. Install the resource-cleanup trap before creating or reusing the exact workspace-named simulator; record pending then owned manifests.
- [ ] Run the focused build/install/launch route using `-destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID"`, never `booted`, and use `.context/DerivedData`.
- [ ] For both boards inspect front/oblique normal, preview highlight, active highlight, clear/restored, portrait, and landscape. Tap all 41 contacts (22 + 19), verify logical labels and nearest-hit selection, verify body/display-only surfaces do not intercept touches, and verify a corrupted fixture yields `boardModel.unavailable` without raster fallback. Record screenshot names/checksums and reviewed states.
- [ ] Run the R7 focused XCTest group on the same UUID, then archive/delete only the exact owned simulator and ephemeral DerivedData. Re-query absence and verify manifests; retain durable evidence. Fresh Terra review compares screenshots to actual package bytes and routes only visual defects to Astra.

### Task D1: documentation, source audit, and demonstrated skill closeout

**Files:** `README.md`, `Tools/HangboardModels/README.md`, `docs/source-audits/2026-08-12-beastmaker-board-packages.md`, and last `.codex/skills/migrate-hangboard-to-3d/SKILL.md`.

**Interfaces:** documented package trees, exact USDZ/descriptor SHA-256 values, packet hashes, 22/19 inventory results, human approval record, native hit-test result, and deferred-scope limitations.

- [ ] Document both final package trees, exact hashes, source packet provenance/conflicts, generic wood and no-hardware omissions, Compact reuse/defect ruling, human render approval, native 41-contact result, and removal of legacy assets. State that GitHub model sync, iOS model editing, and Workbench model editing remain follow-up work.
- [ ] Run `rtk rg -n 'Resources/BoardModels|wood-grips-compact-ii\\.usdz|beastmaker-1000/assets/primary\\.png|metolius-wood-grips-compact-ii/assets/primary\\.png' README.md Tools/HangboardModels docs HangTen HangTen.xcodeproj`; historic removal records may mention deleted paths, but production fallback references must be absent.
- [ ] Update the migration skill only from demonstrated behavior: manufacturer-first evidence, Astra-only geometry, schema-v2 typed media, generated hash-bound descriptors, package-local USDZ, generic runtime/unavailable state, native material/picking validation, human approval, and owned cleanup. Do not add deferred editor/sync promises.
- [ ] Run `rtk git diff --check`; commit with `docs: record model-first board migrations`. Fresh Sol review maps every skill assertion to an implemented contract and checks no deferred capability is described as shipped.

## Plan self-review

- Spec coverage: schema v2/model descriptor contracts and logical-frame separation are assigned to the completed baseline plus R2/R7; generic rendering, exact node binding, materials, picking, cache, unavailable state, and no fallback are assigned to R2/R3/R7; primary-source evidence, human approval, Astra-only geometry, Compact reuse, package promotion, omissions, and native/simulator validation are assigned to E1/G1/M1/R7/V1; the final docs/source-audit/skill codification is assigned to D1.
- Scope consistency: both named boards remain active; unrelated raster packages remain untouched; runtime Task 1 is not duplicated; only runtime Tasks 4, 5, and 6 are deferred, and each limitation is stated.
- Interface consistency: R2 produces the model loader/surface contract consumed by R3 and R7; E1 produces the packet consumed by G1; G1 produces tagged sources consumed by M1; M1 produces package-local USDZ/descriptors consumed by R7/V1; D1 consumes their hashes and review records. No editor or remote-sync interface is required by an active task.
- Constraint scan: no step permits raster fallback, hardware geometry, inferred axes, image tracing, lower-cost geometry authorship, descriptor hand-editing, stable-ID changes, or unowned durable evidence.
- Placeholder scan: no `TBD`, `TODO`, vague implementation directive, or unresolved file/interface appears in this plan; all simulator, package, test, commit, and cleanup commands name their target or exact environment.

## Focused final verification

- [ ] `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` passes with exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json` in each target package; all unrelated packages remain raster and editable.
- [ ] `rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py` and the focused package/compiler tests pass; each descriptor’s `modelSHA256` equals the SHA-256 of its package-local USDZ bytes.
- [ ] The focused R2/R3/R7 XCTest groups pass on the isolated UUID with `.context/DerivedData`; actual SceneKit checks cover all 41 contacts, exact nodes, materials, body rejection, cache/rebind, and unavailable/no-fallback behavior.
- [ ] The focused simulator route proves both boards visually and interactively in portrait/landscape, including all 41 contacts and the unavailable fixture. The exact owned simulator and ephemeral DerivedData are deleted and absence is verified; durable evidence remains owned.
- [ ] `rtk scripts/verify-board-source-boundary-manifest.sh` and `rtk git diff --check` pass. No standalone Compact USDZ, target PNG, board-specific renderer, or raster fallback remains.
- [ ] Documentation/source-audit/skill closeout records the source hierarchy, approvals, hashes, package contract, and explicit deferred limitations without changing training metadata or stable IDs.

## Revised estimate

The original plans serialize schema/runtime/editor/sync/migration work. With the approved amendment, the editor and remote-sync slices are removed from the critical path but retained as backlog. Estimated active effort is:

| Lane | Worker effort | Parallel elapsed contribution |
| --- | ---: | ---: |
| Runtime R2 + R3 + R7 | 7–10 hours | 6–8 hours after the baseline |
| Luna evidence E1 and human approval | 3–5 hours | 3–5 hours |
| Astra Beastmaker geometry plus Compact review gate G1 | 7–12 hours | 7–12 hours after evidence approval |
| Lower-cost compile/package/promotion M1 | 4–6 hours | 4–6 hours after G1; overlaps late runtime work |
| Simulator, source audit, docs, and skill D1/V1 | 5–8 hours | 5–8 hours after package promotion |
| **Active total** | **26–41 worker-hours** | **14–22 elapsed hours with two active lanes**, excluding human approval wait time |

The estimate assumes Compact II passes the visual-fidelity gate and can reuse its existing source. An Astra correction to Compact or a failed native/package contract moves the work back to G1/M1; it does not authorize a lower-cost geometry edit. The three deferred tasks have no active-delivery estimate here and remain follow-up backlog items.
