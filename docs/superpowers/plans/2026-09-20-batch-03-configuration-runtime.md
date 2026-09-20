# Batch 03 Configuration Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Each task has an implementation checkpoint and a separate review checkpoint. Keep the checkbox state in this document current while executing it.

**Goal:** Add the schema-v3 configuration runtime needed by Batch 03: exact per-position depths, multiple original model presentations, position-aware contact requirements, deterministic joint target resolution, immutable activity snapshots, and multi-presentation delivery/audit coverage.

**Architecture:** `BoardPosition` remains the sole configuration authority. Package readers validate authored overrides only after contacts and positions have been materialized; `ContactResolver` then evaluates all requirements for a step against one position at a time and returns an immutable `ResolvedBoardTarget`. Workout setup freezes those targets outside this plan, while the recorder accepts and revalidates the frozen dictionary and writes a nested configuration snapshot plus the hash of the selected presentation. Existing presentation-aware ODR staging and model caching stay in place and gain regression coverage. The cord audit remains one evidence decision per package, but proves that the decision agrees with every model presentation in that package.

**Tech Stack:** Swift 6, Foundation, XCTest, Python 3.12, `pytest`, JSON schema-v3 board packages, Apple On-Demand Resources

**Spec:** `docs/superpowers/specs/2026-09-20-hangboards-batch-03-3d-migration-design.md`

---

## Scope and ownership

This plan owns only the shared/runtime layer. It does **not** author the six Batch 03 packages, training routines, editor/setup UI, workout-session sequence state, 3D geometry, or source-audit records.

| Producer | Output | Consumer |
| --- | --- | --- |
| Task 1 | Python `BoardPosition.effective_depths`, schema validation, and multiple-presentation loading | package authoring plan, staging/audit tools |
| Task 2 | Swift `BoardPosition.effectiveDepths`, multi-presentation store/writer validation | package authoring plan, workout experience plan |
| Task 3 | `ContactRequirement.positionID` persistence and safe copy/normalization rules | workout experience plan |
| Task 4 | immutable `ResolvedBoardTarget` and joint position resolver | workout experience plan and Task 5 |
| Task 5 | strict `ResolvedBoardConfigurationSnapshot` and frozen-target recorder entry point | workout experience plan |
| Task 6 | multi-presentation staging/cache/cord-audit guarantees and snapshot-root policy | package authoring plan |

The package plan may start package JSON only after Tasks 1 and 2 land. It owns the final six packages, 28 promoted evidence artifacts, the source-audit records, and six cord-audit records. The experience plan may build its frozen sequence only after Tasks 3–5 land. It owns setup choice, repair UI, `WorkoutView`/`AppStore` state, and passing the complete frozen-target dictionary to the recorder.

Runtime is the sole owner of `ContactRequirement`'s initializer/codec, every preserve/strip transformation in `CustomRoutineDraft.swift`, contextual validation in `CustomRoutineStore.swift`, and the corresponding `PlanStorageTests`, `CustomRoutineDraftTests`, and `CustomRoutineStoreTests`. The experience plan consumes those behaviors and must not duplicate or edit them. Its package-backed final integration may add resolver/recorder coverage only in the explicitly handed-off test classes named in Task 7.

## Global constraints

- Keep `schemaVersion: 3`; these are additive fields understood by the coordinated new readers and writers.
- An omitted `effectiveDepths` is valid legacy data. An explicit `null` or `{}` is invalid.
- Every authored position override is an exact finite positive range (`minimum == maximum`), references a canonical contact in that position, never exceeds that contact's exact base depth, and is authored for every position that contains the overridden contact.
- A model-only package may have multiple original model presentations, has exactly one default presentation, has no raster fallback, uses unique asset and descriptor paths, and retains the full canonical contact inventory in every descriptor. Pose and orientation metadata are local to their presentation's positions.
- Never select a first/default position to break configuration ambiguity. All simultaneous requirements must resolve within one position.
- A contact with no authored depth remains resolvable when no requirement constrains depth. Its ID is selected and its materialized depth map may be empty.
- `positionID` is legal only for a custom, board-specific, single-selection, exact-contact requirement. Converting a requirement to generic or another board removes both `contactID` and `positionID` while preserving the other constraints.
- Legacy requirements and activity snapshots remain decodable when new fields are absent. Stale explicit IDs are never silently dropped, aliased, or repaired.
- Do not add dependencies, change deployment targets, invent physical facts, change renderer geometry, or change training-plan content.
- Use the existing ODR lease and `BoardModelKey(boardID:presentationID:modelSHA256:)`; change production cache/staging code only if a new failing regression proves it is not already presentation-aware.

## File map

| File | Planned change |
| --- | --- |
| `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` | Decode and validate position effective depths; accept and validate multiple model presentations |
| `Tools/HangboardPackages/tests/test_board_catalog.py` | Python schema, inheritance, cross-position completeness, and presentation-local regression tests |
| `HangTen/Models/TrainingModels.swift` | Add `BoardPosition.effectiveDepths` and materialization helpers |
| `HangTen/Models/BoardPackageStore.swift` | Decode/validate overrides and validate each model against only its own positions |
| `HangTen/Models/BoardPackageWriter.swift` | Preserve/canonicalize the additive position field and apply equivalent validation |
| `HangTenTests/BoardPackageStoreTests.swift` | Swift schema and multi-presentation loading regressions |
| `HangTenTests/BoardPackageWriterTests.swift` | Writer round-trip and rejection regressions |
| `HangTenTests/Fixtures/BoardPackageValidationFixtures.json` | Shared malformed/valid package cases; retire the old blanket second-model rejection |
| `HangTen/Models/PlanStorage.swift` | Add `ContactRequirement.positionID`, strict decoding, and validation boundaries |
| `HangTen/Models/CustomRoutineDraft.swift` | Preserve or strip position identity during hand/copy/board transformations |
| `HangTen/Models/CustomRoutineStore.swift` | Strip identity at generic/cross-board import boundaries and validate custom provenance/board bindings without repair |
| `HangTenTests/PlanStorageTests.swift` | Codable, legacy, and provenance tests |
| `HangTenTests/CustomRoutineDraftTests.swift` | Copy/materialization transformation tests |
| `HangTenTests/CustomRoutineStoreTests.swift` | Import/normalization transformation tests |
| `HangTen/Models/WorkoutActivityRecording.swift` | Add immutable target, joint resolution, strict snapshot configuration, selected hash, and frozen-target recorder input |
| `HangTenTests/BoardTargetSubstitutionTests.swift` | Joint resolution and ambiguity tests |
| `HangTenTests/WorkoutActivityRecordingTests.swift` | Snapshot/legacy/frozen-target/hash tests |
| `scripts/stage-board-packages.py` | No expected production change; retain all-presentation staging |
| `Tools/HangboardPackages/tests/test_board_package_staging.py` | Three-presentation ODR staging regression |
| `HangTen/Views/BoardModelView.swift` | No expected production change; retain presentation-aware cache keys |
| `HangTenTests/BoardModelTests.swift` and `HangTenTests/BoardPackageStoreTests.swift` | Selected-resource and cache-key regressions |
| `Tools/HangboardPackages/src/hangboard_packages/cord_audit.py` | Compare one package record with every model presentation and permit two canonical evidence roots |
| `Tools/HangboardPackages/tests/test_cord_audit.py` | Multi-presentation topology, evidence-root, tracking, and duplicate-path regressions |
| `Tools/HangboardPackages/README.md` | Document package-level/multi-presentation audit semantics and canonical evidence roots |

## Review focus

Reviewers must explicitly inspect these five failure-prone cases rather than relying on broad suite success:

1. `effectiveDepths: null`, `{}`, non-finite JSON, zero/negative ranges, and category values all fail in both readers.
2. If a shared contact is overridden in one position but omitted in another position containing it, the whole package fails.
3. Pose/orientation keys and descriptor inventories never leak between two model presentations.
4. Requirements that are individually satisfiable only in different positions fail joint resolution.
5. A selected depthless contact records its contact ID, an empty configuration depth map, the selected presentation ID, and that presentation's actual SHA-256.

---

## Task 1: Add Python configuration schema and model-presentation parity

**Files:**

- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py` (`BoardPosition`, `_validate_presentation_compatibility`, `_load_positions`, `_load_board`, `_validate_finished_shape`)
- Modify: `Tools/HangboardPackages/tests/test_board_catalog.py` (position/model validation cases)
- Modify: `Tools/HangboardPackages/tests/test_model_first_packages.py:36-180` (shared model fixture writer and multi-presentation cases)
- Modify: `Tools/HangboardPackages/tests/conftest.py` (only the reusable model-package fixture builder)

**Interfaces produced:**

```python
@dataclass(frozen=True)
class BoardPosition:
    id: str
    presentation_id: str
    contact_ids: tuple[str, ...] = ()
    effective_depths: Mapping[str, HoldDepth] | None = None
    contact_ids_authored: bool = False
```

Exact added function signatures are
`BoardPosition.effective_depth_for(self, contact: PhysicalContact) -> HoldDepth | None`,
`BoardRevision.materialized_effective_depths(self, contact_ids: tuple[str, ...], position: BoardPosition) -> Mapping[str, HoldDepth]`, and
`_validate_position_effective_depths(positions: tuple[BoardPosition, ...], contacts: tuple[PhysicalContact, ...]) -> None`.

`effective_depth_for` returns the position override when present and otherwise the contact's base `depth`. `materialized_effective_depths` includes only selected contacts whose effective depth is known, preserving canonical contact order.

- [ ] **Step 1: Bootstrap the shared repository-local Python environment.** Follow `Tools/HangboardPackages/TESTING.md` exactly, while avoiding replacement of an existing environment:

```bash
if [ ! -x .context/hangboard-packages-venv/bin/python ]; then
  rtk python3 -m venv .context/hangboard-packages-venv
fi
rtk .context/hangboard-packages-venv/bin/python -m pip install \
  -e 'Tools/HangboardPackages[dev]'
```

Expected: `.context/hangboard-packages-venv/bin/python` exists and the editable package plus development dependencies install successfully. This environment is shared repository-local tooling; do not register it as this task's owned external resource and do not delete it as an unknown/shared resource.

- [ ] **Step 2: Write failing decode and structural-validation tests.** Add this helper to `test_board_catalog.py`; `add_second_contact` distinguishes an unknown key from a canonical contact omitted by the position:

```python
def effective_depth_document(
    effective_depths: object,
    *,
    contact_ids: list[str] | None = None,
    add_second_contact: bool = False,
) -> dict[str, object]:
    document = board_document()
    document["contacts"][0]["depth"] = {
        "range": {"minimum": 20, "maximum": 20}
    }
    if add_second_contact:
        document["contacts"].append({
            "id": "hold-right",
            "equipmentObjectID": "primary",
            "name": "Right hold",
            "kind": "edge",
            "depth": {"range": {"minimum": 20, "maximum": 20}},
            "gripTypes": [],
        })
    document["positions"] = [{
        "id": "front",
        "presentationID": "primary",
        "contactIDs": contact_ids or ["hold-left"],
        "effectiveDepths": effective_depths,
    }]
    return document


@pytest.mark.parametrize(
    ("case", "effective_depths", "add_second_contact", "message"),
    [
        ("null", None, False, "board.json.positions[0].effectiveDepths must be a non-empty object"),
        ("empty", {}, False, "board.json.positions[0].effectiveDepths must be a non-empty object"),
        ("malformed-key", {"not valid": {"range": {"minimum": 10, "maximum": 10}}}, False, "effectiveDepths key must be identifier-shaped"),
        ("unknown", {"missing": {"range": {"minimum": 10, "maximum": 10}}}, False, "effectiveDepths references unknown contact missing"),
        ("outside-position", {"hold-right": {"range": {"minimum": 10, "maximum": 10}}}, True, "effectiveDepths contact hold-right is not in position front"),
        ("category", {"hold-left": {"category": "small"}}, False, "must be an exact finite positive range"),
        ("zero", {"hold-left": {"range": {"minimum": 0, "maximum": 0}}}, False, "must be an exact finite positive range"),
        ("negative", {"hold-left": {"range": {"minimum": -1, "maximum": -1}}}, False, "minimum must be non-negative and not exceed maximum"),
        ("interval", {"hold-left": {"range": {"minimum": 10, "maximum": 11}}}, False, "must be an exact finite positive range"),
        ("nan", {"hold-left": {"range": {"minimum": float("nan"), "maximum": 10}}}, False, "minimum must be finite"),
        ("infinity", {"hold-left": {"range": {"minimum": 10, "maximum": float("inf")}}}, False, "maximum must be finite"),
    ],
)
def test_position_effective_depths_reject_malformed_values(
    case: str,
    effective_depths: object,
    add_second_contact: bool,
    message: str,
) -> None:
    module = load_board_catalog_module()
    document = effective_depth_document(
        effective_depths, add_second_contact=add_second_contact
    )
    with pytest.raises(ValueError, match=re.escape(message)):
        module._load_board(document)


