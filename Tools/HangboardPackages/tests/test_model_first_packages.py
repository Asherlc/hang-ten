from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path

import pytest

from conftest import (
    PRIMARY_PNG_BYTES,
    load_board_catalog_module,
    multi_presentation_board_document,
)


def _load_migration_module():
    import importlib.util

    path = Path(__file__).parents[1] / "scripts" / "migrate_to_schema_v2.py"
    spec = importlib.util.spec_from_file_location("migrate_to_schema_v2", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    model = fixtures[fixture.get("base", "model")]
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
    suspension = board["presentations"][0]["media"].get("suspension")
    if fixture.get("reorderTwoBranchSuspensionMembers"):
        assert isinstance(suspension, dict)
        board["presentations"][0]["media"]["suspension"] = {
            key: suspension[key]
            for key in ("anchor", "branches", "canonicalPoses", "passages", "type")
        }
        suspension = board["presentations"][0]["media"]["suspension"]
    if fixture.get("reorderTwoBranchPassageMembers"):
        assert isinstance(suspension, dict)
        passages = suspension["passages"]
        assert isinstance(passages, dict)
        left = passages["left"]
        assert isinstance(left, list) and isinstance(left[0], dict)
        left[0] = {
            key: left[0][key]
            for key in ("nodeID", "id", "pointInModel", "provenance")
        }
    if fixture.get("reorderTwoBranchBranchMembers"):
        assert isinstance(suspension, dict)
        branches = suspension["branches"]
        assert isinstance(branches, list) and isinstance(branches[0], dict)
        branches[0] = {
            key: branches[0][key]
            for key in ("passageIDs", "id", "restLength", "radius", "material", "provenance")
        }
    if fixture.get("reorderTwoBranchPoseMembers"):
        assert isinstance(suspension, dict)
        poses = suspension["canonicalPoses"]
        assert isinstance(poses, dict) and isinstance(poses["primary"], dict)
        poses["primary"] = {
            key: poses["primary"][key]
            for key in ("translation", "rotation", "camera")
        }
    board_json = _dump_shared_json_document(board)
    raw_json_replacement = fixture.get("rawJSONReplacement")
    if raw_json_replacement is not None:
        assert isinstance(raw_json_replacement, dict)
        original = raw_json_replacement["from"]
        replacement = raw_json_replacement["to"]
        assert isinstance(original, str) and isinstance(replacement, str)
        assert board_json.count(original) == 1
        board_json = board_json.replace(original, replacement, 1)
    duplicate_member_key = fixture.get("duplicateTwoBranchMemberKey")
    if duplicate_member_key == "passageID":
        board_json = board_json.replace(
            '"id":"left-top","nodeID"',
            '"id":"left-top","id":"left-top","nodeID"',
            1,
        )
    elif duplicate_member_key == "branchID":
        board_json = board_json.replace(
            '"id":"left-branch","passageIDs"',
            '"id":"left-branch","id":"left-branch","passageIDs"',
            1,
        )
    elif duplicate_member_key is not None:
        raise AssertionError(
            f"unsupported two-branch duplicate member key: {duplicate_member_key}"
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


def _logical_hold(hold_id: str, name: str) -> dict[str, object]:
    return {"id": hold_id, "name": name, "kind": "jug"}


def _descriptor() -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "coordinateFrame": "hang-ten-board-v1",
        "modelSHA256": hashlib.sha256(MODEL_BYTES).hexdigest(),
        "modelBounds": {"min": [0, 0, 0], "max": [1, 1, 0.1]},
        "nodes": [
            {"nodeID": "Body", "role": "body"},
            {"nodeID": "Left", "role": "hold", "holdID": "hold-left"},
            {"nodeID": "Right", "role": "hold", "holdID": "hold-right"},
        ],
        "holds": {
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


def _model_document() -> dict[str, object]:
    return {
        "schemaVersion": 2,
        "id": "fixture.model-first",
        "manufacturer": "Fixture Maker",
        "name": "Model-first fixture",
        "subtitle": "A parser fixture.",
        "productURL": "https://example.com/model-first",
        "aspectRatio": 2,
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
        "holds": [
            _logical_hold("hold-left", "Left hold"),
            _logical_hold("hold-right", "Right hold"),
        ],
    }


def _write_model_package(root: Path) -> Path:
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.usdz").write_bytes(MODEL_BYTES)
    (assets / "primary.model.json").write_text(
        json.dumps(_descriptor()), encoding="utf-8"
    )
    (root / "board.json").write_text(
        json.dumps(_model_document()), encoding="utf-8"
    )
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
        "holdGeometry": {
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
            "holdGeometry": {
                "hold-left": [_raster_piece(0.1)],
                "hold-right": [_raster_piece(0.7)],
            },
        },
    }


def test_migrate_v1_raster_moves_only_geometry_and_presentation_ownership() -> None:
    before = {
        "id": "fixture.board",
        "manufacturer": "Fixture Maker",
        "name": "Fixture Board",
        "subtitle": "A parser fixture.",
        "productURL": "https://example.com/fixture",
        "aspectRatio": 2,
        "presentations": [
            {
                "id": "primary",
                "name": "Primary",
                "assetPath": "assets/primary.png",
                "aspectRatio": 2,
                "default": True,
            },
            {
                "id": "inverted",
                "name": "Inverted",
                "assetPath": "assets/inverted.png",
                "aspectRatio": 2,
                "default": False,
                "sourcePresentationID": "primary",
                "isInverted": True,
            },
        ],
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
                "presentationID": "primary",
                "geometry": [_raster_piece(0.1)],
            }
        ],
    }

    after = _load_migration_module().migrate_document(before)

    assert after["schemaVersion"] == 2
    assert after["presentations"][0]["isDefault"] is True
    assert "default" not in after["presentations"][0]
    assert "geometry" not in after["holds"][0]
    assert "presentationID" not in after["holds"][0]
    assert (
        after["presentations"][0]["media"]["holdGeometry"]["hold-left"]
        == before["holds"][0]["geometry"]
    )
    assert after["presentations"][0]["derivation"] == {"type": "original"}
    assert after["presentations"][1]["derivation"] == {
        "type": "derived",
        "sourcePresentationID": "primary",
        "isInverted": True,
    }
    assert after["presentations"][1]["media"]["holdGeometry"] == {
        "hold-left": before["holds"][0]["geometry"]
    }
    assert _load_migration_module().migrate_document(after) == after


