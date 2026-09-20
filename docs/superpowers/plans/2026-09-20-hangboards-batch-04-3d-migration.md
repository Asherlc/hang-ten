# Hangboards Batch 04 3D Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Ship six schema-v3, model-only hangboard packages and reusable-unit instancing while retaining descriptor-v1 packages unchanged.

**Architecture:** A v2 descriptor names generic unit-local contact slots. Exactly two validated media instances map each slot to a canonical board contact, own their pose and suspension state, and share one USDZ decode only. Python and Swift reject the same malformed documents before SceneKit deep-clones the unit twice.

**Tech Stack:** Python, pytest, Blender USDZ export, Swift, SceneKit, XCTest, Xcode, iOS Simulator, Astra.

**Spec:** `docs/superpowers/specs/2026-09-20-hangboards-batch-04-3d-migration-design.md`

## Global Constraints

- Preserve descriptor-v1 serialization and runtime behavior exactly.
- Every target is schema-v3 with only `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`. It has no raster, canonical path, `contactGeometry`, fallback geometry, or fallback presentation.
- Descriptor-v2 has generic `contactSlots` and node `contactSlotID` values. Its `modelBounds` remain unit-local source geometry bounds.
- Reusable media has exactly two instances. Each has an equipment object ID, finite base translation with exactly nine decimal places, a unit quaternion in `[x,y,z,w]` order, optional `reflection: "x"`, exact slot map, and exactly one pose mechanism.
- Apply `F` then `B(p)=c+Rbase*(F(p)-c)+tbase` then `W(p)=ci+Rposition*(B(p)-ci)+tposition`, where `ci=B(c)`.
- Instance slot-map keys equal descriptor slots. Values are unique globally, union to all board contacts, and belong to their equipment object. Both position maps equal the package position IDs and each other.
- Reject invalid descriptor version, transforms, reflection, maps, suspension bindings, hidden-route claims, mixed legacy/per-instance pose data, and position sets. Mark the model unavailable and never raster-fallback.
- Reusable runtime loads USDZ once and deep-clones geometry and materials twice. Keep canonical-ID picking, highlights, workouts, and accessibility isolated per instance. Reflection preserves winding, normals, and culling.
- Cords are per-instance transient non-pickable inaccessible geometry. Active camera framing is the union of transformed units and active cords.
- Retain evidence-backed contacts, recesses, and cord apertures. Remove all screws, holes for mounting, cleats, brackets, and mounting-hardware meshes.
- Directly author geometry from approved evidence. Never trace, segment, vectorize, register, align, contour, crop, mask, detect, or propose geometry from images.
- Astra alone authors and visually approves shape-sensitive geometry. Lower-cost workers handle code, metadata, and automated checks.
- Retain exact approved evidence bytes and hashes. Label unavailable verified bytes `requiresExactRetention`, unknown binary URLs `unhashed`, and unsurveyed dimensions `authored-display-estimate`.
- Generated resources use `.context/learned-giraffe-*`, are registered immediately, and are removed by an exit trap after verification. USDZ alone is ODR.
- Pivot has one manually authored half, a reflected right instance, 18 contacts, and selectable `p1`, `p2`, `p3`, `p5` only. Rock Rings and Penta render identical unreflected units.

## Review Focus

- Reflected Pivot winding, normals, and culling are pinned by Task 5 `BoardModelTests.testReusableUnitReflectionPreservesOutwardNormalsAndCulling()`.
- Material, contact, cord, and pose-cache isolation are pinned by Task 6 `BoardModelTests.testReusableInstancesIsolateHighlightAndSuspensionState()`.
- Rotation about the placed bounds centre is pinned by Task 5 `BoardModelTests.testReusableInstanceAppliesBaseThenPositionAboutPlacedBoundsCenter()`.
- Cross-equipment slot maps are pinned by Task 3 `def test_v3_reusable_instances_reject_cross_object_slot_mapping(tmp_path: Path) -> None`.
- Real apertures versus deleted fastener holes are pinned by Task 13 `def test_batch04_model_geometry_retains_only_documented_attachment_openings() -> None`.

---

## Exact interfaces

- Task 1 owns `Tools/HangboardModels/contact_model_descriptor.py:17-177`: `SlotNodeBinding`, `ContactSlotDescriptorV2`, `ModelDescriptorV2`, and `compile_reusable_descriptor`. It does not alter `NodeBinding`, `ModelDescriptorV1`, or `compile_descriptor`.
- Task 2 owns compiler/importer output. Its exact compiler signature is `compile_model_package(blend_path: Path, board_json_path: Path, output_directory: Path, *, descriptor_version: Literal[1, 2] = 1) -> ModelDescriptorV1 | ModelDescriptorV2`.
- Task 3 owns Python `BoardModelTransform`, `BoardModelInstance`, raw translation lexeme checking, and `PresentationMediaModel.instances`.
- Task 4 owns matching internal Swift `BoardModelTransform`, `BoardModelInstance`, `BoardModelDescriptor.contactSlots`, `BoardModelNodeDescriptor.contactSlotID`, and `BoardModelMedia.instances`.
- Task 5 owns internal `BoardModelInstanceScene`, `BoardModelScene.instanceScenes: [BoardModelInstanceScene]`, and `BoardModelScene.init?(source: SCNScene, descriptor: BoardModelDescriptor, display: BoardModelDisplay, suspension: BoardModelSuspension? = nil, orientation: BoardModelOrientation? = nil, allowedPositionIDs: Set<String>? = nil, resourceLease: BoardModelResourceLease? = nil, instances: [BoardModelInstance]? = nil)`. Task 6 owns internal `BoardModelInstanceScene.transientCordNodes: [SCNNode]` and `BoardModelScene.solveInstanceSuspension(instance: BoardModelInstanceScene, positionID: String) throws -> BoardModelSolvedSuspension`.

### Task 1: Add closed descriptor-v2 slot types

**Files:**
- Modify: `Tools/HangboardModels/contact_model_descriptor.py:17-177`
- Modify: `Tools/HangboardModels/test_contact_model_descriptor.py:9-100`

**Produces:** The exact Python types consumed by Tasks 2 and 3.

- [ ] **Step 1: Write RED tests for generic slots and v1 preservation.**

```python
def test_reusable_descriptor_v2_uses_generic_slots() -> None:
    descriptor = module.compile_reusable_descriptor(
        b"unit-usdz",
        (module.SlotNodeBinding("unit-body", "body"),
         module.SlotNodeBinding("unit-edge", "contact", "edge")),
        {"unit-body": ((0.0, 0.0, 0.0),), "unit-edge": ((0.2, 0.3, 0.0),)},
        frozenset({"edge"}),
    ).to_json()
    assert descriptor["schemaVersion"] == 2
    assert descriptor["nodes"] == [
        {"nodeID": "unit-body", "role": "body"},
        {"nodeID": "unit-edge", "role": "contact", "contactSlotID": "edge"},
    ]
    assert set(descriptor["contactSlots"]) == {"edge"}

def test_v1_descriptor_canonical_bytes_are_frozen() -> None:
    descriptor = module.compile_descriptor(
        b"exact-usdz",
        [module.NodeBinding("Body", "body"), module.NodeBinding("Contact", "contact", "edge-left")],
        {"Body": [(0.0, 0.0, 0.0), (1.0, 1.0, 0.2)], "Contact": [(0.1, 0.2, 0.2), (0.4, 0.5, 0.2)]},
        frozenset({"edge-left"}),
    )
    raw = json.dumps(descriptor.to_json(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert hashlib.sha256(raw).hexdigest() == "63b9ce74f1c8f86011d0396f6638ba987cf83393c39f8899f2bb88b201ae43e0"
```

- [ ] **Step 2: Run RED.**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_descriptor.py -q`

Expected: FAIL with `AttributeError` naming `compile_reusable_descriptor`.

- [ ] **Step 3: Implement exact closed types and parser.**

```python
@dataclass(frozen=True)
class SlotNodeBinding:
    node_id: str
    role: NodeRole | str
    contact_slot_id: str | None = None

@dataclass(frozen=True, init=False)
class ContactSlotDescriptorV2:
    node_ids: Sequence[str]
    face_plane_aabb: FacePlaneAABB
    center: Vector2

@dataclass(frozen=True, init=False)
class ModelDescriptorV2:
    model_sha256: str
    model_bounds: ModelBounds
    nodes: Sequence[SlotNodeBinding]
    contact_slots: Mapping[str, ContactSlotDescriptorV2]