def test_position_effective_depths_omission_remains_legacy_compatible() -> None:
    module = load_board_catalog_module()
    document = effective_depth_document({"hold-left": {"range": {"minimum": 10, "maximum": 10}}})
    del document["positions"][0]["effectiveDepths"]
    assert module._load_board(document).positions[0].effective_depths is None
```

- [ ] **Step 3: Run the focused Python tests and confirm RED.**

Run:

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_board_catalog.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py \
  -q -k 'effective_depth or multiple_model or presentation_local'
```

Expected: failures show `BoardPosition` has no `effective_depths`, empty/null overrides are accepted, and a second model presentation is still rejected.

- [ ] **Step 4: Decode the additive field without weakening closed objects.** In `_load_positions`, allow exactly `id`, `presentationID`, `contactIDs`, and `effectiveDepths`; distinguish omission from explicit null; decode each value through the existing `HoldDepth` loader; and construct the new immutable mapping. Do not validate contact membership until `_load_board` has materialized implicit contacts and canonical contact objects.

```python
if "effectiveDepths" not in payload:
    effective_depths = None
else:
    if payload["effectiveDepths"] is None:
        raise ValueError(f"{source}.effectiveDepths must be a non-empty object")
    effective_depth_payload = _mapping(
        payload["effectiveDepths"], f"{source}.effectiveDepths"
    )
    if not effective_depth_payload:
        raise ValueError(f"{source}.effectiveDepths must be a non-empty object")
    effective_depths = MappingProxyType(
        {
            _identifier(key, f"{source}.effectiveDepths key"): _load_hold_depth(
                value, f"{source}.effectiveDepths.{key}"
            )
            for key, value in effective_depth_payload.items()
        }
    )
```

- [ ] **Step 5: Add failing semantic tests.** Cover exact inheritance, a smaller/equal override, an override greater than the exact base depth, a categorical or absent base depth, and the shared-contact completeness rule. Assert a depthless selected contact is omitted from `materialized_effective_depths` rather than blocking the position.

Use `effective_depth_document(effective_depths:add_second_contact:)` from Step 2 and this exact matrix:

| Base `hold-left.depth` | `front.effectiveDepths` | Peer position | Expected result |
| --- | --- | --- | --- |
| exact 20 | omitted | none | effective/materialized `hold-left` is exact 20 |
| exact 20 | exact 20 | none | valid; materialized exact 20 |
| exact 20 | exact 18 | none | valid; materialized exact 18 |
| exact 20 | exact 21 | none | `effective depth for hold-left cannot exceed its exact base depth` |
| category `large` | exact 18 | none | `override for hold-left requires an exact finite positive base range` |
| omitted | exact 18 | none | `override for hold-left requires an exact finite positive base range` |
| exact 20 | exact 18 | second position contains `hold-left` but omits override | `every position containing hold-left must author its effective depth` |
| omitted | omitted | none | valid; `effective_depth_for(...) is None` and materialized map is `{}` |

```python
def test_shared_overridden_contact_requires_override_in_every_containing_position(
) -> None:
    module = load_board_catalog_module()
    document = board_document()
    document["contacts"][0]["depth"] = {
        "range": {"minimum": 20, "maximum": 20}
    }
    document["positions"] = [
        {
            "id": "deep",
            "presentationID": "primary",
            "contactIDs": ["hold-left"],
            "effectiveDepths": {"hold-left": {"range": {"minimum": 18, "maximum": 18}}},
        },
        {"id": "shallow", "presentationID": "primary", "contactIDs": ["hold-left"]},
    ]
    with pytest.raises(ValueError, match="every position containing hold-left"):
        module._load_board(document)


def test_depthless_contact_materializes_an_empty_map() -> None:
    module = load_board_catalog_module()
    document = effective_depth_document(
        {"hold-left": {"range": {"minimum": 10, "maximum": 10}}}
    )
    del document["contacts"][0]["depth"]
    del document["positions"][0]["effectiveDepths"]
    board = module._load_board(document)
    contact = board.contacts[0]
    position = board.positions[0]
    assert position.effective_depth_for(contact) is None
    assert dict(board.materialized_effective_depths((contact.id,), position)) == {}
```

- [ ] **Step 6: Implement post-materialization semantic validation.** Call `_validate_position_effective_depths` in `_validate_finished_shape` after canonical contacts and implicit position contact IDs exist. Require identifier-shaped keys, membership in both canonical contacts and that position, `.range` only, finite positive equal endpoints, an exact finite positive base range, `override <= base`, and all-position coverage for any overridden contact. Add `effective_depth_for` and `materialized_effective_depths` exactly as declared above.

```python
def _validate_position_effective_depths(
    positions: tuple[BoardPosition, ...], contacts: tuple[PhysicalContact, ...]
) -> None:
    contacts_by_id = {contact.id: contact for contact in contacts}
    overridden_contact_ids: set[str] = set()
    for position in positions:
        for contact_id, override in (position.effective_depths or {}).items():
            contact = contacts_by_id.get(contact_id)
            if contact is None:
                raise ValueError(f"effectiveDepths references unknown contact {contact_id}")
            if contact_id not in position.contact_ids:
                raise ValueError(
                    f"effectiveDepths contact {contact_id} is not in position {position.id}"
                )
            value = override.range
            if value is None or value.minimum <= 0 or value.minimum != value.maximum:
                raise ValueError(
                    f"position {position.id} effective depth for {contact_id} "
                    "must be an exact finite positive range"
                )
            base = contact.depth.range if contact.depth is not None else None
            if base is None or base.minimum <= 0 or base.minimum != base.maximum:
                raise ValueError(
                    f"override for {contact_id} requires an exact finite positive base range"
                )
            if value.maximum > base.maximum:
                raise ValueError(
                    f"effective depth for {contact_id} cannot exceed its exact base depth"
                )
            overridden_contact_ids.add(contact_id)
    for contact_id in overridden_contact_ids:
        if any(
            contact_id in position.contact_ids
            and contact_id not in (position.effective_depths or {})
            for position in positions
        ):
            raise ValueError(
                f"every position containing {contact_id} must author its effective depth"
            )


def effective_depth_for(self, contact: PhysicalContact) -> HoldDepth | None:
    return (self.effective_depths or {}).get(contact.id, contact.depth)


def materialized_effective_depths(
    self, contact_ids: tuple[str, ...], position: BoardPosition
) -> Mapping[str, HoldDepth]:
    selected = set(contact_ids)
    return MappingProxyType({
        contact.id: depth
        for contact in self.contacts
        if contact.id in selected
        if (depth := position.effective_depth_for(contact)) is not None
    })
```

- [ ] **Step 7: Replace the blanket one-model rejection with per-presentation validation tests.** Construct a model-only package with three presentations, unique `assetPath`/`descriptorPath`, one default, one local position per presentation, and a full-inventory descriptor for each. Assert it loads. Then independently prove rejection of duplicate asset paths, duplicate descriptor paths, mixed raster/model media, a descriptor missing a canonical contact, an empty local position union, and an orientation/pose key belonging to another presentation.

Add helpers with exact signatures `write_three_model_parser_package(root: Path) -> Path` and `mutate_three_model_parser_package(package_root: Path, case: str) -> None` to `test_model_first_packages.py`. The writer clones the shared `model` fixture into presentation IDs `deep`, `medium`, `shallow`; writes `assets/{id}.usdz` and `assets/{id}.model.json`; sets only `deep.isDefault`; gives each presentation one same-ID position; and keeps the descriptor contact dictionary identical in all three files. The mutation helper accepts only these cases:

| `case` | Exact mutation | Expected result/diagnostic |
| --- | --- | --- |
| `valid` | none | loads IDs `deep`, `medium`, `shallow` |
| `duplicate-asset` | shallow `assetPath = assets/deep.usdz` | `model assetPath values must be unique` |
| `duplicate-descriptor` | shallow `descriptorPath = assets/deep.model.json` | `model descriptorPath values must be unique` |
| `mixed-media` | replace shallow media with a valid raster media object | `packages may not mix model and raster presentations` |
| `incomplete-descriptor` | remove `hold-left` from shallow descriptor contacts | `model descriptor contacts must equal physical contacts` |
| `no-local-position` | remove the shallow position | `model presentation shallow must have at least one local position` |
| `foreign-orientation` | add `deep` to shallow orientation rotations | `orientation.rotations must exactly match model position IDs` |
| `foreign-pose` | add `deep` to shallow suspension canonical poses | `suspension canonical poses must exactly match position IDs` |

```python
def test_three_model_presentations_validate_their_own_position_namespaces(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    write_three_model_parser_package(tmp_path / "fixture-model")
    inventory = module.discover_board_packages(
        tmp_path, require_complete_inventory=True
    )
    board = inventory.packages[0].board
    assert [presentation.id for presentation in board.presentations] == [
        "deep",
        "medium",
        "shallow",
    ]
    assert [position.presentation_id for position in board.positions] == [
        "deep",
        "medium",
        "shallow",
    ]
```

- [ ] **Step 8: Implement multiple-presentation loading.** Remove only the `len(model_media) > 1` guard from `_validate_presentation_compatibility`. Keep the exactly-one-default and no-mixed-media checks. Reject duplicate model `asset_path` and `descriptor_path` values. In `_validate_finished_shape`, derive `local_position_ids` and `local_positions` by `presentation_id` for each model and pass only those sets to descriptor inventory, orientation, suspension, and pose validation.

```python
model_presentations = tuple(
    presentation
    for presentation in presentations
    if isinstance(presentation.media, PresentationMediaModel)
)
asset_paths = [presentation.media.asset_path for presentation in model_presentations]
descriptor_paths = [
    presentation.media.descriptor_path for presentation in model_presentations
]
if len(asset_paths) != len(set(asset_paths)):
    raise ValueError("model assetPath values must be unique")
if len(descriptor_paths) != len(set(descriptor_paths)):
    raise ValueError("model descriptorPath values must be unique")

for presentation in model_presentations:
    local_positions = tuple(
        position
        for position in positions
        if position.presentation_id == presentation.id
    )
    if not local_positions:
        raise ValueError(
            f"model presentation {presentation.id} must have at least one local position"
        )
    local_position_ids = {position.id for position in local_positions}
    frames = _load_model_descriptor(
        root / presentation.media.descriptor_path,
        root / presentation.media.asset_path,
        physical_contact_ids,
        suspension=presentation.media.suspension,
        position_ids=local_position_ids,
    )
    _validate_model_orientation(
        presentation.media.orientation,
        positions,
        set(frames),
        canonical_contact_ids,
        local_position_ids,
        f"board.json.presentations[{presentation.id}].media.orientation",
    )
```

- [ ] **Step 9: Run the focused tests and confirm GREEN.**

Run:

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_board_catalog.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py -q
```

Expected: all board-catalog tests pass, including every row from Review focus 1–3.

- [ ] **Step 10: Commit and push the Python domain checkpoint.**

```bash
rtk git add \
  Tools/HangboardPackages/src/hangboard_packages/board_catalog.py \
  Tools/HangboardPackages/tests/test_board_catalog.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py \
  Tools/HangboardPackages/tests/conftest.py
rtk git commit -m "feat: validate configurable board positions in package tools"
rtk git push
```

**Review checkpoint:** A reviewer compares Python acceptance/rejection with the approved design matrix, pays special attention to explicit null/non-finite parsing and shared-contact coverage, and records approval before Task 2 begins.

---

## Task 2: Add Swift position depths and multiple-model package loading

**Files:**

- Modify: `HangTen/Models/TrainingModels.swift:1001` (`BoardPresentation`), `:1059` (`BoardPosition`), and `:1115` (`BoardRevision`)
- Modify: `HangTen/Models/BoardPackageStore.swift:754` (media compatibility), `:803` (model loading), `:970` (position construction), `:1296` (model inventory validation), and `:2283`/`:2891` (package documents)
- Modify: `HangTen/Models/BoardPackageWriter.swift:176` (`BoardEditablePositionDocument`), `:685` (validation), and `:1036` (canonical serialization)
- Modify: `HangTenTests/BoardPackageStoreTests.swift` (schema/model loading tests and fixture builders near `makeModelFixtureBundle`)
- Modify: `HangTenTests/BoardPackageWriterTests.swift` (position round-trip tests)
- Modify: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json` (shared position/model cases)

