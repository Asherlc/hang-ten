from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import re

import pytest
from hangboard_packages.board_catalog import load_board_package

from conftest import (
    PRIMARY_PNG_BYTES,
    load_board_catalog_module,
    multi_presentation_board_document,
)



MODEL_BYTES = b"fixed model package bytes"
_SHARED_VALIDATION_FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "HangTenTests"
    / "Fixtures"
    / "BoardPackageValidationFixtures.json"
)
_RAW_NONFINITE_SENTINEL = "__raw_nonfinite_number_1e999__"


def _dump_shared_json_document(document: object) -> str:
    return json.dumps(document, separators=(",", ":"), sort_keys=False).replace(
        json.dumps(_RAW_NONFINITE_SENTINEL), "1e999"
    )


def _shared_model_parser_parity_fixtures() -> tuple[dict[str, object], ...]:
    fixtures = json.loads(_SHARED_VALIDATION_FIXTURES.read_text(encoding="utf-8"))
    matrix = fixtures["modelParserParity"]
    assert isinstance(matrix, list)
    return tuple(matrix)


def _shared_reusable_model_fixture(name: str) -> dict[str, object]:
    fixtures = json.loads(_SHARED_VALIDATION_FIXTURES.read_text(encoding="utf-8"))
    registry = fixtures["reusableModelFixtures"]
    assert isinstance(registry, dict)
    fixture = registry[name]
    assert isinstance(fixture, dict)
    return fixture


def _apply_shared_json_mutation(document: object, mutation: dict[str, object]) -> None:
    path = mutation["path"]
    assert isinstance(path, list) and path
    parent = document
    for component in path[:-1]:
        assert isinstance(parent, (dict, list))
        parent = parent[component]
    final_component = path[-1]
    operation = mutation["op"]
    if operation == "replace":
        assert isinstance(parent, (dict, list))
        parent[final_component] = copy.deepcopy(mutation["value"])
    elif operation == "remove":
        assert isinstance(parent, list) and isinstance(final_component, int)
        parent.pop(final_component)
    elif operation == "append":
        assert isinstance(parent, (dict, list))
        target = parent[final_component]
        assert isinstance(target, list)
        target.append(copy.deepcopy(mutation["value"]))
    else:
        raise AssertionError(f"unsupported shared fixture operation: {operation}")


def _write_shared_model_parser_parity_package(
    root: Path, fixture: dict[str, object]
) -> Path:
    fixtures = json.loads(_SHARED_VALIDATION_FIXTURES.read_text(encoding="utf-8"))
    reusable_fixture_name = fixture.get("reusableFixture")
    if reusable_fixture_name is None:
        model = fixtures[fixture.get("base", "model")]
    else:
        assert isinstance(reusable_fixture_name, str)
        registry = fixtures["reusableModelFixtures"]
        assert isinstance(registry, dict)
        model = registry[reusable_fixture_name]
    assert isinstance(model, dict)
    board = copy.deepcopy(model["board"])
    descriptor = copy.deepcopy(model["descriptor"])
    assert isinstance(board, dict) and isinstance(descriptor, dict)
    mutations = fixture["mutations"]
    assert isinstance(mutations, list)
    for mutation in mutations:
        assert isinstance(mutation, dict)
        target = mutation["target"]
        assert target in {"board", "descriptor"}
        _apply_shared_json_mutation(board if target == "board" else descriptor, mutation)

    assets = root / "assets"
    assets.mkdir(parents=True)
    model_bytes = base64.b64decode(model["assetBase64"])
    (assets / "primary.usdz").write_bytes(model_bytes)
    for extra_asset in fixture.get("extraAssets", []):
        assert isinstance(extra_asset, dict)
        relative_path = extra_asset["path"]
        assert isinstance(relative_path, str)
        asset_path = root / relative_path
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(base64.b64decode(extra_asset["base64"]))
    board_path = root / "board.json"
    if reusable_fixture_name is not None:
        _restore_reusable_translation_sentinels(board)
        board_json = _json_with_numeric_sentinels(board)
    else:
        board_json = _dump_shared_json_document(board)
    if fixture.get("reorderTwoBranchSuspensionMembers"):
        suspension = board["presentations"][0]["media"]["suspension"]
        canonical = json.dumps(suspension, separators=(",", ":"))
        reordered = {
            key: suspension[key]
            for key in ("anchor", "branches", "canonicalPoses", "passages", "type")
        }
        board_json = board_json.replace(
            '"suspension":' + canonical,
            '"suspension":' + json.dumps(reordered, separators=(",", ":")),
            1,
        )
    if fixture.get("reorderPairedLeadSuspensionMembers"):
        suspension = board["presentations"][0]["media"]["suspension"]
        canonical = json.dumps(suspension, separators=(",", ":"))
        reordered = {
            key: suspension[key]
            for key in ("anchor", "attachments", "passages", "canonicalPoses", "cord", "type")
        }
        board_json = board_json.replace(
            '"suspension":' + canonical,
            '"suspension":' + json.dumps(reordered, separators=(",", ":")),
            1,
        )
    if fixture.get("reorderPairedLeadAnchorMembers"):
        suspension = board["presentations"][0]["media"]["suspension"]
        canonical = json.dumps(suspension, separators=(",", ":"))
        reordered = dict(suspension)
        anchor = suspension["anchor"]
        reordered["anchor"] = {
            key: anchor[key]
            for key in ("visibility", "offsetFromBoardBounds", "provenance")
        }
        board_json = board_json.replace(
            '"suspension":' + canonical,
            '"suspension":' + json.dumps(reordered, separators=(",", ":")),
            1,
        )
    if fixture.get("reorderPairedLeadCordMembers"):
        suspension = board["presentations"][0]["media"]["suspension"]
        canonical = json.dumps(suspension, separators=(",", ":"))
        reordered = dict(suspension)
        cord = suspension["cord"]
        reordered["cord"] = {
            key: cord[key]
            for key in ("radius", "restLength", "material", "provenance")
        }
        board_json = board_json.replace(
            '"suspension":' + canonical,
            '"suspension":' + json.dumps(reordered, separators=(",", ":")),
            1,
        )
    board_path.write_text(board_json, encoding="utf-8")
    (assets / "primary.model.json").write_text(
        _dump_shared_json_document(descriptor), encoding="utf-8"
    )
    if fixture.get("duplicateCanonicalPoseKey"):
        board_path = root / "board.json"
        raw = board_json
        pose = json.dumps(
            board["presentations"][0]["media"]["suspension"]["canonicalPoses"]["primary"],
            separators=(",", ":"),
            sort_keys=False,
        )
        needle = '"canonicalPoses":{"primary":' + pose + "}"
        replacement = '"canonicalPoses":{"primary":' + pose + ',"primary":' + pose + "}"
        if needle in raw:
            raw = raw.replace(needle, replacement, 1)
        else:
            prefix = '"canonicalPoses":{"primary":' + pose + ',"'
            assert prefix in raw
            raw = raw.replace(
                prefix,
                '"canonicalPoses":{"primary":' + pose + ',"primary":' + pose + ',"',
                1,
            )
        board_path.write_text(raw, encoding="utf-8")
    return root