def compile_reusable_descriptor(
    model_bytes: bytes,
    nodes: Sequence[SlotNodeBinding],
    vertices_by_node_id: Mapping[str, Sequence[Vector3]],
    contact_slot_ids: frozenset[str],
) -> ModelDescriptorV2:
    bindings = _validate_slot_bindings(nodes)
    slots = _validate_logical_contact_ids(contact_slot_ids)
    vertices = _validate_slot_bound_geometry(bindings, vertices_by_node_id)
    bounds = _raw_model_bounds(vertices.values())
    _require_nonzero_face_span(bounds)
    return ModelDescriptorV2._from_validated(
        hashlib.sha256(model_bytes).hexdigest(),
        _rounded_bounds(bounds),
        tuple(sorted(bindings, key=lambda item: item.node_id)),
        _compile_contact_slots(bindings, vertices, bounds, slots),
    )
```

Require exact v2 root keys `schemaVersion,coordinateFrame,modelSHA256,modelBounds,nodes,contactSlots`. Reject `contactID` on v2 nodes and `contacts` in v2. Descriptor bounds and AABBs retain existing numeric rounding rules.

- [ ] **Step 4: Run GREEN and v1 regression.**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_descriptor.py -q`

Expected: PASS, including the fixed v1 byte SHA-256 freeze.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Tools/HangboardModels/contact_model_descriptor.py Tools/HangboardModels/test_contact_model_descriptor.py`

Run: `rtk git commit -m "feat: add reusable model descriptor v2"`

Run: `rtk git push`

### Task 2: Compile and import direct source-to-slot mappings

**Files:**
- Modify: `Tools/HangboardModels/contact_model_package.py:73-223`
- Modify: `Tools/HangboardModels/import_contact_model_source.py:27-344`
- Modify: `Tools/HangboardModels/test_contact_model_package.py:11-37`
- Modify: `Tools/HangboardModels/test_import_contact_model_source.py:14-119`

**Consumes:** Task 1 types.

**Produces:** `ValidatedMapping.contact_slot_ids_by_node: Mapping[str, str]` for reusable imports and report field `contactSlotMappings: Mapping[str, str]`.

- [ ] **Step 1: Write RED compiler/importer tests.**

```python
def test_reusable_mapping_records_slot_ids() -> None:
    mapping = {"schemaVersion": 2, "unitContactSlotIDs": ["edge"], "objects": [
        {"sourceNodeID": "Body", "role": "body"},
        {"sourceNodeID": "Left", "role": "contact", "contactSlotID": "edge"},
        {"sourceNodeID": "Right", "role": "contact", "contactSlotID": "edge"},
    ]}
    result = importer.validate_mapping(mapping, {"Body": "MESH", "Left": "MESH", "Right": "MESH"})
    assert result.contact_slot_ids_by_node == {"Left": "edge", "Right": "edge"}
```

- [ ] **Step 2: Run RED.**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py -q`

Expected: FAIL because mapping schema version 2 is rejected.

- [ ] **Step 3: Implement the exact v2 branch.** Add `ValidatedMapping.contact_slot_ids_by_node: Mapping[str, str]` with an empty immutable map for v1. In schema v2 accept only `unitContactSlotIDs` and `contactSlotID`, tag Blender source objects with `contact_slot_id`, and call Task 1 compiler. Keep v1 `logicalContactIDs` and `contactID` code unchanged.

```python
def compile_model_package(
    blend_path: Path,
    board_json_path: Path,
    output_directory: Path,
    *,
    descriptor_version: Literal[1, 2] = 1,
) -> ModelDescriptorV1 | ModelDescriptorV2:
    if descriptor_version == 1:
        return _compile_v1_model_package(blend_path, board_json_path, output_directory)
    if descriptor_version == 2:
        return _compile_v2_model_package(blend_path, board_json_path, output_directory)
    raise ValueError("descriptor_version must be 1 or 2")
```

- [ ] **Step 4: Run GREEN.**

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_descriptor.py Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py -q`

Expected: PASS, including `test_v1_descriptor_canonical_bytes_are_frozen`.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Tools/HangboardModels/contact_model_package.py`

Run: `rtk git add Tools/HangboardModels/import_contact_model_source.py`

Run: `rtk git add Tools/HangboardModels/test_contact_model_package.py`

Run: `rtk git add Tools/HangboardModels/test_import_contact_model_source.py`

Run: `rtk git commit -m "feat: compile reusable hangboard units"`

Run: `rtk git push`

### Task 3: Validate instance metadata in Python and shared fixtures

**Files:**
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:376-1105`
- Modify: `Tools/HangboardPackages/tests/test_model_first_packages.py:35-715`
- Modify: `Tools/HangboardPackages/tests/test_model_orientation_inventory.py:67-479`
- Modify: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`

**Consumes:** Task 1 descriptor-v2 JSON.

**Produces:** frozen `BoardModelTransform(translation: tuple[float,float,float], rotation: tuple[float,float,float,float], reflection: Literal["x"] | None)`, frozen `BoardModelInstance`, and `PresentationMediaModel.instances: tuple[BoardModelInstance, BoardModelInstance] | None`. This task extends the existing `write_model_package(tmp_path: Path, *, descriptor_version: int = 1, instances: list[dict[str, object]] | None = None) -> Path` helper in `test_model_first_packages.py`; it adds `_valid_reusable_instances() -> list[dict[str, object]]` and `_write_reusable_model_package(tmp_path: Path) -> Path` there. The latter writes the fixture JSON through `_json_with_numeric_sentinels(value: object) -> str`, which replaces only quoted `@number:-?[0-9]+\.[0-9]{9}@` sentinel values with the contained JSON numeric lexeme before writing `board.json`.

- [ ] **Step 1: Add named RED map and lexical tests.**

```python
def test_v3_reusable_instances_reject_cross_object_slot_mapping(tmp_path: Path) -> None:
    document = _write_reusable_model_package(tmp_path)
    board_path = document / "board.json"
    raw = board_path.read_text()
    changed, count = re.subn(
        r'("contactIDsBySlotID"\s*:\s*\{\s*"edge"\s*:\s*)"edge-left"',
        r'\1"edge-right"', raw, count=1,
    )
    assert count == 1
    board_path.write_text(changed)
    with pytest.raises(ValueError, match="equipmentObjectID"):
        load_board_package(document)

def _valid_reusable_instances() -> list[dict[str, object]]:
    identity = {"translation": ["@number:0.000000000@", "@number:0.000000000@", "@number:0.000000000@"], "rotation": [0, 0, 0, 1]}
    return [
        {"equipmentObjectID": "left-unit", "baseTransform": {"translation": ["@number:-0.120000000@", "@number:0.000000000@", "@number:0.000000000@"], "rotation": [0, 0, 0, 1]}, "contactIDsBySlotID": {"edge": "edge-left"}, "positionTransforms": {"primary": identity}},
        {"equipmentObjectID": "right-unit", "baseTransform": {"translation": ["@number:0.120000000@", "@number:0.000000000@", "@number:0.000000000@"], "rotation": [0, 0, 0, 1]}, "contactIDsBySlotID": {"edge": "edge-right"}, "positionTransforms": {"primary": identity}},
    ]

def _json_with_numeric_sentinels(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True)
    return re.sub(r'"@number:(-?(?:0|[1-9][0-9]*)\.[0-9]{9})@"', r'\1', encoded)

def _write_reusable_model_package(tmp_path: Path) -> Path:
    document = write_model_package(tmp_path, descriptor_version=2, instances=_valid_reusable_instances())
    board_path = document / "board.json"
    board_path.write_text(_json_with_numeric_sentinels(json.loads(board_path.read_text())))
    return document

@pytest.mark.parametrize("invalid", ["0.1000000000", "1e-1", "NaN"])
def test_reusable_instances_reject_non_nine_decimal_raw_translation_lexemes(
    tmp_path: Path, invalid: str
) -> None:
    document = _write_reusable_model_package(tmp_path)
    board_path = document / "board.json"
    raw = board_path.read_text()
    changed, count = re.subn(r"0\.120000000", invalid, raw, count=1)
    assert count == 1
    board_path.write_text(changed)
    with pytest.raises(ValueError, match="nine decimal"):
        load_board_package(document)
```

Also test `translation: [0.1000000000,0.000000000,0.000000000]`, exponent notation, NaN, nonunit quaternion, unknown reflection, incomplete slots, duplicate map values, different position keys, and top-level `orientation` or `suspension`.

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_model_orientation_inventory.py -q`

Expected: FAIL because `instances` is an unknown media key.

- [ ] **Step 3: Implement raw translation lexeme validation before typed parsing.** Add private `_validate_instance_translation_lexemes(raw: str) -> None` in `board_catalog.py`. Use a small JSON token scanner that returns each number token with its object-member path. For every path ending `instances[index].baseTransform.translation[index]` or `instances[index].positionTransforms[positionID].translation[index]`, require regex `^-?(?:0|[1-9][0-9]*)\.[0-9]{9}$`. Reject exponent notation and every other decimal count. Run this scanner on `board.json` text in `load_board_package` before `json.loads`. Leave descriptor bounds and AABB values on their current numeric rounding validation.

- [ ] **Step 4: Parse exact instances.** `_load_media` accepts `instances` only for descriptor-v2. `_load_model_instance(value: Any, source: str) -> BoardModelInstance` requires exact keys `equipmentObjectID,baseTransform,contactIDsBySlotID` plus exactly one of `suspension,positionTransforms`. `_validate_reusable_instances(instances, slots, contacts, equipment_objects, position_ids) -> None` enforces the contract before building `PresentationMediaModel`.

- [ ] **Step 5: Run GREEN.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_model_first_packages.py Tools/HangboardPackages/tests/test_model_orientation_inventory.py -q`

