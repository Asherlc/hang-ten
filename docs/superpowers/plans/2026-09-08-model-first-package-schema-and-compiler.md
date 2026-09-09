# Model-First Package Schema and Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add schema-versioned raster/model package media, evidence-packet validation, and a deterministic USDZ-to-descriptor compiler without changing either production board to model media yet.

**Architecture:** `board.json` version 2 retains only logical hold facts; a tagged `PresentationMedia` owns either raster paths or a model asset plus a generated descriptor. Python is the canonical build validator and Swift independently fails closed while loading the bundled package. The compiler derives the descriptor from tagged approved geometry and the actual exported USDZ; it never changes shape.

**Tech Stack:** Python 3.11 package validator, Blender 5.2 Python (`bpy`), SHA-256, JSON, Swift/Foundation, XCTest, existing Xcode staging script.

**Spec:** `docs/superpowers/specs/2026-09-08-beastmaker-1000-3d-design.md`

## Global Constraints

- Run each implementation task through a fresh subagent and a fresh review subagent; do not make controller edits.
- Luna performs bounded mechanics and primary-source packet assembly; Sol or Terra perform involved non-geometry reasoning; Astra is not used by this plan.
- Stage 0 packets use manufacturer product pages, manuals, dimension diagrams, and manufacturer media first. Authorized retailers/distributors may fill a documented gap only; reviews, forums, search snippets, and AI summaries are discovery/corroboration only and never sole authority.
- Every packet records revision, date, locale, retained actual page/media snapshot paths, SHA-256 values, source tier, confidence, conflicts/rulings, and source-backed logical inventory. It contains no coordinates, radii, section proposals, masks, traced/vectorized/aligned contours, or other geometry proposal.
- Every model uses `hang-ten-board-v1`: metre units, right-handed back-bottom-left origin, +X right, +Y up, +Z toward the climber. Screw holes, mounting holes, and hardware are omitted.
- Descriptor numbers are rounded to nine decimal places; `modelSHA256` hashes the exact USDZ bytes. A descriptor is generated only and is never hand-maintained.
- Model media may not be derived or inverted. Missing, malformed, stale, unbound, or extra model geometry is a package defect; there is no raster fallback for a model presentation.
- Durable evidence packets, editable `.blend` sources, review renders, export reports, and hashes remain under their owned `.context/shaky-rat-*` directories for audit and handoff. Each owner records `ownership.json`, installs an exit trap, and removes only ephemeral scratch directories, processes, tunnels, simulators, and local DerivedData it created.

## Dependency Order

`Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7`; Tasks 8 and 9 consume Tasks 4–7. Task 4 accepts legacy v1 and v2; Task 5 gives Swift the same transition support; Task 6 migrates every package and removes v1 from both parsers. Do not start target-board migration until the third plan.

## Isolated XCTest Device Lifecycle

Before Task 5’s first XCTest command, create one simulator named `Hang Ten Paseo shaky-rat Review`, verify its exact returned UUID and name, write that UUID first to `.context/paseo-pending-simulators` then `.context/paseo-owned-simulators`, and export `HANG_TEN_TEST_DEVICE_UDID`. Install EXIT/INT/TERM cleanup before creation using `PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive`; remove only this workspace-named simulator and `.context/DerivedData`, retaining durable `.context/shaky-rat-*` packet/model artifacts. Every XCTest command below uses the exported UUID, never a named/shared or `booted` destination.

## File Map