**Interfaces produced:**

```swift
struct BoardPosition: Identifiable, Codable, Hashable {
    let id: String
    let presentationID: String
    let contactIDs: [String]
    let effectiveDepths: [String: HoldDepth]?
    let contactIDsWereExplicitlyAuthored: Bool

    init(
        id: String,
        presentationID: String,
        contactIDs: [String],
        effectiveDepths: [String: HoldDepth]? = nil
    )

    init(
        id: String,
        presentationID: String,
        effectiveDepths: [String: HoldDepth]? = nil
    )

    func effectiveDepth(for contact: PhysicalContact) -> HoldDepth?
}

extension BoardRevision {
    func materializedEffectiveDepths(
        for contactIDs: [String],
        in position: BoardPosition
    ) -> [String: HoldDepth]
}

private static func validatePositionEffectiveDepths(
    _ positions: [BoardPosition],
    contacts: [PhysicalContact],
    boardID: String
) throws

private static func modelPositionIDs(
    for presentationID: String,
    positions: [BoardPosition]
) -> Set<String>

extension String {
    var isBoardPackageIdentifier: Bool { get }
}
```

Move the existing identifier implementation from the private extension at `BoardPackageStore.swift:38` to an internal extension in `TrainingModels.swift`; its accepted grammar does not change. Task 3 consumes it for `positionID` instead of introducing a second regex.

- [ ] **Step 1: Port the malformed and inheritance matrix to XCTest.** Extend the shared validation fixture with keys `position-effective-depths-null`, `-empty`, `-unknown-contact`, `-outside-position`, `-category`, `-nonpositive`, `-nonexact`, `-exceeds-base`, `-missing-peer`, and `-valid-exact`. Keep the raw `null` fixture so `decodeIfPresent` cannot accidentally conflate it with omission.

Add `private func assertPositionDepthFixture(_ name: String, error: BoardPackageStoreError, reason: String) throws` to `BoardPackageStoreTests`. It builds the named shared fixture, compares the exact error case, and requires `reason` as a substring of `malformedJSON.detail` or `invalidPackage.reason`. Use this matrix:

| Fixture suffix | Exact expected category | Required diagnostic/result |
| --- | --- | --- |
| `null` | `.malformedJSON` | `effectiveDepths must be a non-null, non-empty object` |
| `empty` | `.invalidPackage` | `effectiveDepths must be a non-empty object` |
| `unknown-contact` | `.invalidPackage` | `effectiveDepths references unknown contact missing` |
| `outside-position` | `.invalidPackage` | `effectiveDepths contact hold-right is not in position front` |
| `category` | `.invalidPackage` | `must be an exact finite positive range` |
| `nonpositive` | `.invalidPackage` | `must be an exact finite positive range` |
| `nonexact` | `.invalidPackage` | `must be an exact finite positive range` |
| `exceeds-base` | `.invalidPackage` | `cannot exceed its exact base depth` |
| `missing-peer` | `.invalidPackage` | `every position containing hold-left must author its effective depth` |
| `valid-exact` | success | effective depth is exact 10 and canonical round trip preserves it |

```swift
func testPositionEffectiveDepthOverridesAreExactCompleteAndBounded() throws {
    let contact = PhysicalContact(
        id: "edge",
        name: "Edge",
        kind: .edge,
        depth: .range(.init(minimum: 18, maximum: 18))
    )
    let position = BoardPosition(
        id: "shallow",
        presentationID: "shallow",
        contactIDs: ["edge"],
        effectiveDepths: ["edge": .range(.init(minimum: 10, maximum: 10))]
    )
    XCTAssertEqual(
        position.effectiveDepth(for: contact),
        .range(.init(minimum: 10, maximum: 10))
    )
}
```

- [ ] **Step 2: Run the focused Swift tests and confirm RED.**

Run:

```bash
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/BoardPackageWriterTests
```

Expected: compile/test failures identify the missing `effectiveDepths` API and the current second-model rejection.

- [ ] **Step 3: Add the domain field and helpers.** Decode omission and explicit null separately in `BoardPackagePositionDocument`; keep `BoardPosition`'s defaulted initializers source-compatible. `effectiveDepth(for:)` is `effectiveDepths?[contact.id] ?? contact.depth`. `materializedEffectiveDepths` walks `contacts` in canonical order, filters to the requested IDs, and inserts only non-`nil` values.

```swift
private enum CodingKeys: String, CodingKey {
    case id, presentationID, contactIDs, effectiveDepths
}

if container.contains(.effectiveDepths) {
    guard try !container.decodeNil(forKey: .effectiveDepths) else {
        throw DecodingError.dataCorruptedError(
            forKey: .effectiveDepths,
            in: container,
            debugDescription: "effectiveDepths must be a non-null, non-empty object"
        )
    }
    effectiveDepths = try container.decode(
        [String: HoldDepth].self,
        forKey: .effectiveDepths
    )
} else {
    effectiveDepths = nil
}

func effectiveDepth(for contact: PhysicalContact) -> HoldDepth? {
    effectiveDepths?[contact.id] ?? contact.depth
}

func materializedEffectiveDepths(
    for contactIDs: [String], in position: BoardPosition
) -> [String: HoldDepth] {
    let selected = Set(contactIDs)
    return contacts.reduce(into: [:]) { result, contact in
        guard selected.contains(contact.id),
              let depth = position.effectiveDepth(for: contact) else { return }
        result[contact.id] = depth
    }
}
```

- [ ] **Step 4: Add closed-schema and semantic validation.** Allow the fourth position key, reject explicit null/empty dictionaries at the document boundary, then run `validatePositionEffectiveDepths` after position contact IDs have been materialized. Match every Python invariant from Task 1, including finite equal endpoints and cross-position completeness. Use `HoldDepth.range` pattern matching rather than `matches`, because categories and broad ranges are forbidden as authored overrides.

```swift
guard case let .range(range) = override,
      range.minimum.isFinite,
      range.maximum.isFinite,
      range.minimum > 0,
      range.minimum == range.maximum
else {
    throw BoardPackageStoreError.invalidPackage(
        boardID: boardID,
        reason: "position \(position.id) effective depth for \(contactID) must be an exact finite positive range"
    )
}
```

After this guard, look up `contactID` in `contactsByID`, require `position.contactIDs.contains(contactID)`, pattern-match the base as an exact positive `.range`, compare `range.maximum <= base.maximum`, and add the contact to `overriddenContactIDs`. A final loop over `overriddenContactIDs` rejects any containing position whose `effectiveDepths?[contactID] == nil`, using the exact diagnostics from the table above.

- [ ] **Step 5: Preserve the field through editable/canonical documents.** Add `effectiveDepths: [String: HoldDepth]?` to `BoardEditablePositionDocument`, validate with the same shared helper or a single factored validator, and emit `effectiveDepths` only when non-`nil`. Add a decode-write-decode test asserting byte-canonical key order and semantic equality. Do not make model-only packages editable if the writer currently rejects them.

```swift
struct BoardEditablePositionDocument: Codable, Equatable {
    let id: String
    let presentationID: String
    let contactIDs: [String]?
    let effectiveDepths: [String: HoldDepth]?
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys]
let encoded = try XCTUnwrap(String(data: encoder.encode(document), encoding: .utf8))
XCTAssertLessThan(
    try XCTUnwrap(encoded.range(of: #"\"contactIDs\""#)?.lowerBound),
    try XCTUnwrap(encoded.range(of: #"\"effectiveDepths\""#)?.lowerBound)
)
XCTAssertEqual(
    try JSONDecoder().decode(BoardEditablePositionDocument.self, from: Data(encoded.utf8)),
    document
)
```

- [ ] **Step 6: Add a valid three-model fixture and cross-presentation failures.** Replace the old `second-model` expectation (which asserted that all second models fail) with a valid three-model case and focused invalid cases for duplicated paths, local empty unions, incomplete full descriptors, and foreign pose/orientation keys. Use distinct dummy USDZ bytes and SHA-256 values so the fixture also exercises presentation identity.

Add `private enum MultipleModelMutation { case none, duplicateAssetPath, duplicateDescriptorPath, removeShallowPosition, removeShallowDescriptorContact, foreignShallowRotation, foreignShallowPose }` and `private func makeMultipleModelFixtureBundle(mutation: MultipleModelMutation = .none) throws -> FixtureBundle`. The helper writes `deep`, `medium`, and `shallow` assets/descriptors with hashes of their actual distinct bytes. Each mutation must produce the same diagnostic listed for its Python counterpart in Task 1; `.none` must load all three presentations.

```swift
func testLoadsThreeOriginalModelPresentationsWithLocalPositions() throws {
    let fixture = try makeMultipleModelFixtureBundle()
    let board = try BoardPackageStore.loadPackage(at: fixture).board

    XCTAssertEqual(board.presentations.map(\.id), ["deep", "medium", "shallow"])
    XCTAssertEqual(board.positions.map(\.presentationID), ["deep", "medium", "shallow"])
    XCTAssertEqual(Set(board.contacts.map(\.id)), Set(board.presentations[0].contactIDs))
    XCTAssertEqual(Set(board.contacts.map(\.id)), Set(board.presentations[1].contactIDs))
    XCTAssertEqual(Set(board.contacts.map(\.id)), Set(board.presentations[2].contactIDs))
}
```

- [ ] **Step 7: Make model validation presentation-local.** Remove the `modelPresentations.count > 1` rejection, preserve exactly-one-default/no-mixed-media rules, and reject repeated asset or descriptor paths. While loading each model, derive its raw local position IDs from `document.positions` (or its implicit presentation position) before suspension/orientation decode. After positions are materialized, call `validateModelPositionInventories` separately for every presentation with only its local positions and its descriptor's full canonical inventory.

```swift
let modelPresentations: [(BoardPresentation, BoardModelMedia)] = presentations.compactMap {
    guard case .model(let media) = $0.media else { return nil }
    return ($0, media)
}
let assetPaths = modelPresentations.map { $0.1.assetPath }
let descriptorPaths = modelPresentations.map { $0.1.descriptorPath }
guard Set(assetPaths).count == assetPaths.count else {
    throw BoardPackageStoreError.invalidPackage(
        boardID: document.id, reason: "model assetPath values must be unique"
    )
}
guard Set(descriptorPaths).count == descriptorPaths.count else {
    throw BoardPackageStoreError.invalidPackage(
        boardID: document.id, reason: "model descriptorPath values must be unique"
    )
}
for (presentation, media) in modelPresentations {
    let localPositions = positions.filter { $0.presentationID == presentation.id }
    guard !localPositions.isEmpty else {
        throw BoardPackageStoreError.invalidPackage(
            boardID: document.id,
            reason: "model presentation \(presentation.id) must have at least one local position"
        )
    }
    try validateModelPositionInventories(
        localPositions,
        descriptorContactIDs: Set(media.descriptor.contacts.keys),
        canonicalContactIDs: contacts.map(\.id),
        orientation: media.orientation,
        requiresExactPartition: true,
        boardID: document.id
    )
}
```

- [ ] **Step 8: Confirm GREEN and Python/Swift parity.**

Run:

```bash
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/BoardPackageWriterTests
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_board_catalog.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py -q
```

Expected: both readers accept and reject the same fixtures; all selected suites pass.

- [ ] **Step 9: Commit and push the Swift package checkpoint.**

```bash
rtk git add \
  HangTen/Models/TrainingModels.swift \
  HangTen/Models/BoardPackageStore.swift \
  HangTen/Models/BoardPackageWriter.swift \
  HangTenTests/BoardPackageStoreTests.swift \
  HangTenTests/BoardPackageWriterTests.swift \
  HangTenTests/Fixtures/BoardPackageValidationFixtures.json
rtk git commit -m "feat: load multi-presentation board configurations"
rtk git push
```

**Review checkpoint:** A reviewer compares every shared fixture result across Python and Swift and confirms each model loader receives only its own position namespace while descriptors still describe the full board.

---

## Task 3: Persist position identity without leaking it across transformations

**Files:**

- Modify: `HangTen/Models/PlanStorage.swift:182` (`ContactRequirement`)
- Modify: `HangTen/Models/CustomRoutineDraft.swift:19` (hand transition), `:146` (requirement construction), `:264` (copy), and `:422` (compatible targets)
- Modify: `HangTen/Models/CustomRoutineStore.swift:672` (generic/cross-board import normalization)
- Modify: `HangTenTests/PlanStorageTests.swift` (strict codec and validation)
- Modify: `HangTenTests/CustomRoutineDraftTests.swift` (copy/hand behavior)
- Modify: `HangTenTests/CustomRoutineStoreTests.swift` (import behavior)