Expected: PASS with explicit errors for every mutation.

- [ ] **Step 6: Fresh review, stage, commit, and push.**

Run: `rtk git add Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`

Run: `rtk git add Tools/HangboardPackages/tests/test_model_first_packages.py`

Run: `rtk git add Tools/HangboardPackages/tests/test_model_orientation_inventory.py`

Run: `rtk git add HangTenTests/Fixtures/BoardPackageValidationFixtures.json`

Run: `rtk git commit -m "feat: validate reusable model instances"`

Run: `rtk git push`

### Task 4: Decode and write the same contract in Swift

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:67-370`
- Modify: `HangTen/Models/BoardPackageStore.swift:780-1263,2398-2898`
- Modify: `HangTen/Models/BoardPackageWriter.swift:283-392`
- Modify: `HangTenTests/BoardPackageStoreTests.swift:520-640`
- Modify: `HangTenTests/BoardPackageWriterTests.swift:1-300`

**Consumes:** Task 3 fixture labels.

**Produces:** internal Swift types with the fields named in Exact interfaces for Tasks 5 and 6. `BoardPackageStoreTests` owns `private func reusableFixtureBoard(named: String) throws -> BoardRevision`, constructed by calling its existing `makeFixtureBundle` helper and `BoardPackageStore(bundle: fixture.bundle).boards.first`.

- [ ] **Step 1: Add RED XCTestCase methods.**

```swift
func testReusableModelMediaDecodesTwoInstances() throws {
    let board = try reusableFixtureBoard(named: "reusable-valid")
    guard case .model(let media) = board.defaultPresentation.media else {
        return XCTFail("fixture must decode model media")
    }
    XCTAssertEqual(media.instances?.count, 2)
    XCTAssertEqual(media.instances?[1].baseTransform.reflection, .x)
}
```

- [ ] **Step 2: Run RED.**

Run: `rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests test`

Expected: FAIL because model media has no `instances` decoder case.

- [ ] **Step 3: Preserve raw translation tokens before `JSONDecoder`.** Extend the existing `BoardPackageRawJSONParser` number representation to retain `lexeme: String` for integer and floating members. Add `private static func validateReusableTranslationLexemes(_ data: Data) throws` in `BoardPackageStore`. Walk raw member paths and require the same nine-decimal regex for only base and position translations. Call it before decoding a board package. Do not apply this lexical rule to descriptor vectors.

- [ ] **Step 4: Add exact Swift construction and validation.**

```swift
struct BoardModelTransform: Hashable {
    enum Reflection: String, Hashable { case x }
    let translation: [Double]
    let rotation: SIMD4<Double>
    let reflection: Reflection?
}

struct BoardModelInstance: Hashable {
    let equipmentObjectID: String
    let baseTransform: BoardModelTransform
    let contactIDsBySlotID: [String: String]
    let suspension: BoardModelSuspension?
    let positionTransforms: [String: BoardModelTransform]?
}
```

Dispatch descriptor documents by `schemaVersion`. Validate exact v2 slots, two instances, unit quaternions, values, position maps, and no top-level reusable pose data. Preserve v1 writer bytes and model decoding.

- [ ] **Step 5: Run GREEN.**

Run: `rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardPackageWriterTests test`

Expected: PASS, including existing v1 fixture decoding and the Task 1 canonical-byte freeze fixture mirrored in `BoardPackageStoreTests`.

- [ ] **Step 6: Fresh review, stage, commit, and push.**

Run: `rtk git add HangTen/Models/TrainingModels.swift`

Run: `rtk git add HangTen/Models/BoardPackageStore.swift`

Run: `rtk git add HangTen/Models/BoardPackageWriter.swift`

Run: `rtk git add HangTenTests/BoardPackageStoreTests.swift`

Run: `rtk git add HangTenTests/BoardPackageWriterTests.swift`

Run: `rtk git commit -m "feat: decode reusable model media"`

Run: `rtk git push`

### Task 5: Deep-clone reusable units and apply exact transforms

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift:147-360,371-1110`
- Modify: `HangTenTests/BoardModelTests.swift:300-2359`

**Consumes:** Task 4 validated `BoardModelMedia.instances`.

**Produces:** internal `final class BoardModelInstanceScene` with `let instance: BoardModelInstance`, `let container: SCNNode`, `var contactNodes: [String:[SCNNode]]`, `var sourceSlotNodes: [String:[SCNNode]]`, and `var originalMaterials: [ObjectIdentifier:[SCNMaterial]]`. `BoardModelScene` gains internal `private(set) var instanceScenes: [BoardModelInstanceScene]`.

`BoardModelTests` owns private method `makeReusableScene(reflection: BoardModelTransform.Reflection?, suspensions: [BoardModelSuspension]?) throws -> BoardModelScene`, constructing the minimal two-triangle `SCNScene`, descriptor-v2 slot `edge`, and exactly two `BoardModelInstance` values. It calls `BoardModelScene(source:descriptor:display:suspension:orientation:allowedPositionIDs:resourceLease:instances:)` with those exact values. `BoardModelScene` owns internal `reusableTriangleSignedArea(instanceIndex: Int) -> Float` and `reusableNormalDotOutward(instanceIndex: Int) -> Float` used only by this test.

- [ ] **Step 1: Add exact RED transform and reflection tests.**

```swift
func testReusableInstanceAppliesBaseThenPositionAboutPlacedBoundsCenter() throws {
    let c = SIMD3<Float>(2, 3, 5)
    let p = SIMD3<Float>(4, 3, 5)
    let f = SIMD3<Float>(0, 3, 5)
    let baseRotation = simd_quatf(angle: .pi, axis: SIMD3<Float>(0, 0, 1))
    let b = c + baseRotation.act(f - c) + SIMD3<Float>(10, 0, 0)
    let ci = c + baseRotation.act(c - c) + SIMD3<Float>(10, 0, 0)
    let positionRotation = simd_quatf(angle: .pi, axis: SIMD3<Float>(0, 1, 0))
    let w = ci + positionRotation.act(b - ci) + SIMD3<Float>(-20, 0, 0)
    XCTAssertEqual(f, SIMD3<Float>(0, 3, 5))
    XCTAssertEqual(b, SIMD3<Float>(14, 3, 5))
    XCTAssertEqual(ci, SIMD3<Float>(12, 3, 5))
    XCTAssertEqual(w, SIMD3<Float>(-10, 3, 5))
    XCTAssertEqual(try BoardModelScene.reusableTransform(point: p, center: c, reflection: .x,
        baseRotation: baseRotation, baseTranslation: SIMD3<Float>(10, 0, 0),
        positionRotation: positionRotation, positionTranslation: SIMD3<Float>(-20, 0, 0)), w)
}

func testReusableUnitReflectionPreservesOutwardNormalsAndCulling() throws {
    let scene = try makeReusableScene(reflection: .x, suspensions: nil)
    XCTAssertTrue(scene.instanceScenes[1].container.childNodes.allSatisfy { $0.geometry?.firstMaterial?.isDoubleSided == false })
    XCTAssertGreaterThan(scene.reusableTriangleSignedArea(instanceIndex: 1), 0)
    XCTAssertGreaterThan(scene.reusableNormalDotOutward(instanceIndex: 1), 0)
}
```

- [ ] **Step 2: Run RED.**

Run: `rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardModelTests test`

Expected: FAIL because `BoardModelScene.reusableTransform` and `instanceScenes` do not exist.

- [ ] **Step 3: Implement one load and two independent clones.** Extend `BoardModelScene.init?` to `init?(source: SCNScene, descriptor: BoardModelDescriptor, display: BoardModelDisplay, suspension: BoardModelSuspension? = nil, orientation: BoardModelOrientation? = nil, allowedPositionIDs: Set<String>? = nil, resourceLease: BoardModelResourceLease? = nil, instances: [BoardModelInstance]? = nil)`. `BoardModelLoader.load` passes `media.instances` while preserving descriptor-v1 `suspension`, `orientation`, `allowedPositionIDs`, and `resourceLease` behavior. Keep `BoardModelCache.loadSource` as the only source-scene decode boundary. Expose only under `#if DEBUG` an internal `BoardModelLoader.debugSourceSceneDecodeCount: Int` and `BoardModelLoader.resetDebugSourceSceneDecodeCount()`, incrementing the count immediately after `BoardModelCache.source` returns a decoded source scene. `BoardModelTests` resets it, loads a two-instance board through `BoardModelLoader.load`, and asserts one. Clone `source.rootNode` twice. For each geometry copy every `SCNGeometry` and every `SCNMaterial`, reverse each triangle index order after X reflection, invert normals if needed, then map slot nodes through `contactIDsBySlotID`.

