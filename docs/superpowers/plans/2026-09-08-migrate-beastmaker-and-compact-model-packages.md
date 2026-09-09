# Migrate Beastmaker 1000 and Compact II Model Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship faithful, reviewed model-first packages for Beastmaker 1000 and Metolius Wood Grips Compact II, with exact package-owned USDZ/descriptor assets and no remaining raster or standalone resource fallback.

**Architecture:** Both packages consume the schema-v2 parser, generated descriptor, compiler, generic SceneKit renderer, sync, and read-only tools delivered by the first two plans. Luna/Sol/Terra assemble evidence, compile/export, package, test, and integrate. Astra alone authors Beastmaker’s physical shape from approved evidence; Compact II’s existing approved editable source is reused unless a validation result identifies a physical-fidelity defect, in which case Astra alone changes its shape.

**Tech Stack:** Manufacturer evidence packets, Blender 5.2, `compile_model_package.py`, Python package validator, SceneKit/XCTest, Xcode iOS simulator validation.

**Spec:** `docs/superpowers/specs/2026-09-08-beastmaker-1000-3d-design.md`

## Global Constraints

- Prerequisite: complete both preceding 2026-09-08 model-first plans and keep their exact `schemaVersion: 2`, `BoardPresentationMedia`, descriptor v1, and `hang-ten-board-v1` contracts unchanged.
- Use a fresh implementation subagent and review subagent per task. Luna handles bounded evidence/packaging mechanics; Sol/Terra handle involved non-geometry work. Astra (`gpt-6-astra`) performs Beastmaker geometry and only physical-fidelity corrections for Compact II.
- Stage 0 sources are manufacturer product pages, manuals, dimension diagrams, and manufacturer media first. Authorized retailers/distributors fill a documented first-party gap only. Reviews, forums, search snippets, and AI summaries are discovery/corroboration only and never sole authority for dimensions, inventory, material, safety/training claims, or geometry facts.
- Each Stage 0 packet lives under `.context/shaky-rat-<board-revision>/`, has immediate `ownership.json`, retained actual page/media snapshots with SHA-256, revision/date/locale, source tiers, confidence, conflicts/rulings, and no geometry proposal, path, contour, mask, coordinate, radius, or section. Before Astra resumes, it must retain at least two complete exact-revision images per board: one manufacturer image plus a materially different oblique/side/back/profile image when available. Record dimensions, angle labels, page linkage, and what each view can/cannot support; authorized commerce images fill only a documented manufacturer gap, and crops/duplicates/search thumbnails/ambiguous revisions do not count.
- Display geometry is not manufacturing CAD. Omit screw holes, mounting holes, countersinks, mounting hardware, and logos from both models; report those omissions explicitly. Do not trace, segment, vectorize, crop, align, or extrude existing raster paths.
- Beastmaker uses sourced 580 × 150 mm face and qualified 58 mm depth from Beech/shared-layout evidence; current Tulipwood `5 mm` text is a recorded conflict, not a thickness fact. Use generic original pale wood. Retain its 22 stable logical IDs and source-backed metadata exactly.
- Compact II uses current primary Metolius evidence and preserves all 19 logical IDs/source-backed metadata. Its existing generated source is geometry authority only after packet/review verification; it does not permit legacy raster geometry retention.
- Final target trees contain only `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`. Delete `Hangboards/beastmaker-1000/assets/primary.png`, `Hangboards/metolius-wood-grips-compact-ii/assets/primary.png`, and `HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz`; remove the now-empty `HangTen/Resources/BoardModels` Xcode resource reference if empty. No raster fallback survives.
- Human visual approval of matched front, three-quarter, and clay-detail views is mandatory before package promotion. Inventory validation does not prove physical fidelity.
- Before simulator work, read `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` completely and follow `validate-hang-ten-ios`: isolated `Hang Ten Paseo shaky-rat Review` only, manifests/traps, `.context/DerivedData`, no shared `booted` target, and exact cleanup verification.

## Dependency Order

`Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7 -> Task 8 -> Task 9`. Task 10 codifies only rules proved by Tasks 1–9.

## Isolated XCTest Device Lifecycle

