# Tension Flash Board Two-Branch Suspended Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Flash Board's provisional `singleCord` presentation with one source-reviewed USDZ containing the seven approved selectable holds, four physical end passages, visible nonselectable ledges/notches, and a deterministic two-branch cord presentation converging on one invisible fixed display anchor.

**Architecture:** Keep `tension.flash-board` model-only with one `primary.usdz` and one hash-bound descriptor. The typed package contract declares two named end passage pairs, two ordered branch paths sharing one metadata-only anchor, and one canonical pose/camera for each existing position. The renderer applies the selected pose to the one USDZ and builds two transient non-pickable catenary branches; only the seven descriptor-bound hold meshes participate in highlighting, accessibility, and nearest-triangle picking.

**Tech Stack:** Python 3 standard-library package/evidence validators, Blender/USDZ authoring and actual-export verification, Swift/SwiftUI/SceneKit/XCTest, Android JVM tests, Xcode Simulator, and the existing package staging scripts.

**Spec:** `docs/superpowers/specs/2026-09-10-flash-board-two-branch-suspension-design.md`

## Global Constraints

- Read `.codex/skills/migrate-hangboard-to-3d/SKILL.md` and this spec before each task; preserve its evidence gate, direct Astra geometry authoring, material, export, picking, cleanup, and unavailable-state requirements.
- The exact approved logical inventory and order is `three-edge-left`, `three-edge-center`, `three-edge-right`, `two-edge-left`, `two-edge-right`, `small-crimp-left`, `small-crimp-right`; no new logical ID may be introduced for shallow ledges/notches or passages.
- Flash remains model-only: exactly one USDZ and one descriptor, no PNG/raster presentation, no canonical 2D paths, no duplicate face model, no baked cord/anchor, no visible nail/hook/carabiner/environment, and no mounting holes or hardware.
- Four passages are physical nonselectable routing features grouped as exactly two named pairs (`left`, `right`), each with exactly two distinct importer-visible points; each branch references exactly one ordered pair and both branches share the same fixed invisible anchor.
- All passage coordinates, anchor offset, branch rest lengths/radius/material, pose transforms, ledge dimensions, and camera values are `displayEstimate` unless a retained primary source proves them; never promote estimates to physical product metadata.
- Canonical poses use the existing four position IDs: `three-edge-upright`, `three-edge-inverted`, `two-edge-upright`, and `two-edge-inverted`. There is exactly one finite pose per supported position and no unknown pose key.
- Straight cord spans are valid only when rest length equals endpoint distance within `1e-5 m`; shorter, nonfinite, unsolved, discontinuous, self-intersecting, colliding, or incorrectly framed branches enter the existing explicit model-unavailable/error state with no fallback.
- The cord is display-only and has no SceneKit node for the anchor, no accessibility element, no hold binding, and no opportunity to become a nearer pick; actual triangle intersections remain the picking proof.
- Use Luna for evidence, schema, conversion, catenary math, validation, tests, packaging, Android, and routine integration; escalate to Terra only after a bounded Luna attempt exposes an intricate non-geometry issue; Astra alone owns the final physical geometry/fidelity pass.
- Preserve the current uncommitted `Tools/HangboardModels/tension_flash_board.py` as user work until the geometry task explicitly reviews/reconciles it. Do not reset, discard, or overwrite it from the controller task.
- Store owned evidence, Blender source, exports, renders, reports, simulator resources, and cleanup records below `.context/pretty-crocodile-tension-flash-board/`; follow the simulator ownership/cleanup trap and do not touch shared CoreSimulator services.
- Do not start an HTTP server for this migration.

## File Structure