- [ ] **Step 4: Implement concrete transform helper.** Add internal static `BoardModelScene.reusableTransform(point:center:reflection:baseRotation:baseTranslation:positionRotation:positionTranslation:) throws -> SIMD3<Float>`. It computes `f`, `b`, `ci`, and `w` in the test order and rejects nonfinite output. Apply its matrix equivalent to each instance container. Build camera bounds from both transformed bounds.

- [ ] **Step 5: Run GREEN.**

Run: `rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardModelTests test`

Expected: PASS.

- [ ] **Step 6: Fresh review, stage, commit, and push.**

Run: `rtk git add HangTen/Views/BoardModelView.swift`

Run: `rtk git add HangTenTests/BoardModelTests.swift`

Run: `rtk git commit -m "feat: instance reusable hangboard models"`

Run: `rtk git push`

### Task 6: Isolate per-instance picking, highlights, and suspension

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift:537-1110`
- Modify: `HangTen/Views/SuspendedBoardPresentation.swift:37-1044`
- Modify: `HangTenTests/BoardModelTests.swift:300-2359`
- Modify: `HangTenTests/SuspendedBoardPresentationTests.swift:1-1350`

**Consumes:** Task 5 instance scenes.

**Produces:** `BoardModelInstanceScene.transientCordNodes: [SCNNode]`, `BoardModelInstanceScene.verifiedPresentations: [String:BoardModelSolvedSuspension]`, `BoardModelInstanceScene.highlightedContactIDs: Set<String>`, and `BoardModelScene.solveInstanceSuspension(instance:positionID:) throws -> BoardModelSolvedSuspension`. `BoardModelTests` adds private `twoIndependentPairedLeadSuspensions() -> [BoardModelSuspension]`, constructing two `BoardModelPairedLeadCord` values with distinct anchor offsets and attachment IDs, then supplies it to Task 5 `makeReusableScene(reflection:suspensions:)`.

- [ ] **Step 1: Add RED isolation test.**

```swift
func testReusableInstancesIsolateHighlightAndSuspensionState() throws {
    let scene = try makeReusableScene(reflection: nil, suspensions: twoIndependentPairedLeadSuspensions())
    scene.highlight(Set(["edge-left"]), mode: .active)
    XCTAssertEqual(scene.instanceScenes[0].highlightedContactIDs, ["edge-left"])
    XCTAssertTrue(scene.instanceScenes[1].highlightedContactIDs.isEmpty)
    XCTAssertTrue(scene.select(positionID: "primary"))
    XCTAssertEqual(scene.instanceScenes[0].transientCordNodes.count, 1)
    XCTAssertEqual(scene.instanceScenes[1].transientCordNodes.count, 1)
    XCTAssertNotEqual(ObjectIdentifier(scene.instanceScenes[0].transientCordNodes[0]), ObjectIdentifier(scene.instanceScenes[1].transientCordNodes[0]))
}
```

- [ ] **Step 2: Run RED.**

Run: `rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/SuspendedBoardPresentationTests test`

Expected: FAIL because current state is shared by `BoardModelScene`.

- [ ] **Step 3: Move mutable state into the instance type.** `solveInstanceSuspension` reads that instance's transformed attachment nodes and per-instance suspension only. It assigns category `cordCategory`, excludes cord nodes from hit test masks and accessibility, and includes their bounds in union framing. Keep `SuspensionProfiles.swift` unchanged.

- [ ] **Step 4: Run GREEN.**

Run: `rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/SuspendedBoardPresentationTests test`

Expected: PASS.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add HangTen/Views/BoardModelView.swift`

Run: `rtk git add HangTen/Views/SuspendedBoardPresentation.swift`

Run: `rtk git add HangTenTests/BoardModelTests.swift`

Run: `rtk git add HangTenTests/SuspendedBoardPresentationTests.swift`

Run: `rtk git commit -m "feat: isolate reusable model suspension"`

Run: `rtk git push`

### Task 7: Add source-audit documents with document-only tests

**Files:**
- Create: `docs/source-audits/2026-09-20-batch-04-3d-source-register.json`
- Create: `docs/source-audits/2026-09-20-batch-04-source-to-contact-audit.md`
- Modify: `docs/source-audits/2026-09-13-model-hangboard-cord-audit.json`
- Modify: `docs/source-audits/2026-09-13-model-hangboard-cord-audit.md`
- Modify: `docs/source-audits/2026-09-11-3d-board-orientation-audit.md`
- Modify: `docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json`
- Create: `Tools/HangboardPackages/tests/test_batch04_source_audit.py`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/batch-checksums.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/crimptonite-helium-mobile.glb`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/metolius-light-rail-2-0.glb`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/metolius-rock-rings-3d.glb`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/owl-climb-poker.glb`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/yy-vertical-penta-evo.glb`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/trango-rock-prodigy-pivot-rejected.glb`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/source-register.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/media-manifest.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/source-register.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/media-manifest.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/source-register.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/media-manifest.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/source-register.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/media-manifest.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/source-register.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/media-manifest.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/source-register.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/media-manifest.json`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/182984fc8f-Helium--mobile-hangboard-by-Crimptonite_08.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/xaEAAOSwFtFmDzoB.webp`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/KQkAAOSwjmJmDzoE.webp`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/61cd4a213f-owlclimb_poker19_0.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/d8dc16e362-owlclimb_poker19_1.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/3231a07015-owlclimb_poker19_2.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/340a73e020-owlclimb_poker19_3.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/14b413b6dd-yy-vertical-agres-nomades-penta-evo-3.webp`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/9957e0d26b-yy-vertical-agres-nomades-penta-evo-6.webp`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/Helium--mobile-hangboard-by-Crimptonite_06.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/Light-Rail-2-PT.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/metolius-light-rail-1.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/Rock-Rings-black-white.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840-501_RockProdigyPivotGrey_MainImage.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage4_DualBoard.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage3_SingleBoard.jpg`
- Create: `docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage2_CloseUp.jpg`

**Produces:** exact evidence/source-map documents used by Tasks 8 through 13.

- [ ] **Step 1: Add a RED document-only parser test.**

