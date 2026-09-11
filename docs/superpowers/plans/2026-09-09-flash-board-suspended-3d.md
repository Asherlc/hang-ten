# Tension Flash Board Suspended 3D Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `tension.flash-board` from four raster orientations to one source-faithful USDZ with package-driven canonical positions and a deterministic, invisible-anchor suspended-cord presentation in the iOS 3D renderer.

**Architecture:** Keep one model-only presentation (`primary.usdz` plus a hash-bound descriptor) and retain all seven existing logical hold IDs. Four existing position IDs map to that presentation; `media.suspension` supplies an attachment point, fixed world-anchor estimate, cord parameters, and one canonical pose/camera per position. SceneKit applies the selected pose to the USDZ, builds a non-pickable catenary transient layer, and permits only camera orbit; it never rotates a hanging board from gestures.

**Tech Stack:** Python 3 standard-library package validation, Blender/USDZ compiler and verifier, Swift/SwiftUI/SceneKit/XCTest, Xcode Simulator. Android remains explicitly model-unavailable (no raster fallback and no fake 3D implementation) until a separately scoped Android renderer exists.

**Spec:** `docs/superpowers/specs/2026-09-09-suspended-hangboard-presentation-design.md`

## Global Constraints

- Read `.codex/skills/migrate-hangboard-to-3d/SKILL.md` and the spec before every task; obey its evidence gate, package isolation, picking, material, and cleanup requirements.
- Use Luna for every task except the final physical board geometry/fidelity pass. Escalate non-geometry work to Terra only after a bounded Luna attempt fails. Delegate only the reviewed physical board shape to Astra after the approved evidence gate; Astra must not author suspension math, metadata, schema, tests, or integration.
- The shipped Flash Board has exactly one USDZ and one descriptor, no PNGs, no 2D hold paths, no extra orientation model, no baked display cord/anchor/nail/environment, and no mounting holes or hardware meshes. An evidence-supported integral attachment feature is permitted.
- Preserve the logical hold IDs and order: `three-edge-left`, `three-edge-center`, `three-edge-right`, `two-edge-left`, `two-edge-right`, `small-crimp-left`, `small-crimp-right`. Preserve their source-backed metadata; do not turn display estimates into physical dimensions.
- Reuse position IDs `three-edge-upright`, `three-edge-inverted`, `two-edge-upright`, and `two-edge-inverted`. All point to `primary`; their pose keys are the position IDs, not replacement logical holds.
- The anchor is invisible and fixed in scene world coordinates. `anchor.offsetFromBoardBounds` is an authored display estimate evaluated once from the unposed descriptor bounds; it does not rotate or translate with later board poses. Every pose must independently satisfy the endpoint/length and clearance checks.
- A slack cord is solved in the gravity plane. A taut line is valid only when `abs(restLength - endpointDistance) <= 1e-5 m`; shorter length, nonfinite inputs, or vertical-only slack with no deterministic gravity-plane direction is invalid/unavailable rather than guessed.
- Store generated evidence, editable Blender source, compiler package, reports, screenshots, xcresults, and ownership record under `.context/pretty-crocodile-tension-flash-board/`. Install the required cleanup trap for disposable simulator, DerivedData, result bundle, and temporary render/export directories; retain the reviewed evidence/report files until the owning migration handoff is complete.
- Do not start an HTTP server for this work. Android is not a fallback: retain its existing model-package omission behavior and explicitly test it after Flash becomes model-only.

## File Structure