| Path | Change | Responsibility |
| --- | --- | --- |
| `.context/pretty-crocodile-tension-flash-board/sources/*` and `evidence-packet.json` | Modify retained evidence | Add the supplied closeups and the retained Amazon annotated face map as commerce-gap evidence, preserving hashes, URLs, tiers, and limitations. |
| `docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md` | Modify | Record the evidence update, lower-groove ambiguity, seven-ID ruling, and unresolved product-revision gap. |
| `Tools/HangboardModels/evidence_packet.py`, `evidence-packet-template.json`, `test_evidence_packet.py` | Modify | Validate source-tiered closeups, position/face mappings, and estimate-versus-source labeling. |
| `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` | Modify | Parse and fail closed on `twoBranchCord`, four passages, branch pairing/order, common anchor, and exact poses. |
| `Tools/HangboardPackages/tests/test_model_first_packages.py` | Modify | Python parser, semantic audit, asset-isolation, and failure behavior tests. |
| `HangTen/Models/TrainingModels.swift`, `HangTen/Models/BoardPackageStore.swift` | Modify | Define closed Swift two-branch types and decode/validate them without widening `singleCord`. |
| `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/Fixtures/BoardPackageValidationFixtures.json` | Modify | Swift parity and shared raw JSON malformed-fixture matrix. |
| `HangTen/Views/SuspendedBoardPresentation.swift` | Modify | Solve two free catenary spans per branch, preserve ordered passage routing, and expose deterministic samples/clearance inputs. |
| `HangTenTests/SuspendedBoardPresentationTests.swift` | Modify | Pure two-branch solver tests. |
| `Tools/HangboardModels/tension_flash_board.py` | Modify by Astra only | Directly author the cylindrical body, both usable faces, seven hold meshes, paired passages, and visible shallow ledges/notches. |
| `Tools/HangboardModels/verify_tension_flash_board.py`, `test_verify_tension_flash_board.py` | Modify | Reimport actual USDZ and prove mesh roles, materials, passage correspondence, per-position surface rays, ligaments, and cord-clearance probes. |
| `.context/pretty-crocodile-tension-flash-board/{flash-board.blend,package/,renders/,export-verification.json}` | Create/replace owned output | Reviewed Astra source, compiled assets, renders, and durable verifier report. |
| `HangTen/Views/BoardModelView.swift`, `HangTen/Views/BoardMapView.swift` | Modify | Load one model, apply canonical position pose, render two transient branches, preserve orbit/reset, mask cord/passage picking, and route failures unavailable. |
| `HangTenTests/BoardModelTests.swift` | Modify | Native SceneKit nearest-triangle, animation, orbit, accessibility, and cord-ignore tests. |
| `Hangboards/tension-flash-board/board.json` | Modify | Replace Flash `singleCord` metadata with the exact two-branch contract while preserving logical IDs, positions, and transitions. |
| `Hangboards/tension-flash-board/assets/primary.usdz`, `primary.model.json` | Replace with verified bytes | Ship the one final model and descriptor; remove all former Flash raster assets. |
| `Tools/HangboardPackages/tests/test_approved_board_packages.py`, `test_board_package_staging.py`, `presentation_remediation_audit.py`, remediation manifest | Modify only where needed | Promote model-only package and narrowly supersede historical raster records without weakening raster-board audits. |
| `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt` | Modify | Prove Android keeps model-only Flash unavailable without raster lookup or fallback. |
| `.codex/skills/migrate-hangboard-to-3d/SKILL.md` | Modify only for observed reusable failures | Add dated, evidence-backed lessons discovered during this migration, with the failed command, root cause, safe remedy, and regression check. |

---

### Task 1: Luna — update and reapprove the retained evidence packet

**Files:**
- Modify: `.context/pretty-crocodile-tension-flash-board/evidence-packet.json` and retained `sources/*`
- Modify: `Tools/HangboardModels/evidence_packet.py`, `Tools/HangboardModels/evidence-packet-template.json`, `Tools/HangboardModels/test_evidence_packet.py`
- Modify: `docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md`

**Interfaces:** Produces a validated packet whose `suspendedPresentation.positionMappings` covers all four position IDs, whose `visualApproval.approvedSnapshotPaths` includes materially distinct retained views, and whose sources identify manufacturer versus commerce-gap tier. The packet must retain `sources/commerce-labelled-faces.jpg` with the Amazon URL and must carry the three user-supplied closeups with their evidence limitations.

- [ ] **Step 1: Add RED evidence tests for the update.** Assert that a valid packet accepts the Amazon annotated face map only as `commerce`, accepts user closeups only with explicit user-evidence limitations, rejects a commerce source that adds a logical hold ID, rejects a lower groove mapped as a new ID, and requires a nonempty conflict/ruling for the unresolved lower-ledge interpretation.

  ```python
  def test_lower_ledges_remain_nonselectable_evidence_only(valid_packet):
      packet = validate_evidence_packet(valid_packet)
      assert packet.suspended_presentation["logicalRuling"] == "no-new-logical-ids"
  ```

- [ ] **Step 2: Run the focused test and confirm RED.**

  ```bash
  python3 -m pytest Tools/HangboardModels/test_evidence_packet.py -q
  ```

  Expected: the new face-map/ruling tests fail because the retained packet contract does not yet express the new source mapping.

