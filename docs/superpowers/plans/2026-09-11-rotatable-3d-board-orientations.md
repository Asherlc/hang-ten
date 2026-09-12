# Rotatable 3D Board Orientations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. All tasks below are completed and verified.

**Goal:** Add auditable, metadata-driven canonical orientations to the shared 3D board model while preserving exact hold identity, fixed-model behavior, suspension behavior, strict cross-language decoding, and interactive orbit.

**Architecture:** Extend the schema-v2 model media with a mutually exclusive `orientation` value and extend `BoardPosition` with an optional-on-wire, materialized-in-memory `holdIDs` array. Python package validation is the authoring/inventory gate; Swift is the iOS authoritative loader/renderer; Android either decodes the same contract or fails with its existing explicit unavailable-model result. SceneKit rotates one shared board container around the descriptor model-bounds center and recalculates orthographic framing.

**Tech Stack:** Swift 5/Xcode 26, SceneKit/simd, XCTest, Kotlin/JUnit/Gradle, Python 3/pytest, canonical JSON package files, isolated iOS Simulator validation.

**Spec:** `docs/superpowers/specs/2026-09-11-rotatable-3d-board-orientations-design.md`

## Global Constraints

- Keep schema version `2`; unknown JSON keys remain rejected.
- Store quaternions as normalized finite `[x, y, z, w]` values, rounded to nine decimal places, in the `hang-ten-board-v1` frame.
- Permit only `pivot: "modelBoundsCenter"`; the saved model path and descriptor remain the sole geometry sources.
- Orientation and suspension are mutually exclusive on one model media object; orientation is never interpreted as raster data.
- Model position `holdIDs` arrays are an exact partition of descriptor hold IDs, in canonical hold order; legacy decoded positions materialize the complete inventory.
- Do not add board-ID runtime conditionals, duplicate USDZs, mesh-normal inference, geometry edits, or generated masks/contours.
- Fixed/front-only model packages have one canonical position and no orientation block; suspension packages retain the existing solver and pose path.
- Baguette quaternion provenance must say exactly “authored display estimate” and cite retained manufacturer evidence; unsupported source claims are omitted.
- Manual orbit remains available on every interactive model detail/workout surface; display-only preview retains its intentional non-interactive policy.
- All generated build products, screenshots, logs, and owned external resources go under `.context/$workspace_owner/`; define `workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"` then `workspace_owner="${workspace_path:t}"` (the final path component) before creating resources, install an exit trap that stops/deletes only exact owned resources, and verify cleanup.
- Route independent, mechanical validator/fixture work to a cheaper agent when available; retain the same fresh-agent implementation and two-stage review gates for every task and use a stronger reviewer for cross-language/runtime or visual-risk work.

## File Map

- Modify `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` and `Tools/HangboardPackages/tests/test_model_first_packages.py` for Python schema/domain parsing, exact partition validation, canonical quaternion checks, and model inventory.
- Modify `HangTen/Models/TrainingModels.swift`, `HangTen/Models/BoardPackageStore.swift`, and `HangTenTests/BoardPackageStoreTests.swift` for the Swift domain contract and strict loader. `BoardPackageWriter.swift` is the legacy editable raster/v1 document and is not a v2 model serializer.
- Modify `HangTen/Views/BoardModelView.swift` and `HangTenTests/BoardModelTests.swift` for canonical rotation, center pivot, transformed framing, reset/orbit behavior, and no-cord orientation state.
- Modify `Android/app/src/main/java/com/hangten/android/content/BoardModels.kt`, `Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt`, and `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt` for the strict decoder boundary.
- Modify `Hangboards/yy-baguette-evo/board.json`, `Hangboards/nature-stone-hanger/board.json`, `Hangboards/beastmaker-1000/board.json`, `Hangboards/metolius-wood-grips-compact-ii/board.json`, and add `docs/source-audits/2026-09-11-3d-board-orientation-audit.md` for reviewed metadata and provenance.
- Modify/add `Tools/HangboardPackages/tests/test_model_orientation_inventory.py` for synthetic/discovered-package coverage; add simulator artifacts only under `.context/$workspace_owner/`.

## Native XCTest Lifecycle (Tasks 2–4)