```python
def test_batch04_source_register_and_pivot_mapping_are_closed() -> None:
    register = json.loads(SOURCE_REGISTER.read_text())
    assert register["schemaVersion"] == 1
    assert set(register["boards"]) == {
        "crimptonite.helium-mobile", "metolius.light-rail-2",
        "metolius.rock-rings-3d", "owl-climb.poker", "yy.penta-evo",
        "trango.rock-prodigy-pivot",
    }
    audit = SOURCE_CONTACT_AUDIT.read_text()
    assert audit.startswith("# Batch 04 Source-to-Contact Audit")
    assert "| Pivot source patch | Slot | Left contact | Right contact |" in audit
    pivot = register["boards"]["trango.rock-prodigy-pivot"]
    assert pivot["pivotPatchMappings"]["wing crest"] == "outer-wedge-pinch"
    assert pivot["selectablePositions"] == ["p1", "p2", "p3", "p5"]
    assert pivot["pivotPatchMappings"] == {
        "wing crest": "outer-wedge-pinch", "wing inner": "outer-wedge-pinch",
        "rail lower": "variable-edge", "rail upper": "variable-edge",
        "rail-end outer": "variable-edge", "rail-end inner": "variable-edge",
        "supported lower": "medium-crimp", "supported upper": "large-crimp",
        "two-finger top": "two-finger-pocket", "two-finger side": "two-finger-pocket",
        "three-finger top": "three-finger-pocket", "top sloped": "upper-sloped-crimp",
        "side sloped": "outer-sloped-crimp", "lower-wave sloper": "lower-sloper",
    }
    delivered_patch_mappings = pivot["pivotPatchMappingsByDeliveredID"]
    delivered_suffixes = {
        "wing crest": "wing-crest", "wing inner": "wing-inner",
        "rail lower": "rail-lower", "rail upper": "rail-upper",
        "rail-end outer": "rail-end-outer", "rail-end inner": "rail-end-inner",
        "supported lower": "supported-lower", "supported upper": "supported-upper",
        "two-finger top": "twofinger-top", "two-finger side": "twofinger-side",
        "three-finger top": "threefinger-top", "top sloped": "top-sloped-crimp",
        "side sloped": "side-sloped-crimp", "lower-wave sloper": "lower-wave-sloper",
    }
    for normalized_patch, delivered_suffix in delivered_suffixes.items():
        slot_id = pivot["pivotPatchMappings"][normalized_patch]
        assert delivered_patch_mappings[f"pv-L-{delivered_suffix}"] == slot_id
        assert delivered_patch_mappings[f"pv-R-{delivered_suffix}"] == slot_id
    retired = pivot["retiredPresentationIDToContactID"]
    expected_retired = {
        "large-crimp-left": "large-crimp-left",
        "large-crimp-left-orientation-2": "large-crimp-left",
        "large-crimp-left-orientation-3": "large-crimp-left",
        "large-crimp-left-orientation-4": "large-crimp-left",
        "large-crimp-right": "large-crimp-right",
        "large-crimp-right-orientation-2": "large-crimp-right",
        "large-crimp-right-orientation-3": "large-crimp-right",
        "large-crimp-right-orientation-4": "large-crimp-right",
        "lower-sloper-left": "lower-sloper-left",
        "lower-sloper-left-orientation-2": "lower-sloper-left",
        "lower-sloper-left-orientation-3": "lower-sloper-left",
        "lower-sloper-left-orientation-4": "lower-sloper-left",
        "lower-sloper-right": "lower-sloper-right",
        "lower-sloper-right-orientation-2": "lower-sloper-right",
        "lower-sloper-right-orientation-3": "lower-sloper-right",
        "lower-sloper-right-orientation-4": "lower-sloper-right",
        "medium-crimp-left": "medium-crimp-left",
        "medium-crimp-left-orientation-2": "medium-crimp-left",
        "medium-crimp-left-orientation-3": "medium-crimp-left",
        "medium-crimp-left-orientation-4": "medium-crimp-left",
        "medium-crimp-right": "medium-crimp-right",
        "medium-crimp-right-orientation-2": "medium-crimp-right",
        "medium-crimp-right-orientation-3": "medium-crimp-right",
        "medium-crimp-right-orientation-4": "medium-crimp-right",
        "outer-sloped-crimp-left": "outer-sloped-crimp-left",
        "outer-sloped-crimp-left-orientation-2": "outer-sloped-crimp-left",
        "outer-sloped-crimp-left-orientation-3": "outer-sloped-crimp-left",
        "outer-sloped-crimp-left-orientation-4": "outer-sloped-crimp-left",
        "outer-sloped-crimp-right": "outer-sloped-crimp-right",
        "outer-sloped-crimp-right-orientation-2": "outer-sloped-crimp-right",
        "outer-sloped-crimp-right-orientation-3": "outer-sloped-crimp-right",
        "outer-sloped-crimp-right-orientation-4": "outer-sloped-crimp-right",
        "outer-wedge-pinch-left": "outer-wedge-pinch-left",
        "outer-wedge-pinch-left-orientation-2": "outer-wedge-pinch-left",
        "outer-wedge-pinch-left-orientation-3": "outer-wedge-pinch-left",
        "outer-wedge-pinch-left-orientation-4": "outer-wedge-pinch-left",
        "outer-wedge-pinch-right": "outer-wedge-pinch-right",
        "outer-wedge-pinch-right-orientation-2": "outer-wedge-pinch-right",
        "outer-wedge-pinch-right-orientation-3": "outer-wedge-pinch-right",
        "outer-wedge-pinch-right-orientation-4": "outer-wedge-pinch-right",
        "three-finger-pocket-left": "three-finger-pocket-left",
        "three-finger-pocket-left-orientation-2": "three-finger-pocket-left",
        "three-finger-pocket-left-orientation-3": "three-finger-pocket-left",
        "three-finger-pocket-left-orientation-4": "three-finger-pocket-left",
        "three-finger-pocket-right": "three-finger-pocket-right",
        "three-finger-pocket-right-orientation-2": "three-finger-pocket-right",
        "three-finger-pocket-right-orientation-3": "three-finger-pocket-right",
        "three-finger-pocket-right-orientation-4": "three-finger-pocket-right",
        "two-finger-pocket-left": "two-finger-pocket-left",
        "two-finger-pocket-left-orientation-2": "two-finger-pocket-left",
        "two-finger-pocket-left-orientation-3": "two-finger-pocket-left",
        "two-finger-pocket-left-orientation-4": "two-finger-pocket-left",
        "two-finger-pocket-right": "two-finger-pocket-right",
        "two-finger-pocket-right-orientation-2": "two-finger-pocket-right",
        "two-finger-pocket-right-orientation-3": "two-finger-pocket-right",
        "two-finger-pocket-right-orientation-4": "two-finger-pocket-right",
        "upper-sloped-crimp-left": "upper-sloped-crimp-left",
        "upper-sloped-crimp-left-orientation-2": "upper-sloped-crimp-left",
        "upper-sloped-crimp-left-orientation-3": "upper-sloped-crimp-left",
        "upper-sloped-crimp-left-orientation-4": "upper-sloped-crimp-left",
        "upper-sloped-crimp-right": "upper-sloped-crimp-right",
        "upper-sloped-crimp-right-orientation-2": "upper-sloped-crimp-right",
        "upper-sloped-crimp-right-orientation-3": "upper-sloped-crimp-right",
        "upper-sloped-crimp-right-orientation-4": "upper-sloped-crimp-right",
        "variable-edge-left": "variable-edge-left",
        "variable-edge-left-orientation-2": "variable-edge-left",
        "variable-edge-left-orientation-3": "variable-edge-left",
        "variable-edge-left-orientation-4": "variable-edge-left",
        "variable-edge-right": "variable-edge-right",
        "variable-edge-right-orientation-2": "variable-edge-right",
        "variable-edge-right-orientation-3": "variable-edge-right",
        "variable-edge-right-orientation-4": "variable-edge-right",
    }
    assert len(retired) == 72
    assert retired == expected_retired
```

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch04_source_audit.py -q`

Expected: FAIL because the source register does not exist.

- [ ] **Step 3: Copy and hash exact source delivery before authoring.** Follow the tracked 2026-09-16 source-delivery precedent. Create every destination before copying. Copy each delivered GLB to the named source-delivery path, including rejected Pivot source, and copy all twelve source-register/media-manifest files to their named evidence paths. Copy the nine batch-present originals first, then retrieve every missing approved hashed byte with the approved URL and verify its exact SHA-256. `requiresExactRetention` is only a pre-retrieval audit state: GREEN requires every approved hashed byte to be retained. Keep Penta source records with `binaryURL: null` and `unhashed` rather than inventing a URL.

Run: `rtk proxy mkdir -p docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/batch-checksums.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/batch-checksums.json`

Run: `rtk proxy mkdir -p docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile`

Run: `rtk proxy mkdir -p docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0`

Run: `rtk proxy mkdir -p docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d`

Run: `rtk proxy mkdir -p docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker`

Run: `rtk proxy mkdir -p docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo`

Run: `rtk proxy mkdir -p docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/crimptonite-helium-mobile/evidence/source-register.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/source-register.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/crimptonite-helium-mobile/evidence/media-manifest.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/media-manifest.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-light-rail-2-0/evidence/source-register.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/source-register.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-light-rail-2-0/evidence/media-manifest.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/media-manifest.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-rock-rings-3d/evidence/source-register.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/source-register.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-rock-rings-3d/evidence/media-manifest.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/media-manifest.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/owl-climb-poker/evidence/source-register.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/source-register.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/owl-climb-poker/evidence/media-manifest.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/media-manifest.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/yy-vertical-penta-evo/evidence/source-register.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/source-register.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/yy-vertical-penta-evo/evidence/media-manifest.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/media-manifest.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/trango-rock-prodigy-pivot/evidence/source-register.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/source-register.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/trango-rock-prodigy-pivot/evidence/media-manifest.json docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/media-manifest.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/source-register.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/media-manifest.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/source-register.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/media-manifest.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/source-register.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/media-manifest.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/source-register.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/media-manifest.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/source-register.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/media-manifest.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/source-register.json`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/media-manifest.json`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/crimptonite-helium-mobile/evidence/originals/182984fc8f-Helium--mobile-hangboard-by-Crimptonite_08.jpg docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/182984fc8f-Helium--mobile-hangboard-by-Crimptonite_08.jpg`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-rock-rings-3d/evidence/originals/xaEAAOSwFtFmDzoB.webp docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/xaEAAOSwFtFmDzoB.webp`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-rock-rings-3d/evidence/originals/KQkAAOSwjmJmDzoE.webp docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/KQkAAOSwjmJmDzoE.webp`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/owl-climb-poker/evidence/originals/61cd4a213f-owlclimb_poker19_0.jpg docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/61cd4a213f-owlclimb_poker19_0.jpg`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/owl-climb-poker/evidence/originals/d8dc16e362-owlclimb_poker19_1.jpg docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/d8dc16e362-owlclimb_poker19_1.jpg`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/owl-climb-poker/evidence/originals/3231a07015-owlclimb_poker19_2.jpg docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/3231a07015-owlclimb_poker19_2.jpg`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/owl-climb-poker/evidence/originals/340a73e020-owlclimb_poker19_3.jpg docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/owl-climb-poker/340a73e020-owlclimb_poker19_3.jpg`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/yy-vertical-penta-evo/evidence/originals/14b413b6dd-yy-vertical-agres-nomades-penta-evo-3.webp docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/14b413b6dd-yy-vertical-agres-nomades-penta-evo-3.webp`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/yy-vertical-penta-evo/evidence/originals/9957e0d26b-yy-vertical-agres-nomades-penta-evo-6.webp docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/yy-vertical-penta-evo/9957e0d26b-yy-vertical-agres-nomades-penta-evo-6.webp`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/crimptonite-helium-mobile/crimptonite-helium-mobile.glb docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/crimptonite-helium-mobile.glb`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/crimptonite-helium-mobile.glb`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-light-rail-2-0/metolius-light-rail-2-0.glb docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/metolius-light-rail-2-0.glb`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/metolius-light-rail-2-0.glb`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/metolius-rock-rings-3d/metolius-rock-rings-3d.glb docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/metolius-rock-rings-3d.glb`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/metolius-rock-rings-3d.glb`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/owl-climb-poker/owl-climb-poker.glb docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/owl-climb-poker.glb`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/owl-climb-poker.glb`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/yy-vertical-penta-evo/yy-vertical-penta-evo.glb docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/yy-vertical-penta-evo.glb`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/yy-vertical-penta-evo.glb`

Run: `rtk proxy cp /Users/asherlc/Downloads/hangboards-batch-04/models/trango-rock-prodigy-pivot/trango-rock-prodigy-pivot.glb docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/trango-rock-prodigy-pivot-rejected.glb`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/source-delivery/trango-rock-prodigy-pivot-rejected.glb`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/Helium--mobile-hangboard-by-Crimptonite_06.jpg 'https://9cbouldering.com/cdn/shop/products/Helium--mobile-hangboard-by-Crimptonite_06.jpg?v=1704979580'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/crimptonite-helium-mobile/Helium--mobile-hangboard-by-Crimptonite_06.jpg`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/Light-Rail-2-PT.jpg 'https://www.metoliusclimbing.com/cdn/shop/files/Light-Rail-2-PT.jpg?v=1767727616'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/Light-Rail-2-PT.jpg`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/metolius-light-rail-1.jpg 'https://images.squarespace-cdn.com/content/v1/5b4544e485ede17941bc95fc/452f6e96-37f1-454d-a405-e801658501a5/metolius-light-rail-1.jpg'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-light-rail-2-0/metolius-light-rail-1.jpg`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/Rock-Rings-black-white.jpg 'https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg?v=1759460123'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/metolius-rock-rings-3d/Rock-Rings-black-white.jpg`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840-501_RockProdigyPivotGrey_MainImage.jpg 'https://trango.com/cdn/shop/products/22840-501_RockProdigyPivotGrey_MainImage.jpg?v=1755037446&width=1946'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840-501_RockProdigyPivotGrey_MainImage.jpg`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage4_DualBoard.jpg 'https://trango.com/cdn/shop/products/22840_RockProdigyPivot_AltImage4_DualBoard.jpg?v=1755037446&width=1946'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage4_DualBoard.jpg`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage3_SingleBoard.jpg 'https://trango.com/cdn/shop/products/22840_RockProdigyPivot_AltImage3_SingleBoard.jpg?v=1755037446&width=1946'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage3_SingleBoard.jpg`

Run: `rtk curl -L -o docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage2_CloseUp.jpg 'https://trango.com/cdn/shop/products/22840_RockProdigyPivot_AltImage2_CloseUp.jpg?v=1755037446&width=1946'`

Run: `rtk proxy shasum -a 256 docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence/trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage2_CloseUp.jpg`

- [ ] **Step 4: Author exact audit documents and source-retention tests.** Register every approved URL, supplied SHA-256, retained path, status, source fact, display-estimate label, supersession/compatibility ruling, and source-to-slot/contact mapping. The normalized Pivot unit-local patch keys map to exact delivered `pv-L-*` and `pv-R-*` IDs; assert every mapping for both halves. Test every retained GLB, copied register/manifest, and approved hashed byte exists and has its exact expected SHA-256. During retrieval, compare every `shasum` result to the following approved values; a mismatch fails and triggers research for the exact variant, never a metadata update to bless changed bytes. The Treeline direct URL is accepted only when it hashes to `93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a`. Include Helium lip merges, four Poker face mappings plus both restored recesses, Ring/Penta maps, Pivot's asserted 72-to-18 inventory, p4 transition-only, and every cord ruling. Document test validates files only and does not discover packages.

```python
EXPECTED_APPROVED_SHA256 = {
    "crimptonite-helium-mobile/Helium--mobile-hangboard-by-Crimptonite_06.jpg": "9f5dea470c326d32c6bde1dd5427f2bfb95a81b99ae258c320ae9deec0384a40",
    "crimptonite-helium-mobile/182984fc8f-Helium--mobile-hangboard-by-Crimptonite_08.jpg": "5d5c18d45ae6d30e6e951aa158a30b303d42d4583d18d4a6d82075ff5de50f6a",
    "metolius-light-rail-2-0/Light-Rail-2-PT.jpg": "7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272",
    "metolius-light-rail-2-0/metolius-light-rail-1.jpg": "93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a",
    "metolius-rock-rings-3d/Rock-Rings-black-white.jpg": "d92a0f25dab857eae2ee9b8581651fa9162452c38e32a7955e23c74de4a3d77c",
    "metolius-rock-rings-3d/xaEAAOSwFtFmDzoB.webp": "b510bd192bb6fe54c6e4dcfa98c9d684a2db7582cbfd3682cebb6e031494a8f0",
    "metolius-rock-rings-3d/KQkAAOSwjmJmDzoE.webp": "df263e67395aa17a2f4df263ca74e4cbbfb7bfcf9c75e0dfa611d352ad3d3cba",
    "owl-climb-poker/61cd4a213f-owlclimb_poker19_0.jpg": "4bae58b408b3f3a82c524b1101079eafa01cd062c398cb203d4803fce9850eab",
    "owl-climb-poker/d8dc16e362-owlclimb_poker19_1.jpg": "0c1d54cb2bc4d8e7fa285f3053b927d7c1a1b3fbafdf0b5d7aface9c82d0dbad",
    "owl-climb-poker/3231a07015-owlclimb_poker19_2.jpg": "5fbff79f31db8e85d078a74eb629abd069fc276ac128b3d85a84fc15ad9f1c4e",
    "owl-climb-poker/340a73e020-owlclimb_poker19_3.jpg": "ae39598fbf75c0e4e4dfbb599c724ff1e2531ef12ecca84b3504805e7bc3af13",
    "yy-vertical-penta-evo/14b413b6dd-yy-vertical-agres-nomades-penta-evo-3.webp": "83b95adc297d634659654f6f27bb43ebae1c53b171b747568ac5e022754e6571",
    "yy-vertical-penta-evo/9957e0d26b-yy-vertical-agres-nomades-penta-evo-6.webp": "1107039ef6d2877cd68a293683c72ec93f3166633199d45484f58c13b48aa2fc",
    "trango-rock-prodigy-pivot/22840-501_RockProdigyPivotGrey_MainImage.jpg": "339f743c7e5fff0b0619314cf6781d8f602c1545975390f4ab4424aa7461bf5d",
    "trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage4_DualBoard.jpg": "e05deb5c0ea6d3361122926d7b3efee6b72bb9aad0a75fc09663bf599731e3e4",
    "trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage3_SingleBoard.jpg": "7aa2556dec24293e62c2be110fa7dfb6bcf118333ff35693e455a8a7babc67f7",
    "trango-rock-prodigy-pivot/22840_RockProdigyPivot_AltImage2_CloseUp.jpg": "26cf8d599a1a08bbcbbf688e14c9806d5f2381dc2aecdb608998ab22cee2c1b3",
}