- [ ] **Step 3: Extend the closed evidence fields.** Preserve source hashes and unique local paths, add explicit `faceInventoryNotes`, `nonSelectableFeatures`, and `logicalRuling` fields inside the suspended presentation contract, and reject proposal/geometry fields. Do not treat the Amazon labels as manufacturer facts; record the seven-ID ruling exactly.

- [ ] **Step 4: Retain and audit the supplied imagery.** Record each exact retained image's SHA-256, publisher/source tier, view label, supported face or routing claim, and limitation. Include the manufacturer page, Backcountry hanging view, Amazon annotated face map, and supplied closeups; preserve the statement that the shallow lower grooves are not proven new contacts and may be authored only as nonselectable geometry.

- [ ] **Step 5: Validate and commit the evidence contract.**

  ```bash
  python3 -B Tools/HangboardModels/validate_evidence_packet.py .context/pretty-crocodile-tension-flash-board/evidence-packet.json
  python3 -m pytest Tools/HangboardModels/test_evidence_packet.py -q
  git add Tools/HangboardModels/evidence_packet.py Tools/HangboardModels/evidence-packet-template.json Tools/HangboardModels/test_evidence_packet.py docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md
  git commit -m "Update Flash Board face evidence for two-branch migration"
  git push
  ```

**Review gate:** A Luna reviewer checks source hashes, URL/tier correctness, exact seven-ID preservation, and that no commerce or photo evidence has been promoted into a selectable hold. Resolve evidence-contract findings before any geometry handoff.

### Task 2: Luna — define closed Python/Swift `twoBranchCord` package types and shared rejection matrix

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`, `Tools/HangboardPackages/tests/test_model_first_packages.py`
- Modify: `HangTen/Models/TrainingModels.swift`, `HangTen/Models/BoardPackageStore.swift`, `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
- Modify if descriptor role tests require it: `Tools/HangboardModels/model_descriptor.py`, `Tools/HangboardModels/compile_model_package.py`, `Tools/HangboardModels/test_model_descriptor.py`, `Tools/HangboardModels/test_compile_model_package_blender.py`

**Interfaces:** Replace the current single-value suspension model with an explicit discriminator while preserving unrelated boards:

```swift
struct BoardModelPassage: Hashable {
    let id: String
    let nodeID: String
    let pointInModel: [Double]
    let provenance: String
}

struct BoardModelPassagePairs: Hashable {
    let left: [BoardModelPassage]   // exactly two, order-sensitive
    let right: [BoardModelPassage]  // exactly two, order-sensitive
}

struct BoardModelCordBranch: Hashable {
    let id: String
    let passageIDs: [String]        // exactly two, ordered
    let restLength: Double
    let radius: Double
    let material: String
    let provenance: String
}

struct BoardModelTwoBranchSuspension: Hashable {
    let passages: BoardModelPassagePairs
    let branches: [BoardModelCordBranch] // exactly two
    let anchor: BoardModelInvisibleAnchor
    let canonicalPoses: [String: BoardModelCanonicalPose]
}

enum BoardModelSuspension: Hashable {
    case singleCord(BoardModelSingleCordSuspension)
    case twoBranchCord(BoardModelTwoBranchSuspension)
}
```

`makeModelSuspension(...) throws -> BoardModelSuspension` must reject a `singleCord`-to-`twoBranchCord` shape mismatch rather than silently converting it. The Python parser exposes the equivalent immutable mapping and validates the same raw member/order contract.

- [ ] **Step 1: Add shared RED fixtures.** Extend `modelParserParity` with unknown suspension members, wrong discriminator, missing/extra passage, duplicate passage IDs, unknown/hold attachment node, nonfinite/out-of-bounds passage point, missing/duplicate branch, wrong branch pair/order, distinct branch anchors, invalid rest/radius/material, missing/unknown/duplicate pose, explicit null, scalar-kind mismatch, duplicate raw JSON key, raster sibling, second model, baked cord/anchor, and order violation.

- [ ] **Step 2: Add parity test consumers before implementation.** Python must load every matrix case and assert its expected category; Swift must load the same JSON fixture names and assert the corresponding `BoardPackageStoreError` category. Add a valid fixture with exactly four passages, exactly two branches, and four pose keys.

  ```python
  @pytest.mark.parametrize("fixture", _shared_two_branch_fixtures(), ids=lambda f: f["name"])
  def test_two_branch_fixture_category(fixture, tmp_path):
      package = _write_shared_model_parser_parity_package(tmp_path, fixture)
      with pytest.raises(ValueError, match=fixture["pythonError"]):
          load_board_catalog_module().load_board_package(package)
  ```