Before each native XCTest RED or GREEN command, read `docs/IOS_SIMULATOR_VALIDATION.md` and `docs/IOS_RUNTIME_SERVICES.md`. Use the exact lifecycle from those documents: derive `workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"` and `workspace_name="${workspace_path:t}"` in zsh, set `task_name` to `task-2`, `task-3`, or `task-4`, create the exact device name `Hang Ten Paseo royal-anaconda Review`, record its UUID in `.context/paseo-pending-simulators` before boot and `.context/paseo-owned-simulators` before use, and keep an EXIT/INT/TERM trap active. The trap must call `scripts/paseo-resource-cleanup.sh archive`, delete only the exact owned UUID after name/UUID ownership checks, and remove `.context/$workspace_name/${task_name}-DerivedData` and `.context/$workspace_name/${task_name}.xcresult`; verify manifests, simulator UUID, DerivedData, and result bundle deletion. Use a bounded readiness poll and `-destination 'platform=iOS Simulator,id='"$simulator_uuid"'` for every command. Never use `booted`, a shared device, or `name=iPhone 17 Pro`.

### Task 1: Extend the Python package/domain schema and validators first

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` (`BoardPosition`, `PresentationMediaModel`, `_load_v2_media`, `_load_positions`, model validation)
- Modify: `Tools/HangboardPackages/tests/test_model_first_packages.py`
- Add: `Tools/HangboardPackages/tests/test_model_orientation_inventory.py`
- Test fixture input: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json` only if shared parity cases are added

**Interfaces:**
- `BoardPosition.hold_ids: tuple[str, ...]`, defaulting to `()` only for the compatibility constructor; `_load_positions` materializes the complete model inventory before validation.
- `BoardModelOrientation(pivot: str, rotations: Mapping[str, tuple[float, float, float, float]])` and `PresentationMediaModel.orientation: BoardModelOrientation | None`.
- `BoardDocument.hold_ids_for_position(position_id: str) -> tuple[str, ...]` returns authored model membership in canonical board hold order and raster ownership as before.
- `_validate_model_orientation(orientation, positions, descriptor_hold_ids, model_position_ids, source)` raises field-specific `ValueError`.
- Test helper `write_model_package(root, orientation, positions, media_overrides=None)` writes the existing minimal model fixture with the supplied board JSON values and descriptor bytes.

- [x] **Step 1: Write RED tests for parsing and validation.** Add fixtures for valid front/reverse orientation, legacy positions without `holdIDs`, sorted rotation keys, raster orientation, wrong/missing pivot, unknown keys, unknown/duplicate positions, missing/extra rotation IDs, duplicate/unknown/missing/repeated/extra hold IDs, non-finite/zero/non-unit/non-nine-decimal quaternion components, orientation+suspension, and orientation on a fixed one-position model. Assert exact reason substrings such as `orientation.pivot`, `orientation.rotations`, `positions[0].holdIDs`, and `orientation and suspension are mutually exclusive`.

```python
def test_model_orientation_is_normalized_and_membership_is_exact(tmp_path):
    package = write_model_package(tmp_path, orientation={
        "pivot": "modelBoundsCenter",
        "rotations": {"reverse": [0, 1, 0, 0], "front": [0, 0, 0, 1]},
    }, positions=[
        {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left"]},
        {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-right"]},
    ])
    board = load_board_catalog_module().load_board_package(package)
    assert board.positions[0].hold_ids == ("hold-left",)
    assert tuple(board.presentations[0].media.orientation.rotations) == ("front", "reverse")
```