| File | Change | Responsibility |
| --- | --- | --- |
| `Tools/HangboardModels/evidence_packet.py` | Create | Strict Stage 0 packet model and validator. |
| `Tools/HangboardModels/evidence-packet-template.json` | Create | Copyable packet skeleton with no geometry fields. |
| `Tools/HangboardModels/validate_evidence_packet.py` | Create | CLI validation of a packet and its retained references. |
| `Tools/HangboardModels/test_evidence_packet.py` | Create | Fast packet/schema regressions. |
| `Tools/HangboardModels/model_descriptor.py` | Create | Descriptor v1 types, normalisation, rounding, and JSON encoding. |
| `Tools/HangboardModels/compile_model_package.py` | Create | Blender-only export/reimport compiler producing USDZ and descriptor. |
| `Tools/HangboardModels/test_compile_model_package_blender.py` | Create | Blender background regression that creates invalid tagged meshes in memory. |
| `Tools/HangboardModels/test_model_descriptor.py` | Create | Descriptor and compiler-pure-function regressions. |
| `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` | Modify | Schema v1/v2 discriminated parser and exact typed asset validation. |
| `Tools/HangboardPackages/scripts/migrate_to_schema_v2.py` | Create | Deterministic v1-to-v2 raster document conversion after both parsers support the transition. |
| `Tools/HangboardPackages/tests/test_model_first_packages.py` | Create | v2 raster/model fixtures and negative package validation. |
| `HangTen/Models/BoardPackageStore.swift` | Modify | Independent v2 media/descriptor decoding and confined asset validation. |
| `HangTen/Models/TrainingModels.swift` | Modify | Typed presentation media plus descriptor-backed logical frame source. |
| `HangTenTests/BoardPackageStoreTests.swift` | Modify | Swift parser/descriptor/hash rejection tests. |
| `HangTenTests/Fixtures/BoardPackageValidationFixtures.json` | Modify | v2 raster and model fixture documents. |
| `scripts/stage-board-packages.py` | Inspect unchanged | Existing recursive copy already stages the parser-approved package tree. |
| `Tools/HangboardPackages/tests/test_board_package_staging.py` | Modify | Characterize model asset + descriptor byte identity after unchanged staging. |
| `README.md`, `Tools/HangboardPackages/README.md`, `Tools/HangboardModels/README.md` | Modify | Document v2 package and compiler commands. |

### Task 1: Luna — Stage 0 evidence packet contract

**Files:**
- Create: `Tools/HangboardModels/evidence_packet.py`, `Tools/HangboardModels/evidence-packet-template.json`, `Tools/HangboardModels/validate_evidence_packet.py`, `Tools/HangboardModels/test_evidence_packet.py`
- Modify: `Tools/HangboardModels/README.md`

**Interfaces:**
- Produces `validate_evidence_packet(packet_path: Path) -> EvidencePacket` and CLI `python3 -B Tools/HangboardModels/validate_evidence_packet.py PATH`.
- `EvidencePacket` has `boardRevision`, `boardRevisionDate`, `locale`, `primarySources`, `commerceSources`, `logicalInventory`, `sourcedClaims`, `conflictsAndRulings`, `unknownsForAstra`, `deliberateOmissions`, `materialFidelity`, and `requiredReviewViews` exactly.

- [ ] **Step 1: Write the failing packet tests**

```python
def test_accepts_retained_manufacturer_media_and_rejects_geometry_proposal(tmp_path):
    packet = valid_packet(tmp_path)
    assert validate_evidence_packet(packet).primary_sources[0].source_tier == "manufacturer"
    payload = json.loads(packet.read_text())
    payload["unknownsForAstra"] = ["radius 8 mm"]
    packet.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="numeric shape prescription"):
        validate_evidence_packet(packet)
```