- [ ] **Step 3: Run Python and Swift RED checks.**

  ```bash
  python3 -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests
  ```

  Expected: new `twoBranchCord` fixtures fail as unsupported/unknown.

- [ ] **Step 4: Implement strict parsing and descriptor binding.** Require two named pairs of two distinct passages, exactly two branches, one ordered pair per branch, a single common anchor derived from unposed bounds plus offset, and importer-visible passage nodes whose roles are body/attachment but never hold. Preserve duplicate-key/raw scalar-kind/order checks and explicit-null rejection in both languages. Keep `singleCord` behavior unchanged for other packages.

- [ ] **Step 5: Verify and commit the contract.**

  ```bash
  python3 -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardModels/test_model_descriptor.py Tools/HangboardModels/test_compile_model_package_blender.py -q
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests
  git add Tools/HangboardPackages Tools/HangboardModels HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/Fixtures/BoardPackageValidationFixtures.json
  git commit -m "Add strict two-branch suspension package contract"
  git push
  ```

**Review gate:** A Terra reviewer is allowed only if Luna's bounded parser attempt exposes cross-language/order-sensitive integration complexity. The reviewer verifies that exactly four passage points and one common anchor are enforced, while existing `singleCord` boards and raster/model isolation remain valid.

### Task 3: Luna — implement deterministic two-branch solver and geometry-independent policy tests

**Files:**
- Modify: `HangTen/Views/SuspendedBoardPresentation.swift`
- Modify: `HangTenTests/SuspendedBoardPresentationTests.swift`

**Interfaces:** Add:

```swift
struct SuspendedBranchSolution {
    let id: String
    let passageIDs: [String]
    let spans: [[SIMD3<Float>]]
    let centerlineSamples: [SIMD3<Float>]
    let tangentSamples: [SIMD3<Float>]
    let arcLength: Float
}

struct SuspendedTwoBranchSolvedPresentation {
    let boardTransform: simd_float4x4
    let fixedAnchor: SIMD3<Float>
    let branches: [SuspendedBranchSolution]
    let cameraFraming: SuspendedCameraFraming
    let tubeRadius: Float
    let requiredClearance: Float
}

static func SuspendedBoardPresentation.solve(
    pose: BoardModelCanonicalPose,
    suspension: BoardModelTwoBranchSuspension,
    bounds: BoardModelBounds
) throws -> SuspendedTwoBranchSolvedPresentation
```

The solver uses the existing fixed 32 samples, gravity vector, `1e-6 m` bisection tolerance, and `1e-5 m` taut tolerance. Each branch is the ordered continuous path `anchor -> passage[0] -> passage[1] -> anchor`: its declared `restLength` is the total route length; reserve the exact modeled interior passage span, then distribute the remaining free length between the two anchor-to-passage catenaries in proportion to their endpoint separations. Reject a declared length shorter than the two endpoint separations plus the interior span. The solver and package verifier must assert this decomposition and the measured route length within the existing tolerances. Preserve positional continuity at passage joins; tangent discontinuity between an independently solved catenary and the modeled interior span is permitted. Do not replace the passage span with a direct shortcut or invent knot geometry.

- [ ] **Step 1: Add RED pure tests.** Cover identity and quarter-turn transforms for all four passages, exact taut free span, slack catenary endpoint/tangent/length determinism, common-anchor equality, passage order, short rest length, zero-horizontal slack, nonunit pose, nonfinite values, self-intersection, and camera inclusion of board corners, both passages, both branches, and the anchor.

- [ ] **Step 2: Run focused RED tests.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/SuspendedBoardPresentationTests
  ```

- [ ] **Step 3: Implement the two-branch solve.** Transform passage points by the pose while keeping the anchor fixed; solve each free span in the gravity plane; concatenate exact endpoint samples and the declared ordered interior route; reject an impossible or nonfinite result. Expose samples to SceneKit but do not claim mesh clearance in this pure layer.

- [ ] **Step 4: Add a deterministic clearance/probe input contract.** Return the cord radius, required radius-plus-clearance threshold, and ordered samples so the actual-export and SceneKit layers can perform triangle/ray checks away from approved passage interfaces. Do not use screen masks or camera visibility as collision proof.

- [ ] **Step 5: Run GREEN tests and commit.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/SuspendedBoardPresentationTests
  git add HangTen/Views/SuspendedBoardPresentation.swift HangTenTests/SuspendedBoardPresentationTests.swift
  git commit -m "Solve deterministic two-branch suspended cords"
  git push
  ```