- [x] **Step 2: Run the focused RED tests.** Run `rtk python3 -m pytest -q Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_model_orientation_inventory.py`; expected failures include missing `orientation` parsing, missing `hold_ids`, and unchanged model positions accepting incomplete membership.
- [x] **Step 3: Implement the smallest Python contract.** Add closed-key parsing, finite/unit/9-decimal quaternion validation, `modelBoundsCenter` validation, orientation/suspension exclusivity, model-only exact partition checks, and legacy materialization. Validate canonical source object/member order where the parser contract requires it; Python has no model JSON serializer, so source JSON is hand-authored in canonical order.
- [x] **Step 4: Add discovery mechanics without reclassifying current packages.** Discover `Hangboards/**/board.json`, select packages whose presentations contain `media.type == "model"`, load each through the real package validator, and assert the discovered model set is non-empty, every package has complete descriptor hold inventory, and synthetic fixtures exercise the multi-orientation/fixed branches. Defer expectations about Baguette and Nature metadata to Task 6; do not encode board IDs in runtime code.
- [x] **Step 5: Run GREEN Python checks.** Run `rtk python3 -m pytest -q Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_model_orientation_inventory.py Tools/HangboardPackages/tests/test_board_catalog.py` and `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`; expected result is all focused tests passing and a valid final inventory.
- [x] **Step 6: Commit.** `git add Tools/HangboardPackages/src/hangboard_packages/board_catalog.py Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_model_orientation_inventory.py HangTenTests/Fixtures/BoardPackageValidationFixtures.json && git commit -m "feat: validate model orientation metadata"`

### Task 2: Add Swift schema/domain decoding and strict loading

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` (`BoardPosition`, `BoardModelOrientation`, `BoardModelMedia`)
- Modify: `HangTen/Models/BoardPackageStore.swift` (document/media decoding and field-specific `invalidPackage` validation)
- Do not modify: `HangTen/Models/BoardPackageWriter.swift` (legacy editable raster/v1 document; no v2 model serializer)
- Modify: `HangTenTests/BoardPackageStoreTests.swift`

**Interfaces:**
- `BoardPosition.init(id:presentationID:holdIDs:)` plus compatibility `init(id:presentationID:)` supplying `[]`.
- `struct BoardModelOrientation: Hashable { let pivot: String; let rotations: [String: SIMD4<Double>] }` where components are `[x,y,z,w]`.
- `BoardModelMedia.orientation: BoardModelOrientation?` and initializer parameter `orientation: BoardModelOrientation? = nil`.
- Store decoding produces `BoardModelMedia` only after descriptor bounds/node/hold validation. v2 model package JSON remains hand-authored and validator-owned; Workbench model editing stays unavailable.

- [x] **Step 1: Write RED XCTest cases** mirroring Task 1’s valid/invalid matrix, including legacy `BoardPosition` decoding and strict member order/unknown-key checks. Do not add writer tests: there is no v2 model serializer. Add one regression assertion that legacy editable-document bytes remain unchanged if a compatibility initializer is touched.
- [x] **Step 2: Run RED using the Native XCTest Lifecycle.** After creating/recording `Hang Ten Paseo royal-anaconda Review` and setting `$simulator_uuid`, run `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id='$simulator_uuid -derivedDataPath .context/$workspace_name/task-2-DerivedData -resultBundlePath .context/$workspace_name/task-2.xcresult -only-testing:HangTenTests/BoardPackageStoreTests`; expected failures show absent Swift members/decoders. Cleanup must remain armed after the RED run.
- [x] **Step 3: Implement Swift value types and strict decoding.** Add explicit CodingKeys/rejectUnknownKeys for `orientation`, require exact rotation IDs and model hold partition after descriptor load, materialize legacy inventories, reject both metadata blocks, and retain `invalidPackage(boardID:reason:)` with stable field-specific reasons. Ensure fixed model packages cannot gain orientation implicitly.
- [x] **Step 4: Run GREEN using the Native XCTest Lifecycle.** Re-run the same focused command with the fresh exact UUID and task-specific paths; all tests pass before cleanup and commit. Do not add model editing or serializer behavior to Workbench.
- [x] **Step 5: Commit.** `git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTenTests/BoardPackageStoreTests.swift && git commit -m "feat: add Swift orientation package contract"`