**Interfaces produced:**

- Consumes: Task 2's internal `String.isBoardPackageIdentifier` and board-position APIs.
- Produces exclusively for the experience plan: the exact `ContactRequirement` interface and transformations below. Experience code must call these APIs; it must not edit their codec, `CustomRoutineDraft`/`CustomRoutineStore` transformation logic, validators, or unit-test files.

```swift
struct ContactRequirement: Codable, Hashable {
    let contactID: String?
    let positionID: String?
    let kind: HoldKind?
    let shape: HoldShape?
    let depth: HoldDepth?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let selection: ContactSelectionPolicy

    init(
        contactID: String? = nil,
        positionID: String? = nil,
        kind: HoldKind? = nil,
        shape: HoldShape? = nil,
        depth: HoldDepth? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        selection: ContactSelectionPolicy = .single
    )

    func strippingExactContactIdentity() -> ContactRequirement
    var singleHandSelection: ContactRequirement { get }
}
```

Rename `strippingExactContactID()` to `strippingExactContactIdentity()` and update all callers in the same commit so no call site can strip only half of the identity. `singleHandSelection` retains both IDs when the same exact board/contact identity remains; any transition to `.bilateralPair` strips both.

- [ ] **Step 1: Write failing strict-Codable tests.** Assert the encoded key is exactly `positionID`; old JSON without it decodes to `nil`; unknown keys still fail; malformed/empty identifiers fail; and explicit `positionID: null` fails rather than becoming an omission.

Use `private func decodeRequirement(_ json: String) throws -> ContactRequirement` in `PlanStorageTests` and this exact matrix:

| JSON change from `{"contactID":"edge","selection":"single"}` | Expected result |
| --- | --- |
| no `positionID` | success; `positionID == nil` |
| `"positionID":"front"` | success; re-encode contains exactly that key/value |
| `"positionID":null` | decode failure containing `positionID must be a non-null identifier` |
| `"positionID":""` | decode failure containing `positionID must be identifier-shaped` |
| `"positionID":"Front Space"` | decode failure containing `positionID must be identifier-shaped` |
| position present, `contactID` omitted | decode failure containing `positionID requires an exact contactID` |
| position present, `selection:"bilateralPair"` | decode failure containing `positionID requires single selection` |
| extra `"position": "front"` | existing unknown-key failure for `position` |

```swift
func testLegacyRequirementWithoutPositionIDStillDecodes() throws {
    let requirement = try JSONDecoder().decode(
        ContactRequirement.self,
        from: Data(#"{"contactID":"edge","selection":"single"}"#.utf8)
    )
    XCTAssertEqual(requirement.contactID, "edge")
    XCTAssertNil(requirement.positionID)
}

func testExplicitNullPositionIDIsRejected() {
    XCTAssertThrowsError(
        try JSONDecoder().decode(
            ContactRequirement.self,
            from: Data(#"{"contactID":"edge","positionID":null,"selection":"single"}"#.utf8)
        )
    )
}
```

- [ ] **Step 2: Write failing context-free legality tests.** Prove `positionID` requires a nonempty exact `contactID` and `.single`, while omission remains legal. Assert transformations into generic mode emit both IDs as `nil`. Task 4 adds the board/provenance checks because those require joint resolution against a `BoardRevision`.

Add `private func exactRequirement(positionID: String? = "front", selection: ContactSelectionPolicy = .single) -> ContactRequirement` to `CustomRoutineDraftTests`. Pin the transformation outputs exactly:

| Operation | Starting identity | Expected identity; depth |
| --- | --- | --- |
| `singleHandSelection` | `edge` / `front` / single | `edge` / `front`; exact 15 retained |
| ordinary same-board draft copy | `edge` / `front` / single | `edge` / `front`; exact 15 retained |
| change selection to bilateral | `edge` / `front` / single | `nil` / `nil`; exact 15 retained |
| `strippingExactContactIdentity()` | `edge` / `front` / single | `nil` / `nil`; exact 15 retained |
| draft conversion to `.generic` | `edge` / `front` / single | `nil` / `nil`; exact 15 retained |
| copy from `fixture.a` to `fixture.b` | `edge` / `front` / single | `nil` / `nil`; exact 15 retained |

- [ ] **Step 3: Run the focused suites and confirm RED.**

Run:

```bash
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/PlanStorageTests \
  -only-testing:HangTenTests/CustomRoutineDraftTests \
  -only-testing:HangTenTests/CustomRoutineStoreTests
```

Expected: compile failures for `positionID` and `strippingExactContactIdentity` precede the new assertion failures.

- [ ] **Step 4: Implement the strict codec and initializer invariants.** Add `positionID` to `CodingKeys`; use `container.contains(.positionID)` plus `decode(String.self, forKey:)` so explicit null fails; validate identifier shape with the same package identifier grammar; and require `contactID != nil && selection == .single` whenever `positionID != nil`. Keep omission compatible.

```swift
if container.contains(.positionID) {
    guard try !container.decodeNil(forKey: .positionID) else {
        throw DecodingError.dataCorruptedError(
            forKey: .positionID,
            in: container,
            debugDescription: "positionID must be a non-null identifier"
        )
    }
    positionID = try container.decode(String.self, forKey: .positionID)
    guard positionID?.isBoardPackageIdentifier == true else {
        throw DecodingError.dataCorruptedError(
            forKey: .positionID,
            in: container,
            debugDescription: "positionID must be identifier-shaped"
        )
    }
} else {
    positionID = nil
}
if positionID != nil && contactID == nil {
    throw DecodingError.dataCorruptedError(
        forKey: .contactID,
        in: container,
        debugDescription: "positionID requires an exact contactID"
    )
}
if positionID != nil && selection != .single {
    throw DecodingError.dataCorruptedError(
        forKey: .selection,
        in: container,
        debugDescription: "positionID requires single selection"
    )
}
```

- [ ] **Step 5: Enforce context-free identity invariants at every construction boundary.** Decoder failures use `DecodingError.dataCorrupted`; programmatic construction uses preconditions; draft/store transformations construct only legal values. Do not look up a board or auto-repair an ID in `ContactRequirement` itself—the contextual validation in Task 4 is the single board-aware authority.

```swift
if let positionID {
    precondition(positionID.isBoardPackageIdentifier)
    precondition(contactID?.isBoardPackageIdentifier == true)
    precondition(selection == .single)
}
self.contactID = contactID
self.positionID = positionID
```

- [ ] **Step 6: Implement and test transformation rules.** Apply this complete matrix in both draft and store code:

| Transformation | `contactID` | `positionID` | Other constraints |
| --- | --- | --- | --- |
| same board + same contact + single hand | preserve | preserve | preserve |
| single-hand materialization | preserve | preserve | preserve |
| switch to bilateral selection | strip | strip | preserve |
| switch to generic target | strip | strip | preserve |
| copy/import to a different board | strip | strip | preserve |

```swift
func strippingExactContactIdentity() -> ContactRequirement {
    ContactRequirement(
        kind: kind,
        shape: shape,
        depth: depth,
        fingerCapacity: fingerCapacity,
        handCapacity: handCapacity,
        selection: selection
    )
}
```

At each call site, compute `preservesExactIdentity = destinationBoardID == sourceBoardID && destinationContactID == sourceContactID && selection == .single`; copy the original requirement only when true, otherwise call `strippingExactContactIdentity()`. Tests invoke the actual draft/store entry points rather than this Boolean in isolation.

- [ ] **Step 7: Confirm GREEN.** Re-run the Task 3 command. Expected: all three suites pass, and an encoded generic requirement contains neither identity key.

- [ ] **Step 8: Commit and push the persistence checkpoint.**

```bash
rtk git add \
  HangTen/Models/PlanStorage.swift \
  HangTen/Models/CustomRoutineDraft.swift \
  HangTen/Models/CustomRoutineStore.swift \
  HangTenTests/PlanStorageTests.swift \
  HangTenTests/CustomRoutineDraftTests.swift \
  HangTenTests/CustomRoutineStoreTests.swift
rtk git commit -m "feat: persist exact board position requirements"
rtk git push
```

**Review checkpoint:** A reviewer traces every construction/copy/import path found by `rtk rg 'ContactRequirement\(' HangTen HangTenTests` and confirms none can preserve `positionID` after dropping or changing its board/contact identity.

---

## Task 4: Resolve all simultaneous requirements into one immutable board target

**Files:**

- Modify: `HangTen/Models/WorkoutActivityRecording.swift:411` (`ContactResolutionError`) and `:428` (`ContactResolver`)
- Modify: `HangTen/Models/PlanStorage.swift:1291` (call joint validation once per target group)
- Modify: `HangTen/Models/CustomRoutineStore.swift:120` (`CustomRoutineValidationIssue` and `CustomRoutineValidator`)
- Modify: `HangTenTests/BoardTargetSubstitutionTests.swift` (joint resolution matrix)
- Modify: `HangTenTests/PlanStorageTests.swift` (validator integration)
- Modify: `HangTenTests/CustomRoutineStoreTests.swift` (custom provenance/repair boundary integration)

**Interfaces produced:**

- Consumes: Tasks 2–3 position metadata and exact requirement identity.
- Produces: the immutable target/result interfaces below for runtime Task 5 and experience Tasks 3–8.

```swift
struct ResolvedBoardTarget: Hashable {
    let boardID: String
    let revisionID: String
    let contactIDs: [String]
    let positionID: String
    let presentationID: String
    let effectiveDepths: [String: HoldDepth]
    let modelSHA256: String?
}

enum BoardTargetResolution: Hashable {
    case resolved(ResolvedBoardTarget)
    case positionChoiceRequired([ResolvedBoardTarget])
}

enum ContactResolutionError: LocalizedError, Equatable {
    case noMatches
    case ambiguousSingle(candidateCount: Int)
    case invalidBilateralPair(candidateCount: Int)
    case invalidExplicitPosition(positionID: String)
    case conflictingExplicitPositions(positionIDs: [String])
    case positionChoiceRequired(positionIDs: [String])
}

enum ContactResolver {
    static func resolveTarget(
        _ requirements: [ContactRequirement],
        step: WorkoutStep,
        board: BoardRevision
    ) throws -> BoardTargetResolution

    static func resolveTarget(
        _ requirements: [ContactRequirement],
        step: WorkoutStep,
        board: BoardRevision,
        positionID: String
    ) throws -> ResolvedBoardTarget

    static func contacts(
        for requirement: ContactRequirement,
        step: WorkoutStep,
        board: BoardRevision,
        in target: ResolvedBoardTarget
    ) throws -> [PhysicalContact]
}
```

Keep the existing `resolve(_:step:board:) -> [PhysicalContact]` overloads as compatibility wrappers. They may return contacts only for `.resolved`; a position choice becomes `.positionChoiceRequired(positionIDs:)`, never a first-position fallback.

- [ ] **Step 1: Write the failing target-resolution matrix.** Add tests for one unique position, two viable positions, an explicit valid position, a stale explicit position, conflicting requirement position IDs, and two requirements individually satisfiable only in different positions. Verify candidate target order follows `board.positions` solely for stable display; the order never chooses a winner.

Add `private func configurableBoard(contacts: [PhysicalContact], presentations: [BoardPresentation], positions: [BoardPosition]) -> BoardRevision`, `private func fixtureStep(targets: [ContactRequirement], handUse: WorkoutHandUse = .single, side: WorkoutSide = .left) -> WorkoutStep`, and `private func targets(from result: BoardTargetResolution) -> [ResolvedBoardTarget]` to `ContactResolverTests`. Exercise this matrix exactly:

| Candidate positions / authored IDs | Expected result |
| --- | --- |
| only `front` satisfies | `.resolved(positionID: "front")` |
| `front`, then `back` both satisfy | `.positionChoiceRequired` with IDs `front`, `back` in that order |
| requirement explicitly says `back` and it satisfies | resolved `back`; `front` is not searched |
| requirement explicitly says `removed` | `.invalidExplicitPosition(positionID: "removed")` |
| simultaneous requirements say `front` and `back` | `.conflictingExplicitPositions(positionIDs: ["back", "front"])` |
| edge exists only in `front`, jug only in `back` | `.noMatches` |