**Review gate:** Luna reviews mathematical determinism and endpoint/length failure behavior; any unresolved non-geometry solver failure may escalate to Terra. No reviewer may adjust passage or notch geometry to make a branch pass.

### Task 4: Astra — re-author Flash Board geometry from approved face and closeup evidence

**Files:**
- Modify only through Astra's geometry task: `Tools/HangboardModels/tension_flash_board.py`
- Create/update owned source and renders: `.context/pretty-crocodile-tension-flash-board/flash-board.blend`, `.context/pretty-crocodile-tension-flash-board/renders/*`

**Interfaces:** The generator creates exactly one `flash-board-body`, seven selectable hold meshes with the approved IDs, and four importer-visible physical passage features. Shallow lower ledges/notches, upper ledges, and passage surfaces are body geometry or explicitly nonselectable decoration; they do not gain logical IDs, descriptor hold bindings, accessibility, or picking masks. The source contains no display cord, anchor, knot, nail, carabiner, wall, ceiling, mounting hardware, source-image trace, segmentation, or image-derived contour.

- [ ] **Step 1: Preserve and inspect current geometry work.** Astra receives the approved evidence packet, current uncommitted generator diff, coordinate frame, seven-ID inventory, and the defect statement: hold shapes/placement and backside/ledge/notch completeness are inaccurate. Astra must reconcile the existing work instead of silently discarding it.

- [ ] **Step 2: Author analytic geometry directly.** Model the cylindrical body, three-well face with outboard small crimps and upper/lower ledges, opposite two-well face with documented ledges, four end passages, real mouth/back fillets, and continuous exterior/inter-pocket ligaments. Keep all dimensions/radii/depths as display estimates and author symmetry where the evidence supports it.

- [ ] **Step 3: Produce review renders before final export.** Generate front, opposite-face, oblique, clay-detail, and close passage/notch views with matched cameras. Record each view and Astra's fidelity judgment in the owned geometry report; a lower-cost worker may flag discrepancies but may not repair physical shape.

- [ ] **Step 4: Commit only geometry source and owned review outputs after human review.**

  ```bash
  rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/tension_flash_board.py -- --output .context/pretty-crocodile-tension-flash-board/geometry --render
  git add Tools/HangboardModels/tension_flash_board.py
  git commit -m "Refine Flash Board faces passages and shallow ledges"
  git push
  ```

**Review gate:** Astra's front/opposite/oblique/detail renders must be compared to all approved evidence. The human-approved geometry set is required before compilation; if fidelity is wrong, return only to Astra.

### Task 5: Luna — compile and verify actual USDZ geometry, materials, passages, and per-surface cord probes

**Files:**
- Modify: `Tools/HangboardModels/verify_tension_flash_board.py`, `Tools/HangboardModels/test_verify_tension_flash_board.py`
- Modify compiler only if the reviewed export contract requires it: `Tools/HangboardModels/compile_model_package.py`, `model_descriptor.py`, and their tests
- Create owned output: `.context/pretty-crocodile-tension-flash-board/package/`, `export-verification.json`

**Interfaces:** `verify_tension_flash_board.py --output PACKAGE --skip-renders` reimports only the exported USDZ after source materials/images are removed and writes a report with exact node correspondence, roles, hashes, material/image payload, triangle count, bounds, logical bindings, and per-position probe results. Its `positionProbes[positionID]` contains `surfaceRayResults`, `branchClearanceResults`, `allRayProbesPassed`, `allClearanceProbesPassed`, and exact diagnostics.

- [ ] **Step 1: Add RED report assertions.** Require one body, exactly seven descriptor-bound IDs, four passage correspondences, no extra selectable mesh, material on every board/contact, no baked cord/anchor/hardware, and every position's expected face inventory. Add report fixtures where a lower ledge or passage is incorrectly bound as a hold.

- [ ] **Step 2: Add RED actual-export probes.** Build front-to-back parallel rays for every active hold surface and assert nearest imported triangle ID; build sampled cord-tube probes for both branches in all four canonical poses and require radius-plus-clearance outside passage interfaces. Assert full exterior ligaments and inter-pocket ligaments from actual mesh/rays, not a camera mask.