### Task 3: Make BoardPosition hold partition and selection deterministic

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift` (`TrainingBoard.holdIDs(inPosition:)`, position initialization/selection helpers)
- Modify: `HangTen/Models/BoardPackageStore.swift` (loaded position membership)
- Modify: `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`

**Interfaces:**
- `TrainingBoard.holdIDs(inPosition:) -> [String]` returns the position’s explicit `holdIDs` in canonical `holds` order, with legacy positions already materialized by the loader.
- `TrainingBoard.position(id:) -> BoardPosition?` remains the sole position lookup used by model selection; no board-ID checks are introduced.

- [x] **Step 1: Write RED tests** proving shuffled authored hold IDs return canonical board order, unknown/duplicate IDs fail package loading, every model hold appears exactly once across positions, and selecting a position does not borrow another position’s presentation or holds.
- [x] **Step 2: Run RED using the Native XCTest Lifecycle.** With a newly recorded exact UUID for `Hang Ten Paseo royal-anaconda Review`, run `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id='$simulator_uuid -derivedDataPath .context/$workspace_name/task-3-DerivedData -resultBundlePath .context/$workspace_name/task-3.xcresult -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests`; expected failure is current `holdIDs(inPosition:)` deriving all model descriptor holds for every position.
- [x] **Step 3: Implement deterministic selection.** Use explicit membership for model positions, preserve raster geometry ownership behavior, and reject an unavailable or mismatched selected position rather than falling back.
- [x] **Step 4: Run GREEN using the Native XCTest Lifecycle.** Re-run with a fresh exact UUID and task-specific paths; expected all tests pass with exact hold arrays and stable active position IDs, then verify cleanup.
- [x] **Step 5: Commit.** `git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardPackageStore.swift HangTenTests/BoardModelTests.swift HangTenTests/BoardPackageStoreTests.swift && git commit -m "feat: select model holds by position"`

### Task 4: Rotate SceneKit models around bounds center, reframe, and preserve orbit

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift` (`BoardModelScene` initializer/select/framing/orbit/reset and interaction forwarding)
- Modify: `HangTenTests/BoardModelTests.swift`

**Interfaces:**
- `BoardModelScene.init?(source:descriptor:display:orientation:suspension:)` accepts orientation and rejects simultaneous orientation/suspension at runtime initialization.
- `BoardModelScene.select(positionID:) -> Bool` applies orientation metadata or the existing suspension solver.
- `BoardModelScene.orbit(azimuth:elevation:zoomScale:)` and `resetCamera(animated:)` remain public behavior for all interactive model surfaces.
- Internal helpers `rotatedBounds(_:by:pivot:) -> BoardModelBounds` and `framing(descriptor:display:)` provide testable center-pivot and transformed-bounds calculations.

- [x] **Step 1: Write RED tests** with a non-centered `[min,max]` descriptor and a 180° Y quaternion. Assert the transform is applied to `boardContainer`, the pivot is `(min+max)/2`, hold node/object bindings are unchanged, camera target/width/height use rotated bounds, no cord/transient attachment is created, and orbit changes camera after canonical selection then reset returns to the new framing.
- [x] **Step 2: Run RED using the Native XCTest Lifecycle.** With a newly recorded exact UUID for `Hang Ten Paseo royal-anaconda Review`, run `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id='$simulator_uuid -derivedDataPath .context/$workspace_name/task-4-DerivedData -resultBundlePath .context/$workspace_name/task-4.xcresult -only-testing:HangTenTests/BoardModelTests`; expected failure is orientation ignored and current selection leaving front framing.
- [x] **Step 3: Implement orientation path.** Rotate the shared board container with `simd_quatf(ix:iy:iz: r: w)` in `[x,y,z,w]` order about only the model bounds center, compute all eight transformed corners, derive new orthographic framing, animate with `canonicalTransitionDuration`, reset orbit accumulators, and leave the suspension solver untouched.
- [x] **Step 4: Audit gesture forwarding.** Ensure detail/workout `BoardModelView` forwards drag/magnify orbit/reset for orientation, fixed, and suspension models while preview continues to honor its existing display-only policy; preview hit testing must not disable interactive surfaces.
- [x] **Step 5: Run GREEN using the Native XCTest Lifecycle.** Re-run focused XCTest and then `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id='$simulator_uuid -derivedDataPath .context/$workspace_name/task-4-DerivedData -resultBundlePath .context/$workspace_name/task-4.xcresult -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/SuspendedBoardPresentationTests`; expected all pass and suspension snapshots remain unchanged, then verify cleanup.
- [x] **Step 6: Commit.** `git add HangTen/Views/BoardModelView.swift HangTenTests/BoardModelTests.swift && git commit -m "feat: render canonical model orientations"`

### Task 5: Enforce the Android decoder boundary

**Files:**
- Modify: `Android/app/src/main/java/com/hangten/android/content/BoardModels.kt`
- Modify: `Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt`
- Modify: `Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt`

