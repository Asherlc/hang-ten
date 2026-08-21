from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest

from conftest import (
    ALTERNATE_PRIMARY_PNG_BYTES,
    PRIMARY_PNG_BYTES,
    board_document,
    load_board_catalog_module,
    write_board_package,
    write_multi_presentation_board_package,
    write_primary_only_draft,
)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(chunk_type: bytes, body: bytes = b"") -> bytes:
    return (
        struct.pack(">I", len(body))
        + chunk_type
        + body
        + struct.pack(">I", zlib.crc32(chunk_type + body) & 0xFFFFFFFF)
    )


def _png_without_idat() -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return _PNG_SIGNATURE + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IEND")


def test_discovery_reads_direct_child_packages_without_a_catalog_and_sorts_them(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    write_board_package(
        tmp_path / "zeta-model",
        board_id="zeta.board",
        manufacturer="Zeta",
        name="Model",
    )
    write_board_package(
        tmp_path / "alpha-zulu",
        board_id="alpha.zulu",
        manufacturer="Alpha",
        name="Zulu",
    )
    write_board_package(
        tmp_path / "alpha-alpha-b",
        board_id="alpha.b",
        manufacturer="Alpha",
        name="Alpha",
    )
    write_board_package(
        tmp_path / "alpha-alpha-a",
        board_id="alpha.a",
        manufacturer="Alpha",
        name="Alpha",
    )
    draft = write_primary_only_draft(tmp_path / "draft-model")

    inventory = module.discover_board_packages(tmp_path)

    assert [package.board.id for package in inventory.packages] == [
        "alpha.a",
        "alpha.b",
        "alpha.zulu",
        "zeta.board",
    ]
    assert [package.root.name for package in inventory.packages] == [
        "alpha-alpha-a",
        "alpha-alpha-b",
        "alpha-zulu",
        "zeta-model",
    ]
    assert inventory.drafts == (draft.resolve(),)
    assert not (tmp_path / "catalog.json").exists()


def test_final_inventory_rejects_a_primary_only_draft(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    write_primary_only_draft(tmp_path / "draft-model")

    with pytest.raises(ValueError, match="missing board.json"):
        module.discover_board_packages(tmp_path, require_complete_inventory=True)


def test_discovery_rejects_duplicate_board_ids(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    write_board_package(tmp_path / "first-model", board_id="duplicate.board")
    write_board_package(tmp_path / "second-model", board_id="duplicate.board")

    with pytest.raises(ValueError, match="duplicate board id: duplicate.board"):
        module.discover_board_packages(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda root: (root / "assets" / "primary.png").unlink(), "primary.png"),
        (lambda root: (root / "semantics.json").write_text("{}"), "unknown package entry"),
        (
            lambda root: (root / "assets" / "extra.png").write_bytes(b"extra"),
            "undeclared presentation asset",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(b"not a png"),
            "must be a PNG image",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(
                PRIMARY_PNG_BYTES[:-1] + bytes([PRIMARY_PNG_BYTES[-1] ^ 0xFF])
            ),
            "corrupt chunk checksum",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(_png_without_idat()),
            "must contain image data",
        ),
        (
            lambda root: (root / "assets" / "primary.png").write_bytes(
                PRIMARY_PNG_BYTES + b"trailing"
            ),
            "trailing data after IEND",
        ),
    ],
)
def test_completed_package_requires_the_exact_finished_shape(
    tmp_path: Path,
    mutation,
    message: str,
) -> None:
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "fixture-model")
    mutation(package)

    with pytest.raises(ValueError, match=message):
        module.discover_board_packages(tmp_path)