def test_migrate_v1_rejects_unknown_ownership_and_non_raster_media() -> None:
    module = _load_migration_module()
    document = {
        "id": "fixture.board",
        "manufacturer": "Fixture Maker",
        "name": "Fixture Board",
        "subtitle": "A parser fixture.",
        "productURL": "https://example.com/fixture",
        "aspectRatio": 2,
        "presentations": [
            {
                "id": "primary",
                "name": "Primary",
                "assetPath": "assets/primary.usdz",
                "aspectRatio": 2,
                "default": True,
            }
        ],
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
                "presentationID": "primary",
                "geometry": [_raster_piece(0.1)],
            }
        ],
    }

    with pytest.raises(ValueError, match="PNG"):
        module.migrate_document(document)


def test_migrate_v1_preserves_disjoint_multi_presentation_hold_ownership() -> None:
    after = _load_migration_module().migrate_document(
        multi_presentation_board_document()
    )

    assert [
        sorted(presentation["media"]["holdGeometry"])
        for presentation in after["presentations"]
    ] == [["hold-left"], ["hold-right"]]


def test_migrate_v1_rejects_unknown_presentation_members() -> None:
    document = {
        "id": "fixture.board",
        "manufacturer": "Fixture Maker",
        "name": "Fixture Board",
        "subtitle": "A parser fixture.",
        "productURL": "https://example.com/fixture",
        "aspectRatio": 2,
        "presentations": [{
            "id": "primary",
            "name": "Primary",
            "assetPath": "assets/primary.png",
            "aspectRatio": 2,
            "default": True,
        }],
        "holds": [{
            "id": "hold-left",
            "name": "Left hold",
            "kind": "jug",
            "presentationID": "primary",
            "geometry": [_raster_piece(0.1)],
        }],
    }
    document["presentations"][0]["extensionScalar"] = "retain-or-reject"

    with pytest.raises(ValueError, match="unknown keys.*extensionScalar"):
        _load_migration_module().migrate_document(document)


def test_catalog_rejects_unversioned_documents_after_migration() -> None:
    module = _load_migration_module()
    document = multi_presentation_board_document()
    document.pop("schemaVersion")

    with pytest.raises(ValueError, match="schemaVersion"):
        module.board_catalog._load_board(document)