| Path | Change | Responsibility |
| --- | --- | --- |
| `Tools/HangboardModels/evidence_packet.py` | Modify | Add closed, source-linked portable-suspension evidence fields. |
| `Tools/HangboardModels/test_evidence_packet.py` | Modify | Prove required retained views, position mapping, attachment evidence, and estimate labeling. |
| `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` | Modify | Parse and validate `singleCord` media plus descriptor attachment nodes. |
| `Tools/HangboardPackages/tests/test_model_first_packages.py` | Modify | Python parser/asset-isolation/suspension rejection matrix. |
| `HangTenTests/Fixtures/BoardPackageValidationFixtures.json` | Modify | Shared Swift/Python malformed suspended-model fixture matrix. |
| `HangTen/Models/TrainingModels.swift` | Modify | Public typed suspension, canonical pose, attachment-node descriptor types. |
| `HangTen/Models/BoardPackageStore.swift` | Modify | Closed Swift decoder/validator and conversion into typed model media. |
| `HangTenTests/BoardPackageStoreTests.swift` | Modify | Swift parity and model-package loading tests. |
| `Tools/HangboardModels/model_descriptor.py` and `compile_model_package.py` | Modify | Permit exactly one non-selectable `attachment` mesh role while preserving body/hold bindings. |
| `Tools/HangboardModels/tension_flash_board.py` | Create | Astra-owned, source-reviewed Blender authoring entrypoint; no cord or environment geometry. |
| `Tools/HangboardModels/verify_tension_flash_board.py` | Create | Actual-export inventory, attachment, material, triangle, collision-probe, and review-report verifier. |
| `HangTen/Views/SuspendedBoardPresentation.swift` | Create | Pure deterministic transforms/catenary/clearance/framing policy, independent of SwiftUI gestures. |
| `HangTen/Views/BoardModelView.swift` | Modify | Pose application, transient cord, masked picking, camera orbit, canonical reset, unavailable routing. |
| `HangTen/Views/BoardMapView.swift` | Modify | Carry selected/resolved position independently from presentation ID into model rendering. |
| `HangTenTests/SuspendedBoardPresentationTests.swift` | Create | Solver and pose unit tests. |
| `HangTenTests/BoardModelTests.swift` | Modify | Native SceneKit cord-ignore, canonical pose, orbit/reset, exact nearest-triangle checks. |
| `Hangboards/tension-flash-board/board.json` | Modify | Model-only package, one primary presentation, four positions, suspension metadata. |
| `Hangboards/tension-flash-board/assets/{primary.usdz,primary.model.json}` | Create | Hash-bound final model package; delete the four raster PNGs only in the promotion task. |
| `docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md` | Create | Retained source mapping, approval, estimates, omissions, and face-to-hold audit. |
| `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json` and package audit tests | Modify only if the existing audit rejects the now-superseded raster records | Mark the four historic raster records superseded by this model-only migration; preserve their provenance, never fabricate PNG checks. |
| `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt` | Modify | Confirm model-only Flash is omitted/unavailable without attempting a raster asset. No Android production source changes. |

---

### Task 1: Luna — retain and approve the Flash Board portable evidence packet

**Files:**
- Create (workspace-owned, durable handoff evidence): `.context/pretty-crocodile-tension-flash-board/{ownership.json,evidence-packet.json,evidence-approval.md,sources/*}`
- Modify: `Tools/HangboardModels/evidence_packet.py`, `Tools/HangboardModels/test_evidence_packet.py`, `Tools/HangboardModels/evidence-packet-template.json`
- Create: `docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md`

**Interfaces:** Produces a validated `EvidencePacket.suspended_presentation` containing `positionMappings`, `attachmentEvidence`, `visualApproval`, and `displayEstimates`. Every mapping has `{positionID, holdIDs, sourceLocalPath}`; attachment evidence has a retained source reference; every display estimate is labeled `displayEstimate` or `estimatedFromApprovedModel`.

- [ ] **Step 1: Write failing packet-validator tests.** Add a valid portable fixture and rejection cases for missing second distinct view, an attachment-region view claimed as available but not retained, unknown/duplicate position IDs, unretained source references, unlabelled cord/anchor/pose/camera estimate, missing approval, and a geometry proposal sneaking into the evidence packet.

