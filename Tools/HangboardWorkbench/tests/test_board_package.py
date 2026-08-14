from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WORKBENCH_ROOT.parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402
from board_package import (  # noqa: E402
    BoardPackageError,
    discover_packages,
    editor_document,
    load_board_package,
    primary_image_path,
    replace_package,
    save_editor_document,
)


SLUG = "metolius-wood-grips-compact-ii"


def _copy_library(tmp_path: Path) -> Path:
    library = tmp_path / "Hangboards"
    shutil.copytree(REPOSITORY_ROOT / "Hangboards", library)
    return library


def test_loads_a_registered_package_with_its_primary_image_and_hold_document() -> None:
    package = load_board_package(REPOSITORY_ROOT / "Hangboards" / SLUG)

    assert primary_image_path(package).name == "primary.png"
    document = editor_document(package)
    assert document["canvas"]["width"] > 0
    assert {region["key"] for region in document["regions"]} == {
        hold["id"] for hold in package.board["holds"]
    }
    assert all(region["displayPath"].endswith(" Z") for region in document["regions"])


def test_discovers_registered_canonical_packages() -> None:
    assert discover_packages(REPOSITORY_ROOT / "Hangboards") == (
        board_package.CatalogEntry("metolius.wood-grips-compact-ii", SLUG),
    )


def test_rejects_duplicate_board_hold_ids_and_mismatched_artwork_ids(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    package_root = library / SLUG
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["holds"][1]["id"] = board["holds"][0]["id"]
    board_path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="duplicate hold ID"):
        load_board_package(package_root)

    board["holds"][1]["id"] = "restored-hold"
    board_path.write_text(json.dumps(board), encoding="utf-8")
    semantics_path = package_root / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    for semantic in semantics["semanticHolds"].values():
        semantic["holdIDs"] = [
            "restored-hold" if hold_id == "sloper-flat-left" else hold_id
            for hold_id in semantic["holdIDs"]
        ]
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")
    with pytest.raises(BoardPackageError, match="hold IDs must exactly match"):
        load_board_package(package_root)


def test_replaces_a_valid_candidate_and_leaves_live_files_untouched_when_validation_fails(
    tmp_path: Path,
) -> None:
    library = _copy_library(tmp_path)
    live = library / SLUG
    candidate = tmp_path / "candidate"
    shutil.copytree(live, candidate)
    board_path = candidate / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["name"] = "Edited board name"
    board_path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")

    replace_package(library, SLUG, candidate)

    assert json.loads((live / "board.json").read_text(encoding="utf-8"))["name"] == "Edited board name"
    catalog_before = (library / "catalog.json").read_bytes()
    package_before = (live / "board.json").read_bytes()
    invalid = tmp_path / "invalid"
    shutil.copytree(live, invalid)
    invalid_artwork = json.loads((invalid / "artwork.json").read_text(encoding="utf-8"))
    duplicate_piece = dict(invalid_artwork["holdPieces"][0])
    duplicate_piece["id"] = "duplicate-piece"
    invalid_artwork["holdPieces"].append(duplicate_piece)
    (invalid / "artwork.json").write_text(json.dumps(invalid_artwork), encoding="utf-8")

    with pytest.raises(BoardPackageError, match="duplicate hold ID"):
        replace_package(library, SLUG, invalid)

    assert (library / "catalog.json").read_bytes() == catalog_before
    assert (live / "board.json").read_bytes() == package_before


def test_saves_an_edited_contour_with_its_derived_board_frame(tmp_path: Path) -> None:
    library = _copy_library(tmp_path)
    package = load_board_package(library / SLUG)
    document = editor_document(package)
    region = document["regions"][0]
    region["displayPath"] = "M 10 20 L 50 20 L 50 60 L 10 60 Z"

    saved = save_editor_document(library, SLUG, document)

    edited_hold = next(hold for hold in saved.board["holds"] if hold["id"] == region["key"])
    assert edited_hold["frame"] == {"x": 10 / document["canvas"]["width"], "y": 20 / document["canvas"]["height"], "width": 40 / document["canvas"]["width"], "height": 40 / document["canvas"]["height"]}
    reloaded = editor_document(saved)
    assert reloaded["regions"][0]["displayPath"] == region["displayPath"]


def test_restores_the_prior_package_and_catalog_when_replacement_io_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    library = _copy_library(tmp_path)
    live = library / SLUG
    candidate = tmp_path / "candidate"
    shutil.copytree(live, candidate)
    package_before = (live / "board.json").read_bytes()
    catalog_before = (library / "catalog.json").read_bytes()
    real_replace = board_package.os.replace

    def fail_staged_package_replace(source: str | Path, destination: str | Path) -> None:
        if Path(source).parent.name.startswith(".workbench-save-") and Path(source).name == SLUG:
            raise OSError("injected replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(board_package.os, "replace", fail_staged_package_replace)

    with pytest.raises(BoardPackageError, match="could not save"):
        replace_package(library, SLUG, candidate)

    assert (live / "board.json").read_bytes() == package_before
    assert (library / "catalog.json").read_bytes() == catalog_before
