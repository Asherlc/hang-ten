from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from conftest import PRIMARY_PNG_BYTES, load_board_catalog_module


MODEL_BYTES = b"fixed model package bytes"


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
    (package_root / "assets" / "inverted.png").write_bytes(PRIMARY_PNG_BYTES)
    _rewrite(board_path, board)

    package = module.load_board_package(package_root)

    assert [presentation.id for presentation in package.board.presentations] == [
        "primary",
        "inverted",
    ]


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