- [ ] **Step 3: Compile through the self-bootstrapping Blender entrypoint.**

  ```bash
  rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/pretty-crocodile-tension-flash-board/flash-board.blend --board-json Hangboards/tension-flash-board/board.json --output-directory .context/pretty-crocodile-tension-flash-board/package
  ```

  If Blender SIGSEGVs before Python in the managed sandbox, run exactly one fresh-config minimal repro, then one narrowly authorized identical host-context comparison; use owned config/cache/output and retain the diagnostics. Do not misclassify a pre-Python Metal boundary as geometry failure or touch shared services.

- [ ] **Step 4: Implement minimal verifier changes and run GREEN checks.** Reimport actual output in isolation, preserve importer-renamed correspondence on temporary export copies, and record exact command/options, hashes, node mapping, rays, catenary samples, and failure diagnostics.

  ```bash
  rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/verify_tension_flash_board.py -- --output .context/pretty-crocodile-tension-flash-board/package --skip-renders
  python3 -m pytest Tools/HangboardModels/test_verify_tension_flash_board.py -q
  ```

- [ ] **Step 5: Commit tooling and verifier report.**

  ```bash
  git add Tools/HangboardModels/verify_tension_flash_board.py Tools/HangboardModels/test_verify_tension_flash_board.py Tools/HangboardModels/compile_model_package.py Tools/HangboardModels/model_descriptor.py
  git commit -m "Verify Flash Board passages and per-surface suspension clearance"
  git push
  ```

**Review gate:** Luna reviews the report and tests; Terra may review only if export/import correspondence or probe tooling remains intricate after a bounded Luna attempt. Geometry defects return to Astra and are never hidden by verifier thresholds.

### Task 6: Luna — integrate typed two-branch presentation into SceneKit and position routing

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift`, `HangTen/Views/BoardMapView.swift`
- Modify: `HangTenTests/BoardModelTests.swift`

**Interfaces:** `BoardModelScene` accepts `positionID: String?` and a `BoardModelSuspension`; for `.twoBranchCord` it exposes `select(positionID:)`, applies the canonical `SCNMatrix4`, solves both branches, and atomically replaces its transient cord layer. `BoardModelSurface` continues passing position separately from presentation identity. Model picking uses `modelPickCategory = 1`; transient cord uses `cordCategory = 2` and is never in accessibility.

- [ ] **Step 1: Add RED native tests.** Use a synthetic descriptor and two-branch fixture to assert transformed endpoints, common fixed anchor, both branch paths, passage/notch nonselection, closest actual triangle for every active hold, cord ignored even when visually crossing a ray, no cord accessibility element, and explicit unavailable state on every listed malformed/unsolved case.

- [ ] **Step 2: Implement transient SceneKit branch rendering.** Create cylinders/junctions from fixed solver samples with independent cord materials, exclude them from the selectable node set, and remove/rebuild them atomically on pose transitions. Verify actual mesh/tube clearance before adding the layer; no SceneKit anchor node is created.

- [ ] **Step 3: Implement canonical reset and orbit policy.** Animate board, camera, and both branches for `0.18` seconds on hold selection, workout position resolution, or explicit position change. Pan/pinch may change only camera azimuth/elevation/allowed zoom; selection after orbit always snaps to canonical pose/frame and ends on the exact deterministic cord.

- [ ] **Step 4: Preserve non-suspended model behavior and fail closed.** Keep existing non-suspended model path unchanged; missing passage node, invalid pose/branch, collision, bad framing, or load failure routes to `BoardModelUnavailableView` without raster, straight-line, alternate-model, or visible-anchor rescue.

- [ ] **Step 5: Run focused native tests and commit.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/SuspendedBoardPresentationTests
  git add HangTen/Views/BoardModelView.swift HangTen/Views/BoardMapView.swift HangTenTests/BoardModelTests.swift
  git commit -m "Render Flash Board two-branch suspended presentation"
  git push
  ```

**Review gate:** Review native nearest-hit diagnostics, transaction flushes, camera/board independence, and accessibility tree. Escalate to Terra only after a bounded Luna renderer attempt exposes a non-geometry integration issue.

### Task 7: Luna — promote the verified model-only Flash package