- [ ] **Step 2: Run the focused test and confirm the import fails**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardModels/test_evidence_packet.py -q`

Expected: FAIL because `evidence_packet` does not exist.

- [ ] **Step 3: Implement the closed packet schema**

Implement `EvidenceSource(localPath: str, sha256: str, sourceTier: Literal["manufacturer","commerce"], url: str)`; require an HTTPS URL, an existing regular non-symlink retained path beneath the packet directory, and a SHA-256 equal to its bytes. Permit only `manufacturer` in `primarySources`; require authorized retailer identity plus `snapshotSHA256` in `commerceSources`; reject a commerce claim that overrides a recorded manufacturer conflict without a ruling. Enforce the closed packet keys rather than a global banned-word scan: cited `sourcedClaims` and `sourceBackedMetadata` may contain legitimate measurements; qualitative `unknownsForAstra` may name `cavity sections`, `radii`, and `back profile`. Reject proposal fields such as `geometry`, `coordinates`, `contours`, `masks`, `vectors`, `trace`, and `alignment`, and reject a numeric shape prescription only in `unknownsForAstra` or another proposal-like field (for example `radius 8 mm` or `[0.2, 0.4]`). Require `deliberateOmissions` to contain both `screw holes` and `mounting hardware` and review views `front`, `three-quarter`, `clay-detail`.

- [ ] **Step 4: Run packet tests and CLI**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardModels/test_evidence_packet.py -q`

Expected: PASS, including manufacturer-first, commerce-gap, stale-hash, invalid-locale/date, and no-geometry cases.

- [ ] **Step 5: Commit and review**

Run: `git add Tools/HangboardModels/evidence_packet.py Tools/HangboardModels/evidence-packet-template.json Tools/HangboardModels/validate_evidence_packet.py Tools/HangboardModels/test_evidence_packet.py Tools/HangboardModels/README.md && git commit -m "feat: validate model evidence packets"`

Review gate: a fresh Terra reviewer confirms that an actual primary source snapshot is required and that no geometry field can enter an Astra brief.

### Task 2: Terra — Descriptor v1 pure schema

**Files:**
- Create: `Tools/HangboardModels/model_descriptor.py`, `Tools/HangboardModels/test_model_descriptor.py`

**Interfaces:**
- Consumes `Sequence[NodeBinding]`, `Mapping[str, Sequence[Vector3]]`, `ModelBounds`.
- Produces `ModelDescriptorV1.to_json() -> dict[str, object]`, `ModelDescriptorV1.from_json(value: Mapping[str, object]) -> ModelDescriptorV1`, and `compile_descriptor(model_bytes: bytes, nodes: Sequence[NodeBinding], vertices_by_node_id: Mapping[str, Sequence[Vector3]], logical_hold_ids: frozenset[str]) -> ModelDescriptorV1`.

- [ ] **Step 1: Write descriptor failures**

```python
def test_compiler_rounds_normalized_face_bounds_and_requires_exact_inventory():
    descriptor = compile_descriptor(b"usdz", [body("Board/Body"), hold("Board/Hold/JugLeft", "jug-left")], {"Board/Body": [(0,0,0),(0.58,0.15,0.058)], "Board/Hold/JugLeft": [(0.01234567891,0.10123456789,0),(0.14567890123,0.14999999991,0.02)]}, frozenset({"jug-left"}))
    assert descriptor.holds["jug-left"].center == (0.136227224, 0.83744956)
    with pytest.raises(ValueError, match="logical hold IDs"):
        compile_descriptor(b"usdz", [body("Board/Body")], {"Board/Body": [(0,0,0),(1,1,1)]}, frozenset({"jug-left"}))
```

- [ ] **Step 2: Run the focused descriptor test**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardModels/test_model_descriptor.py -q`

Expected: FAIL because `compile_descriptor` is absent.

- [ ] **Step 3: Implement exact descriptor semantics**

Define `NodeBinding(nodeID, role, holdID=None)`, `ModelBounds(min,max)`, `FacePlaneAABB(min,max)`, and `ModelDescriptorV1`. Reject unknown keys, duplicate `nodeID`, no body, `decoration`, a body `holdID`, zero-vertex geometry, node/vertex disagreement, unbound geometry, or a hold inventory unequal to `logical_hold_ids`. Compute physical metre `modelBounds` over all vertices; normalise each hold union using `(x-minX)/(maxX-minX)` and `(y-minY)/(maxY-minY)`; sort node and hold output by ID; round every derived float with `round(value, 9)`; set `coordinateFrame` to `hang-ten-board-v1`, `schemaVersion` to `1`, and `modelSHA256` from exact bytes.

- [ ] **Step 4: Run descriptor tests**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardModels/test_model_descriptor.py -q`