- [ ] **Step 2: Run the focused evidence tests and confirm RED.**

  ```bash
  python3 -m pytest Tools/HangboardModels/test_evidence_packet.py -q
  ```

  Expected: the newly named suspended-presentation tests fail because the closed packet schema has no such member.

- [ ] **Step 3: Implement the closed packet extension.** Accept `suspendedPresentation` only when all referenced source paths are retained/hash-checked; reject unknown keys and preserve generic packets by making it optional. Require the approval object to name the exact two-or-more materially distinct snapshot paths and decision date; require a nonempty source-linked mapping for every declared portable position, while the Flash audit/fixture asserts its exact four mappings. Record unsupported dimensions/knot detail as unknowns rather than numeric shape prescriptions.

- [ ] **Step 4: Retain real sources and write the audit.** Capture the manufacturer product/front source and each approved Google-image-search discovery result at its publisher URL (manufacturer tier first; commerce tier only with retailer and snapshot hashes). Retain the three currently approved visual candidates plus any better exact-revision attachment view found, hash every exact byte, record publisher/tier/view/support/limitations, map the four positions to the seven existing IDs, and explicitly record invisible anchor, cord length/radius/material, attachment coordinates, poses, and camera as estimates. Record the human-approved exact view set in `evidence-approval.md`; do not proceed to Astra without it.

- [ ] **Step 5: Validate and commit source-contract code/docs (not ignored evidence).**

  ```bash
  python3 -B Tools/HangboardModels/validate_evidence_packet.py .context/pretty-crocodile-tension-flash-board/evidence-packet.json
  python3 -m pytest Tools/HangboardModels/test_evidence_packet.py -q
  git add Tools/HangboardModels/evidence_packet.py Tools/HangboardModels/test_evidence_packet.py Tools/HangboardModels/evidence-packet-template.json docs/source-audits/2026-09-09-tension-flash-board-suspended-3d.md
  git commit -m "Add suspended Flash Board evidence contract"
  git push
  ```

### Task 2: Luna — extend descriptor and package contracts for one suspended model

**Files:**
- Modify: `Tools/HangboardModels/model_descriptor.py`, `Tools/HangboardModels/compile_model_package.py`, `Tools/HangboardModels/test_model_descriptor.py`, `Tools/HangboardModels/test_compile_model_package_blender.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`, `Tools/HangboardPackages/tests/test_model_first_packages.py`
- Modify: `HangTen/Models/TrainingModels.swift`, `HangTen/Models/BoardPackageStore.swift`, `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`

**Interfaces:** Add descriptor node role `attachment` (zero or one; never a logical hold) and `BoardModelSuspension`:

```swift
struct BoardModelSuspension: Hashable {
  let attachment: BoardModelAttachment
  let anchor: BoardModelInvisibleAnchor
  let cord: BoardModelCord
  let canonicalPoses: [String: BoardModelCanonicalPose]
}
```

`BoardModelMedia.suspension: BoardModelSuspension?`; a model descriptor node addressed by `attachment.nodeID` must be role `.body` or `.attachment`, never `.hold`.

- [ ] **Step 1: Add failing shared parser fixtures.** Extend the existing Python/Swift fixture matrix with: unknown suspension field, `type != singleCord`, missing/extra canonical pose, duplicate position key in raw JSON, nonfinite or nonunit quaternion, nonpositive radius/rest length, missing/hold attachment node, point outside inclusive model bounds, shorter-than-endpoint rest length, raster sibling, second model, and baked cord/anchor role. Add Python and Swift tests consuming the same names and expected error categories.

- [ ] **Step 2: Confirm both parsers are RED.**

  ```bash
  python3 -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests
  ```

  Expected: fixtures mentioning `suspension` or attachment nodes are rejected as unknown.

- [ ] **Step 3: Implement the descriptor role without weakening model binding.** Permit at most one `attachment` node in compiler/descriptor parsing; still require exactly one body and an exact logical hold-node partition. It must have no `holdID`, be materially valid, be importer-visible, and never enter derived hold frames. Continue rejecting arbitrary decoration, rope, anchor, nail, and unbound meshes.