def test_batch04_retains_every_approved_hashed_byte() -> None:
    evidence_root = REPO_ROOT / "docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence"
    for relative_path, expected_sha256 in EXPECTED_APPROVED_SHA256.items():
        retained = evidence_root / relative_path
        assert retained.is_file(), retained
        assert hashlib.sha256(retained.read_bytes()).hexdigest() == expected_sha256

def test_batch04_copied_source_documents_are_present_and_parseable() -> None:
    evidence_root = REPO_ROOT / "docs/source-audits/2026-09-20-hangboards-batch-04-model-imports/evidence"
    for slug in ("crimptonite-helium-mobile", "metolius-light-rail-2-0", "metolius-rock-rings-3d", "owl-climb-poker", "yy-vertical-penta-evo", "trango-rock-prodigy-pivot"):
        for filename in ("source-register.json", "media-manifest.json"):
            retained = evidence_root / slug / filename
            assert retained.is_file(), retained
            json.loads(retained.read_text())

def test_batch04_retained_source_delivery_glbs_match_batch_checksums() -> None:
    audit_root = REPO_ROOT / "docs/source-audits/2026-09-20-hangboards-batch-04-model-imports"
    batch_checksums = json.loads((audit_root / "batch-checksums.json").read_text())
    retained_to_original = {
        "crimptonite-helium-mobile.glb": "models/crimptonite-helium-mobile/crimptonite-helium-mobile.glb",
        "metolius-light-rail-2-0.glb": "models/metolius-light-rail-2-0/metolius-light-rail-2-0.glb",
        "metolius-rock-rings-3d.glb": "models/metolius-rock-rings-3d/metolius-rock-rings-3d.glb",
        "owl-climb-poker.glb": "models/owl-climb-poker/owl-climb-poker.glb",
        "yy-vertical-penta-evo.glb": "models/yy-vertical-penta-evo/yy-vertical-penta-evo.glb",
        "trango-rock-prodigy-pivot-rejected.glb": "models/trango-rock-prodigy-pivot/trango-rock-prodigy-pivot.glb",
    }
    for retained_name, original_path in retained_to_original.items():
        retained = audit_root / "source-delivery" / retained_name
        assert retained.is_file(), retained
        assert hashlib.sha256(retained.read_bytes()).hexdigest() == batch_checksums[original_path]
