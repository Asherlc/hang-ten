from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil

import pytest

import board_package


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _copy_package(library: Path, slug: str) -> Path:
    destination = library / slug
    shutil.copytree(REPOSITORY_ROOT / "Hangboards" / slug, destination)
    return destination


def test_native_v3_catalog_discovers_raster_and_read_only_model_packages(
    tmp_path: Path,
) -> None:
    library = tmp_path / "Hangboards"
    library.mkdir()
    _copy_package(library, "lattice-mini-bar")
    _copy_package(library, "yy-baguette-evo")

    packages = {package.board_id: package for package in board_package.discover_packages(library)}

    assert packages["lattice.mini-bar"].editor_available is True
    assert packages["yy.baguette-evo"].editor_available is False
    assert packages["lattice.mini-bar"].schema_version == 3
    with pytest.raises(board_package.BoardEditorUnavailableError):
        board_package.editor_document(packages["yy.baguette-evo"])


def test_editor_save_changes_only_contacts_and_selected_raster_geometry(
    tmp_path: Path,
) -> None:
    library = tmp_path / "Hangboards"
    library.mkdir()
    package_root = _copy_package(library, "lattice-mini-bar")
    before = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package, "edge-10")
    selected = document["regions"][0]
    contact_id = selected["metadata"]["contactID"]
    contact = next(item for item in document["contacts"] if item["id"] == contact_id)
    contact["name"] += " reviewed"
    selected["displayPath"] = "M 5 5 L 25 5 L 25 25 L 5 25 Z"
    selected.pop("shapeConstraint", None)

    saved = board_package.save_editor_document(
        library, "lattice-mini-bar", document
    ).board

    expected = copy.deepcopy(before)
    next(item for item in expected["contacts"] if item["id"] == contact_id)["name"] = contact["name"]
    assert saved["contacts"] == expected["contacts"]
    assert saved["presentations"][1:] == expected["presentations"][1:]
    assert (
        saved["presentations"][0]["media"]["contactGeometry"]
        != expected["presentations"][0]["media"]["contactGeometry"]
    )


def test_delete_presentation_keeps_native_contacts_and_reassigns_default(
    tmp_path: Path,
) -> None:
    library = tmp_path / "Hangboards"
    library.mkdir()
    package_root = _copy_package(library, "lattice-mini-bar")
    before = board_package.load_board_package(package_root)

    after = board_package.delete_presentation(
        library, "lattice-mini-bar", "edge-20"
    )

    assert set(after.contact_ids) < set(before.contact_ids)
    remaining_geometry_ids = {
        contact_id
        for presentation in after.board["presentations"]
        for contact_id in presentation["media"]["contactGeometry"]
    }
    assert set(after.contact_ids) == remaining_geometry_ids
    assert {item.id for item in after.presentations} == {
        "edge-10", "ergonomic-jug", "mini-pinch"
    }
    assert next(item for item in after.presentations if item.is_default).id == "edge-10"
    assert not (package_root / "assets" / "edge-20.png").exists()


def test_editor_rejects_facts_duplicated_into_media_regions(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path, "lattice-mini-bar")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["regions"][0]["kind"] = "edge"

    with pytest.raises(board_package.BoardPackageError, match="unknown keys:.*kind"):
        board_package.apply_editor_document(package, document)


@pytest.mark.parametrize("legacy_field", ["holdName", "presentationID", "geometry"])
def test_editor_rejects_unknown_or_legacy_contact_facts(
    tmp_path: Path, legacy_field: str
) -> None:
    package_root = _copy_package(tmp_path, "lattice-mini-bar")
    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package)
    document["contacts"][0][legacy_field] = "legacy"

    with pytest.raises(board_package.BoardPackageError):
        board_package.apply_editor_document(package, document)


def test_no_op_save_does_not_rewrite_board_json(tmp_path: Path) -> None:
    library = tmp_path / "Hangboards"
    library.mkdir()
    package_root = _copy_package(library, "lattice-mini-bar")
    before = (package_root / "board.json").read_bytes()
    package = board_package.load_board_package(package_root)

    saved = board_package.save_editor_document(
        library, package_root.name, board_package.editor_document(package)
    )

    assert saved.board == package.board
    assert (package_root / "board.json").read_bytes() == before


def test_cannot_delete_the_only_raster_presentation(tmp_path: Path) -> None:
    library = tmp_path / "Hangboards"
    library.mkdir()
    package_root = _copy_package(library, "lattice-mini-bar")
    board = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    board["presentations"] = board["presentations"][:1]
    board["presentations"][0]["isDefault"] = True
    geometry_ids = set(board["presentations"][0]["media"]["contactGeometry"])
    board["contacts"] = [
        contact for contact in board["contacts"] if contact["id"] in geometry_ids
    ]
    equipment_ids = {contact["equipmentObjectID"] for contact in board["contacts"]}
    board["equipmentObjects"] = [
        item for item in board["equipmentObjects"] if item["id"] in equipment_ids
    ]
    (package_root / "board.json").write_text(
        json.dumps(board, indent=2) + "\n", encoding="utf-8"
    )
    for asset in ("edge-20.png", "ergonomic-jug.png", "mini-pinch.png"):
        (package_root / "assets" / asset).unlink()

    with pytest.raises(board_package.BoardPackageError, match="only original"):
        board_package.delete_presentation(
            library, "lattice-mini-bar", "edge-10"
        )