- [ ] **Step 4: Implement closed suspension parsing in Python and Swift.** Require exactly the spec keys, finite three-vectors, a normalized quaternion (unit tolerance `1e-6`), positive finite cord values, invisible anchor visibility, and exactly one pose for every `positions[].id` when suspension is present. Compute the fixed unposed anchor from descriptor bounds plus offset, transform each attachment using its pose, and reject `restLength < endpointDistance - 1e-5`. Preserve raw member order checks so duplicate keys cannot escape keyed decoding.

- [ ] **Step 5: Verify green parser parity and commit.**

  ```bash
  python3 -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardModels/test_model_descriptor.py Tools/HangboardModels/test_compile_model_package_blender.py -q
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests
  git add Tools/HangboardModels Tools/HangboardPackages HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/Fixtures/BoardPackageValidationFixtures.json
  git commit -m "Add suspended model package validation"
  git push
  ```

### Task 3: Luna — implement deterministic suspended-presentation math before SceneKit wiring

**Files:**
- Create: `HangTen/Views/SuspendedBoardPresentation.swift`, `HangTenTests/SuspendedBoardPresentationTests.swift`

**Interfaces:** `SuspendedBoardPresentation.solve(pose:suspension:bounds:) throws -> SuspendedSolvedPresentation` returns board transform, fixed anchor, transformed attachment, finite ordered centerline samples, and canonical camera framing. `SuspendedCordSolver` uses a fixed 32 samples and bisection tolerance `1e-6 m`; it does no UI, USDZ load, or picking.

- [ ] **Step 1: Write RED unit tests.** Cover identity and quarter-turn attachment transforms; exact taut segment; slack catenary endpoints/arc length/finite tangent continuity; deterministic repeat solve; invalid short length; nonunit transform; zero-horizontal slack; self-intersection; and each pose’s attachment/cord camera-framing inclusion.

- [ ] **Step 2: Implement the catenary solver.** Project endpoints into gravity `SIMD3<Float>(0,-1,0)` and solve `2a*sinh(horizontal/(2a)) = sqrt(L²-vertical²)` with bounded bisection. Derive shift from endpoint vertical difference, sample including exact endpoints, and reject unbracketed/nonfinite/degenerate solves. Use the strict taut tolerance from Global Constraints rather than silently drawing a line for slack.

- [ ] **Step 3: Implement mesh-independent validation hooks.** Expose tube radius plus required clearance and the canonical camera target/frustum inputs as immutable solve output. The later SceneKit layer must supply actual mesh ray/triangle probes; the pure solver must not claim collision success from a screen mask.

- [ ] **Step 4: Run focused tests and commit.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/SuspendedBoardPresentationTests
  git add HangTen/Views/SuspendedBoardPresentation.swift HangTenTests/SuspendedBoardPresentationTests.swift
  git commit -m "Add deterministic suspended board presentation solver"
  git push
  ```

### Task 4: Luna — integrate poses, non-pickable cord, camera orbit, and unavailable behavior

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift`, `HangTen/Views/BoardMapView.swift`, `HangTenTests/BoardModelTests.swift`

**Interfaces:** `BoardModelSurface` gains `positionID: String?`; `BoardModelScene.select(positionID:)` applies a `SCNMatrix4` canonical board transform and creates/replaces its transient cord node. `BoardMapView` keeps selected position separately from selected presentation, passes resolved workout/active-hold position to the model, and a selection always calls `select(positionID:)` after an orbit.

- [ ] **Step 1: Write RED native/interaction tests.** Add a synthetic descriptor with body, attachment, and hold mesh. Assert: cord endpoint equals transformed attachment; nearest hit through a cord crossing uses model category mask and remains the descriptor hold; cord has no accessibility element; invalid solve/node/collision enters `boardModel.unavailable`; pan/pinch alter camera but not board/anchor/curve; selected hold/position resets camera and smoothly returns canonical pose after orbit.