```swift
func testJointResolutionRejectsRequirementsSplitAcrossPositions() throws {
    let board = makeBoard(
        positions: [
            position("front", contacts: ["edge"]),
            position("back", contacts: ["jug"]),
        ]
    )
    let requirements = [
        ContactRequirement(contactID: "edge"),
        ContactRequirement(contactID: "jug"),
    ]

    XCTAssertThrowsError(
        try ContactResolver.resolveTarget(
            requirements,
            step: fixtureStep(targets: requirements),
            board: board
        )
    ) { error in
        XCTAssertEqual(error as? ContactResolutionError, .noMatches)
    }
}
```

- [ ] **Step 2: Add depth-specific failing tests.** Use one exact base-18 contact with position overrides 18/15/10 and one contact with `depth == nil`:

| Requirement | Expected result |
| --- | --- |
| exact 10 | resolved `depth-10mm`, effective map `edge: 10` |
| exact 12 | `.noMatches` |
| no depth against the three edge positions | choice IDs `depth-18mm`, `depth-15mm`, `depth-10mm` |
| exact unmeasured contact, no required depth | resolved contact `unmeasured`, effective map `{}` |
| exact unmeasured contact, required exact 10 | `.noMatches` |

Build `private func plateauLikeDepthBoard() -> BoardRevision` with one exact-base-18 `edge`, presentations and positions authored in the order `depth-18mm`, `depth-15mm`, `depth-10mm`, and respective exact `effectiveDepths` values 18, 15, and 10. Every presentation supplies the same edge frame; only the position effective depth differs. Add `private func exactEdgeRequirement(_ millimeters: Double, positionID: String? = nil) -> ContactRequirement` returning a single-selection exact edge requirement. This is a synthetic runtime fixture and does not depend on package-plan output.

Pin candidate continuation, explicit-position failure, and stable authored order with these direct tests:

```swift
func testExactTenSkipsEighteenAndFifteenThenResolvesTen() throws {
    let board = plateauLikeDepthBoard()
    let requirement = exactEdgeRequirement(10)
    let result = try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board
    )
    let target = try XCTUnwrap(targets(from: result).only)
    XCTAssertEqual(target.positionID, "depth-10mm")
    XCTAssertEqual(
        target.effectiveDepths,
        ["edge": .range(.init(minimum: 10, maximum: 10))]
    )
}

func testExactFifteenSkipsEighteenThenResolvesFifteen() throws {
    let board = plateauLikeDepthBoard()
    let requirement = exactEdgeRequirement(15)
    let result = try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board
    )
    XCTAssertEqual(targets(from: result).map(\.positionID), ["depth-15mm"])
}

func testAllCandidatePositionsFailingDepthThrowsNoMatches() {
    let board = plateauLikeDepthBoard()
    let requirement = exactEdgeRequirement(12)
    XCTAssertThrowsError(try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board
    )) { error in
        XCTAssertEqual(error as? ContactResolutionError, .noMatches)
    }
}

func testExplicitEighteenWithExactTenPropagatesNoMatches() {
    let board = plateauLikeDepthBoard()
    let requirement = exactEdgeRequirement(10)
    XCTAssertThrowsError(try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board,
        positionID: "depth-18mm"
    )) { error in
        XCTAssertEqual(error as? ContactResolutionError, .noMatches)
    }
}

func testAmbiguousTargetsPreserveAuthoredPositionOrder() throws {
    let board = plateauLikeDepthBoard()
    let requirement = ContactRequirement(contactID: "edge")
    let result = try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board
    )
    XCTAssertEqual(
        targets(from: result).map(\.positionID),
        ["depth-18mm", "depth-15mm", "depth-10mm"]
    )
}
```

Define the test-only `Array.only` helper as `var only: Element? { count == 1 ? self[0] : nil }`; `testExactTen…` therefore also rejects an accidental multi-target result.

Preserve the existing single-position selection-error contract while moving those fixtures onto the new target API. Extend the existing `jugBoard` helper with `emptyGeometryContactIDs: Set<String> = []`; keep each named key in raster `contactGeometry`, but use an empty piece array for IDs in that set. That makes the contact part of `board.contactIDs(inPosition:)` while deliberately leaving it without a selectable frame. Add these exact regressions to `ContactResolverTests` alongside the existing `testBilateralPairRejects…` cases:

```swift
func testSinglePositionTargetPreservesAmbiguousSingleError() {
    let board = jugBoard(
        [
            .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-center", frame: CGRect(x: 0.45, y: 0.4, width: 0.1, height: 0.1)),
        ],
        emptyGeometryContactIDs: ["jug-center"]
    )
    let requirement = ContactRequirement.kind(.jug, selection: .single)
    XCTAssertEqual(board.positions.map(\.id), ["front"])

    XCTAssertThrowsError(try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board
    )) { error in
        XCTAssertEqual(
            error as? ContactResolutionError,
            .ambiguousSingle(candidateCount: 2)
        )
    }
}

func testSinglePositionTargetPreservesInvalidBilateralPairError() {
    let board = jugBoard([
        .init(id: "jug-near", frame: CGRect(x: 0.55, y: 0.4, width: 0.1, height: 0.1)),
        .init(id: "jug-far", frame: CGRect(x: 0.85, y: 0.4, width: 0.1, height: 0.1)),
    ])
    let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)
    XCTAssertEqual(board.positions.map(\.id), ["front"])

    XCTAssertThrowsError(try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board
    )) { error in
        XCTAssertEqual(
            error as? ContactResolutionError,
            .invalidBilateralPair(candidateCount: 2)
        )
    }
}
```

Use `configurableBoard` to add this exact candidate-continuation and zero-success reduction matrix; position arrays are authored in the displayed order:

| Candidate-local failures in authored order | Final board-wide error |
| --- | --- |
| `[.ambiguousSingle(candidateCount: 2)]` | same `.ambiguousSingle(candidateCount: 2)` |
| `[.invalidBilateralPair(candidateCount: 2)]` | same `.invalidBilateralPair(candidateCount: 2)` |
| two identical `.ambiguousSingle(candidateCount: 2)` values | same `.ambiguousSingle(candidateCount: 2)` |
| two identical `.invalidBilateralPair(candidateCount: 2)` values | same `.invalidBilateralPair(candidateCount: 2)` |
| `.invalidBilateralPair(candidateCount: 1)`, then `.invalidBilateralPair(candidateCount: 2)` | `.noMatches` |
| `.noMatches`, then `.invalidBilateralPair(candidateCount: 2)` | `.noMatches` |
| `.noMatches`, then a successful target | resolved second target; the first failure does not escape |

- [ ] **Step 3: Add presentation/hash and legacy-raster failing tests.** Give deep/medium/shallow descriptors hashes `aaa…`, `bbb…`, and `ccc…` (64 characters each). Resolving medium must return `presentationID == "medium-model"` and `modelSHA256 == String(repeating: "b", count: 64)` even when deep is default. A single raster fixture must return `modelSHA256 == nil`.

Also exercise the real legacy raster package whose synthesized position deliberately has no authored membership. This pins the resolver to `BoardRevision.contactIDs(inPosition:)`, which derives raster membership from `media.contactGeometry`, instead of reading the empty `BoardPosition.contactIDs` storage directly:

```swift
func testTargetResolutionUsesDerivedMembershipForLegacyRasterPosition() throws {
    let board = try XCTUnwrap(
        BoardCatalog.packageStore.board(id: "yy.verticalboard-light")
    )
    let position = try XCTUnwrap(board.position(id: "primary"))
    XCTAssertFalse(position.contactIDsWereExplicitlyAuthored)
    XCTAssertTrue(position.contactIDs.isEmpty)
    XCTAssertTrue(board.contactIDs(inPosition: position.id).contains("jug-left"))

    let requirement = ContactRequirement(
        contactID: "jug-left",
        positionID: "primary"
    )
    let target = try ContactResolver.resolveTarget(
        [requirement],
        step: fixtureStep(targets: [requirement]),
        board: board,
        positionID: "primary"
    )

    XCTAssertEqual(target.contactIDs, ["jug-left"])
    XCTAssertEqual(target.positionID, "primary")
    XCTAssertEqual(target.presentationID, "primary")
    XCTAssertEqual(target.effectiveDepths, [:])
    XCTAssertNil(target.modelSHA256)
}
```

- [ ] **Step 4: Run focused resolver tests and confirm RED.**

Run:

```bash
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/ContactResolverTests \
  -only-testing:HangTenTests/PlanStorageTests \
  -only-testing:HangTenTests/CustomRoutineStoreTests
```

Expected: the immutable target/result types are missing and current resolution searches only the default presentation.

- [ ] **Step 5: Build one-position-at-a-time resolution.** Collect all non-`nil` requirement `positionID`s. More than one distinct ID throws `.conflictingExplicitPositions` with sorted IDs; one ID restricts candidates and a missing board position throws `.invalidExplicitPosition`. With no explicit ID, evaluate every board position. For each candidate, resolve **every** simultaneous requirement using only `board.contactIDs(inPosition: position.id)`, `position.effectiveDepth(for:)`, and the spatial frames from `board.presentation(id: position.presentationID)`. Never read `position.contactIDs` directly on this path because legacy raster positions store an empty authored array while their membership lives in raster contact geometry.

```swift
private static func target(
    for requirements: [ContactRequirement],
    step: WorkoutStep,
    board: BoardRevision,
    position: BoardPosition
) throws -> ResolvedBoardTarget {
    guard let presentation = board.presentation(id: position.presentationID) else {
        throw ContactResolutionError.noMatches
    }
    var selected = Set<String>()
    for requirement in requirements {
        let contacts = try contacts(
            for: requirement,
            step: step,
            board: board,
            position: position,
            presentation: presentation
        )
        selected.formUnion(contacts.map(\.id))
    }
    guard !selected.isEmpty else { throw ContactResolutionError.noMatches }
    let orderedIDs = board.contacts.map(\.id).filter(selected.contains)
    let modelSHA256: String?
    switch presentation.media {
    case .raster:
        modelSHA256 = nil
    case .model(let media):
        modelSHA256 = media.descriptor.modelSHA256
    }
    return ResolvedBoardTarget(
        boardID: board.id,
        revisionID: board.revisionID,
        contactIDs: orderedIDs,
        positionID: position.id,
        presentationID: presentation.id,
        effectiveDepths: board.materializedEffectiveDepths(
            for: orderedIDs, in: position
        ),
        modelSHA256: modelSHA256
    )
}

private static func contacts(
    for requirement: ContactRequirement,
    step: WorkoutStep,
    board: BoardRevision,
    position: BoardPosition,
    presentation: BoardPresentation
) throws -> [PhysicalContact] {
    let allowed = Set(board.contactIDs(inPosition: position.id))
    let candidates = board.contacts.filter { contact in
        allowed.contains(contact.id)
            && matches(
                requirement,
                contact: contact,
                effectiveDepth: position.effectiveDepth(for: contact)
            )
            && matches(stepGripType: step.gripType, contact: contact)
    }
    return try applySelection(
        requirement.selection,
        candidates: candidates,
        step: step,
        presentation: presentation
    )
}

private static func applySelection(
    _ selection: ContactSelectionPolicy,
    candidates: [PhysicalContact],
    step: WorkoutStep,
    presentation: BoardPresentation
) throws -> [PhysicalContact] {
    guard !candidates.isEmpty else { throw ContactResolutionError.noMatches }
    switch selection {
    case .single:
        return try singleCandidate(from: candidates, in: presentation)
    case .bilateralPair:
        guard step.handUse == .double, step.side == .both,
              let pair = outermostPair(from: candidates, in: presentation) else {
            throw ContactResolutionError.invalidBilateralPair(
                candidateCount: candidates.count
            )
        }
        return pair
    }
}

```

Refactor the existing spatial helpers to the exact private signatures `singleCandidate(from candidates: [PhysicalContact], in presentation: BoardPresentation) throws -> [PhysicalContact]` and `outermostPair(from candidates: [PhysicalContact], in presentation: BoardPresentation) -> [PhysicalContact]?`; replace their reads of `board.defaultPresentation` with the passed presentation.

Also replace the metadata predicate with this exact signature/body so an unmeasured contact passes only when depth is unconstrained:

```swift
private static func matches(
    _ requirement: ContactRequirement,
    contact: PhysicalContact,
    effectiveDepth: HoldDepth?
) -> Bool {
    if let contactID = requirement.contactID, contact.id != contactID { return false }
    if let kind = requirement.kind, contact.kind != kind { return false }
    if let shape = requirement.shape, contact.shape != shape { return false }
    if let depth = requirement.depth, !depth.matches(effectiveDepth) { return false }
    if let capacity = requirement.fingerCapacity, contact.fingerCapacity != capacity { return false }
    if let capacity = requirement.handCapacity, contact.handCapacity != capacity { return false }
    return true
}
```