**Interfaces:**
- Kotlin `BoardPosition.holdIds: List<String>` and model `BoardOrientation(pivot: String, rotations: Map<String, List<Float>>)` use the same JSON names and `[x,y,z,w]` order.
- `decodeSchemaV2Board` either validates/decodes orientation fields through the shared strict path or marks model media unavailable with the existing explicit `unavailableBoardIds` result; malformed orientation must never become raster geometry.

- [x] **Step 1: Write RED JUnit tests** for valid orientation, legacy positions, unknown orientation keys, bad pivot/quaternion/rotation IDs, orientation+suspension, and a model package returning the explicit unavailable-model result. Assert no model orientation field is read as `holdGeometry`.
- [x] **Step 2: Run RED.** `rtk ./Android/gradlew -p Android testDebugUnitTest --tests com.hangten.android.content.BoardRepositoryTest`; expected failure is missing fields or acceptance of the model as an undifferentiated unsupported payload.
- [x] **Step 3: Implement the strict boundary.** Add closed-key parsing and exact validation; keep board-ID-agnostic behavior and preserve the explicit unavailable-model path if Android does not render models.
- [x] **Step 4: Run GREEN Android tests.** Re-run the command above and `rtk ./Android/gradlew -p Android test`; expected all unit tests pass.
- [x] **Step 5: Commit.** `git add Android/app/src/main/java/com/hangten/android/content/BoardModels.kt Android/app/src/main/java/com/hangten/android/content/BoardRepository.kt Android/app/src/test/java/com/hangten/android/content/BoardRepositoryTest.kt && git commit -m "feat: enforce Android model orientation decoding"`

### Task 6: Deliberately audit and backfill every current 3D package