Before Task 5’s first XCTest command, create one simulator named `Hang Ten Paseo shaky-rat Review`, verify the exact returned UUID/name, append it first to `.context/paseo-pending-simulators` then `.context/paseo-owned-simulators`, and export `HANG_TEN_TEST_DEVICE_UDID`. Install EXIT/INT/TERM cleanup first with `PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive`. Every XCTest command uses `-destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID"`; no named/shared, placeholder, or `booted` destination is allowed. Cleanup removes only this verified simulator and `.context/DerivedData`, preserving durable evidence packets, `.blend` sources, review renders, export reports, hashes, and simulator screenshots under their owned `.context/shaky-rat-*` directories.

## File Map

| File | Change | Responsibility |
| --- | --- | --- |
| `.context/shaky-rat-beastmaker-1000/`, `.context/shaky-rat-metolius-wood-grips-compact-ii/` | Generate and retain | Owned Stage 0 evidence, editable sources, reports, exports, and review renders. |
| `Tools/HangboardModels/beastmaker_1000.py` | Create | Astra-authored Beastmaker analytic model source. |
| `Tools/HangboardModels/verify_beastmaker_1000.py` | Create | Beastmaker export/reimport checks. |
| `Tools/HangboardModels/wood_grips_compact_ii.py` | Modify only if Astra evidence shows physical defect | Compact source tags/export integration; no lower-cost shape editing. |
| `Tools/HangboardModels/verify_wood_grips_compact_ii.py` | Modify | Consume generic compiler outputs and 19-ID package contract. |
| `Tools/HangboardModels/test_model_reports.py` | Modify | Track Beastmaker script/report source boundaries. |
| `Hangboards/beastmaker-1000/board.json`, `Hangboards/metolius-wood-grips-compact-ii/board.json` | Modify | v2 model media and preserved logical metadata only. |
| `Hangboards/beastmaker-1000/assets/primary.usdz`, `assets/primary.model.json` | Create | Compiled Beastmaker artifacts. |
| `Hangboards/metolius-wood-grips-compact-ii/assets/primary.usdz`, `assets/primary.model.json` | Create | Compiled Compact artifacts. |
| `Hangboards/*/assets/primary.png` for the two targets | Delete | Exact legacy raster assets. |
| `HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz` | Delete | Superseded standalone resource. |
| `HangTen.xcodeproj/project.pbxproj`, `HangTenTests/BoardSourceBoundaryTrackedPaths.txt` | Modify | Remove empty standalone resource group/reference and refresh boundary manifest. |
| `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift` | Modify | Actual two-board SceneKit/parser assertions. |
| `docs/source-audits/2026-08-12-beastmaker-board-packages.md`, `Tools/HangboardModels/README.md` | Modify | Evidence/authoring record and tool contract. |
| `.codex/skills/migrate-hangboard-to-3d/SKILL.md` | Modify last | Codify demonstrated reusable evidence/model-first/routing/validation rules. |

### Task 1: Luna — build two approved Stage 0 evidence packets

**Files:**
- Create: `.context/shaky-rat-beastmaker-1000/ownership.json`, `evidence-packet.json`, `evidence-brief.md`, `astra-handoff.md`, `invalid-unknown-hold.blend`, `references/*`
- Create: `.context/shaky-rat-metolius-wood-grips-compact-ii/ownership.json`, `evidence-packet.json`, `evidence-brief.md`, `references/*`
- Modify: `docs/source-audits/2026-08-12-beastmaker-board-packages.md`

**Interfaces:**
- Consumes `Tools/HangboardModels/validate_evidence_packet.py` from plan one.
- Produces `evidence-packet.json` conforming exactly to `EvidencePacket` and an Astra-readable brief whose claims cite packet indices only.

- [ ] **Step 1: Create packet validation failure fixtures**

Create a Beastmaker packet whose retained search-result snippet and matching hash are labeled as a manufacturer source for `580 × 150`, and a Compact packet with an unsnapshotted retailer image. Each must be rejected by the packet CLI; write the rejected packet paths and errors in the evidence brief’s audit log rather than preserving them as approved data.

- [ ] **Step 2: Run packet validation and confirm failure**