Expected: PASS for repeated hold pieces, all roles, non-finite values, zero face span, hash changes, and deterministic key/order output.

- [ ] **Step 5: Commit and review**

Run: `git add Tools/HangboardModels/model_descriptor.py Tools/HangboardModels/test_model_descriptor.py && git commit -m "feat: add model descriptor schema"`

Review gate: a fresh Sol reviewer checks that no descriptor field accepts hand-authored bounds or inferred axes.

### Task 3: Sol — deterministic model compiler/exporter

**Files:**
- Create: `Tools/HangboardModels/compile_model_package.py`, `Tools/HangboardModels/test_compile_model_package_blender.py`
- Modify: `Tools/HangboardModels/test_model_descriptor.py`, `Tools/HangboardModels/README.md`

**Interfaces:**
- Consumes `--blend PATH --board-json PATH --output-directory PATH`; source mesh custom properties `role` (`body`/`hold`) and `hold_id` on hold meshes.
- Produces exactly `assets/primary.usdz` and `assets/primary.model.json`; `compile_model_package(blend_path, board_json_path, output_directory) -> ModelDescriptorV1`.

- [ ] **Step 1: Add a compiler contract regression**

```python
def test_compiler_rejects_missing_tag_before_export(monkeypatch, tmp_path):
    fake_scene = scene_with_mesh("Body", role=None)
    monkeypatch.setattr(compiler, "open_scene", lambda _: fake_scene)
    with pytest.raises(ValueError, match="role"):
        compiler.validate_tagged_scene(fake_scene, {"jug-left"})
```

- [ ] **Step 2: Run the test**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardModels/test_model_descriptor.py -q`

Expected: FAIL because `compile_model_package` is absent.

- [ ] **Step 3: Implement export then reimport, never repair**

Open the supplied `.blend`; reject non-mesh authored geometry, missing/unknown `role`, untagged hold, unknown hold ID, missing body, and inventory mismatch before export. Export only tagged meshes after transforming to `hang-ten-board-v1`; triangulate temporary export copies only; write a fixed `primary.usdz`; reimport that USDZ into an empty Blender scene and derive importer-visible node IDs, vertices, materials, triangle count, and descriptor through Task 2. Fail if any imported mesh has no image/material, any node binding changed, an expected hold vanished, a node has no vertices, or the reimported physical bounds differ from the exported source by more than `0.000001` metres. Write canonical JSON descriptor only after all checks pass. Do not alter vertices, names, materials, or object topology to satisfy a failure.

- [ ] **Step 4: Run pure tests and a Blender malformed-scene check**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardModels/test_model_descriptor.py -q`

Expected: PASS; Blender is not required for pure `validate_tagged_scene` tests.

Run: `rtk proxy blender --background --factory-startup --python-exit-code 1 --python Tools/HangboardModels/test_compile_model_package_blender.py`

Expected: exit 0 after the script creates an in-memory mesh with no `role`, calls `validate_tagged_scene`, and asserts the resulting `ValueError` mentions `role`; a second in-memory mesh with `role="hold"` and `hold_id="unknown"` must assert the unknown-ID error. No external `.blend`, USDZ, descriptor, or `.context` fixture is required.

- [ ] **Step 5: Commit and review**

Run: `git add Tools/HangboardModels/compile_model_package.py Tools/HangboardModels/test_compile_model_package_blender.py Tools/HangboardModels/test_model_descriptor.py Tools/HangboardModels/README.md && git commit -m "feat: compile tagged hangboard models"`