def _physical_contact(contact_id: str, name: str) -> dict[str, object]:
    return {
        "id": contact_id,
        "equipmentObjectID": "primary",
        "name": name,
        "kind": "jug",
        "gripTypes": [],
    }


def _descriptor() -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "coordinateFrame": "hang-ten-board-v1",
        "modelSHA256": hashlib.sha256(MODEL_BYTES).hexdigest(),
        "modelBounds": {"min": [0, 0, 0], "max": [1, 1, 0.1]},
        "nodes": [
            {"nodeID": "Body", "role": "body"},
            {"nodeID": "Left", "role": "contact", "contactID": "hold-left"},
            {"nodeID": "Right", "role": "contact", "contactID": "hold-right"},
        ],
        "contacts": {
            "hold-left": {
                "nodeIDs": ["Left"],
                "facePlaneAABB": {"min": [0.1, 0.2], "max": [0.4, 0.6]},
                "center": [0.25, 0.4],
            },
            "hold-right": {
                "nodeIDs": ["Right"],
                "facePlaneAABB": {"min": [0.6, 0.2], "max": [0.9, 0.6]},
                "center": [0.75, 0.4],
            },
        },
    }


def _reusable_descriptor() -> dict[str, object]:
    return {
        "schemaVersion": 2,
        "coordinateFrame": "hang-ten-board-v1",
        "modelSHA256": hashlib.sha256(MODEL_BYTES).hexdigest(),
        "modelBounds": {"min": [0, 0, 0], "max": [1, 1, 0.1]},
        "nodes": [
            {"nodeID": "UnitBody", "role": "body"},
            {"nodeID": "UnitEdge", "role": "contact", "contactSlotID": "edge"},
        ],
        "contactSlots": {
            "edge": {
                "nodeIDs": ["UnitEdge"],
                "facePlaneAABB": {"min": [0.1, 0.2], "max": [0.4, 0.6]},
                "center": [0.25, 0.4],
            }
        },
    }


def _model_document() -> dict[str, object]:
    return {
        "schemaVersion": 3,
        "id": "fixture.model-first",
        "revisionID": "2026-09-contact-first",
        "manufacturer": "Fixture Maker",
        "name": "Model-first fixture",
        "subtitle": "A parser fixture.",
        "productURL": "https://example.com/model-first",
        "aspectRatio": 2,
        "equipmentObjects": [{"id": "primary"}],
        "presentations": [
            {
                "id": "primary",
                "name": "Primary",
                "aspectRatio": 2,
                "isDefault": True,
                "derivation": {"type": "original"},
                "media": {
                    "type": "model",
                    "assetPath": "assets/primary.usdz",
                    "descriptorPath": "assets/primary.model.json",
                    "display": {
                        "camera": {
                            "type": "orthographic",
                            "viewDirection": [0, 0, -1],
                            "up": [0, 1, 0],
                            "fitPadding": 0.08,
                        }
                    },
                },
            }
        ],
        "contacts": [
            _physical_contact("hold-left", "Left hold"),
            _physical_contact("hold-right", "Right hold"),
        ],
    }