Run: `rtk proxy python3 -B Tools/HangboardModels/validate_evidence_packet.py .context/shaky-rat-beastmaker-1000/rejected-snippet-packet.json`

Expected: exit 2 stating that a manufacturer source URL must not be a search result. The Compact unsnapshotted-retailer fixture also exits 2 with the retained-source error.

- [ ] **Step 3: Gather first-party packets, then authorized-commerce gaps**

For Beastmaker retain snapshots/hashes of the current exact manufacturer product page `https://www.beastmaker.co.uk/products/beastmaker-1000-series`, manufacturer Beech/shared-layout page `https://www.beastmaker.co.uk/products/beastmaker-1000-beech`, official front media `https://cdn.shopify.com/s/files/1/0107/6442/files/1000_Small_Tulip.jpg?v=1756733068`, official downloads page, and official mounting guide. Record `en-GB`, retrieval/revision date, face `580 × 150 mm`, 22-ID inventory ruling, 58 mm qualified depth ruling, current Tulip `5 mm` conflict, generic pale wood, 17 cavity/three sloper/two jug visual inventory, unknown cavity sections/radii/back profile, and omitted hardware. The manufacturer pages expose only one complete front image; old official Vimeo embeds and mounting-guide setup photos do not provide a complete exact-1000 profile/side/back source. Retain the complete FluxPerfect commerce-gap three-quarter image `https://cdn.shopify.com/s/files/1/0646/8832/4836/files/Trainingsboard_Beastmaker_1000_Series_Hangboard_Ansicht_1.jpg?v=1756383659` and its page snapshot `https://www.fluxperfect.at/products/beastmaker-1000-series-hangboard` (1080 × 1080; SHA-256 `959801633efd53b10dba145a659988290d5189ea2bcc171329fedd1e6d52a3ff`). It visibly exposes top plane, outer side/depth, and rounded end and is the qualifying second view; label it commerce-gap and do not use it to override manufacturer claims. Retain the prior 9c image and all inspected FluxPerfect/Ellis Brigham alternatives with original hashes/dimensions and explicit rejection labels: 9c is a near-front nonqualifying variant; FluxPerfect 2–6 and Ellis 01–03 are crops or near-front views and are not part of the approval set.

For Compact retain snapshots/hashes of the current Metolius product page `https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards`, official product photo `https://www.metoliusclimbing.com/cdn/shop/files/Wood-Grips-II-Compact-Training-Board.jpg?v=1759460952&width=2000`, and official depth diagram `https://www.metoliusclimbing.com/cdn/shop/files/woodgrips-boards-depths.jpg?v=1762201428&width=2000`. Record 610 × 157 mm; the lower Compact diagram (not upper Deluxe); its #2 56 mm flat-sloper and #9 56 mm round-sloper callouts; and the exact 19-ID numbered mapping. Do not treat 56 mm as overall board/body/display thickness: physical Compact body Z/depth is source-unresolved, and any existing model depth is estimated authored geometry. Record unknown apertures/profiles/back and omitted hardware. Also retain the complete Bergfreunde Compact II commerce-gap image `https://www.bfgcdn.com/1500_1500_90/342-0111/metolius-wood-grips-compact-ii-training-board.jpg` and its page snapshot because the manufacturer exposes no second complete angle; label it elevated front oblique/top-and-side thickness reveal and do not use it to override manufacturer claims. Add authorized retailer/distributor entries only when they fill a cited missing manufacturer fact; no reviewer/forum/AI claim becomes a sourced fact.

- [ ] **Step 4: Validate packets and request human evidence approval**

Run: `rtk proxy python3 -B Tools/HangboardModels/validate_evidence_packet.py .context/shaky-rat-beastmaker-1000/evidence-packet.json && rtk proxy python3 -B Tools/HangboardModels/validate_evidence_packet.py .context/shaky-rat-metolius-wood-grips-compact-ii/evidence-packet.json`

Expected: both exit 0. Present the two human-readable briefs and matched official media for approval; do not start geometry without that approval.

- [ ] **Step 5: Commit source audit only**

Run: `git add docs/source-audits/2026-08-12-beastmaker-board-packages.md && git commit -m "docs: record model migration evidence rulings"`