Review gate: a fresh Terra reviewer verifies that shape changes are impossible in compiler code and that a native consumer still independently validates the actual USDZ later.

### Task 4: Sol — Python schema v2 tagged media parser

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`
- Create: `Tools/HangboardPackages/tests/test_model_first_packages.py`

**Interfaces:**
- Produces `PresentationMediaRaster(asset_path, hold_geometry) | PresentationMediaModel(asset_path, descriptor_path, display)` inside `BoardPresentation.media`; presentation derivation is exactly `{"type":"original"}` or raster-only `{"type":"derived","sourcePresentationID":String,"isInverted":Bool}`.
- `BoardHold` removes `geometry` and `presentation_id`; `BoardDocument.hold_frame(hold_id, presentation_id) -> NormalizedFrame` returns raster union or model descriptor AABB.

- [ ] **Step 1: Write strict v2 fixture tests**

```python
def test_v2_model_requires_hash_bound_complete_descriptor(package_root):
    write_model_package(package_root, hold_ids=("hold-left", "hold-right"))
    package = load_board_package(package_root)
    assert package.board.hold_frame("hold-left", "primary") == NormalizedFrame(.1, .2, .3, .4)
    mutate_descriptor(package_root, modelSHA256="0" * 64)
    with pytest.raises(ValueError, match="SHA-256"):
        load_board_package(package_root)
```

- [ ] **Step 2: Run focused Python package tests**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: FAIL because v2 media is unknown.

- [ ] **Step 3: Implement dual version loading and exact assets**

Keep legacy v1 decoding temporarily so current package JSON remains valid until Task 6; v1 retains its existing flat `assetPath`, per-hold `geometry`, and `presentationID` representation. For v2 require root keys `schemaVersion`, logical fields, `presentations`, and `holds`; presentation keys are `id,name,aspectRatio,isDefault,derivation,media`. Accept raster media only as `{type:"raster",assetPath,holdGeometry}` and model media only as `{type:"model",assetPath,descriptorPath,display}`. Confine raster to `.png`, model to `.usdz`, descriptors to `.model.json`, all beneath `assets/`; exact actual files must equal the union of media asset and descriptor paths. Parse descriptor v1 independently, hash USDZ bytes, require model node/hold inventory equality, and reject derived/inverted model media. Convert raster path pieces from `media.holdGeometry[holdID]`; reject missing, extra, or empty raster ownership.

- [ ] **Step 4: Run focused and existing parser tests**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_board_catalog.py -q`

Expected: PASS; negative fixtures cover extra PNG fallback, escaped descriptor, stale hash, missing hold binding, extra geometry node, model inversion, and raster paths outside media.

- [ ] **Step 5: Commit and review**

Run: `git add Tools/HangboardPackages/src/hangboard_packages/board_catalog.py Tools/HangboardPackages/tests/test_model_first_packages.py && git commit -m "feat: parse model-first board packages"`

Review gate: a fresh Terra reviewer verifies Python accepts unchanged logical metadata but refuses every mixed model/raster fallback shape.

### Task 5: Sol — Swift transitional v1/v2 package loader and logical frame resolver

**Files:**
- Modify: `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`, `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`

**Interfaces:**
- Produces `struct BoardRasterMedia { let assetPath: String; let holdGeometry: [String: [BoardHoldPiece]] }`, `struct BoardModelMedia { let assetPath: String; let descriptorPath: String; let descriptor: BoardModelDescriptor; let display: BoardModelDisplay }`, `enum BoardPresentationMedia: Hashable { case raster(BoardRasterMedia); case model(BoardModelMedia) }`, `BoardModelDescriptor`, and `BoardHold.resolvedFrame(in: BoardPresentation) -> HoldFrame?` while decoding both legacy v1 and v2 documents.
- `BoardPackageStore.presentationAssetURL(for: TrainingBoard, presentationID: String?) -> URL?` and `presentationDescriptorURL(for:presentationID:) -> URL?` replace image-only lookup.