- [ ] **Step 6: Construct immutable targets only after full success and complete the candidate loop.** The `target(for:step:board:position:)` helper above canonicalizes selected contact IDs in `board.contacts` order, materializes all known effective depths through Task 2's helper, and copies the selected presentation's model hash. The board-wide overload evaluates positions in authored order and appends every candidate-local failure in that same order. `.noMatches`, `.ambiguousSingle`, and `.invalidBilateralPair` mean that candidate failed and therefore continue the loop; `.invalidExplicitPosition`, `.conflictingExplicitPositions`, and `.positionChoiceRequired` are terminal board/request errors and propagate immediately. Any non-`ContactResolutionError` also propagates because the catch is type-specific.

When no target succeeds, preserve selection-error compatibility deterministically: one evaluated position rethrows its exact `.ambiguousSingle` or `.invalidBilateralPair`; multiple positions rethrow a selection error only when **every** evaluated position produced the same error value, including its candidate count. Empty failures, any `.noMatches`, or mixed/different selection errors collapse to `.noMatches`. Thus an early depth/contact `.noMatches` never prevents a later valid position from resolving, while the existing single-position `ContactResolverTests` exact `.invalidBilateralPair` assertions remain valid.

The explicit overload first validates embedded/requested position agreement and board membership, then evaluates exactly that position by calling `target` directly. It never enters the candidate loop and therefore propagates the candidate's exact `.noMatches`, `.ambiguousSingle`, or `.invalidBilateralPair` instead of converting it to a board-wide zero-match result or choice.

```swift
static func resolveTarget(
    _ requirements: [ContactRequirement],
    step: WorkoutStep,
    board: BoardRevision
) throws -> BoardTargetResolution {
    let explicitIDs = Array(Set(requirements.compactMap(\.positionID))).sorted()
    guard explicitIDs.count <= 1 else {
        throw ContactResolutionError.conflictingExplicitPositions(
            positionIDs: explicitIDs
        )
    }
    if let explicitID = explicitIDs.first {
        return .resolved(try resolveTarget(
            requirements,
            step: step,
            board: board,
            positionID: explicitID
        ))
    }

    var successfulTargets: [ResolvedBoardTarget] = []
    var candidateFailures: [ContactResolutionError] = []
    for position in board.positions {
        do {
            successfulTargets.append(try target(
                for: requirements,
                step: step,
                board: board,
                position: position
            ))
        } catch let error as ContactResolutionError {
            switch error {
            case .noMatches,
                 .ambiguousSingle(candidateCount: _),
                 .invalidBilateralPair(candidateCount: _):
                candidateFailures.append(error)
                continue
            case .invalidExplicitPosition(positionID: _),
                 .conflictingExplicitPositions(positionIDs: _),
                 .positionChoiceRequired(positionIDs: _):
                throw error
            }
        }
    }

    switch successfulTargets.count {
    case 0:
        throw collapsedCandidateFailure(candidateFailures)
    case 1:
        return .resolved(successfulTargets[0])
    default:
        return .positionChoiceRequired(successfulTargets)
    }
}

private static func collapsedCandidateFailure(
    _ failures: [ContactResolutionError]
) -> ContactResolutionError {
    guard let first = failures.first else { return .noMatches }
    switch first {
    case .ambiguousSingle(candidateCount: _),
         .invalidBilateralPair(candidateCount: _):
        // A one-position list satisfies allSatisfy and preserves its exact
        // legacy selection error. Multi-position lists must agree exactly.
        return failures.allSatisfy { $0 == first } ? first : .noMatches
    case .noMatches:
        return .noMatches
    case .invalidExplicitPosition(positionID: _),
         .conflictingExplicitPositions(positionIDs: _),
         .positionChoiceRequired(positionIDs: _):
        // These are propagated in the loop and are never collected.
        return first
    }
}

static func resolveTarget(
    _ requirements: [ContactRequirement],
    step: WorkoutStep,
    board: BoardRevision,
    positionID: String
) throws -> ResolvedBoardTarget {
    let embeddedIDs = Array(Set(requirements.compactMap(\.positionID))).sorted()
    guard embeddedIDs.count <= 1 else {
        throw ContactResolutionError.conflictingExplicitPositions(
            positionIDs: embeddedIDs
        )
    }
    if let embeddedID = embeddedIDs.first, embeddedID != positionID {
        throw ContactResolutionError.conflictingExplicitPositions(
            positionIDs: [embeddedID, positionID].sorted()
        )
    }
    guard let position = board.position(id: positionID) else {
        throw ContactResolutionError.invalidExplicitPosition(
            positionID: positionID
        )
    }
    return try target(
        for: requirements,
        step: step,
        board: board,
        position: position
    )
}
```

- [ ] **Step 7: Update both validation boundaries to be joint and provenance-aware.** In `PlanLibraryValidator`, reject any authored `positionID` because manufacturer/catalog content may not invent a configuration, and replace per-requirement board checks with one `resolveTarget(requirements,step:board:)` call per simultaneous target group. Generic catalog ambiguity remains a valid pre-session choice. In `CustomRoutineValidator`, require `positionID` only under `.boardSpecific`, require the bound board/position/contact relationship, and run the same joint resolver. A board-specific custom target returning `.positionChoiceRequired` remains decodable but is an `unresolvableSegmentTargets`/`unresolvableTargets` save/start issue until the experience layer records an athlete-selected position; a stale explicit ID is the same fail-closed issue. Generic custom targets must have both identity fields unset. Neither validator mutates, aliases, nor drops IDs.

Pin the boundary results with this table before changing the validators:

| Definition boundary | Target | Expected validation |
| --- | --- | --- |
| plan library | any non-`nil positionID` | issue at exact target path: catalog requirements cannot author `positionID` |
| plan library, board-agnostic | no exact IDs, two viable positions | no issue; setup choice remains deferred |
| custom `.generic` | either exact ID non-`nil` | `.targetModeMismatch` |
| custom `.boardSpecific`, explicit valid position | joint resolver returns `.resolved` | no target issue |
| custom `.boardSpecific`, stale explicit position | resolver throws | `.unresolvableTargets` or `.unresolvableSegmentTargets` at owning path |
| custom `.boardSpecific`, no position and two viable positions | resolver returns choice | same unresolvable issue until athlete chooses |

- [ ] **Step 8: Confirm GREEN.** Re-run the Task 4 command. Expected: all resolver/validator cases pass, including Review focus 4 and the depthless half of Review focus 5.

- [ ] **Step 9: Commit and push the resolution checkpoint.**

```bash
rtk git add \
  HangTen/Models/WorkoutActivityRecording.swift \
  HangTen/Models/PlanStorage.swift \
  HangTen/Models/CustomRoutineStore.swift \
  HangTenTests/BoardTargetSubstitutionTests.swift \
  HangTenTests/PlanStorageTests.swift \
  HangTenTests/CustomRoutineStoreTests.swift
rtk git commit -m "feat: resolve workout requirements by board configuration"
rtk git push
```

**Review checkpoint:** A reviewer follows the contact matching call graph and confirms no access to `defaultPresentation` or `positions.first` remains on the new target-resolution path.

---

## Task 5: Record strict immutable configuration snapshots from frozen targets

**Files:**

- Modify: `HangTen/Models/WorkoutActivityRecording.swift:3` (`ResolvedContactSnapshot`) and `:578` (`WorkoutActivityRecorder`)
- Modify: `HangTenTests/WorkoutActivityRecordingTests.swift` (codec, legacy, target revalidation, and hash tests)

**Interfaces produced:**

- Consumes: Task 4's immutable target and exact-position resolver.
- Produces: strict snapshot persistence and the recorder handoff consumed unchanged by experience Tasks 7–8.

```swift
struct ResolvedBoardConfigurationSnapshot: Codable, Hashable {
    let positionID: String
    let presentationID: String
    let effectiveDepths: [String: HoldDepth]
}

struct ResolvedContactSnapshot: Codable, Hashable {
    let boardID: String
    let revisionID: String
    let modelSHA256: String?
    let requirement: ContactRequirement
    let contactIDs: [String]
    let configuration: ResolvedBoardConfigurationSnapshot?

    init(
        boardID: String,
        revisionID: String,
        modelSHA256: String?,
        requirement: ContactRequirement,
        contactIDs: [String],
        configuration: ResolvedBoardConfigurationSnapshot? = nil
    )
}

enum WorkoutActivityRecordingError: LocalizedError, Equatable {
    case unresolvedTarget(stepID: String, segmentIndex: Int)
    case handSideRequired(stepID: String)
    case invalidObservedDuration(WorkoutActivitySegmentKey)
    case missingResolvedTarget(WorkoutActivitySegmentKey)
    case unexpectedResolvedTarget(WorkoutActivitySegmentKey)
    case invalidResolvedTarget(WorkoutActivitySegmentKey)
}

struct WorkoutActivitySegmentKey: Hashable {
    let stepID: String
    let segmentIndex: Int
}

struct WorkoutActivityRecorder {
    func segments(
        for plan: TrainingPlan,
        on board: BoardRevision,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:],
        selectedHandSide: WorkoutSide? = nil,
        handPreference: WorkoutSessionHandPreference? = nil,
        sessionSteps: [WorkoutStep]? = nil,
        resolvedTargets: [WorkoutActivitySegmentKey: ResolvedBoardTarget]? = nil
    ) throws -> [RecordedActivitySegment]

    func metadata(
        for plan: TrainingPlan,
        on board: BoardRevision,
        stopwatchDurations: [WorkoutActivitySegmentKey: TimeInterval] = [:],
        selectedHandSide: WorkoutSide? = nil,
        handPreference: WorkoutSessionHandPreference? = nil,
        sessionSteps: [WorkoutStep]? = nil,
        resolvedTargets: [WorkoutActivitySegmentKey: ResolvedBoardTarget]? = nil,
        stepMeasurements: [WorkoutStepMeasurement] = []
    ) throws -> WorkoutActivityMetadata
}
```

`nil` means the legacy caller has not frozen a dictionary and the recorder may use joint resolution. A non-`nil` dictionary is a complete frozen contract: every board-target segment must have exactly one entry and unknown extra keys fail.

- [ ] **Step 1: Write strict snapshot-codec tests.** For `configuration`, test omission (legacy success), explicit null (failure), unknown members, missing members, malformed identifiers, and depth keys outside `contactIDs`. An empty `effectiveDepths` object is valid here. Also assert top-level `contactIDs` is nonempty and unique for a configured snapshot.

Add `private func decodeSnapshot(_ json: String) throws -> ResolvedContactSnapshot` and use this exact matrix:

| Configuration mutation | Expected result/diagnostic |
| --- | --- |
| key omitted | legacy success; `configuration == nil` |
| value `null` | failure: `configuration must be a non-null object` |
| omit `positionID`, `presentationID`, or `effectiveDepths` | failure naming the missing key |
| add `unknown` | failure: `Unsupported board configuration snapshot field unknown` |
| empty/malformed either ID | failure: `<key> must be identifier-shaped` |
| depth key absent from snapshot `contactIDs` | failure: `effectiveDepths may contain only selected contact IDs` |
| configured snapshot with `contactIDs: []` or duplicates | failure: `contactIDs must be non-empty and unique` |
| `effectiveDepths: {}` with one selected unmeasured ID | successful round trip |

```swift
func testLegacyResolvedContactSnapshotWithoutConfigurationDecodes() throws {
    let snapshot = try JSONDecoder().decode(
        ResolvedContactSnapshot.self,
        from: Data(#"{"boardID":"fixture.board","revisionID":"2026-09","modelSHA256":null,"requirement":{"contactID":"legacy-hold","selection":"single"},"contactIDs":["legacy-hold"]}"#.utf8)
    )
    XCTAssertNil(snapshot.configuration)
}

func testDepthlessConfigurationAllowsEmptyMaterializedDepths() throws {
    let configuration = ResolvedBoardConfigurationSnapshot(
        positionID: "front",
        presentationID: "front-model",
        effectiveDepths: [:]
    )
    let snapshot = ResolvedContactSnapshot(
        boardID: "fixture.board",
        revisionID: "2026-09",
        modelSHA256: String(repeating: "a", count: 64),
        requirement: ContactRequirement(contactID: "unmeasured", positionID: "front"),
        contactIDs: ["unmeasured"],
        configuration: configuration
    )
    let data = try JSONEncoder().encode(snapshot)
    XCTAssertEqual(
        try JSONDecoder().decode(ResolvedContactSnapshot.self, from: data),
        snapshot
    )
}
```