**Files:**
- Modify: `Hangboards/tension-flash-board/board.json`
- Replace assets: `Hangboards/tension-flash-board/assets/primary.usdz`, `primary.model.json`
- Delete only the four former Flash raster files: `primary.png`, `three-edge-inverted.png`, `two-edge-surface.png`, `two-edge-inverted.png`
- Modify tests: `Tools/HangboardPackages/tests/test_approved_board_packages.py`, `test_board_package_staging.py`
- Modify audit implementation/manifest only if its existing contract rejects this exact model-only supersession: `presentation_remediation_audit.py`, `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`

**Interfaces:** The final board document retains all seven holds, four positions, transitions, and provenance; declares one `primary` model media with `suspension.type == "twoBranchCord"`; has no raster media or paths; and declares assets exactly `{assets/primary.usdz, assets/primary.model.json}` with descriptor hash equal to USDZ bytes.

- [ ] **Step 1: Add RED promotion/staging assertions.** Assert exact logical ID/order, four position IDs and pose keys, two named passage pairs, two branch IDs, common anchor semantics, no raster or path fields, no PNG, exact asset inventory, and staged byte/hash equality.

- [ ] **Step 2: Write the model-only document and copy verified bytes.** Use only verifier-approved USDZ/descriptor bytes and display-estimate values from the audit. Preserve source-backed availability and `setupRequired` transitions. Do not add lower ledges as holds or source dimensions.

- [ ] **Step 3: Handle historical raster records narrowly.** Run the audit first. If needed, add a terminal `supersededByModelMigration` state naming only `tension.flash-board`; prove raster packages still require complete PNG evidence and arbitrary missing assets are still rejected.

- [ ] **Step 4: Run full package promotion checks.**

  ```bash
  scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  python3 -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py Tools/HangboardPackages/tests/test_board_package_staging.py Tools/HangboardPackages/tests/test_model_first_packages.py -q
  python3 Tools/HangboardPackages/scripts/migrate_to_schema_v2.py --root Hangboards --check
  ```

- [ ] **Step 5: Commit and push the package migration.**

  ```bash
  git add -A Hangboards/tension-flash-board Tools/HangboardPackages docs/source-audits
  git commit -m "Promote Flash Board two-branch model package"
  git push
  ```

**Review gate:** Verify package bytes against the actual-export report and ensure no historical audit weakening or unintended package changes entered the commit.

### Task 8: Luna — verify Android model-only boundary

**Files:**
- Modify: `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt`
- Modify production `Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt` only if the focused test proves an actual incorrect fallback.

**Interfaces:** `AssetBoardRepository` continues to omit/unavailable model-only Flash; it must not look up `assets/primary.png`, derive raster geometry, attach a neighboring board's plan mapping, or create a fake Android USDZ renderer.

- [ ] **Step 1: Add the Flash fixture regression.** Provide only model/descriptor paths and assert omission/unavailable behavior, no PNG access, and unchanged neighboring raster-board loading.

- [ ] **Step 2: Run the focused Android test.**

  ```bash
  cd Android && ./gradlew test --tests com.hangten.android.content.BoardRepositoryTest
  ```

- [ ] **Step 3: Run iOS package regressions and commit the Android boundary test.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardModelTests
  git add Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt
  git commit -m "Keep Flash Board model-only on Android"
  git push
  ```

**Review gate:** Confirm no Android production change is present unless the test demonstrated a real fallback defect; review the exact accessed asset paths.

### Task 9: Luna — run owned iOS first-migration acceptance and record reusable skill lessons

**Files:**
- Create owned transient results: `.context/pretty-crocodile-tension-flash-board/{DerivedData,FlashBoard.xcresult,flash-*.png,ios-review.md}`
- Modify only for a verified reusable incident: `.codex/skills/migrate-hangboard-to-3d/SKILL.md` and a focused regression test/source file

**Interfaces:** The review uses the exact simulator name `Hang Ten Paseo pretty-crocodile Review`, records its UUID before XCTest, and retains front/opposite/oblique/active-hold captures and native picking diagnostics for all four positions. The final review report marks every acceptance item pass or a concrete environment/product blocker.

- [ ] **Step 1: Install the ownership and cleanup trap before simulator creation.** Follow `validate-hang-ten-ios`: set `PASEO_WORKTREE_PATH`, record pending and owned manifests, create the exact named simulator, use only its UUID, and register cleanup for simulator, DerivedData, result bundle, and screenshots.

  ```bash
  review_device_uuid="$(xcrun simctl create 'Hang Ten Paseo pretty-crocodile Review' 'iPhone 16 Pro' 'iOS 26.0')"
  printf '%s\n' "$review_device_uuid" > .context/pretty-crocodile-tension-flash-board/review-device.uuid
  ```

- [ ] **Step 2: Build focused XCTest with owned DerivedData/result bundle.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$review_device_uuid" -derivedDataPath .context/pretty-crocodile-tension-flash-board/DerivedData -resultBundlePath .context/pretty-crocodile-tension-flash-board/FlashBoard.xcresult -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/SuspendedBoardPresentationTests
  ```