- [ ] **Step 1: Add Swift fixture assertions before implementation**

```swift
func testStoreLoadsV2ModelAndKeepsV1PackageReadableDuringTransition() throws {
    let fixture = try makeModelFixtureBundle(modelSHA256Matches: true)
    defer { fixture.remove() }
    let board = try XCTUnwrap(BoardPackageStore(bundle: fixture.bundle).boards.first)
    let presentation = try XCTUnwrap(board.presentations.first)
    XCTAssertEqual(presentation.media.kind, .model)
    XCTAssertEqual(board.holds[0].resolvedFrame(in: presentation), HoldFrame(x: 0.1, y: 0.2, width: 0.3, height: 0.4))
    XCTAssertNoThrow(try BoardPackageStore(bundle: legacyV1FixtureBundle().bundle))
}
```

- [ ] **Step 2: Run the focused XCTest method**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardPackageStoreTests/testStoreLoadsV2ModelAndKeepsV1PackageReadableDuringTransition`

Expected: FAIL because `BoardPresentation.media` is absent.

- [ ] **Step 3: Implement independent fail-closed Swift decoding**

Dispatch on an optional `schemaVersion`: preserve current v1 decoding exactly for existing package JSON, then decode v2 media through a keyed discriminator. Decode descriptor bytes with `JSONDecoder`, reject unknown fields, invalid fixed-size vectors, non-finite values, duplicate node IDs, invalid role, descriptor inventory mismatch, and an SHA-256 mismatch using `CryptoKit.SHA256.hash(data:)`. Replace `validateFinishedPackage` PNG sizes with typed regular-file checks, decode PNG dimensions only for raster, and validate model camera `{type:"orthographic",viewDirection:[Double],up:[Double],fitPadding:Double}` with finite nonzero vectors and positive padding. Internally adapt v1 paths/presentation ownership into `BoardRasterMedia` so `BoardHold` becomes logical (no stored paths or presentation ID); map raster pieces and model descriptor AABB into `resolvedFrame(in:)`.

- [ ] **Step 4: Run Swift parser regression group**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: PASS; existing v1 catalog packages remain readable, while fixture coverage includes v2 raster compatibility, stale USDZ hash, missing descriptor, descriptor extra node, hold inventory mismatch, unknown media tag, model-derived/inverted rejection, and no image decode attempted for model media.

- [ ] **Step 5: Commit and review**

Run: `git add HangTen/Models/BoardPackageStore.swift HangTen/Models/TrainingModels.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/Fixtures/BoardPackageValidationFixtures.json && git commit -m "feat: load transitional typed board media"`

Review gate: a fresh Sol reviewer compares every accepted/rejected rule against the Python parser's fixtures.

### Task 6: Luna — convert all packages, then remove legacy parser acceptance

**Files:**
- Create: `Tools/HangboardPackages/scripts/migrate_to_schema_v2.py`
- Modify: every `Hangboards/*/board.json`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`, `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`
- Modify: `Tools/HangboardPackages/tests/test_model_first_packages.py`, `HangTenTests/BoardPackageStoreTests.swift`, `Tools/HangboardPackages/README.md`

**Interfaces:**
- Produces canonical version-2 raster documents with `isDefault`; hold records have no `geometry`/`presentationID`, and one `media.holdGeometry[holdID]` owns each previous canonical piece. After conversion, neither parser accepts v1.

- [ ] **Step 1: Write migration, rejection, and preservation tests**

```python
def test_migrate_v1_raster_moves_only_geometry_and_presentation_ownership(tmp_path):
    before = read_fixture("legacy-raster-board.json")
    after = migrate_document(before)
    assert after["schemaVersion"] == 2
    assert after["presentations"][0]["isDefault"] is True
    assert "geometry" not in after["holds"][0] and "presentationID" not in after["holds"][0]
    assert after["presentations"][0]["media"]["holdGeometry"]["hold-left"] == before["holds"][0]["geometry"]
    assert migrate_document(after) == after
```

```swift
func testStoreRejectsLegacyV1OnlyAfterAllBundledPackagesAreV2() throws {
    XCTAssertThrowsError(try BoardPackageStore(bundle: legacyV1FixtureBundle().bundle))
    XCTAssertNoThrow(try BoardPackageStore(bundle: .main))
}
```

- [ ] **Step 2: Run converter test and confirm the converter is missing**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: FAIL because `migrate_to_schema_v2.py` is absent; Task 5 has already proved Swift can load both formats.

- [ ] **Step 3: Implement, test, and apply deterministic conversion while both parsers accept v1/v2**

Read every direct child discovered by `discover_board_packages`; for each v1 presentation create `derivation: {"type":"original"}` when canonical and a raster-only `derivation: {"type":"derived","sourcePresentationID":String,"isInverted":Bool}` when its legacy `sourcePresentationID`/`isInverted` fields require it; write `isDefault`; move each hold’s geometry into canonical raster `media.holdGeometry` keyed by stable ID; preserve JSON scalar values, logical hold ordering, and every path command. Refuse non-raster input, unknown presentation ownership, duplicate key, or a v2 document that differs on a second invocation. Run `--root Hangboards --write`, then `--root Hangboards --check`; after each run execute the Task 5 focused XCTest command so no commit leaves current package JSON unreadable by the app.

- [ ] **Step 4: Remove v1 acceptance from both parsers only after all files are v2**

Change Python and Swift to require `schemaVersion == 2`, remove legacy document adapters, update the legacy fixture assertion to rejection, and keep v2 raster/model decoding unchanged. Verify `rg -l '"schemaVersion"' Hangboards/*/board.json | wc -l` reports the same count as `find Hangboards -name board.json -type f | wc -l`.

- [ ] **Step 5: Run full package/app parser checks**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Expected: PASS with all 53 current direct-child packages decoded as schema-v2 raster packages.

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: PASS with v1 fixture rejection and all bundled packages loaded as v2.

- [ ] **Step 6: Commit and review**

Run: `git add Hangboards Tools/HangboardPackages/scripts/migrate_to_schema_v2.py Tools/HangboardPackages/src/hangboard_packages/board_catalog.py HangTen/Models/BoardPackageStore.swift HangTen/Models/TrainingModels.swift Tools/HangboardPackages/tests/test_model_first_packages.py HangTenTests/BoardPackageStoreTests.swift Tools/HangboardPackages/README.md && git commit -m "feat: migrate board packages to schema v2"`

Review gate: fresh Sol reviewer verifies Task 5’s transitional commit precedes this one, then spot-checks every moved raster path and v1 rejection after the final conversion.

### Task 7: Terra — characterize existing staging for typed assets

**Files:**
- Inspect unchanged: `scripts/stage-board-packages.py`
- Modify: `Tools/HangboardPackages/tests/test_board_package_staging.py`, `README.md`

**Interfaces:**
- Consumes `discover_board_packages(Hangboards)` v2 package inventory.
- Produces byte-identical staged package trees containing each declared raster PNG or model USDZ plus descriptor, with no app-side model resource substitution.

- [ ] **Step 1: Add a v2 model fixture and byte-identity assertion**

```python
def test_staging_copies_model_and_hash_bound_descriptor_byte_for_byte(tmp_path, monkeypatch):
    source = make_v2_model_package(tmp_path / "repo")
    staged = stage_with_xcode_environment(source)
    assert (staged / "fixture-model/assets/primary.usdz").read_bytes() == (source / "Hangboards/fixture-model/assets/primary.usdz").read_bytes()
    assert (staged / "fixture-model/assets/primary.model.json").read_bytes() == (source / "Hangboards/fixture-model/assets/primary.model.json").read_bytes()