- [ ] **Step 6: Luna prepares Astra handoff and compiler-negative evidence**

Write `astra-handoff.md` containing only the approved packet SHA, exact 22 logical IDs, coordinate frame, required review views, no-hardware rule, and sourced-versus-estimated boundary. Create the minimal tagged invalid Blender fixture `invalid-unknown-hold.blend` with `role="hold"` and `hold_id="unknown"`; this is compiler test data, not a proposed board shape. Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/shaky-rat-beastmaker-1000/invalid-unknown-hold.blend --board-json Hangboards/beastmaker-1000/board.json --output-directory .context/shaky-rat-beastmaker-1000/compiler-scratch-invalid`

Expected: exit 1 mentioning unknown hold ID, no descriptor, and the ephemeral `compiler-scratch-invalid` directory removed while the packet/handoff/fixture remain.

Review gate: fresh Sol reviewer checks every claimed primary fact has a retained actual source/media hash, qualified secondary facts are labelled, and neither packet nor handoff contains a geometry proposal.

### Task 2: Astra — author and visually review Beastmaker physical geometry

**Files:**
- Create: `Tools/HangboardModels/beastmaker_1000.py`
- Create owned generated source: `.context/shaky-rat-beastmaker-1000/beastmaker-1000.blend`, `model-report.json`, `source-versus-estimate.md`, `front.png`, `three-quarter.png`, `clay-three-quarter.png`, `clay-detail.png`, `selected-holds.png`

**Interfaces:**
- Consumes only the approved Beastmaker `evidence-packet.json`, its brief, and logical ID list from `Hangboards/beastmaker-1000/board.json`.
- Produces tagged Blender meshes: one or more `role="body"`; every contact `role="hold"` and `hold_id` equal to one of the 22 canonical IDs.

- [ ] **Step 1: Astra authoring implementation**

In `beastmaker_1000.py`, directly author the rounded 580 × 150 × 58 mm display silhouette in the exact `hang-ten-board-v1` metre frame. Build bilateral body/jug/35-degree-sloper geometry once and mirror where physically symmetric; author the center 20-degree sloper and all 17 visible recess mouths, walls, back fillets, and curved transitions. Retain all 22 IDs: `jug-left`, `jug-right`, `sloper-35-left`, `sloper-35-right`, `sloper-center`, four upper, seven middle, and six lower pocket IDs from the package. Use continuous geometry and sufficient tessellation; do not derive any mesh from the old PNG/path JSON. Use generic pale wood, no logos, no screws/countersinks/hardware.

- [ ] **Step 2: Render matched inexpensive review views**

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/beastmaker_1000.py -- --output .context/shaky-rat-beastmaker-1000`

Expected: exit 0 and report source/estimate map, bounds, tags, triangle count, renderer/camera/light settings, all-contact overview, and required front/three-quarter/clay-detail PNGs.

- [ ] **Step 3: Human visual fidelity gate**

Compare the three required views against retained official media. Record approval or concrete visual defects in `source-versus-estimate.md`. Route only a silhouette, cavity, profile, or physical-shape defect back to Astra; route tag/material/export/schema defects to lower-cost workers. Do not continue to package promotion until approved.

- [ ] **Step 4: Commit authored generator, not `.context` evidence/artifacts**

Run: `git add Tools/HangboardModels/beastmaker_1000.py && git commit -m "feat: author Beastmaker 1000 display model"`

Review gate: fresh Sol reviewer checks only tags/outputs/metadata and sends any visual geometry defect to Astra, not to a lower-cost editor.

### Task 3: Terra — compile, reimport, and verify both packages

**Files:**
- Create: `Tools/HangboardModels/verify_beastmaker_1000.py`
- Modify: `Tools/HangboardModels/verify_wood_grips_compact_ii.py`, `Tools/HangboardModels/test_model_reports.py`, `Tools/HangboardModels/README.md`
- Create owned outputs in both `.context/shaky-rat-*` directories.

**Interfaces:**
- Consumes approved `.blend`, package logical inventory, and generic `compile_model_package.py`.
- Produces exact package-ready `primary.usdz`, `primary.model.json`, `export-verification.json`, and actual-export roundtrip renders.