**Files:**
- Modify: `Hangboards/yy-baguette-evo/board.json`
- Modify: `Hangboards/nature-stone-hanger/board.json`
- Modify: `Hangboards/beastmaker-1000/board.json`
- Modify: `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Add: `docs/source-audits/2026-09-11-3d-board-orientation-audit.md`
- Test: `Tools/HangboardPackages/tests/test_model_orientation_inventory.py`

**Interfaces:**
- Each model package remains one `primary.usdz` plus its existing descriptor; only board JSON metadata and audit documentation change.
- The audit table records package, physical disposition, exact ordered positions, hold IDs, pivot/quaternion (or “none” for fixed), model bounds, evidence URL/artifact, grouping rationale, and author of each estimate.

- [x] **Step 1: Write RED inventory expectations** from discovered model packages: Nature has reviewed front/reverse positions with rotations; Baguette has every deliberate reviewed contact grouping and authored display estimates; Beastmaker 1000 and Compact II remain one fixed canonical position with no orientation object.
- [x] **Step 2: Run RED inventory.** `rtk python3 -m pytest -q Tools/HangboardPackages/tests/test_model_orientation_inventory.py`; expected failure reports absent orientation metadata/audit rows in current packages.
- [x] **Step 3: Run the cheaper evidence-preparation pass.** Luna gathers and structures the direct YY Vertical and Nature manufacturer evidence, descriptor bounds/hold inventories, and existing audit links without authoring quaternions or changing assets; record evidence URLs/artifacts and uncertainty in the new audit draft. If evidence cannot support a second physical view, stop and request human direction.
- [x] **Step 4: Perform the Astra-only orientation judgment.** After Luna’s evidence packet is reviewed, Astra decides the Baguette contact groupings and authored display-estimate quaternions, and the Nature front/reverse grouping, using direct visual inspection and unchanged model geometry. Terra reviews schema fit; no other agent authors the final orientation judgment. Fixed packages remain one canonical position with no orientation object.
- [x] **Step 5: Author metadata and audit.** Keep position arrays in canonical hold order, rotations sorted by position ID, normalized to nine decimals, and label every Baguette value exactly `authored display estimate` with evidence and grouping rationale. Do not edit USDZ/descriptor bytes.
- [x] **Step 6: Run GREEN validation.** `rtk python3 -m pytest -q Tools/HangboardPackages/tests/test_model_orientation_inventory.py Tools/HangboardPackages/tests/test_model_first_packages.py` and `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`; expected all four model packages load and no USDZ/descriptor hash changes occur (`git diff --stat -- Hangboards/*/assets`).
- [x] **Step 7: Commit.** `git add Hangboards/yy-baguette-evo/board.json Hangboards/nature-stone-hanger/board.json Hangboards/beastmaker-1000/board.json Hangboards/metolius-wood-grips-compact-ii/board.json docs/source-audits/2026-09-11-3d-board-orientation-audit.md Tools/HangboardPackages/tests/test_model_orientation_inventory.py && git commit -m "data: audit current model board orientations"`

### Task 7: Isolated iOS simulator visual validation and resource cleanup

**Files:**
- Add validation artifacts only under `.context/$workspace_owner/orientation-validation/`
- Review: `HangTen/Views/BoardModelView.swift`, `HangTen/Views/BoardModelView.swift` callers, and current DEBUG review routes used by `validate-hang-ten-ios`
- Test evidence: landscape screenshots/logs for each current model package

**Interfaces:**
- Use the existing Hang Ten simulator validation route; no production UI or package changes are permitted in this task.
- Validation covers canonical selection, hold hit testing, orbit/reset, detail/workout surfaces, and preview gesture policy.

- [x] **Step 1: Prepare owned resources.** Derive `workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"` and `workspace_owner="${workspace_path:t}"` in zsh, create `.context/$workspace_owner/orientation-validation`, allocate the exact device name `Hang Ten Paseo royal-anaconda Review`, record pending/owned UUID manifests, and install the documented EXIT/INT/TERM cleanup trap.
- [x] **Step 2: Build and install.** Boot and readiness-poll only `$simulator_uuid`, then run `rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -destination 'platform=iOS Simulator,id='$simulator_uuid -derivedDataPath .context/$workspace_owner/orientation-validation/DerivedData build`; install and launch by UUID, and record logs under the owned directory.
- [ ] **Step 3: Capture GREEN evidence after Tasks 1–6.** In landscape, capture front and every canonical position for Baguette, Nature, Beastmaker 1000, and Compact II; verify expected holds are visible/selectable, manually orbit then reset, switch positions, and verify framing stays in viewport on detail and workout. Confirm display-only preview remains intentionally non-interactive and malformed packages show unavailable state. Automated RED tests in Tasks 1–5 provide the pre-change baseline. Baguette, Beastmaker 1000, and Compact II have landscape evidence, and Nature's front/reverse positions are verified in portrait; Nature landscape validation remains open because its 3D card is blank under the synthetic-landscape flag and has not yet been verified on a physical device genuinely rotated to landscape.
- [x] **Step 4: Verify cleanup.** Stop the app, shut down/delete the exact simulator UUID, remove only `.context/$workspace_owner/orientation-validation` and its owned DerivedData/results, assert the UUID and paths no longer exist, and leave shared/unknown resources untouched.
- [x] **Step 5: Commit review evidence only if repository policy accepts it.** Keep screenshots/logs under ignored `.context`; otherwise commit the concise audit checklist at `docs/source-audits/2026-09-11-3d-board-orientation-audit.md` only with `git add` and `git commit -m "test: validate model orientation surfaces"`.

## Final Review Gate

- [x] Run the full relevant suites: `rtk python3 -m pytest -q Tools/HangboardPackages/tests`, the Native XCTest Lifecycle with a fresh `Hang Ten Paseo royal-anaconda Review` UUID and `-destination 'platform=iOS Simulator,id='$simulator_uuid` using `.context/$workspace_name/final-DerivedData` and `.context/$workspace_name/final.xcresult`, and `rtk ./Android/gradlew -p Android test`.
- [x] Re-read the spec section-by-section and map each acceptance criterion to Tasks 1–7; verify no board-ID conditional, USDZ/descriptor edit, invented provenance, orientation+suspension combination, arbitrary pivot, or incomplete hold partition exists.
- [x] Search this plan for forbidden planning markers and vague instructions; none may remain. Check that all later interfaces use the exact names/types defined above.
- [x] A fresh reviewer must inspect each task’s diff and test output before the implementation branch is integrated. Push every resulting commit automatically: `git push -u origin HEAD`. (Auto-push is the established workflow policy; maintainer review happens on the PR, not per-commit.)