```

- [ ] **Step 5: Run GREEN.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_batch04_source_audit.py -q`

Expected: PASS.

- [ ] **Step 6: Fresh review, stage, commit, and push.**

Run: `rtk git add docs/source-audits`

Run: `rtk git add Tools/HangboardPackages/tests/test_batch04_source_audit.py`

Run: `rtk git commit -m "docs: audit batch 04 model evidence"`

Run: `rtk git push`

### Task 8: Astra migrate Helium Mobile

**Files:**
- Modify: `Hangboards/crimptonite-helium-mobile/board.json`
- Create: `Hangboards/crimptonite-helium-mobile/assets/primary.usdz`
- Create: `Hangboards/crimptonite-helium-mobile/assets/primary.model.json`
- Delete: `Hangboards/crimptonite-helium-mobile/assets/primary.png`
- Delete: `Hangboards/crimptonite-helium-mobile/assets/front-inverted.png`
- Delete: `Hangboards/crimptonite-helium-mobile/assets/reverse.png`
- Delete: `Hangboards/crimptonite-helium-mobile/assets/reverse-inverted.png`
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py:392-760`

- [ ] **Step 1: Add RED Helium test.** Assert one model media record, v1 descriptor hash, six contacts, mappings `edge-14` from both 14 lips and `edge-22` from both 22 lips, no `contactGeometry`, no raster assets, pairedLeadCord exterior leads only, and no mounting hardware.

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k helium -q`

Expected: FAIL because Helium has raster presentations.

- [ ] **Step 3: Astra author and replace board media.** Manually author/compile one v1 USDZ. Replace four raster presentation records with one original `primary` model record and a single canonical position. Remove raster `contactGeometry`, derived/original raster fields, all PNGs, and hardware. Keep real front/reverse apertures and paired exterior leads without inferred internal connection.

- [ ] **Step 4: Run GREEN and Astra review.**

Run: `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k helium -q`

Expected: PASS after Astra front, reverse, and oblique review.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Hangboards/crimptonite-helium-mobile`

Run: `rtk git add Tools/HangboardPackages/tests/test_approved_board_packages.py`

Run: `rtk git commit -m "feat: migrate helium to 3d"`

Run: `rtk git push`

### Task 9: Astra migrate Light Rail 2.0

**Files:**
- Modify: `Hangboards/metolius-light-rail-2/board.json`
- Create: `Hangboards/metolius-light-rail-2/assets/primary.usdz`
- Create: `Hangboards/metolius-light-rail-2/assets/primary.model.json`
- Delete: `Hangboards/metolius-light-rail-2/assets/primary.png`
- Delete: `Hangboards/metolius-light-rail-2/assets/15mm-surface.png`
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py:687-760`

- [ ] **Step 1: Add RED Light Rail test.** Assert one v1 model-only presentation, exact four contacts `jug-40-20mm-side,edge-20,jug-40-15mm-side,edge-15`, no raster/contactGeometry/hardware, and paired exterior leads with no undocumented underside bore.

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k light_rail -q`

Expected: FAIL because Light Rail is raster-only.

- [ ] **Step 3: Astra author and replace board media.** Directly author one reversible rail model, compile v1 descriptor, replace the two raster records with one primary model record and positions exposing all four canonical IDs, delete PNGs/contactGeometry/derived raster state, preserve confirmed upper exterior entry regions only, and omit hardware.

- [ ] **Step 4: Run GREEN and Astra review.**

Run: `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k light_rail -q`

Expected: PASS.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Hangboards/metolius-light-rail-2`

Run: `rtk git add Tools/HangboardPackages/tests/test_approved_board_packages.py`

Run: `rtk git commit -m "feat: migrate light rail to 3d"`

Run: `rtk git push`

### Task 10: Astra migrate Rock Rings 3D

**Files:**
- Modify: `Hangboards/metolius-rock-rings-3d/board.json`
- Create: `Hangboards/metolius-rock-rings-3d/assets/primary.usdz`
- Create: `Hangboards/metolius-rock-rings-3d/assets/primary.model.json`
- Delete: `Hangboards/metolius-rock-rings-3d/assets/primary.png`
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py:760-878`

- [ ] **Step 1: Add RED Rock Rings test.** Assert descriptor v2, exactly two unreflected identical instances, slots `jug,pocket-40,pocket-32,pocket-25`, exact left/right maps, unique ownership, independent pairedLeadCord anchors, retained roof exits/lateral windows, no central through-bore, no raster/contactGeometry/hardware.

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k rock_rings -q`

Expected: FAIL because Rock Rings has raster media.

- [ ] **Step 3: Astra author and replace board media.** Manually make one unit, compile descriptor v2, replace raster pair presentation with one primary model plus two instances and canonical positions, delete PNG/contactGeometry, create independent per-instance paired exterior leads, and remove all hardware.

- [ ] **Step 4: Run GREEN and Astra review.**

Run: `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk proxy scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k rock_rings -q`

Expected: PASS.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Hangboards/metolius-rock-rings-3d`

Run: `rtk git add Tools/HangboardPackages/tests/test_approved_board_packages.py`

Run: `rtk git commit -m "feat: migrate rock rings to reusable 3d"`

Run: `rtk git push`

### Task 11: Astra migrate Penta Evo

**Files:**
- Modify: `Hangboards/yy-penta-evo/board.json`
- Create: `Hangboards/yy-penta-evo/assets/primary.usdz`
- Create: `Hangboards/yy-penta-evo/assets/primary.model.json`
- Delete: `Hangboards/yy-penta-evo/assets/primary.png`
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py:760-878`

- [ ] **Step 1: Add RED Penta test.** Assert `equipmentObjects` is exactly `left-penta,right-penta`, all seven `*-left` contacts have `equipmentObjectID: left-penta`, all seven `*-right` contacts have `equipmentObjectID: right-penta`, and instances use those exact IDs. Assert descriptor v2, exactly two unreflected instances, exact seven slot maps `edge-25,edge-20,edge-15,edge-10,mono,duo,tray` to canonical left/right IDs, two independent exterior loops around upper band through the visible central ring, absent retired small passage holes, no raster/contactGeometry/hardware.

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k penta -q`

Expected: FAIL because Penta has raster media.

- [ ] **Step 3: Astra author and replace board media.** Replace sole `primary` equipment object with `left-penta` and `right-penta`, reassign each canonical left/right contact before adding instances, then manually author one Penta unit, compile v2 descriptor, replace raster media with primary model/two instances/positions, delete PNG/contactGeometry, preserve visible exterior strands and central ring, invent no channel or knot, and remove hardware.

- [ ] **Step 4: Run GREEN and Astra review.**

Run: `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk proxy scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k penta -q`

Expected: PASS.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Hangboards/yy-penta-evo`

Run: `rtk git add Tools/HangboardPackages/tests/test_approved_board_packages.py`

Run: `rtk git commit -m "feat: migrate penta to reusable 3d"`

Run: `rtk git push`

### Task 12: Astra migrate Poker

**Files:**
- Modify: `Hangboards/owl-climb-poker/board.json`
- Create: `Hangboards/owl-climb-poker/assets/primary.usdz`
- Create: `Hangboards/owl-climb-poker/assets/primary.model.json`
- Delete: `Hangboards/owl-climb-poker/assets/face-a.png`
- Delete: `Hangboards/owl-climb-poker/assets/face-b.png`
- Delete: `Hangboards/owl-climb-poker/assets/face-c.png`
- Delete: `Hangboards/owl-climb-poker/assets/face-d.png`
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py:392-455`

- [ ] **Step 1: Add RED Poker test.** Assert one v1 model record, exact 34 canonical contact IDs including both Face D deep rounded recesses, source mappings remain face-prefixed, no suspension, no raster/contactGeometry/hardware.

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k poker -q`