- [ ] **Step 1: Write failing Beastmaker verifier expectations**

```python
def test_beastmaker_report_requires_22_hold_ids_and_no_hardware():
    report = verify_report(load_report("fixture-report.json"), expected_ids=BEASTMAKER_IDS)
    assert report["hold_ids_preserved"] == 22
    assert report["hardware_mesh_count"] == 0
```

- [ ] **Step 2: Run model report test**

Run: `rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py`

Expected: FAIL until the Beastmaker verifier/report family is registered.

- [ ] **Step 3: Compile and verify Beastmaker actual export**

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/shaky-rat-beastmaker-1000/beastmaker-1000.blend --board-json Hangboards/beastmaker-1000/board.json --output-directory .context/shaky-rat-beastmaker-1000/package`

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/verify_beastmaker_1000.py -- --output .context/shaky-rat-beastmaker-1000/package`

Expected: both exit 0; reimported USDZ has 580 × 150 × 58 mm bounds within one micrometre, all 22 hold IDs, all geometry bound, no hardware meshes, texture/material on every mesh, explicit triangles, below recorded triangle ceiling, and actual-export review renders.

- [ ] **Step 4: Recompile Compact without lower-cost shape changes**

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/shaky-rat-metolius-wood-grips-compact-ii/wood-grips-compact-ii.blend --board-json Hangboards/metolius-wood-grips-compact-ii/board.json --output-directory .context/shaky-rat-metolius-wood-grips-compact-ii/package`

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/verify_wood_grips_compact_ii.py -- --format usdz --skip-renders .context/shaky-rat-metolius-wood-grips-compact-ii/package`

Expected: exit 0 with 19 IDs, all material/node/hash checks, and no geometry edit. If the official comparison reveals a physical defect, stop and dispatch only that correction to Astra, regenerate all exports/views, and repeat this task.

- [ ] **Step 5: Run report tests and commit deterministic tooling**

Run: `rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py`

Expected: PASS.

Run: `git add Tools/HangboardModels/verify_beastmaker_1000.py Tools/HangboardModels/verify_wood_grips_compact_ii.py Tools/HangboardModels/test_model_reports.py Tools/HangboardModels/README.md && git commit -m "feat: verify model-first board exports"`

Review gate: fresh Terra reviewer verifies compiler/verifier never modifies authored vertex shape and output descriptor hashes exact USDZ bytes.

### Task 4: Luna — promote model artifacts and remove exact raster/standalone assets

**Files:**
- Modify: `Hangboards/beastmaker-1000/board.json`, `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Create: `Hangboards/beastmaker-1000/assets/primary.usdz`, `Hangboards/beastmaker-1000/assets/primary.model.json`, `Hangboards/metolius-wood-grips-compact-ii/assets/primary.usdz`, `Hangboards/metolius-wood-grips-compact-ii/assets/primary.model.json`
- Delete: `Hangboards/beastmaker-1000/assets/primary.png`, `Hangboards/metolius-wood-grips-compact-ii/assets/primary.png`, `HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz`
- Modify: `HangTen.xcodeproj/project.pbxproj`, `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:**
- Produces each target’s single default model presentation: `media.type="model"`, `assetPath="assets/primary.usdz"`, `descriptorPath="assets/primary.model.json"`, orthographic display camera, and `derivation.type="original"`.

- [ ] **Step 1: Add package rejection tests before promotion**

```python
def test_target_model_package_rejects_legacy_png_fallback():
    package = copy_target("beastmaker-1000")
    (package / "assets/primary.png").write_bytes(PNG_BYTES)
    with pytest.raises(ValueError, match="exactly the declared"):
        load_board_package(package)
```

```swift
func testCompactUsesPackageModelNotStandaloneResource() {
    XCTAssertNil(Bundle.main.url(forResource: "wood-grips-compact-ii", withExtension: "usdz", subdirectory: "BoardModels"))
    XCTAssertNotNil(BoardCatalog.packageStore.presentationAssetURL(for: compact))
}
```

- [ ] **Step 2: Run failure tests**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: FAIL until target manifests are model media and no fallback asset exists.