def test_discovery_rejects_malformed_completed_package(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "fixture-model")
    (package / "board.json").write_text("{ malformed", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        module.discover_board_packages(tmp_path)


def test_discovery_rejects_symlinked_direct_children_and_members(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    outside = write_board_package(tmp_path / "outside")
    root = tmp_path / "Hangboards"
    root.mkdir()
    (root / "linked-model").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        module.discover_board_packages(root)

    (root / "linked-model").unlink()
    package = write_board_package(root / "fixture-model")
    primary = package / "assets" / "primary.png"
    primary.unlink()
    primary.symlink_to(outside / "assets" / "primary.png")

    with pytest.raises(ValueError, match="symlink"):
        module.discover_board_packages(root)


def test_package_loader_consumes_embedded_hold_geometry(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"].append(
        {
            "frame": {"x": 0.4, "y": 0.1, "width": 0.1, "height": 0.2},
            "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
        }
    )
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)
    hold = package.board.holds[0]

    assert len(hold.geometry) == 2
    assert (hold.frame.x, hold.frame.y, hold.frame.width, hold.frame.height) == pytest.approx(
        (0.1, 0.1, 0.4, 0.4)
    )
    assert package.board.presentation_asset_path == "assets/primary.png"


def test_schema_v1_exposes_an_implicit_primary_presentation(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document.pop("presentation")
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")
    package = module.load_board_package(package_root)

    assert package.board.presentations == (
        module.BoardPresentation(
            id="primary",
            name="Primary",
            asset_path="assets/primary.png",
            aspect_ratio=2,
            is_default=True,
        ),
    )
    assert {hold.presentation_id for hold in package.board.holds} == {"primary"}


def test_schema_v2_loads_declared_presentations_and_scoped_holds(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(
        write_multi_presentation_board_package(tmp_path / "fixture-model")
    )

    assert package.board.presentations == (
        module.BoardPresentation("front", "Front", "assets/primary.png", 2, True),
        module.BoardPresentation("back", "Back", "assets/back.png", 2, False),
    )
    assert [(hold.id, hold.presentation_id) for hold in package.board.holds] == [
        ("hold-left", "front"),
        ("hold-right", "back"),
    ]
    assert package.board.presentation_asset_path == "assets/primary.png"


def test_schema_v2_rejects_a_declared_image_with_a_mismatched_aspect_ratio(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    (package_root / "assets" / "back.png").write_bytes(ALTERNATE_PRIMARY_PNG_BYTES)

    with pytest.raises(ValueError, match="aspectRatio.*within 0.1%"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document["presentations"].__setitem__(
                1,
                {
                    **document["presentations"][1],
                    "id": "front",
                },
            ),
            "duplicate presentation id",
        ),
        (
            lambda document: [
                presentation.__setitem__("default", False)
                for presentation in document["presentations"]
            ],
            "exactly one default presentation",
        ),
        (
            lambda document: document["presentations"].__setitem__(
                1,
                {
                    **document["presentations"][1],
                    "default": True,
                },
            ),
            "exactly one default presentation",
        ),
    ],
)
def test_schema_v2_rejects_invalid_presentation_identifiers_and_defaults(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    mutation(document)
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


def test_schema_v2_rejects_hold_with_an_unknown_presentation_id(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["holds"][0]["presentationID"] = "missing"
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown presentationID"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda package, document: (package / "assets" / "undeclared.png").write_bytes(
                PRIMARY_PNG_BYTES
            ),
            "undeclared presentation asset",
        ),
        (
            lambda package, document: (package / "assets" / "back.png").unlink(),
            "missing declared presentation asset",
        ),
        (
            lambda package, document: document["presentations"][1].__setitem__(
                "assetPath", "assets/../outside.png"
            ),
            "assetPath must name a PNG beneath assets/",
        ),
    ],
)
def test_schema_v2_rejects_undeclared_missing_and_escaping_assets(
    tmp_path: Path, mutation, message: str
) -> None:
    module = load_board_catalog_module()
    package_root = write_multi_presentation_board_package(tmp_path / "fixture-model")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    mutation(package_root, document)
    (package_root / "board.json").write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        module.load_board_package(package_root)


def test_package_loader_retains_shape_constraint(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"][0]["shapeConstraint"] = {
        "shape": "roundedRectangle",
        "rotationDegrees": -17.5,
    }
    board_path.write_text(json.dumps(document), encoding="utf-8")

    package = module.load_board_package(package_root)

    constraint = package.board.holds[0].geometry[0].shape_constraint
    assert constraint is not None
    assert constraint.shape == "roundedRectangle"
    assert constraint.rotation_degrees == -17.5


def test_package_loader_rejects_path_that_does_not_fill_its_declared_frame(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"][0]["shape"] = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0.1, 0.1]},
            {"command": "line", "to": [0.9, 0.1]},
            {"command": "line", "to": [0.9, 0.9]},
            {"command": "line", "to": [0.1, 0.9]},
            {"command": "close"},
        ],
    }
    board_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="frame must match its derived shape bounds"):
        module.load_board_package(package_root)


@pytest.mark.parametrize(
    "constraint",
    [
        {"rotationDegrees": 0},
        {"shape": "oval"},
        {"shape": "triangle", "rotationDegrees": 0},
        {"shape": "circle", "rotationDegrees": True},
        {"shape": "pill", "rotationDegrees": float("inf")},
        {"shape": "pill", "rotationDegrees": 10**1000},
        {"shape": "rectangle", "rotationDegrees": -180.01},
        {"shape": "oval", "rotationDegrees": 180},
        {"shape": "oval", "rotationDegrees": 0, "unexpected": True},
    ],
)
def test_package_loader_rejects_invalid_shape_constraints(
    tmp_path: Path, constraint: object
) -> None:
    module = load_board_catalog_module()
    package_root = write_board_package(tmp_path / "fixture-model")
    board_path = package_root / "board.json"
    document = json.loads(board_path.read_text(encoding="utf-8"))
    document["holds"][0]["geometry"][0]["shapeConstraint"] = constraint
    board_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="shapeConstraint"):
        module.load_board_package(package_root)


def test_package_loader_rejects_unknown_board_hold_and_geometry_keys(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    for location in ("board", "hold", "geometry"):
        package = write_board_package(tmp_path / location)
        board_path = package / "board.json"
        document = board_document()
        if location == "board":
            document["unexpected"] = True
        elif location == "hold":
            document["holds"][0]["unexpected"] = True
        else:
            document["holds"][0]["geometry"][0]["unexpected"] = True
        board_path.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(ValueError, match="unknown keys"):
            module.load_board_package(package)