- [ ] **Step 2: Build the transient SceneKit layer.** Put board meshes in `modelPickCategory = 1` and cord segments/junctions in `cordCategory = 2`; all tap and native picking calls must use category `1` with closest actual-triangle hits. Build cord from fixed samples with cylinders/junctions under a dedicated transient node, set it non-accessible, do not bind it to descriptor nodes, and remove/rebuild it atomically on canonical pose changes. Verify mesh/ray clearance (except declared attachment interface) before adding it.

- [ ] **Step 3: Implement interaction policy.** Add pan/pinch recognizers for bounded azimuth/elevation/zoom orbit around the solved board-and-cord target. Do not use `allowsCameraControl`; never rotate board or anchor from a gesture. On hold selection, workout position resolution, or explicit position change, animate board/camera for fixed `0.18` seconds to the canonical pose/frame and finish on the exact deterministic destination cord.

- [ ] **Step 4: Preserve existing behavior.** Non-suspended model packages keep their existing display/camera/picking path. Loading, malformed descriptor, missing attachment, invalid position, solve failure, collision, or nonfinite camera state routes to the existing explicit unavailable view; no raster, second model, visible anchor, or straight-line rescue is permitted.

- [ ] **Step 5: Run tests and commit.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/SuspendedBoardPresentationTests
  git add HangTen/Views/BoardModelView.swift HangTen/Views/BoardMapView.swift HangTenTests/BoardModelTests.swift
  git commit -m "Render suspended model poses and camera orbit"
  git push
  ```

### Task 5: Astra — author the reviewed physical Flash Board and Luna verifies the actual export

**Files:**
- Create: `Tools/HangboardModels/tension_flash_board.py`, `Tools/HangboardModels/verify_tension_flash_board.py`, `Tools/HangboardModels/test_verify_tension_flash_board.py`
- Create durable working files only: `.context/pretty-crocodile-tension-flash-board/{flash-board.blend,package/,renders/,export-verification.json}`

**Interfaces:** Astra receives only the approved evidence packet/audit and writes the physical board source through `tension_flash_board.py`; it tags one `body`, the seven named `hold` meshes, and at most one integral `attachment` mesh. `verify_tension_flash_board.py --output PACKAGE --skip-renders` writes a report proving exact descriptor/hash/binding/material/triangle/attachment facts.

- [ ] **Step 1: Hand Astra the narrow geometry brief after approval.** Include all retained approved images and limitations, hold/position mapping, coordinate-frame convention, material requirements, exact IDs, and explicit prohibitions: do not trace pixels, generate a display cord, add nail/hook/mount hardware, alter logical IDs, or choose cord/camera estimates.

- [ ] **Step 2: Astra author/review loop.** Directly author the cylindrical body, usable faces, real edge/recess transitions, and evidence-supported attachment feature. Review front, oblique, clay-detail, and attachment-region renders against approved views. Any fidelity defect returns only to Astra; no Luna visual workaround through lighting/camera/cord.

- [ ] **Step 3: Compile through the standard entrypoint.**

  ```bash
  rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/compile_model_package.py -- --blend .context/pretty-crocodile-tension-flash-board/flash-board.blend --board-json Hangboards/tension-flash-board/board.json --output-directory .context/pretty-crocodile-tension-flash-board/package
  ```

- [ ] **Step 4: Luna actual-export verification.** Reimport the USDZ with source materials removed; prove exact seven-ID binding, one body/optional attachment, no unbound/baked cord/anchor/hardware meshes, loaded image material bytes, explicit triangles, source-to-import correspondence, triangle ceiling recorded from actual output, and attachment node/point accessibility. Add ray probes for all selectable surfaces and cord-clearance probes against the actual board mesh for each canonical pose.

- [ ] **Step 5: Commit generator/verifier/tests only after verification.**

  ```bash
  rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/verify_tension_flash_board.py -- --output .context/pretty-crocodile-tension-flash-board/package --skip-renders
  python3 -m pytest Tools/HangboardModels/test_verify_tension_flash_board.py -q
  git add Tools/HangboardModels/tension_flash_board.py Tools/HangboardModels/verify_tension_flash_board.py Tools/HangboardModels/test_verify_tension_flash_board.py
  git commit -m "Add Flash Board model compiler verification"
  git push
  ```

### Task 6: Luna — promote the verified package and migrate the Flash Board document

**Files:**
- Modify: `Hangboards/tension-flash-board/board.json`, `Tools/HangboardPackages/tests/test_approved_board_packages.py`, `Tools/HangboardPackages/tests/test_board_package_staging.py`, `Tools/HangboardPackages/src/hangboard_packages/presentation_remediation_audit.py` only if the audit requires a model-only supersession state
- Create: `Hangboards/tension-flash-board/assets/primary.usdz`, `Hangboards/tension-flash-board/assets/primary.model.json`
- Delete: `Hangboards/tension-flash-board/assets/primary.png`, `three-edge-inverted.png`, `two-edge-surface.png`, `two-edge-inverted.png`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json` only if required by its updated audit contract