- [ ] **Step 2: Write frozen-target validation tests.** Build a complete dictionary keyed by each target-bearing segment's `stepID` and zero-based `segmentIndex` and prove recording succeeds. Then mutate, one at a time, board ID, revision ID, contact IDs, position ID, presentation ID, effective depths, and model hash; each mutation must fail rather than record stale setup. Test missing and extra dictionary keys.

Use `private func frozenRecordingFixture() throws -> (plan: TrainingPlan, board: BoardRevision, key: WorkoutActivitySegmentKey, target: ResolvedBoardTarget)` and rebuild the target with one changed field per row:

| Frozen-map input | Exact expected error |
| --- | --- |
| exact one-entry map | success |
| map missing `key` | `.missingResolvedTarget(key)` |
| valid entry plus `WorkoutActivitySegmentKey(stepID: "extra", segmentIndex: 0)` | `.unexpectedResolvedTarget(extraKey)` |
| wrong board/revision/contact/position/presentation/depth/hash | `.invalidResolvedTarget(key)` for each independent mutation |

- [ ] **Step 3: Write the selected-presentation regression.** Use three positions/presentations with distinct model hashes, select the medium target, and assert every generated contact snapshot has the medium configuration and medium hash—not the default presentation hash. Include a depthless selected contact and assert its empty map is retained.

This task intentionally uses synthetic boards so it can land before package migration. Do not look up `frictitious.port-a-board` here; the exact package-backed Port acceptance cases are handed to experience plan Task 8 (final integration) in this plan's Task 7.

```swift
XCTAssertEqual(snapshot.configuration?.positionID, "medium")
XCTAssertEqual(snapshot.configuration?.presentationID, "medium-model")
XCTAssertEqual(snapshot.configuration?.effectiveDepths, [:])
XCTAssertEqual(snapshot.modelSHA256, String(repeating: "b", count: 64))
XCTAssertEqual(snapshot.contactIDs, ["unmeasured"])
```

- [ ] **Step 4: Run the recorder suite and confirm RED.**

Run:

```bash
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/WorkoutActivityRecordingTests
```

Expected: configuration decoding and frozen-target overloads are absent; existing code records the default presentation hash.

- [ ] **Step 5: Implement the closed nested codec.** Give `ResolvedBoardConfigurationSnapshot` a custom decoder that rejects unknown/missing/null members, validates both IDs, and accepts an empty but structurally valid `effectiveDepths` map. In `ResolvedContactSnapshot.init(from:)`, distinguish absent `configuration` from explicit null. Validate configuration depth keys are a subset of unique, nonempty `contactIDs`; values use ordinary structurally valid `HoldDepth` because inherited contact depth may be categorical.

```swift
private enum CodingKeys: String, CodingKey, CaseIterable {
    case positionID, presentationID, effectiveDepths
}

let raw = try decoder.container(keyedBy: ActivityCodingKey.self)
let allowed = Set(CodingKeys.allCases.map(\.rawValue))
if let unknown = raw.allKeys.first(where: { !allowed.contains($0.stringValue) }) {
    throw DecodingError.dataCorruptedError(
        forKey: unknown,
        in: raw,
        debugDescription: "Unsupported board configuration snapshot field \(unknown.stringValue)"
    )
}
let container = try decoder.container(keyedBy: CodingKeys.self)
positionID = try container.decode(String.self, forKey: .positionID)
presentationID = try container.decode(String.self, forKey: .presentationID)
effectiveDepths = try container.decode(
    [String: HoldDepth].self, forKey: .effectiveDepths
)
guard positionID.isBoardPackageIdentifier else {
    throw DecodingError.dataCorruptedError(
        forKey: .positionID,
        in: container,
        debugDescription: "positionID must be identifier-shaped"
    )
}
guard presentationID.isBoardPackageIdentifier else {
    throw DecodingError.dataCorruptedError(
        forKey: .presentationID,
        in: container,
        debugDescription: "presentationID must be identifier-shaped"
    )
}
```

In `ResolvedContactSnapshot.init(from:)`, use the following branch before shape checks:

```swift
if container.contains(.configuration) {
    guard try !container.decodeNil(forKey: .configuration) else {
        throw DecodingError.dataCorruptedError(
            forKey: .configuration,
            in: container,
            debugDescription: "configuration must be a non-null object"
        )
    }
    configuration = try container.decode(
        ResolvedBoardConfigurationSnapshot.self,
        forKey: .configuration
    )
} else {
    configuration = nil
}
```

After decoding, require `!contactIDs.isEmpty`, `Set(contactIDs).count == contactIDs.count`, and `Set(configuration.effectiveDepths.keys).isSubset(of: Set(contactIDs))` with the matrix diagnostics.

- [ ] **Step 6: Revalidate frozen targets at the recording boundary.** For every target-bearing work segment, call Task 4's explicit-position overload against the current board and compare the resulting value to the supplied `ResolvedBoardTarget`. Reject any mismatch, missing key, or extra key with a deterministic recording error. Do not repair or partially reuse the supplied target.

```swift
let requiredKeys = Set(recordingSteps.flatMap { step in
    step.segments.indices.compactMap { index in
        guard requirements(in: step.segments[index]) != nil else { return nil }
        return WorkoutActivitySegmentKey(stepID: step.id, segmentIndex: index)
    }
})
if let resolvedTargets {
    let suppliedKeys = Set(resolvedTargets.keys)
    if let missing = requiredKeys.subtracting(suppliedKeys).sorted(by: keyOrder).first {
        throw WorkoutActivityRecordingError.missingResolvedTarget(missing)
    }
    if let extra = suppliedKeys.subtracting(requiredKeys).sorted(by: keyOrder).first {
        throw WorkoutActivityRecordingError.unexpectedResolvedTarget(extra)
    }
}
```

Define `private func requirements(in segment: WorkoutSegment) -> [ContactRequirement]?` by pattern-matching `.requirements(let values)` only for `.work`, and define `private func keyOrder(_ lhs: WorkoutActivitySegmentKey, _ rhs: WorkoutActivitySegmentKey) -> Bool` as lexicographic `stepID`, then `segmentIndex`. For each required key, recompute with `ContactResolver.resolveTarget(requirements, step: recordedStep, board: board, positionID: frozen.positionID)` and require exact `ResolvedBoardTarget` equality; otherwise throw `.invalidResolvedTarget(key)`.

- [ ] **Step 7: Record per-requirement snapshots from the validated target.** Use `ContactResolver.contacts(for:step:board:in:)` for each requirement. Write the target's selected hash. Write a configuration for every new board-backed snapshot, filtering the target's materialized depth map to that requirement's selected contact IDs; this may be empty. Preserve `configuration == nil` only for decoded historical records, not new records.

```swift
let selectedIDs = contacts.map(\.id)
let selectedIDSet = Set(selectedIDs)
let snapshot = ResolvedContactSnapshot(
    boardID: target.boardID,
    revisionID: target.revisionID,
    modelSHA256: target.modelSHA256,
    requirement: requirement,
    contactIDs: selectedIDs,
    configuration: ResolvedBoardConfigurationSnapshot(
        positionID: target.positionID,
        presentationID: target.presentationID,
        effectiveDepths: target.effectiveDepths.filter {
            selectedIDSet.contains($0.key)
        }
    )
)
```

- [ ] **Step 8: Confirm GREEN and legacy isolation.**

Run:

```bash
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/WorkoutActivityRecordingTests \
  -only-testing:HangTenTests/ContactResolverTests
```

Expected: all tests pass; historical snapshots decode without loading the current board catalog, while every newly recorded board snapshot contains configuration.

- [ ] **Step 9: Commit and push the recording checkpoint.**

```bash
rtk git add \
  HangTen/Models/WorkoutActivityRecording.swift \
  HangTenTests/WorkoutActivityRecordingTests.swift
rtk git commit -m "feat: record immutable board configuration snapshots"
rtk git push
```

**Review checkpoint:** A reviewer inspects the serialized JSON for the medium and depthless cases and confirms the selected presentation—not the default—is the sole source of `modelSHA256`.

---

## Task 6: Prove ODR, cache, staging, and cord audit work for every presentation

**Files:**

- Modify only if a regression fails: `scripts/stage-board-packages.py:216` (model asset collection)
- Modify: `Tools/HangboardPackages/tests/test_board_package_staging.py:83` (model fixture) and `:283` (staging assertions)
- Modify only if a regression fails: `HangTen/Views/BoardModelView.swift:7` (`BoardModelKey`) and `:202` (model store)
- Modify: `HangTenTests/BoardModelTests.swift` (selected-resource regressions)
- Modify: `HangTenTests/BoardPackageStoreTests.swift:516` (`BoardModelKey` identity regression)
- Modify: `Tools/HangboardPackages/src/hangboard_packages/cord_audit.py:31` (snapshot roots), `:75` (`CordAuditReport`), and `:377` (topology discovery)
- Modify: `Tools/HangboardPackages/tests/test_cord_audit.py` (evidence and multi-presentation regressions)
- Modify: `Tools/HangboardPackages/README.md:55` (audit contract)

**Interfaces produced:**

```python
_SNAPSHOT_ROOTS = (
    Path("docs/source-audits/2026-09-13-model-cord-snapshots"),
    Path("docs/source-audits/2026-09-20-hangboards-batch-03-evidence"),
)


@dataclass(frozen=True)
class CordAuditReport:
    model_package_ids: tuple[str, ...]
    model_presentation_ids: tuple[str, ...]
    decisions: Mapping[str, int]


def _model_package_topologies(
    inventory: BoardInventory,
) -> dict[str, dict[str, str | None]]:
    """Return every model presentation topology grouped by package ID."""
```

Presentation report IDs use the unambiguous string `f"{package_id}/{presentation.id}"`. The cord manifest schema remains version 1 and retains exactly one record per package.

- [ ] **Step 1: Add a failing three-presentation staging test.** Add `write_three_model_staging_fixture(repository_root: Path) -> tuple[Path, tuple[Path, ...]]`; it writes deep/medium/shallow descriptors and distinct model bytes under one valid package. Run `stage_board_packages(repository_root, destination)` and assert the base staged package contains all three descriptors and no USDZ, while the package-level ODR tag directory contains exactly all three USDZ paths. All three assets deliberately share the existing package-level tag; do not invent presentation-level tags.

```python
assert sorted(path.relative_to(staged_package).as_posix() for path in staged_package.rglob("*")) == [
    "board.json",
    "deep-descriptor.json",
    "medium-descriptor.json",
    "shallow-descriptor.json",
]
assert sorted(path.name for path in odr_root.rglob("*.usdz")) == [
    "deep.usdz",
    "medium.usdz",
    "shallow.usdz",
]
```

- [ ] **Step 2: Add failing model-cache tests.** Assert two keys with the same board/hash but different presentation IDs are unequal, simultaneous loads do not share an in-flight task, and requesting each model presentation resolves its own package resource. Keep `BoardModelKey`'s exact existing signature:

```swift
struct BoardModelKey: Hashable {
    let boardID: String
    let presentationID: String
    let modelSHA256: String
}

func testCacheIdentityIncludesPresentationEvenWhenHashMatches() {
    let hash = String(repeating: "a", count: 64)
    let deep = BoardModelKey(
        boardID: "fixture.board", presentationID: "deep", modelSHA256: hash
    )
    let shallow = BoardModelKey(
        boardID: "fixture.board", presentationID: "shallow", modelSHA256: hash
    )
    XCTAssertNotEqual(deep, shallow)
    XCTAssertEqual(Set([deep, shallow]).count, 2)
}
```

In `BoardModelTests`, use `private func makeThreePresentationModelFixture() throws -> (store: BoardPackageStore, board: BoardRevision)` and an injected `BoardModelResourceAccess` whose acquire closure records `(presentationID, URL)`. Concurrently load deep and shallow, release both acquisitions, and assert two distinct calls/URLs and the matching descriptor hash on each returned scene.

- [ ] **Step 3: Run staging/cache tests and make only a proven correction.**

Run:

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_board_package_staging.py -q
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/BoardModelTests \
  -only-testing:HangTenTests/BoardPackageStoreTests