- [ ] **Step 3: Capture the interactive acceptance matrix.** Inspect three-well and two-well upright/inverted positions in portrait and landscape; retain front/opposite/oblique/active-hold views; tap all seven approved holds; tap passages/notches and prove no selection; verify highlight, clear/reappear, workout-driven transitions, cord continuity through both passage pairs, selection snap, orbit, and reset after orbit.

- [ ] **Step 4: Verify explicit unavailable behavior.** Exercise malformed/short/nonfinite/missing-passage/collision/framing cases and confirm `boardModel.unavailable` with no raster, straight-line, visible-anchor, or alternate-model fallback. If CoreSimulator is unavailable, record the exact connection/build failure and stop acceptance without restarting or killing shared services.

- [ ] **Step 5: Add only concrete reusable skill notes.** For each issue actually encountered, append a dated note containing the exact symptom, root cause, safe remedy, and regression command. At minimum, if observed during this migration, record that transformed passage-to-fixed-anchor feasibility must be checked per canonical pose (not only source rest length), and that a pre-Python Blender Metal SIGSEGV is an environment boundary requiring one minimal repro plus one narrow host comparison. Do not add speculative guidance.

- [ ] **Step 6: Run final verification, clean owned resources, commit, and push.**

  ```bash
  python3 -m pytest Tools/HangboardModels/test_evidence_packet.py Tools/HangboardModels/test_verify_tension_flash_board.py Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_approved_board_packages.py -q
  scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  git add .codex/skills/migrate-hangboard-to-3d/SKILL.md HangTenTests Tools/HangboardModels Tools/HangboardPackages docs/source-audits
  git commit -m "Record Flash Board two-branch acceptance lessons"
  git push
  ```

**Review gate:** Final review checks the evidence packet, geometry renders, actual-export report, staged hashes, Python/Swift/Android tests, native picking diagnostics, and iOS captures. The migration is not accepted while required iOS checks remain blocked by CoreSimulator; retain the blocker report and leave shared services untouched.

## Self-Review

- **Spec coverage:** Tasks 1–2 cover the evidence update, source-versus-estimate ruling, exact closed contract, raw order/scalar/null rejection, common anchor, four passages, and explicit migration from `singleCord`. Task 3 covers deterministic per-branch catenary and failure outcomes. Task 4 covers Astra-only physical shape correction and nonselectable ledges/notches. Task 5 covers actual export materials, node correspondence, per-surface rays/catenaries, ligaments, and diagnostics. Task 6 covers SceneKit two-branch rendering, picking/accessibility, orbit/reset, transitions, and unavailable behavior. Tasks 7–9 cover package promotion, Android boundary, owned iOS acceptance, captures, cleanup, and reusable skill notes.
- **Placeholder scan:** No `TBD`, `TODO`, “implement later,” or unspecified “appropriate error handling” instructions appear. Runtime simulator UUID is captured by the concrete `xcrun simctl create` command and reused through the shell variable rather than invented in the plan.
- **Type consistency:** `BoardModelPassage`, `BoardModelPassagePairs`, `BoardModelCordBranch`, `BoardModelTwoBranchSuspension`, `BoardModelSuspension`, `SuspendedBranchSolution`, and `SuspendedTwoBranchSolvedPresentation` are defined before later tasks consume them. JSON names `passages`, `branches`, `passageIDs`, `anchor`, and `canonicalPoses` match the Swift members and verifier report keys. Existing `singleCord` is represented as a separate enum case and remains unchanged for unrelated boards.
- **Cost and ownership check:** Astra is the only geometry author; Luna owns the bounded evidence/schema/math/verifier/package/Android/iOS work; Terra is conditional review escalation only. The plan never asks a lower-cost worker to change physical shape to satisfy a test, and it preserves the existing uncommitted generator before the Astra task.

Plan complete and saved to `docs/superpowers/plans/2026-09-10-flash-board-two-branch-suspension.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task with review gates.
2. **Inline Execution** — execute the tasks in this session with executing-plans checkpoints.

Which approach?