**Interfaces:** The final `board.json` has one `primary` model presentation and the exact `media.suspension` contract. Four `positions` map to `primary`; `positionTransitions` preserve source-supported setup requirements. The descriptor SHA matches final USDZ bytes and assets equal exactly `{primary.usdz, primary.model.json}`.

- [ ] **Step 1: Write promotion regression assertions.** Replace the raster-specific Flash test with assertions for logical ID/order preservation, one model presentation, no hold geometry/presentation ownership, exact four positions, exact pose key set, descriptor attachment node, declared asset equality, and no PNG. Add staging byte-equality characterization for Flash USDZ/descriptor.

- [ ] **Step 2: Create the model-only document.** Copy only the compiler-verified USDZ/descriptor bytes; set `primary` as original/default model media. Populate `positions` with the four existing IDs all targeting `primary`, preserve source-audited availability/transitions, and write suspension values only from the approved display-estimate audit. Do not add dimensions not established by sources.

- [ ] **Step 3: Resolve the historical raster audit honestly.** Run the existing presentation audit first. If it rejects missing former PNG records, add a generic `supersededByModelMigration` terminal record/state that preserves old hashes/provenance but exempts only the named migrated package from PNG byte/dimension checks; tests must prove raster packages still require complete records and only a valid model-only package can use this state. Do not delete historical evidence or make the audit ignore arbitrary missing assets.

- [ ] **Step 4: Validate package and promotion.**

  ```bash
  scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
  python3 -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py Tools/HangboardPackages/tests/test_board_package_staging.py Tools/HangboardPackages/tests/test_model_first_packages.py -q
  python3 Tools/HangboardPackages/scripts/migrate_to_schema_v2.py --root Hangboards --check
  ```

- [ ] **Step 5: Commit and push.**

  ```bash
  git add -A Hangboards/tension-flash-board Tools/HangboardPackages docs/source-audits
  git commit -m "Migrate Flash Board to suspended 3D model"
  git push
  ```

### Task 7: Luna — verify package consumers and the Android non-fallback boundary

**Files:**
- Modify: `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt`
- Modify only if a test reveals an actual incorrect fallback: `Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt`

**Interfaces:** Android continues `AssetBoardRepository` behavior for model-only media: no `BoardCanvas` data, no PNG read, no derived raster geometry, and plan mappings for that unavailable board are not silently attached elsewhere. This task does not introduce an Android USDZ renderer.

- [ ] **Step 1: Write the Flash-specific Android regression.** Feed a model-only `tension.flash-board` fixture with only `primary.usdz`/descriptor-like paths and assert it is omitted, no `assets/primary.png` lookup occurs, and a neighboring raster board remains valid.

