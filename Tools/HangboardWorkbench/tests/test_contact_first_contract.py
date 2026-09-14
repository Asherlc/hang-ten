from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil

import pytest

import board_package


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _copy_package(library: Path, slug: str) -> Path:
    source = REPOSITORY_ROOT / "Hangboards" / slug
    destination = library / slug
    shutil.copytree(source, destination)
    return destination


def test_schema_v3_raster_edit_keeps_facts_and_geometry_in_native_owners(
    tmp_path: Path,
) -> None:
    library = tmp_path / "Hangboards"
    library.mkdir()
    package_root = _copy_package(library, "trango-rock-prodigy-pivot")
    original = json.loads((package_root / "board.json").read_text(encoding="utf-8"))

    package = board_package.load_board_package(package_root)
    document = board_package.editor_document(package, "orientation-1")

    assert document["regions"]
    assert document["contacts"] == original["contacts"]
    first = document["regions"][0]
    assert set(first["metadata"]) == {"contactID", "pieceIndex", "presentationID"}
    assert not {
        "kind",
        "features",
        "gripTypes",
        "pairedContactID",
        "equipmentObjectID",
        "fingerCapacity",
        "handCapacity",
        "depthRangeMillimeters",
    }.intersection(first)

    edited_contact_id = first["metadata"]["contactID"]
    edited_contact = next(
        contact for contact in document["contacts"] if contact["id"] == edited_contact_id
    )
    edited_contact["name"] = f'{edited_contact["name"]} (reviewed)'
    first["displayPath"] = "M 5 5 L 25 5 L 25 25 L 5 25 Z"
    first.pop("shapeConstraint", None)
    saved = board_package.save_editor_document(
        library, "trango-rock-prodigy-pivot", document
    )

    assert saved.board["schemaVersion"] == 3
    expected_contacts = copy.deepcopy(original["contacts"])
    next(
        contact for contact in expected_contacts if contact["id"] == edited_contact_id
    )["name"] = edited_contact["name"]
    assert saved.board["contacts"] == expected_contacts
    before_media = original["presentations"][0]["media"]
    after_media = saved.board["presentations"][0]["media"]
    assert after_media["contactGeometry"] != before_media["contactGeometry"]
    assert {
        key: value for key, value in after_media.items() if key != "contactGeometry"
    } == {key: value for key, value in before_media.items() if key != "contactGeometry"}


def test_schema_v3_model_package_is_discoverable_but_read_only(tmp_path: Path) -> None:
    library = tmp_path / "Hangboards"
    library.mkdir()
    _copy_package(library, "yy-baguette-evo")

    discovered = board_package.discover_packages(library)

    assert len(discovered) == 1
    assert discovered[0].schema_version == 3
    assert discovered[0].editor_available is False
    with pytest.raises(
        board_package.BoardEditorUnavailableError,
        match="3D model editing is not supported",
    ):
        board_package.open_package(library, discovered[0].board_id)


def test_schema_v2_board_is_rejected_without_a_compatibility_reader(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path, "trango-rock-prodigy-pivot")
    document = json.loads((package_root / "board.json").read_text(encoding="utf-8"))
    document["schemaVersion"] = 2
    (package_root / "board.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(
        board_package.BoardPackageError, match="schemaVersion must be 3"
    ):
        board_package.load_board_package(package_root)


def test_editor_document_contains_no_legacy_hold_contract(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path, "trango-rock-prodigy-pivot")
    document = board_package.editor_document(
        board_package.load_board_package(package_root)
    )

    encoded = json.dumps(document, sort_keys=True)
    for legacy_name in ("holdID", "holdIDs", "pairedHoldID", '"holds"'):
        assert legacy_name not in encoded