- [ ] **Step 3: Apply package-local asset promotion**

Copy exact verified bytes from each owned package directory into its target `assets/`; write model media using compiler-generated descriptor path, preserve logical holds/equipment/positions/transitions/metadata without `geometry` or `presentationID`, then delete the two named PNGs and standalone Compact USDZ. Remove `BoardModels` group/build file/resource phase entries only if no tracked member remains, and regenerate `BoardSourceBoundaryTrackedPaths.txt` by `git ls-files -- HangTen HangTen.xcodeproj/project.pbxproj` sorted exactly as the manifest script expects.

- [ ] **Step 4: Validate finished trees**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Expected: PASS with the two targets model media and every other board raster media.

- [ ] **Step 5: Commit and review**

Run: `git add Hangboards/beastmaker-1000 Hangboards/metolius-wood-grips-compact-ii HangTen.xcodeproj/project.pbxproj HangTenTests/BoardSourceBoundaryTrackedPaths.txt && git add -u -- HangTen/Resources/BoardModels/wood-grips-compact-ii.usdz && git commit -m "feat: migrate Beastmaker and Compact packages to models"`

Review gate: fresh Sol reviewer verifies only the three specified files remain per target package and no `BoardModels` fallback resource/reference survives.

### Task 5: Sol — native SceneKit semantic tests against actual two-board USDZs

**Files:**
- Modify: `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`

**Interfaces:**
- Consumes package URLs/descriptor via generic `BoardPackageStore` and generic `BoardModelScene` from plan two.

- [ ] **Step 1: Add actual inventory/picking tests**

```swift
func testEveryMigratedModelHoldHasExactNearestHitAndMaterial() throws {
    for id in ["beastmaker-1000", "metolius.wood-grips-compact-ii"] {
        let board = BoardCatalog.board(for: id)
        let model = try XCTUnwrap(BoardModelLoader.load(board: board, presentation: board.defaultPresentation, store: BoardCatalog.packageStore))
        SCNTransaction.flush()
        XCTAssertEqual(Set(model.holdNodes.keys), Set(board.holds.map(\.id)))
        try assertNearestHeadOnHitForEveryHold(model, board: board)
        XCTAssertTrue(model.geometryNodes.allSatisfy { $0.geometry?.firstMaterial?.diffuse.contents != nil })
    }
}
```

- [ ] **Step 2: Run the native tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: FAIL until both package-local actual USDZs bind every logical hold.

- [ ] **Step 3: Implement test fixture helpers only**

Add helpers that derive each ray from descriptor `facePlaneAABB` and camera, choose the closest native SceneKit hit after `SCNTransaction.flush()`, assert exact `holdID`, assert body IDs cannot be selected, and test unavailable UI when package bytes/descriptors are deliberately corrupted in a temporary fixture. Do not add a per-board renderer branch.

- [ ] **Step 4: Run native semantic group**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: PASS for all 41 total contacts, original materials, highlight/restoration, display-only hit-testing behavior, and stale/missing descriptor failure.

- [ ] **Step 5: Commit and review**

Run: `git add HangTenTests/BoardModelTests.swift HangTenTests/BoardPackageStoreTests.swift && git commit -m "test: verify migrated model package semantics"`

Review gate: fresh Terra reviewer confirms the test uses actual package USDZ, not a standalone resource or fake node-name mapping.

### Task 6: Terra — stage/build and source-boundary verification

**Files:**
- Modify: `Tools/HangboardPackages/tests/test_board_package_staging.py`, `README.md`

- [ ] **Step 1: Add staged target identity assertions**

```python
def test_staged_targets_have_only_model_media_and_hash_bound_descriptors(staged_hangboards):
    for slug in ("beastmaker-1000", "metolius-wood-grips-compact-ii"):
        assert sorted(path.name for path in (staged_hangboards / slug / "assets").iterdir()) == ["primary.model.json", "primary.usdz"]
        assert descriptor_hash(staged_hangboards / slug) == sha256_file(staged_hangboards / slug / "assets/primary.usdz")
```