```

- [ ] **Step 2: Run the new characterization test**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_board_package_staging.py -q`

Expected: FAIL only because the new v2 model fixture/helper is absent; `scripts/stage-board-packages.py` already recursively copies every parser-validated package file and must remain unchanged.

- [ ] **Step 3: Implement the fixture/helper only and inspect unchanged staging**

Add `make_v2_model_package` and `stage_with_xcode_environment` test helpers, then assert the staged model asset and descriptor bytes equal their source bytes and the staged asset filename set is exactly `{primary.usdz, primary.model.json}`. Inspect `stage_board_packages` and `_copy_regular_tree` to document that their recursive regular-file copy already preserves the complete parser-validated tree. Do not modify `scripts/stage-board-packages.py`.

- [ ] **Step 4: Verify staging and catalog commands**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_board_package_staging.py Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: PASS.

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Expected: PASS.

- [ ] **Step 5: Commit and review**

Run: `git add Tools/HangboardPackages/tests/test_board_package_staging.py README.md && git commit -m "test: characterize staged typed board media"`

Review gate: fresh Terra review confirms staging copies the parser-approved package verbatim, and generated resource directories are recorded/cleaned if tests create them.

### Task 8: Cross-parser contract review

**Model tier:** Sol — involved non-geometry review.

**Files:**
- Modify: `Tools/HangboardPackages/tests/test_model_first_packages.py`, `HangTenTests/BoardPackageStoreTests.swift`