```

Expected: the new regressions pass with current staging/cache production code once Tasks 1–2 permit multiple models. If staging fails, preserve the current `model_asset_paths_by_slug` comprehension over **all** model presentations and remove any single-asset indexing exposed by the test. If cache identity fails, construct `BoardModelKey(boardID:presentationID:modelSHA256:)` from the requested presentation at `BoardModelLoader.load`; do not change ODR lease lifetime, load throttling, or scene decoding.

- [ ] **Step 4: Write failing cord-audit multi-presentation tests.** Cover a package whose three presentations all use `pairedLeadCord`, one with a differing topology, and an excluded record where one presentation unexpectedly has suspension. The first succeeds with one package record and reports all three presentation IDs; the latter two fail and name the offending presentation.

Extend the test helper to `def _model_package(package_id: str, *, presentations: tuple[tuple[str, object | None], ...]) -> BoardPackage`. Use this exact matrix:

| Presentations | Manifest record | Expected result |
| --- | --- | --- |
| deep/medium/shallow all paired | represented paired | success; one package ID and three presentation IDs |
| deep paired, medium single, shallow paired | represented paired | `record topology pairedLeadCord does not match fixture.plateau/medium topology singleCord` |
| deep/medium/shallow all `None` | excluded | success |
| deep `None`, medium paired, shallow `None` | excluded | `excluded record requires no suspension at fixture.plateau/medium` |

```python
assert report.to_json() == {
    "modelPackageIDs": ["fixture.plateau"],
    "modelPresentationIDs": [
        "fixture.plateau/deep",
        "fixture.plateau/medium",
        "fixture.plateau/shallow",
    ],
    "decisions": {"represented": 1},
}
```

- [ ] **Step 5: Write failing evidence-root and retention tests.** Accept files below each exact `_SNAPSHOT_ROOTS` entry. Reject prefix lookalikes, absolute/parent paths, symlinks, directories, missing files, hash mismatches, untracked files when a Git repository root is present, and duplicate `snapshotPath` values globally across different records as well as within one record. The old production manifest must continue to load unchanged.

Use helpers `write_snapshot(base: Path, relative_path: str, body: bytes = b"evidence") -> tuple[str, str]` (returns path and SHA-256) and `load_manifest_with_paths(tmp_path: Path, paths: list[str]) -> CordAuditManifest`. Pin these diagnostics:

| Path/state | Expected result/diagnostic |
| --- | --- |
| child of old root | success |
| child of Batch 03 root | success |
| `docs/source-audits/2026-09-20-hangboards-batch-03-evidence-copy/x` | `snapshotPath must remain beneath an approved snapshot root` |
| absolute path or component `..` | `snapshotPath must be a relative retained path` |
| symlink component | `snapshotPath must not contain a symbolic link` |
| directory/missing path | `snapshot path does not name a regular file` |
| wrong digest | `snapshot SHA-256 does not match` |
| untracked file under a discovered Git root | `snapshotPath must name a tracked repository file` |
| same path twice in one or two records | `duplicate snapshotPath in cord audit manifest` |

- [ ] **Step 6: Implement the closed package/multi-presentation audit.** Return a nested topology map for every model presentation. For `represented`, every presentation topology must equal the record topology. For `excluded`, every presentation topology must be `None`. Keep manifest coverage one-to-one with package IDs. Include sorted package/presentation IDs in the report.

```python
def _model_package_topologies(
    inventory: BoardInventory,
) -> dict[str, dict[str, str | None]]:
    result: dict[str, dict[str, str | None]] = {}
    for package in inventory.packages:
        presentations = {
            presentation.id: _suspension_topology(presentation.media.suspension)
            for presentation in package.board.presentations
            if isinstance(presentation.media, PresentationMediaModel)
        }
        if presentations:
            if package.board.id in result:
                raise CordAuditError(
                    f"duplicate model package ID in inventory: {package.board.id}"
                )
            result[package.board.id] = presentations
    return result

for presentation_id, actual in topologies_by_package[package_id].items():
    qualified = f"{package_id}/{presentation_id}"
    if record.decision == "represented" and actual != record.topology:
        raise CordAuditError(
            f"record topology {record.topology} does not match "
            f"{qualified} topology {actual}"
        )
    if record.decision == "excluded" and actual is not None:
        raise CordAuditError(
            f"excluded record requires no suspension at {qualified}"
        )
```

- [ ] **Step 7: Implement the canonical evidence-root allowlist and retention check.** Add `import subprocess`. `_relative_snapshot_path` succeeds only if the normalized path is beneath one of the two exact roots. Resolve beneath the discovered repository root, reject symlinks/non-regular files, verify SHA-256, and when a `.git` root is discovered require `git ls-files --error-unmatch -- <path>` to succeed. Build one global set of snapshot paths while loading the manifest and reject any duplicate before topology validation. Temp-fixture tests that are not inside a Git repository still exercise path/type/hash checks; the dedicated tracking test creates or mocks a Git root explicitly.

```python
def _approved_snapshot_path(candidate: Path) -> bool:
    return any(
        candidate == root or root in candidate.parents
        for root in _SNAPSHOT_ROOTS
    )

def _is_tracked_repository_file(repository_root: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repository_root), "ls-files", "--error-unmatch", "--", relative_path],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0

seen_snapshot_paths: set[str] = set()
for record_index, record in enumerate(records):
    for evidence_index, evidence in enumerate(record.evidence):
        if evidence.snapshot_path in seen_snapshot_paths:
            raise CordAuditError("duplicate snapshotPath in cord audit manifest")
        seen_snapshot_paths.add(evidence.snapshot_path)
        _verify_snapshot(
            evidence,
            manifest_path=path,
            source=f"cord audit manifest records[{record_index}].evidence[{evidence_index}]",
        )
```

- [ ] **Step 8: Update the README contract and confirm GREEN.** State that one record governs all model presentations in a package, all presentation topologies must agree with it, both canonical roots are accepted, and snapshot paths remain globally unique tracked regular files.

Run:

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_cord_audit.py \
  Tools/HangboardPackages/tests/test_board_package_staging.py -q
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/BoardModelTests \
  -only-testing:HangTenTests/BoardPackageStoreTests
```

Expected: all selected tests pass; the unchanged 2026-09-13 manifest validates and a three-presentation represented package produces one decision plus three presentation coverage IDs.

- [ ] **Step 9: Commit and push the delivery/audit checkpoint.** Stage production files only when their focused failing tests required a change.

```bash
rtk git add \
  Tools/HangboardPackages/tests/test_board_package_staging.py \
  HangTenTests/BoardModelTests.swift \
  HangTenTests/BoardPackageStoreTests.swift \
  Tools/HangboardPackages/src/hangboard_packages/cord_audit.py \
  Tools/HangboardPackages/tests/test_cord_audit.py \
  Tools/HangboardPackages/README.md
rtk git add scripts/stage-board-packages.py HangTen/Views/BoardModelView.swift
rtk git commit -m "test: cover multi-presentation board delivery and audits"
rtk git push
```

If neither production file changed, omit the second `git add`; do not create a no-op diff.

**Review checkpoint:** A reviewer confirms one package record covers all model presentations, the two evidence roots are an exact allowlist rather than a broad parent, duplicate paths are rejected across the whole manifest, and existing ODR/cache architecture was not rewritten without a failing test.

---

## Task 7: Run the cross-layer verification gate and publish consumer handoff

**Files:**

- Modify only for checkbox state: `docs/superpowers/plans/2026-09-20-batch-03-configuration-runtime.md`

**Interfaces consumed/produced:** No new runtime interface. This gate proves Tasks 1–6 are ready for the package and experience plans. The handoff must name these frozen public contracts verbatim: `BoardPosition.effectiveDepths`, `BoardRevision.materializedEffectiveDepths`, `ContactRequirement.positionID`, `ResolvedBoardTarget`, `BoardTargetResolution`, `ContactResolver.resolveTarget`, `ResolvedBoardConfigurationSnapshot`, `WorkoutActivitySegmentKey`, and the `resolvedTargets` recorder parameter.

- [ ] **Step 1: Run all affected Python tests.**

```bash
rtk .context/hangboard-packages-venv/bin/python -m pytest \
  Tools/HangboardPackages/tests/test_board_catalog.py \
  Tools/HangboardPackages/tests/test_model_first_packages.py \
  Tools/HangboardPackages/tests/test_board_package_staging.py \
  Tools/HangboardPackages/tests/test_cord_audit.py -q
```

Expected: all selected Python tests pass with no skips introduced by this work.

- [ ] **Step 2: Validate the current package inventory and closed cord manifest.**

```bash
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh audit-cords \
  --root Hangboards \
  --manifest docs/source-audits/2026-09-13-model-hangboard-cord-audit.json
```

Expected: both commands exit 0. Before the package plan appends its six records, the report still covers every current model package and every current model presentation.

- [ ] **Step 3: Run all affected Swift tests.**

```bash
rtk xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/BoardPackageWriterTests \
  -only-testing:HangTenTests/PlanStorageTests \
  -only-testing:HangTenTests/CustomRoutineDraftTests \
  -only-testing:HangTenTests/CustomRoutineStoreTests \
  -only-testing:HangTenTests/ContactResolverTests \
  -only-testing:HangTenTests/WorkoutActivityRecordingTests \
  -only-testing:HangTenTests/BoardModelTests
```

Expected: `** TEST SUCCEEDED **` and zero failures.

- [ ] **Step 4: Build the app and inspect the diff.**

```bash
rtk xcodebuild build \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
rtk git diff --check
rtk git status --short
```

Expected: `** BUILD SUCCEEDED **`, no whitespace errors, and only intended runtime/test/plan files appear.

- [ ] **Step 5: Perform the five-item review-focus audit.** For each item under **Review focus**, link the exact named test(s) that fail before the implementation and pass after it. Reject completion if any item is covered only indirectly.

- [ ] **Step 6: Hand off exact dependent-plan acceptance work.** Tell the package implementer that Tasks 1, 2, and 6 are complete and that package-level cord records must agree with every presentation. Tell the experience implementer that runtime solely owns the requirement codec, draft/store transformations, custom validation, their three unit-test files, and Task 5 recording/revalidation; experience code owns freezing and threading `[WorkoutActivitySegmentKey: ResolvedBoardTarget]`.

After package-plan Task 10 has created `frictitious.port-a-board`, experience plan **Task 8 (final integration)** must add these exact package-backed tests—never earlier—exclusively to `HangTenTests/Batch03WorkoutExperienceIntegrationTests.swift` in `final class Batch03WorkoutExperienceIntegrationTests: XCTestCase`. Package-plan Task 18 is the final package handoff gate.

| Test | Runtime interface exercised | Required assertions |
| --- | --- | --- |
| `testPortDepthlessContactsResolveUniqueAuthoredPositionsWithEmptyEffectiveDepths` | `BoardCatalog.packageStore.board(id:)`, `ContactResolver.resolveTarget(_:step:board:positionID:)` | `jug-outer-rim` resolves uniquely in `outer-upper`; `pinch-body` resolves uniquely in `pinch-side`; each target contains only that contact and has `effectiveDepths == [:]` |
| `testPortAuthoredDepthRequirementsAreRejected` | the same resolver overload with `ContactRequirement.depth == .range(.init(minimum: 10, maximum: 10))` | both explicit Port positions throw `.noMatches`; no depth is synthesized |
| `testPortRecordingPersistsEmptyDepthsAndActualModelIdentity` | `WorkoutActivityRecorder.segments(for:on:stopwatchDurations:selectedHandSide:handPreference:sessionSteps:resolvedTargets:)` | both frozen Port targets serialize `"effectiveDepths":{}`, their authored position, `primary` presentation, contact ID, and `BoardModelMedia.descriptor.modelSHA256` loaded from the actual package |
| `testHistoricalRemovedContactIDsDecodeAndReencodeUnchanged` | `JSONDecoder.decode(ResolvedContactSnapshot.self,from:)` and a sorted-key `JSONEncoder.encode(_:)` round trip that performs no catalog lookup | legacy snapshots for `pocket-30-two-finger-mono`, `blocker-edge-15`, and `blocker-edge-10` each preserve requirement/contact IDs, board/revision/hash, and `configuration == nil` byte-for-canonical-byte after decode/re-encode |

These four tests consume runtime APIs and final package data only. Do not place any of them in `BoardTargetSubstitutionTests.swift`, `WorkoutActivityRecordingTests.swift`, `PlanStorageTests.swift`, `CustomRoutineDraftTests.swift`, or `CustomRoutineStoreTests.swift`.

- [ ] **Step 7: Commit and push the verified plan state if checkbox updates were retained.**

```bash
rtk git add docs/superpowers/plans/2026-09-20-batch-03-configuration-runtime.md
rtk git commit -m "docs: verify batch 03 configuration runtime"
rtk git push
```

**Final review checkpoint:** Request a fresh code review focused on schema parity, fail-closed legacy boundaries, joint resolution, immutable recording, and presentation-aware audit coverage. Address every substantive comment, rerun Steps 1–4, then hand control to the package and experience plans.