Expected: FAIL because Poker still has four raster presentations.

- [ ] **Step 3: Astra author and replace board media.** Manually author source-backed faces and recesses, restore only `face-d-left-deep-rounded-recess` and `face-d-right-deep-rounded-recess`, compile v1 descriptor, replace four raster presentations with one primary model/positions, delete face PNGs/contactGeometry, add no suspension, and remove hardware.

- [ ] **Step 4: Run GREEN and Astra review.**

Run: `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py -k poker -q`

Expected: PASS.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Hangboards/owl-climb-poker`

Run: `rtk git add Tools/HangboardPackages/tests/test_approved_board_packages.py`

Run: `rtk git commit -m "feat: migrate poker to 3d"`

Run: `rtk git push`

### Task 13: Astra reauthor Pivot

**Files:**
- Modify: `Hangboards/trango-rock-prodigy-pivot/board.json`
- Create: `Hangboards/trango-rock-prodigy-pivot/assets/primary.usdz`
- Create: `Hangboards/trango-rock-prodigy-pivot/assets/primary.model.json`
- Delete: `Hangboards/trango-rock-prodigy-pivot/assets/primary.png`
- Delete: `Hangboards/trango-rock-prodigy-pivot/assets/orientation-2.png`
- Delete: `Hangboards/trango-rock-prodigy-pivot/assets/orientation-3.png`
- Delete: `Hangboards/trango-rock-prodigy-pivot/assets/orientation-4.png`
- Modify: `Tools/HangboardPackages/tests/test_approved_board_packages.py:131-160,1116-1200`
- Modify: `Tools/HangboardPackages/tests/test_model_orientation_inventory.py:479-560`

- [ ] **Step 1: Add RED Pivot/aperture test.**

```python
def test_batch04_model_geometry_retains_only_documented_attachment_openings() -> None:
    source_boards = json.loads(
        (REPO_ROOT / "docs/source-audits/2026-09-20-batch-04-3d-source-register.json").read_text()
    )["boards"]
    expected = {
        "crimptonite-helium-mobile": {"boardID": "crimptonite.helium-mobile", "apertures": {"front-lead-mouth", "reverse-lead-mouth"}},
        "metolius-light-rail-2": {"boardID": "metolius.light-rail-2", "apertures": {"left-upper-entry", "right-upper-entry"}},
        "metolius-rock-rings-3d": {"boardID": "metolius.rock-rings-3d", "apertures": {"roof-exit", "lateral-window"}},
        "owl-climb-poker": {"boardID": "owl-climb.poker", "apertures": set()},
        "yy-penta-evo": {"boardID": "yy.penta-evo", "apertures": {"central-ring", "upper-band-exterior"}},
        "trango-rock-prodigy-pivot": {"boardID": "trango.rock-prodigy-pivot", "apertures": {"two-finger-opening", "three-finger-end-window"}},
    }
    for slug, requirement in expected.items():
        descriptor = json.loads((HANGBOARDS_ROOT / slug / "assets/primary.model.json").read_text())
        node_ids = {node["nodeID"] for node in descriptor["nodes"]}
        assert requirement["apertures"] <= node_ids
        assert not any(token in node_id for node_id in node_ids for token in ("fastener", "screw", "mount", "cleat", "bracket"))
        assert source_boards[requirement["boardID"]]["approvedApertures"] == sorted(requirement["apertures"])
    board = json.loads((PIVOT_ROOT / "board.json").read_text())
    assert [position["id"] for position in board["positions"]] == ["p1", "p2", "p3", "p5"]
```

Also assert `equipmentObjects` is exactly `left-half,right-half`, each of the nine left contacts belongs to `left-half`, each of the nine right contacts belongs to `right-half`, and instances use those exact IDs. Assert 18 contacts, one v2 half/two instances, reflected right, complete translations and rotations in every map, no selectable p4, no top-level orientation/suspension, no raster/contactGeometry/hardware, and exact 14-patch mapping. Astra additionally verifies actual geometry absence and aperture retention structurally and side-by-side, so node names alone never pass acceptance.

- [ ] **Step 2: Run RED.**

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py Tools/HangboardPackages/tests/test_model_orientation_inventory.py -k pivot -q`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py::test_batch04_model_geometry_retains_only_documented_attachment_openings -q`

Expected: FAIL because Pivot is raster media with 72 presentation records.

- [ ] **Step 3: Astra manually reauthor and replace board media.** Reject delivered GLB as production geometry. Replace sole `primary` equipment object with `left-half` and `right-half`, then reassign all nine left/right physical contacts before adding instances. Build continuous molded perimeter/ridges, inward pockets, supported-crimp ridges, broad integrated concave wing, true two-finger opening, three-finger end window, and correct normals from approved Trango evidence. Mark envelope/rear `authored-display-estimate`. Remove six fastener holes and all hardware. Replace four raster records with one v2 model, two instances, positions `p1,p2,p3,p5`, reflected right base transform, and full per-instance translations/rotations. Preserve p4 only in audit transition evidence.

- [ ] **Step 4: Run GREEN and Astra review.**

Run: `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py Tools/HangboardPackages/tests/test_model_orientation_inventory.py -k pivot -q`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests/test_approved_board_packages.py::test_batch04_model_geometry_retains_only_documented_attachment_openings -q`

Expected: PASS.

- [ ] **Step 5: Fresh review, stage, commit, and push.**

Run: `rtk git add Hangboards/trango-rock-prodigy-pivot`

Run: `rtk git add Tools/HangboardPackages/tests/test_approved_board_packages.py`

Run: `rtk git add Tools/HangboardPackages/tests/test_model_orientation_inventory.py`

Run: `rtk git commit -m "feat: reauthor pivot reusable 3d model"`

Run: `rtk git push`

### Task 14: Acceptance-only integration and current-source validation

**Files:**
- Create: `docs/source-audits/2026-09-20-batch-04-3d-acceptance.md`

**Consumes:** Green tests and reviewed packages from Tasks 1 through 13.

- [ ] **Step 1: Run all already-green Python lanes.**

Run: `rtk proxy ruby Tools/HangboardModels/check_production_cord_clearance.rb`

Run: `rtk proxy scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk proxy scripts/hangboard-packages.sh audit-cords --root Hangboards --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json`

Run: `rtk proxy .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardPackages/tests -q`

Run: `rtk proxy env PYTHONPATH=Tools/HangboardModels .context/hangboard-packages-venv/bin/python -m pytest Tools/HangboardModels/test_contact_model_descriptor.py Tools/HangboardModels/test_contact_model_package.py Tools/HangboardModels/test_import_contact_model_source.py -q`

Run: `rtk proxy python3 -m compileall -q Tools/HangboardPackages/src`

Expected: PASS.

- [ ] **Step 2: Run native tests.**

Run: `rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' test`

Expected: PASS.

- [ ] **Step 3: Run isolated Simulator and Astra acceptance.** Use `validate-hang-ten-ios`. Create only `Hang Ten Paseo learned-giraffe Review`, register its exact UUID before boot, use `.context/DerivedData`, and remove the exact device/artifacts by trap. Inspect every target front, oblique, reverse, active contact, every canonical pose, reusable highlight isolation, cord clearance/non-picking, workout-driven selection, orbit/reset, and Pivot p1/p2/p3/p5. Astra records side-by-side evidence review.

- [ ] **Step 4: Record actual acceptance evidence.** Include package contact counts `6,4,8,34,14,18`, descriptor and USDZ hashes, audit output, source-review result, command results, owned resource names, and confirmed cleanup. Do not add a new feature test in this task.

- [ ] **Step 5: Fresh whole-branch review, stage, commit, and push.**

Run: `rtk proxy git diff --check`

Run: `rtk git add docs/source-audits/2026-09-20-batch-04-3d-acceptance.md`

Run: `rtk git commit -m "test: verify batch 04 3d migration"`

Run: `rtk git push`

## Self-review

- [x] All approved spec areas map to Tasks 1 through 14, including v1 freeze, slot contract, transforms, tooling, Swift parity, isolation, exact audit evidence, six package migrations, Astra review, audit/clearance/build/Simulator acceptance, and cleanup.
- [x] No placeholder, pseudocode marker, literal three-dot ellipsis, chained command, or unsupported direct RTK command remains.
- [x] Every proposed symbol has an owner, visibility, signature or stored type, and a consuming task.
- [x] Only instance base and position translations have lexical nine-decimal validation. Descriptor numeric vectors retain their existing rounding policy.
- [x] Each Review Focus test is defined by exact XCTestCase or Python test syntax in its owning task.
- [x] Final acceptance runs existing green tests only. Each package task owns its RED cross-package assertions before authoring.

## Execution handoff

Execute with `superpowers:subagent-driven-development`: one fresh implementation agent, one fresh reviewer, one commit, and one push per task.