- [ ] **Step 1: Add shared malformed fixture matrix**

Create one JSON fixture per rule: wrong `schemaVersion`, unknown media type, escaped typed path, extra asset, stale SHA, omitted node, extra node, body with hold ID, unbound geometry, invalid camera, and model inversion. Assert Python rejects every fixture and Swift returns `.invalidPackage` or `.malformedJSON` for the matching fixture.

- [ ] **Step 2: Run both parser suites**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py -q`

Expected: PASS.

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: PASS.

- [ ] **Step 3: Commit and review**

Run: `git add Tools/HangboardPackages/tests/test_model_first_packages.py HangTenTests/BoardPackageStoreTests.swift && git commit -m "test: align model package parsers"`

Review gate: a fresh Terra reviewer signs off exact Python/Swift acceptance parity.

### Task 9: Plan-one integration verification

**Model tier:** Luna — routine verification and cleanup.

**Files:**
- Modify: `README.md`, `Tools/HangboardPackages/README.md`, `Tools/HangboardModels/README.md`

- [ ] **Step 1: Document commands and version boundary**

Document the v2 JSON contract, packet CLI, compiler CLI, the fact that all current packages are raster v2 at this checkpoint, and that no geometry task appears in this plan. Include the exact current validator command below.

- [ ] **Step 2: Run the focused full package verification**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory && rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests Tools/HangboardModels/test_evidence_packet.py Tools/HangboardModels/test_model_descriptor.py -q`

Expected: PASS.

- [ ] **Step 3: Run formatting and ownership checks**

Run: `rtk git diff --check`

Expected: no output and exit 0.

- [ ] **Step 4: Commit and review**

Run: `git add README.md Tools/HangboardPackages/README.md Tools/HangboardModels/README.md && git commit -m "docs: describe model-first package tooling"`

Review gate: fresh Sol reviewer confirms the plan did not grant Astra work, did not migrate either target, and leaves no owned resources running.

## Final Verification

- [ ] `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` exits 0.
- [ ] `rtk proxy python3 -B -m pytest Tools/HangboardPackages/tests Tools/HangboardModels/test_evidence_packet.py Tools/HangboardModels/test_model_descriptor.py -q` exits 0.
- [ ] `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardPackageStoreTests` exits 0.
- [ ] The exact owned simulator and `.context/DerivedData` are deleted and their absence verified; durable `.context/shaky-rat-*` evidence/compiler reports remain for the next plan.