- [ ] **Step 2: Run the focused staging/package characterization**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_board_package_staging.py Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: PASS. `stage_board_packages` already recursively copies its validated package tree; this new target assertion proves the promoted USDZ/descriptor bytes survive that unchanged behavior.

- [ ] **Step 3: Run package, staging, and Xcode build checks**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory && rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_board_package_staging.py Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: PASS.

Run: `rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData build`

Expected: BUILD SUCCEEDED.

- [ ] **Step 4: Verify source boundary and commit**

Run: `rtk scripts/verify-board-source-boundary-manifest.sh && git add Tools/HangboardPackages/tests/test_board_package_staging.py README.md && git commit -m "test: stage model-first board packages"`

Expected: source-boundary command exits 0.

Review gate: fresh Luna reviewer confirms staged contents are exact package bytes and no resource bypass exists.

### Task 7: Sol — isolated simulator visual and interaction validation

**Files:**
- Create then clean: `.context/paseo-pending-simulators`, `.context/paseo-owned-simulators`, `.context/DerivedData`, `.context/workout-raw.png`, `.context/workout-landscape.png`
- Modify: `docs/IOS_SIMULATOR_VALIDATION.md` only if a demonstrated route/result changes.

- [ ] **Step 1: Read required validation documents and install cleanup trap**

Read `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md` to EOF. Reuse the lifecycle-created `Hang Ten Paseo shaky-rat Review` identified by `HANG_TEN_TEST_DEVICE_UDID`; re-query its exact UUID/name and verify it is present in both pending and owned manifests before boot/build. Do not create a second simulator.

- [ ] **Step 2: Build/install/launch the exact isolated simulator**

Run the skill’s explicit `xcodebuild`, `simctl install`, and route commands with the created UUID, never `booted`.

Expected: app launches from package-local models.

- [ ] **Step 3: Inspect required behavior and capture evidence**

For Beastmaker and Compact, inspect front/oblique normal, preview-highlight, active-highlight, clear/restored, reappearance, portrait, and landscape. Physically tap each selectable contact (22 + 19) and confirm exact logical label/selection; confirm display-only surfaces with nil callbacks do not intercept parent touches; corrupt a copied fixture package to confirm generic `boardModel.unavailable` with no raster fallback. Capture named screenshots under `.context` and record reviewed states/checksums in `simulator-validation.md`.

- [ ] **Step 4: Run targeted tests on the same UUID**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: PASS.

- [ ] **Step 5: Cleanup and verify**

Allow the trap to archive/delete only the verified workspace-named simulator and ephemeral `.context/DerivedData`/runtime scratch. Re-query UUID absence and verify pending/owned records are consumed only after success; retain manifests if cleanup fails. Preserve owned evidence packets, `.blend` sources, review renders, export reports, hashes, and simulator screenshots for audit; do not commit them.

Review gate: fresh Terra reviewer checks screenshot evidence against the actual packaged assets and reports any physical fidelity defect to Astra only.

### Task 8: Documentation and reviewed-output closeout

**Model tier:** Luna — documentation mechanics; Sol review.

**Files:**
- Modify: `Tools/HangboardModels/README.md`, `docs/source-audits/2026-08-12-beastmaker-board-packages.md`, `README.md`

- [ ] **Step 1: Document final provenance and package shape**

Record exact package-local USDZ/descriptor SHA-256 values, source packet hashes, 22/19 inventory outcomes, qualified Beastmaker depth ruling, Compact source/estimate distinction, material fidelity, deliberate omissions, human render approval, native hit-test result, and removal of legacy assets. Replace stale README assertions that all boards own `assets/primary.png` or that Compact uses a standalone BoardModels resource.

- [ ] **Step 2: Test documentation paths and stale references**

Run: `rtk rg -n 'Resources/BoardModels|wood-grips-compact-ii\.usdz|beastmaker-1000/assets/primary\.png|metolius-wood-grips-compact-ii/assets/primary\.png' README.md Tools/HangboardModels docs HangTen HangTen.xcodeproj`

Expected: no remaining production fallback reference; source audit may mention an explicit deleted historic path only in a removal record.

- [ ] **Step 3: Commit and review**

Run: `git add README.md Tools/HangboardModels/README.md docs/source-audits/2026-08-12-beastmaker-board-packages.md && git commit -m "docs: record model-first board migrations"`