def test_v2_model_requires_hash_bound_complete_descriptor(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = _write_model_package(tmp_path / "fixture-model")

    package = module.load_board_package(package_root)

    presentation = package.board.presentations[0]
    assert isinstance(presentation.media, module.PresentationMediaModel)
    assert not hasattr(package.board.holds[0], "geometry")
    assert not hasattr(package.board.holds[0], "presentation_id")
    assert presentation.media.asset_path == "assets/primary.usdz"
    assert presentation.media.descriptor_path == "assets/primary.model.json"
    assert presentation.media.suspension is None
    assert package.board.hold_frame("hold-left", "primary") == module.NormalizedFrame(
        0.1, 0.2, 0.3, 0.4
    )
    assert package.board.hold_ids_for_position("primary") == (
        "hold-left",
        "hold-right",
    )

    descriptor_path = package_root / "assets" / "primary.model.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["modelSHA256"] = "0" * 64
    _rewrite(descriptor_path, descriptor)
    with pytest.raises(ValueError, match="SHA-256"):
        module.load_board_package(package_root)


def test_v2_model_accepts_valid_two_branch_suspension(tmp_path: Path) -> None:
    fixture = {"base": "twoBranchModel", "mutations": []}
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


def test_v2_model_preserves_valid_single_cord_behavior(tmp_path: Path) -> None:
    package_root = _write_shared_model_parser_parity_package(
        tmp_path / "valid-single-cord", {"base": "singleCordModel", "mutations": []}
    )

    package = load_board_catalog_module().load_board_package(package_root)
    suspension = package.board.presentations[0].media.suspension
    assert suspension is not None
    assert suspension.__class__.__name__ == "BoardModelSingleCordSuspension"


def test_shared_matrix_declares_specific_python_error_for_every_fixture() -> None:
    for fixture in _shared_model_parser_parity_fixtures():
        expected = fixture.get("pythonError")
        assert isinstance(expected, str) and expected and expected != ".*", fixture["name"]


def test_two_branch_order_and_segment_regressions_are_specific(tmp_path: Path) -> None:
    fixtures = {
        fixture["name"]: fixture
        for fixture in _shared_model_parser_parity_fixtures()
    }
    module = load_board_catalog_module()
    for name in ("two-branch-suspension-member-order", "two-branch-passage-segment-too-short"):
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
    _shared_model_parser_parity_fixtures(),
    ids=lambda fixture: str(fixture["name"]),
)
def test_v2_model_rejects_shared_cross_parser_malformed_fixture_matrix(
    tmp_path: Path, fixture: dict[str, object]
) -> None:
    """Catches a parser accepting a model document rejected by the shared matrix."""

    assert fixture["pythonException"] == "ValueError"
    assert fixture["swiftError"] in {"invalidPackage", "malformedJSON"}
    module = load_board_catalog_module()
    package_root = _write_shared_model_parser_parity_package(
        tmp_path / str(fixture["name"]), fixture
    )

    if raw_json_replacement := fixture.get("rawJSONReplacement"):
        assert isinstance(raw_json_replacement, dict)
        board_json = (package_root / "board.json").read_text(encoding="utf-8")
        assert raw_json_replacement["from"] not in board_json
        assert board_json.count(str(raw_json_replacement["to"])) == 1

    with pytest.raises(ValueError, match=str(fixture["pythonError"])):
        module.load_board_package(package_root)


def test_v2_raster_owns_geometry_and_unions_hold_frame(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(
        _write_raster_package(tmp_path / "fixture-raster")
    )

    presentation = package.board.presentations[0]
    assert isinstance(presentation.media, module.PresentationMediaRaster)
    assert set(presentation.media.hold_geometry) == {"hold-left", "hold-right"}
    assert package.board.hold_frame("hold-left", "primary") == module.NormalizedFrame(
        0.1, 0.2, 0.45, 0.4
    )


def test_v2_rejects_original_model_plus_original_raster_fallback(
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


def test_v2_rejects_raster_derivation_from_model_presentation(
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


def test_v2_preserves_raster_only_derived_presentations(tmp_path: Path) -> None:
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
    derived["media"]["holdGeometry"] = json.loads(
        json.dumps(board["presentations"][0]["media"]["holdGeometry"])
    )
    board["presentations"].append(derived)
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    package = module.load_board_package(package_root)

    assert [presentation.id for presentation in package.board.presentations] == [
        "primary",
        "inverted",
    ]


def test_v2_raster_originals_exactly_partition_logical_holds(tmp_path: Path) -> None:
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


def test_v2_raster_rejects_hold_owned_only_by_derived_media(tmp_path: Path) -> None:
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
    del board["presentations"][0]["media"]["holdGeometry"]["hold-left"]
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
def test_v2_derived_raster_geometry_must_exactly_equal_source(
    tmp_path: Path, mutation
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    source_geometry = board["presentations"][0]["media"]["holdGeometry"]
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
                "holdGeometry": derived_geometry,
            },
        }
    )
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="exactly equal its source geometry"):
        module.load_board_package(package_root)


def test_v2_derived_raster_geometry_preserves_numeric_scalar_types(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    source_geometry = board["presentations"][0]["media"]["holdGeometry"]
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
    derived["media"]["holdGeometry"] = derived_geometry
    board["presentations"].append(derived)
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="exactly equal its source geometry"):
        module.load_board_package(package_root)


def test_v2_derived_raster_geometry_preserves_path_command_order(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    source_geometry = board["presentations"][0]["media"]["holdGeometry"]
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
    derived["media"]["holdGeometry"] = derived_geometry
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
            lambda root, board, descriptor: descriptor["holds"].pop("hold-right"),
            "holds",
        ),
        (
            lambda root, board, descriptor: descriptor["nodes"].append(
                {"nodeID": "Extra", "role": "body"}
            ),
            "body",
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
            lambda root, board, descriptor: board["holds"][0].__setitem__(
                "geometry", [_raster_piece(0.1)]
            ),
            "unknown keys",
        ),
    ],
)
def test_v2_model_rejects_mixed_or_incomplete_package_shapes(
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
def test_v2_tagged_union_rejects_fields_outside_their_variant(
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
def test_v2_raster_requires_exact_nonempty_logical_hold_ownership(
    tmp_path: Path, mutation
) -> None:
    module = load_board_catalog_module()
    package_root = _write_raster_package(tmp_path / "fixture-raster")
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    geometry = board["presentations"][0]["media"]["holdGeometry"]
    mutation(geometry)
    _rewrite(board_path, board)

    with pytest.raises(ValueError, match="holdGeometry"):
        module.load_board_package(package_root)


def test_v2_descriptor_rejects_finite_bounds_whose_span_overflows(
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