def write_model_package(
    root: Path,
    orientation: dict[str, object] | None = None,
    positions: list[dict[str, object]] | None = None,
    media_overrides: dict[str, object] | None = None,
    *,
    descriptor_version: int = 1,
    instances: list[dict[str, object]] | None = None,
) -> Path:
    document = _model_document()
    if descriptor_version == 2:
        document["equipmentObjects"] = [{"id": "left-unit"}, {"id": "right-unit"}]
        document["contacts"] = [
            {**_physical_contact("edge-left", "Left edge"), "equipmentObjectID": "left-unit"},
            {**_physical_contact("edge-right", "Right edge"), "equipmentObjectID": "right-unit"},
        ]
    elif descriptor_version != 1:
        raise ValueError("descriptor_version must be 1 or 2")
    if orientation is not None:
        document["presentations"][0]["media"]["orientation"] = orientation
    if media_overrides:
        document["presentations"][0]["media"].update(media_overrides)
    if instances is not None:
        document["presentations"][0]["media"]["instances"] = instances
    if positions is not None:
        document["positions"] = positions
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.usdz").write_bytes(MODEL_BYTES)
    (assets / "primary.model.json").write_text(
        json.dumps(_reusable_descriptor() if descriptor_version == 2 else _descriptor()),
        encoding="utf-8",
    )
    (root / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return root


_write_model_package = write_model_package


def _valid_reusable_instances() -> list[dict[str, object]]:
    identity = {
        "translation": [
            "@number:0.000000000@",
            "@number:0.000000000@",
            "@number:0.000000000@",
        ],
        "rotation": [0, 0, 0, 1],
    }
    return [
        {
            "equipmentObjectID": "left-unit",
            "baseTransform": {
                "translation": [
                    "@number:-0.120000000@",
                    "@number:0.000000000@",
                    "@number:0.000000000@",
                ],
                "rotation": [0, 0, 0, 1],
            },
            "contactIDsBySlotID": {"edge": "edge-left"},
            "positionTransforms": {"primary": identity},
        },
        {
            "equipmentObjectID": "right-unit",
            "baseTransform": {
                "translation": [
                    "@number:0.120000000@",
                    "@number:0.000000000@",
                    "@number:0.000000000@",
                ],
                "rotation": [0, 0, 0, 1],
                "reflection": "x",
            },
            "contactIDsBySlotID": {"edge": "edge-right"},
            "positionTransforms": {"primary": identity},
        },
    ]


def _json_with_numeric_sentinels(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True)
    return re.sub(
        r'"@number:(-?(?:0|[1-9][0-9]*)\.[0-9]{9})@"', r"\1", encoded
    )


def _write_reusable_model_package(tmp_path: Path) -> Path:
    document = write_model_package(
        tmp_path, descriptor_version=2, instances=_valid_reusable_instances()
    )
    board_path = document / "board.json"
    board_path.write_text(
        _json_with_numeric_sentinels(json.loads(board_path.read_text())),
        encoding="utf-8",
    )
    return document


def _restore_reusable_translation_sentinels(document: dict[str, object]) -> None:
    media = document["presentations"][0]["media"]
    assert isinstance(media, dict)
    instances = media["instances"]
    assert isinstance(instances, list)
    for instance in instances:
        assert isinstance(instance, dict)
        transforms = [instance["baseTransform"]]
        position_transforms = instance.get("positionTransforms", {})
        assert isinstance(position_transforms, dict)
        transforms.extend(position_transforms.values())
        for transform in transforms:
            assert isinstance(transform, dict)
            translation = transform["translation"]
            assert isinstance(translation, list)
            transform["translation"] = [
                f"@number:{float(component):.9f}@" for component in translation
            ]


def write_v3_model_package(
    root: Path,
    *,
    contacts: tuple[str, ...],
    body_nodes: tuple[str, ...],
) -> Path:
    document = _model_document()
    document["contacts"] = [
        {
            "id": contact_id,
            "equipmentObjectID": "primary",
            "name": contact_id.replace("-", " ").title(),
            "kind": "edge",
            "gripTypes": [],
        }
        for contact_id in contacts
    ]

    descriptor = _descriptor()
    descriptor["nodes"] = sorted([
        *({"nodeID": node_id, "role": "body"} for node_id in body_nodes),
        *(
            {
                "nodeID": f"{contact_id}-node",
                "role": "contact",
                "contactID": contact_id,
            }
            for contact_id in contacts
        ),
    ], key=lambda node: node["nodeID"])
    descriptor["contacts"] = {
        contact_id: {
            "nodeIDs": [f"{contact_id}-node"],
            "facePlaneAABB": {"min": [0.1, 0.2], "max": [0.4, 0.6]},
            "center": [0.25, 0.4],
        }
        for contact_id in contacts
    }

    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.usdz").write_bytes(MODEL_BYTES)
    (assets / "primary.model.json").write_text(
        json.dumps(descriptor), encoding="utf-8"
    )
    (root / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return root


def _rewrite(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def _raster_piece(x: float) -> dict[str, object]:
    return {
        "frame": {"x": x, "y": 0.2, "width": 0.2, "height": 0.4},
        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
    }


def _write_raster_package(root: Path) -> Path:
    document = _model_document()
    presentation = document["presentations"][0]
    presentation["media"] = {
        "type": "raster",
        "assetPath": "assets/primary.png",
        "contactGeometry": {
            "hold-left": [_raster_piece(0.1), _raster_piece(0.35)],
            "hold-right": [_raster_piece(0.7)],
        },
    }
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(root / "board.json", document)
    return root


def _raster_presentation(
    presentation_id: str, asset_path: str, derivation: dict[str, object]
) -> dict[str, object]:
    return {
        "id": presentation_id,
        "name": presentation_id.title(),
        "aspectRatio": 2,
        "isDefault": False,
        "derivation": derivation,
        "media": {
            "type": "raster",
            "assetPath": asset_path,
            "contactGeometry": {
                "hold-left": [_raster_piece(0.1)],
                "hold-right": [_raster_piece(0.7)],
            },
        },
    }



def test_catalog_rejects_unversioned_documents_after_migration() -> None:
    module = load_board_catalog_module()
    document = multi_presentation_board_document()
    document.pop("schemaVersion")

    with pytest.raises(ValueError, match="schemaVersion"):
        module._load_board(document)


def test_v3_model_descriptor_binds_contacts_and_allows_two_bodies(tmp_path):
    package = write_v3_model_package(tmp_path, contacts=("left-edge", "right-edge"), body_nodes=("left-body", "right-body"))
    loaded = load_board_package(package)
    assert loaded.board.revision_id == "2026-09-contact-first"
    assert tuple(contact.id for contact in loaded.board.contacts) == ("left-edge", "right-edge")


def test_v3_reusable_instances_bind_each_contact_slot_to_its_equipment_object(
    tmp_path: Path,
) -> None:
    package = load_board_package(_write_reusable_model_package(tmp_path))

    media = package.board.presentations[0].media
    assert media.instances is not None
    assert [instance.equipment_object_id for instance in media.instances] == [
        "left-unit",
        "right-unit",
    ]
    assert media.instances[0].contact_ids_by_slot_id == {"edge": "edge-left"}
    assert media.instances[1].base_transform.translation == (0.12, 0.0, 0.0)
    assert media.instances[1].base_transform.reflection == "x"
    assert media.instances[1].position_transforms["primary"].reflection is None


def test_v3_reusable_instances_reject_cross_object_slot_mapping(tmp_path: Path) -> None:
    document = _write_reusable_model_package(tmp_path)
    board_path = document / "board.json"
    raw = board_path.read_text()
    changed, count = re.subn(
        r'(\"contactIDsBySlotID\"\s*:\s*\{\s*\"edge\"\s*:\s*)\"edge-left\"',
        r'\1"edge-right"',
        raw,
        count=1,
    )
    assert count == 1
    board_path.write_text(changed)
    with pytest.raises(ValueError, match="equipmentObjectID"):
        load_board_package(document)


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


def test_reusable_instances_reject_non_nine_decimal_position_translation_lexeme(
    tmp_path: Path,
) -> None:
    document = _write_reusable_model_package(tmp_path)
    board_path = document / "board.json"
    raw = board_path.read_text()
    changed, count = re.subn(
        r'("positionTransforms"\s*:\s*\{\s*"primary"\s*:\s*\{[^}]*"translation"\s*:\s*\[)0\.000000000',
        r"\g<1>1e-1",
        raw,
        count=1,
    )
    assert count == 1
    board_path.write_text(changed)

    with pytest.raises(ValueError, match="nine decimal"):
        load_board_package(document)


def test_shared_reusable_fixture_is_accepted_by_python_parser(tmp_path: Path) -> None:
    fixture = _shared_reusable_model_fixture("reusable-valid")
    assert fixture["board"]["id"] == "fixture.reusable-model"

    media = load_board_package(
        _write_shared_model_parser_parity_package(
            tmp_path, {"reusableFixture": "reusable-valid", "mutations": []}
        )
    ).board.presentations[0].media
    assert media.instances is not None
    assert media.instances[1].base_transform.reflection == "x"


@pytest.mark.parametrize(
    ("path", "value", "error"),
    [
        (
            ["presentations", 0, "media", "instances", 0, "baseTransform", "rotation"],
            [0, 0, 0, 2],
            "unit length",
        ),
        (
            [
                "presentations",
                0,
                "media",
                "instances",
                0,
                "positionTransforms",
                "primary",
                "reflection",
            ],
            "x",
            "reflection must be omitted",
        ),
        (
            ["presentations", 0, "media", "instances", 0, "contactIDsBySlotID"],
            {},
            "contactIDsBySlotID",
        ),
        (
            ["presentations", 0, "media", "instances", 1, "contactIDsBySlotID"],
            {"edge": "edge-left"},
                "equipmentObjectID|duplicate",
        ),
        (
            ["presentations", 0, "media", "instances", 1, "positionTransforms"],
            {
                "secondary": {
                    "translation": [0, 0, 0],
                    "rotation": [0, 0, 0, 1],
                }
            },
            "positionTransforms",
        ),
    ],
)
def test_reusable_instances_reject_invalid_transform_or_inventory_contract(
    tmp_path: Path, path: list[object], value: object, error: str
) -> None:
    document = _write_reusable_model_package(tmp_path)
    board_path = document / "board.json"
    board = json.loads(board_path.read_text())
    parent: object = board
    for component in path[:-1]:
        assert isinstance(parent, (dict, list))
        parent = parent[component]
    assert isinstance(parent, (dict, list))
    parent[path[-1]] = value
    _restore_reusable_translation_sentinels(board)
    board_path.write_text(_json_with_numeric_sentinels(board))

    with pytest.raises(ValueError, match=error):
        load_board_package(document)


@pytest.mark.parametrize("legacy_key", ["orientation", "suspension"])
def test_reusable_instances_reject_legacy_pose_mechanisms(
    tmp_path: Path, legacy_key: str
) -> None:
    document = _write_reusable_model_package(tmp_path)
    board_path = document / "board.json"
    board = json.loads(board_path.read_text())
    board["presentations"][0]["media"][legacy_key] = {}
    _restore_reusable_translation_sentinels(board)
    board_path.write_text(_json_with_numeric_sentinels(board))

    with pytest.raises(ValueError, match="instances"):
        load_board_package(document)


@pytest.mark.parametrize("missing_contact", ["left-edge", "right-edge"])
def test_v3_model_descriptor_requires_exact_contact_node_coverage(
    tmp_path: Path, missing_contact: str
) -> None:
    package = write_v3_model_package(
        tmp_path,
        contacts=("left-edge", "right-edge"),
        body_nodes=("left-body", "right-body"),
    )
    descriptor_path = package / "assets" / "primary.model.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["nodes"] = [
        node
        for node in descriptor["nodes"]
        if node.get("contactID") != missing_contact
    ]
    _rewrite(descriptor_path, descriptor)

    with pytest.raises(ValueError, match="node contact IDs must equal physical contacts"):
        load_board_package(package)


def test_v3_model_requires_hash_bound_complete_descriptor(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = _write_model_package(tmp_path / "fixture-model")

    package = module.load_board_package(package_root)

    presentation = package.board.presentations[0]
    assert isinstance(presentation.media, module.PresentationMediaModel)
    assert not hasattr(package.board.contacts[0], "geometry")
    assert not hasattr(package.board.contacts[0], "presentation_id")
    assert presentation.media.asset_path == "assets/primary.usdz"
    assert presentation.media.descriptor_path == "assets/primary.model.json"
    assert presentation.media.suspension is None
    assert package.board.contact_frame("hold-left", "primary") == module.NormalizedFrame(
        0.1, 0.2, 0.3, 0.4
    )
    assert package.board.contact_ids_for_position("primary") == (
        "hold-left",
        "hold-right",
    )

    descriptor_path = package_root / "assets" / "primary.model.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["modelSHA256"] = "0" * 64
    _rewrite(descriptor_path, descriptor)
    with pytest.raises(ValueError, match="SHA-256"):
        module.load_board_package(package_root)


@pytest.mark.parametrize("base,rest_length", [("twoBranchModel", 0.92), ("directedTwoBranchModel", 1.5)])
def test_v3_model_accepts_valid_two_branch_suspension(tmp_path: Path, base: str, rest_length: float) -> None:
    fixture = {"base": base, "mutations": []}
    package_root = _write_shared_model_parser_parity_package(
        tmp_path / "valid-two-branch", fixture
    )

    package = load_board_catalog_module().load_board_package(package_root)
    suspension = package.board.presentations[0].media.suspension
    assert suspension is not None
    assert suspension.__class__.__name__ == "BoardModelTwoBranchSuspension"
    assert len(suspension.passages.left) == 2
    assert len(suspension.passages.right) == 2
    assert len(suspension.branches) == 2
    assert set(suspension.canonical_poses) == {
        "primary", "secondary", "tertiary", "quaternary"
    }
    assert [branch.rest_length for branch in suspension.branches] == [rest_length, rest_length]
    assert all(passage.is_through_bore == (base == "directedTwoBranchModel") for passage in suspension.passages.left + suspension.passages.right)


def test_v3_model_preserves_valid_single_cord_behavior(tmp_path: Path) -> None:
    package_root = _write_shared_model_parser_parity_package(
        tmp_path / "valid-single-cord", {"base": "singleCordModel", "mutations": []}
    )

    package = load_board_catalog_module().load_board_package(package_root)
    suspension = package.board.presentations[0].media.suspension
    assert suspension is not None
    assert suspension.__class__.__name__ == "BoardModelSingleCordSuspension"


def test_v2_model_accepts_valid_paired_lead_cord_suspension(tmp_path: Path) -> None:
    """Catches removal or mis-decoding of the two exterior lead contract."""

    package_root = _write_shared_model_parser_parity_package(
        tmp_path / "valid-paired-lead", {"base": "pairedLeadCordModel", "mutations": []}
    )

    suspension = load_board_catalog_module().load_board_package(
        package_root
    ).board.presentations[0].media.suspension
    assert suspension is not None
    assert suspension.__class__.__name__ == "BoardModelPairedLeadCord"
    assert [attachment.id for attachment in suspension.attachments] == [
        "left-lead", "right-lead"
    ]
    assert suspension.cord.rest_length == 0.8
    assert set(suspension.canonical_poses) == {"primary"}


def test_v2_paired_leads_preserve_ordered_route_contacts(tmp_path: Path) -> None:
    """Catches collapsing an over-lip route back through the board body."""

    package_root = _write_shared_model_parser_parity_package(
        tmp_path / "routed-paired-lead",
        {"base": "pairedLeadCordModel", "mutations": []},
    )

    suspension = load_board_catalog_module().load_board_package(
        package_root
    ).board.presentations[0].media.suspension
    assert [attachment.contact_points_in_model for attachment in suspension.attachments] == [
        ((0.2, 0.5, 0.05), (0.2, 0.45, 0.05)),
        ((0.8, 0.5, 0.05), (0.8, 0.45, 0.05)),
    ]


def test_v2_paired_leads_preserve_distinct_points_when_sharing_node(tmp_path: Path) -> None:
    package_root = _write_shared_model_parser_parity_package(
        tmp_path / "shared-paired-lead-node",
        {
            "base": "pairedLeadCordModel",
            "mutations": [{
                "target": "board",
                "op": "replace",
                "path": ["presentations", 0, "media", "suspension", "attachments", 1, "nodeID"],
                "value": "Body",
            }],
        },
    )

    suspension = load_board_catalog_module().load_board_package(
        package_root
    ).board.presentations[0].media.suspension
    assert suspension is not None
    assert [attachment.id for attachment in suspension.attachments] == ["left-lead", "right-lead"]
    assert [attachment.node_id for attachment in suspension.attachments] == ["Body", "Body"]
    assert [attachment.point_in_model for attachment in suspension.attachments] == [
        (0.2, 0.5, 0.1), (0.8, 0.5, 0.1)
    ]


def test_v2_paired_leads_preserve_pose_specific_mouths(tmp_path: Path) -> None:
    points = {"left-lead": [0.2, 0.45, 0.1], "right-lead": [0.8, 0.45, 0.1]}
    package = _write_shared_model_parser_parity_package(tmp_path, {
        "base": "pairedLeadCordModel", "mutations": [{
            "target": "board", "op": "replace",
            "path": ["presentations", 0, "media", "suspension", "canonicalPoses", "primary", "attachmentPoints"],
            "value": points,
        }],
    })
    suspension = load_board_catalog_module().load_board_package(package).board.presentations[0].media.suspension
    assert dict(suspension.canonical_poses["primary"].attachment_points) == {key: tuple(value) for key, value in points.items()}


def test_v2_paired_leads_use_pose_contact_route_for_length_validation(tmp_path: Path) -> None:
    package = _write_shared_model_parser_parity_package(tmp_path, {
        "base": "pairedLeadCordModel", "mutations": [{
            "target": "board", "op": "replace",
            "path": ["presentations", 0, "media", "suspension", "canonicalPoses", "primary", "cordContactPoints"],
            "value": {"left-lead": [[0.2, 0.6, 0.1]], "right-lead": [[0.8, 0.6, 0.1]]},
        }],
    })
    module = load_board_catalog_module()
    suspension = module.load_board_package(package).board.presentations[0].media.suspension
    assert dict(suspension.canonical_poses["primary"].cord_contact_points) == {
        "left-lead": ((0.2, 0.6, 0.1),), "right-lead": ((0.8, 0.6, 0.1),),
    }
    document = json.loads((package / "board.json").read_text())
    document["presentations"][0]["media"]["suspension"]["canonicalPoses"]["primary"]["cordContactPoints"]["left-lead"] = [[0.2, 5, 0.1]]
    _rewrite(package / "board.json", document)
    with pytest.raises(ValueError, match="restLength"):
        module.load_board_package(package)


def test_shared_matrix_declares_specific_python_error_for_every_fixture() -> None:
    for fixture in _shared_model_parser_parity_fixtures():
        if fixture.get("valid"):
            continue
        expected = fixture.get("pythonError")
        assert isinstance(expected, str) and expected and expected != ".*", fixture["name"]


@pytest.mark.parametrize("routes", [
    {},
    {"left-lead": [[0.2, 0.6, 0.1]]},
    {"left-lead": [], "right-lead": [[0.8, 0.6, 0.1]]},
    {"left-lead": [[0.2, 0.6]], "right-lead": [[0.8, 0.6, 0.1]]},
    {"left-lead": [[0.2, 0.6, 0.1], [0.2, 0.6, 0.1]], "right-lead": [[0.8, 0.6, 0.1]]},
    {"left-lead": [[0.2, 0.5, 0.1]], "right-lead": [[0.8, 0.6, 0.1]]},
    {"unknown": [[0.2, 0.6, 0.1]], "right-lead": [[0.8, 0.6, 0.1]]},
])
def test_v2_rejects_incomplete_or_degenerate_pose_contact_routes(tmp_path: Path, routes: dict) -> None:
    package = _write_shared_model_parser_parity_package(tmp_path, {
        "base": "pairedLeadCordModel", "mutations": [{
            "target": "board", "op": "replace",
            "path": ["presentations", 0, "media", "suspension", "canonicalPoses", "primary", "cordContactPoints"],
            "value": routes,
        }],
    })
    with pytest.raises(ValueError, match="cordContactPoints|distinct"):
        load_board_catalog_module().load_board_package(package)


def test_v2_paired_leads_reject_duplicate_passage_ids(tmp_path: Path) -> None:
    package = _write_shared_model_parser_parity_package(tmp_path, {
        "base": "pairedLeadCordModel", "mutations": [{
            "target": "board", "op": "replace",
            "path": ["presentations", 0, "media", "suspension", "passages", "right", 0, "id"],
            "value": "left-lip",
        }],
    })
    with pytest.raises(ValueError, match="passage IDs must be distinct"):
        load_board_catalog_module().load_board_package(package)


def test_two_branch_order_and_segment_regressions_are_specific(tmp_path: Path) -> None:
    fixtures = {
        fixture["name"]: fixture
        for fixture in _shared_model_parser_parity_fixtures()
    }
    module = load_board_catalog_module()
    for name in ("two-branch-suspension-member-order", "two-branch-directed-route-too-short"):
        fixture = fixtures[name]
        package_root = _write_shared_model_parser_parity_package(
            tmp_path / name, fixture
        )
        with pytest.raises(ValueError, match=fixture["pythonError"]):
            module.load_board_package(package_root)


def test_two_branch_declared_member_order_loads_without_sorting(tmp_path: Path) -> None:
    fixture: dict[str, object] = {
        "base": "twoBranchModel",
        "mutations": [],
    }
    package_root = _write_shared_model_parser_parity_package(tmp_path, fixture)
    board_json = (package_root / "board.json").read_text(encoding="utf-8")
    assert '"suspension":{"type":"twoBranchCord","passages":' in board_json

    package = load_board_catalog_module().load_board_package(package_root)
    assert package.board.presentations[0].media.suspension.__class__.__name__ == "BoardModelTwoBranchSuspension"


@pytest.mark.parametrize(
    "fixture",
    tuple(
        fixture
        for fixture in _shared_model_parser_parity_fixtures()
        if not fixture.get("valid")
    ),
    ids=lambda fixture: str(fixture["name"]),
)
def test_v3_model_rejects_shared_cross_parser_malformed_fixture_matrix(
    tmp_path: Path, fixture: dict[str, object]
) -> None:
    """Catches a parser accepting a model document rejected by the shared matrix."""

    assert fixture["pythonException"] == "ValueError"
    assert fixture["swiftError"] in {"invalidPackage", "malformedJSON"}
    module = load_board_catalog_module()
    package_root = _write_shared_model_parser_parity_package(
        tmp_path / str(fixture["name"]), fixture
    )

    with pytest.raises(ValueError, match=str(fixture["pythonError"])):
        module.load_board_package(package_root)


def test_v3_raster_owns_geometry_and_unions_hold_frame(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(
        _write_raster_package(tmp_path / "fixture-raster")
    )

    presentation = package.board.presentations[0]
    assert isinstance(presentation.media, module.PresentationMediaRaster)
    assert set(presentation.media.contact_geometry) == {"hold-left", "hold-right"}
    assert package.board.contact_frame("hold-left", "primary") == module.NormalizedFrame(
        0.1, 0.2, 0.45, 0.4
    )


def test_v3_rejects_original_model_plus_original_raster_fallback(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = _write_model_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["presentations"].append(
        _raster_presentation("fallback", "assets/fallback.png", {"type": "original"})
    )
    (package_root / "assets" / "fallback.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="model and raster"):
        module.load_board_package(package_root)


def test_v3_rejects_raster_derivation_from_model_presentation(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = _write_model_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["presentations"].append(
        _raster_presentation(
            "fallback",
            "assets/fallback.png",
            {
                "type": "derived",
                "sourcePresentationID": "primary",
                "isInverted": True,
            },
        )
    )
    (package_root / "assets" / "fallback.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="derived.*raster.*raster"):
        module.load_board_package(package_root)


def test_v3_preserves_raster_only_derived_presentations(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    derived = _raster_presentation(
            "inverted",
            "assets/inverted.png",
            {
                "type": "derived",
                "sourcePresentationID": "primary",
                "isInverted": True,
            },
        )
    derived["media"]["contactGeometry"] = json.loads(
        json.dumps(board["presentations"][0]["media"]["contactGeometry"])
    )
    board["presentations"].append(derived)
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    package = module.load_board_package(package_root)

    assert [presentation.id for presentation in package.board.presentations] == [
        "primary",
        "inverted",
    ]


def test_v3_raster_originals_exactly_partition_physical_contacts(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["presentations"].append(
        _raster_presentation("other", "assets/other.png", {"type": "original"})
    )
    (package_root / "assets" / "other.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="original.*exactly once"):
        module.load_board_package(package_root)


def test_v3_raster_rejects_hold_owned_only_by_derived_media(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["presentations"].append(
        _raster_presentation(
            "inverted",
            "assets/inverted.png",
            {
                "type": "derived",
                "sourcePresentationID": "primary",
                "isInverted": True,
            },
        )
    )
    del board["presentations"][0]["media"]["contactGeometry"]["hold-left"]
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="original.*exactly once"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda geometry: geometry["hold-left"].reverse(),
        lambda geometry: geometry.__setitem__(
            "hold-left",
            [
                dict(reversed(list(geometry["hold-left"][0].items()))),
                geometry["hold-left"][1],
            ],
        ),
        lambda geometry: geometry.__setitem__(
            "hold-left", [_raster_piece(0.2)]
        ),
    ],
)
def test_v3_derived_raster_geometry_must_exactly_equal_source(
    tmp_path: Path, mutation
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    source_geometry = board["presentations"][0]["media"]["contactGeometry"]
    derived_geometry = json.loads(json.dumps(source_geometry))
    mutation(derived_geometry)
    board["presentations"].append(
        {
            **_raster_presentation(
                "inverted",
                "assets/inverted.png",
                {
                    "type": "derived",
                    "sourcePresentationID": "primary",
                    "isInverted": True,
                },
            ),
            "media": {
                "type": "raster",
                "assetPath": "assets/inverted.png",
                "contactGeometry": derived_geometry,
            },
        }
    )
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="exactly equal its source geometry"):
        module.load_board_package(package_root)


def test_v3_derived_raster_geometry_preserves_numeric_scalar_types(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    source_geometry = board["presentations"][0]["media"]["contactGeometry"]
    source_geometry["hold-left"][0]["shape"]["cornerRadiusFraction"] = 0.0
    derived_geometry = json.loads(json.dumps(source_geometry))
    derived_geometry["hold-left"][0]["shape"]["cornerRadiusFraction"] = 0
    derived = _raster_presentation(
        "inverted",
        "assets/inverted.png",
        {
            "type": "derived",
            "sourcePresentationID": "primary",
            "isInverted": True,
        },
    )
    derived["media"]["contactGeometry"] = derived_geometry
    board["presentations"].append(derived)
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="exactly equal its source geometry"):
        module.load_board_package(package_root)


def test_v3_derived_raster_geometry_preserves_path_command_order(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    source_geometry = board["presentations"][0]["media"]["contactGeometry"]
    source_geometry["hold-left"] = [{
        "frame": {"x": 0.1, "y": 0.2, "width": 0.2, "height": 0.4},
        "shape": {
            "type": "path",
            "commands": [
                {"command": "move", "to": [0, 0]},
                {"command": "line", "to": [1, 0]},
                {"command": "line", "to": [1, 1]},
                {"command": "line", "to": [0, 1]},
                {"command": "close"},
            ],
        },
    }]
    derived_geometry = json.loads(json.dumps(source_geometry))
    derived_geometry["hold-left"][0]["shape"]["commands"] = [
        {"command": "move", "to": [0, 0]},
        {"command": "line", "to": [0, 1]},
        {"command": "line", "to": [1, 1]},
        {"command": "line", "to": [1, 0]},
        {"command": "close"},
    ]
    derived = _raster_presentation(
        "inverted",
        "assets/inverted.png",
        {
            "type": "derived",
            "sourcePresentationID": "primary",
            "isInverted": True,
        },
    )
    derived["media"]["contactGeometry"] = derived_geometry
    board["presentations"].append(derived)
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="exactly equal its source geometry"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda root, board, descriptor: (root / "assets" / "fallback.png").write_bytes(
                PRIMARY_PNG_BYTES
            ),
            "undeclared presentation asset",
        ),
        (
            lambda root, board, descriptor: board["presentations"][0]["media"].__setitem__(
                "descriptorPath", "assets/../escaped.model.json"
            ),
            "descriptorPath",
        ),
        (
            lambda root, board, descriptor: descriptor["contacts"].pop("hold-right"),
            "contacts",
        ),
        (
            lambda root, board, descriptor: descriptor["nodes"][0].__setitem__(
                "role", "attachment"
            ),
            "at least one body",
        ),
        (
            lambda root, board, descriptor: board["presentations"][0].__setitem__(
                "derivation",
                {
                    "type": "derived",
                    "sourcePresentationID": "primary",
                    "isInverted": True,
                },
            ),
            "model.*derived",
        ),
        (
            lambda root, board, descriptor: board["contacts"][0].__setitem__(
                "geometry", [_raster_piece(0.1)]
            ),
            "unknown keys",
        ),
    ],
)
def test_v3_model_rejects_mixed_or_incomplete_package_shapes(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = _write_model_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    descriptor_path = package_root / "assets" / "primary.model.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    mutation(package_root, board, descriptor)
    _rewrite(board_path, board)
    _rewrite(descriptor_path, descriptor)

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda board: board["presentations"][0].__setitem__("assetPath", "assets/old.png"),
            r"presentations\[0\] has unknown keys",
        ),
        (
            lambda board: board["presentations"][0]["media"].__setitem__(
                "descriptorPath", "assets/extra.model.json"
            ),
            r"presentations\[0\]\.media has unknown keys",
        ),
        (
            lambda board: board["presentations"][0]["media"].__setitem__(
                "display", {"camera": {}}
            ),
            r"presentations\[0\]\.media has unknown keys",
        ),
        (
            lambda board: board["presentations"][0]["media"].__setitem__(
                "type", "video"
            ),
            "type must be raster or model",
        ),
    ],
)
def test_v3_tagged_union_rejects_fields_outside_their_variant(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    mutation(board)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda geometry: geometry.pop("hold-right"),
        lambda geometry: geometry.__setitem__("extra", [_raster_piece(0.7)]),
        lambda geometry: geometry.__setitem__("hold-left", []),
    ],
)
def test_v3_raster_requires_exact_nonempty_logical_hold_ownership(
    tmp_path: Path, mutation
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    geometry = board["presentations"][0]["media"]["contactGeometry"]
    mutation(geometry)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="contactGeometry"):
        module.load_board_package(package_root)


def test_v3_descriptor_rejects_finite_bounds_whose_span_overflows(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = _write_model_package(tmp_path / "fixture-model")
    descriptor_path = package_root / "assets" / "primary.model.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["modelBounds"] = {
        "min": [-1e308, -1e308, 0],
        "max": [1e308, 1e308, 0.1],
    }
    _rewrite(descriptor_path, descriptor)

    with pytest.raises(ValueError, match="finite"):
        module.load_board_package(package_root)