- [ ] **Step 2: Run the Android content test.**

  ```bash
  cd Android && ./gradlew test --tests com.hangten.android.content.BoardRepositoryTest
  ```

  Expected: green using existing fail-closed model omission. If it is already green without production changes, do not modify Android runtime files.

- [ ] **Step 3: Run iOS package/model regressions and commit the Android test.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardModelTests
  git add Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt
  git commit -m "Cover Flash Board model-only Android boundary"
  git push
  ```

### Task 8: Luna — run the first-migration iOS acceptance review and retain outcomes

**Files:**
- Create transient owned results: `.context/pretty-crocodile-tension-flash-board/{DerivedData,FlashBoard.xcresult,flash-*.png,ios-review.md}`
- Modify only when an issue is discovered: the smallest responsible source file and `.codex/skills/migrate-hangboard-to-3d/SKILL.md`

**Interfaces:** Uses exact simulator name `Hang Ten Paseo pretty-crocodile Review`; confirms every supported Flash position’s canonical pose, cord continuity, pickability, highlight lifecycle, camera orbit/reset, workout-driven position, and unavailable state.

- [ ] **Step 1: Install ownership/cleanup trap before simulator creation.** Follow `validate-hang-ten-ios` exactly: register the generated UUID in pending then owned manifests, use its UUID for every command, set `PASEO_WORKTREE_PATH`, and ensure exit trap archives it plus exact local DerivedData/screenshots/result bundle.

- [ ] **Step 2: Build and run focused native tests on the owned device.**

  ```bash
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=<owned-uuid>' -derivedDataPath .context/pretty-crocodile-tension-flash-board/DerivedData -resultBundlePath .context/pretty-crocodile-tension-flash-board/FlashBoard.xcresult -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/SuspendedBoardPresentationTests
  ```

- [ ] **Step 3: Use DEBUG review routes and capture every position.** Inspect normal, preview, active, clear, reappear, and unavailable state; physically tap every visible contact on all four positions; verify the cord cannot receive a hit/accessibility focus; orbit camera, select another hold, and observe reset. Capture front, oblique, and active-hold images per pose in portrait and landscape.

- [ ] **Step 4: Record visual and physics review.** In `ios-review.md`, list simulator name/UUID, build command, package/USDZ/descriptor hashes, evidence set, each pose, each hold/tap result, ray/collision proof, reviewed screenshots, and any physical-device PBR limitation. Compare board silhouette/attachment/face/active highlighting with the approved evidence before calling it accepted.

- [ ] **Step 5: Feed real lessons back into the skill only when new.** If implementation required a generalizable workaround, failure mode, validation threshold, importer behavior, catenary edge case, or SceneKit gesture/picking rule absent from `.codex/skills/migrate-hangboard-to-3d/SKILL.md`, add a concise source-independent requirement and focused regression in the responsible test. Do not add board-specific dimensions or incident narration. Run the skill validator, commit/push the code/skill amendment, then rerun only checks invalidated by it.

  ```bash
  python3 /Users/asherlc/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/migrate-hangboard-to-3d
  ```

## Final Verification and Handoff

- [ ] Run `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, focused Python model/evidence/verifier tests, Android content test, and the affected iOS XCTest suite after the final change.
- [ ] Confirm the staged Flash USDZ and descriptor match source SHA-256 bytes exactly, and `assets/` contains no PNG/raster fallback.
- [ ] Confirm each canonical pose passes endpoint, length, finite, self-intersection, actual-mesh clearance, camera-framing, and nearest-bound-triangle/cord-ignore proof.
- [ ] Confirm `.context/pretty-crocodile-tension-flash-board/ios-review.md` has human visual acceptance; remove only disposable owned simulator/DerivedData/xcresult/scratch paths via the installed trap.
- [ ] Check `git status --short`, commit every intentional source change, and push the commit automatically.