Review gate: fresh Sol reviewer validates every source claim’s packet hash and no description misrepresents display estimates as manufacturing facts.

### Task 9: Full migration acceptance verification

**Model tier:** Terra — integrated non-geometry verification.

**Files:**
- Test: `Tools/HangboardPackages/tests`, `Tools/HangboardModels/test_model_reports.py`, `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`

- [ ] **Step 1: Run final package/model checks**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Expected: PASS.

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests -q`

Expected: PASS.

Run: `rtk proxy python3 -B Tools/HangboardModels/test_model_reports.py`

Expected: PASS.

- [ ] **Step 2: Run final focused native test group**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/GitHubBoardSyncServiceTests -only-testing:HangTenTests/BoardEditorStoreTests`

Expected: PASS.

- [ ] **Step 3: Verify git cleanliness rules**

Run: `rtk scripts/verify-board-source-boundary-manifest.sh && rtk git diff --check`

Expected: both exit 0.

- [ ] **Step 4: Commit any verification-only fixture adjustment**

Run: `git add Tools/HangboardPackages/tests HangTenTests && git commit -m "test: complete model migration acceptance"`

Review gate: fresh Sol reviewer cross-checks all acceptance items: model-first target trees, two reviewed packets, all contacts native-pickable, model hashes, no raster fallback, unrelated raster boards still parse/edit, and no training metadata changes.

### Task 10: Sol — codify demonstrated reusable migration rules in the skill

**Files:**
- Modify: `.codex/skills/migrate-hangboard-to-3d/SKILL.md`

- [ ] **Step 1: Write skill regression checklist before editing**

Create a short review checklist in the task notes requiring the final skill to state: Stage 0 manufacturer-first source hierarchy and retained hashes; low-cost research/compiler/integration division; Astra-only physical geometry; no hardware; schema-v2 tagged raster/model media; generated hash-bound descriptor; exact package-local USDZ; generic runtime/read-only Workbench; native SceneKit/material/picking validation; human render approval; explicit unavailable/no raster fallback; owned-resource cleanup.

- [ ] **Step 2: Update only demonstrated rules**

Replace legacy language that keeps canonical 2D paths, a 2D fallback, or a separate app model resource. Add the completed data-model field names exactly (`schemaVersion`, `media.type`, `descriptorPath`, `modelSHA256`, `hang-ten-board-v1`, `facePlaneAABB`); include the primary-source/authorized-commerce hierarchy and confidence/conflict packet requirements; explicitly say lower-cost workers do research/evidence, deterministic compiler/exporter, schema/tools/tests/integration and must route fidelity defects to Astra. Do not prescribe unimplemented future model-editing or derived-model features.

- [ ] **Step 3: Run focused skill/document consistency checks**

Run: `rtk rg -n 'canonical 2D|2D fallback|separate app resource|BoardModels/wood-grips-compact-ii' .codex/skills/migrate-hangboard-to-3d/SKILL.md Tools/HangboardModels/README.md README.md`

Expected: no legacy requirement remains.

- [ ] **Step 4: Commit and review**

Run: `git add .codex/skills/migrate-hangboard-to-3d/SKILL.md && git commit -m "docs: codify model-first hangboard migration"`

Review gate: fresh Terra reviewer maps every new skill assertion to evidence from Tasks 1–9 and rejects advice that the implementation did not validate.

## Final Verification

- [ ] Both target packages contain exactly `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`; their descriptors hash-bind actual USDZ bytes.
- [ ] `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, Python model checks, focused Xcode tests, source-boundary verification, and `rtk git diff --check` all exit 0.
- [ ] Human-reviewed front/three-quarter/clay-detail renders, native 41-contact interaction proof, and simulator screenshots are recorded in owned output before cleanup.
- [ ] Exact owned simulator, compiler scratch, and `.context/DerivedData` are deleted and absence verified; durable owned evidence packets, `.blend` sources, review renders, export reports, hashes, and screenshots remain for audit, while unrelated resources are untouched.
- [ ] The migration skill reflects only the demonstrated final contract and lower-cost/Astra routing.
