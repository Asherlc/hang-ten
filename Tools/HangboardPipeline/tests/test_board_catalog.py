from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from conftest import load_board_catalog_module


def _write_catalog(root: Path, *, path: str = "example-board") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[3] / "Hangboards/metolius-wood-grips-compact-ii"
    shutil.copytree(source, root / "example-board")
    catalog_path = root / "catalog.json"
    catalog_path.write_text(json.dumps({"schemaVersion": 1, "boards": [{"id": "metolius.wood-grips-compact-ii", "path": path}]}), encoding="utf-8")
    return catalog_path


def test_catalog_requires_a_complete_package_for_every_entry(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    catalog = module.validate_catalog(catalog_path)
    assert catalog.entries[0].path == "example-board"


def test_registered_packages_use_the_canonical_primary_presentation_asset() -> None:
    module = load_board_catalog_module()
    catalog_path = Path(__file__).resolve().parents[3] / "Hangboards/catalog.json"
    catalog = module.validate_catalog(catalog_path)

    for entry in catalog.entries:
        package_root = catalog_path.parent / entry.path
        package = module.load_board_package(package_root)
        assert package.board.presentation_asset_path == "assets/primary.png"
        assert {path.name for path in package_root.glob("*.json")} == {
            "board.json",
            "evidence.json",
            "semantics.json",
            "artwork.json",
        }

        asset_paths = {
            path.relative_to(package_root).as_posix()
            for path in (package_root / "assets").iterdir()
        }
        assert "assets/primary.png" in asset_paths
        source_photos = asset_paths - {"assets/primary.png"}
        assert len(source_photos) <= 1
        assert all(Path(path).suffix.lower() in {".jpg", ".jpeg", ".webp", ".heic"} for path in source_photos)
        assert set(package.evidence.asset_evidence) == asset_paths


def test_catalog_rejects_a_registered_package_without_the_primary_presentation_asset(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    board_path = tmp_path / "example-board" / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board.pop("presentation")
    board_path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(ValueError, match="must present assets/primary.png"):
        module.validate_catalog(catalog_path)


def test_catalog_rejects_a_registered_package_that_presents_a_source_photo(
    tmp_path: Path,
) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    board_path = tmp_path / "example-board" / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["presentation"] = {"assetPath": "assets/WoodGripsCompactII.jpg"}
    board_path.write_text(json.dumps(board), encoding="utf-8")

    with pytest.raises(ValueError, match="must present assets/primary.png"):
        module.validate_catalog(catalog_path)


def test_catalog_rejects_status_and_nested_lifecycle_paths(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    payload["boards"][0]["status"] = "draft"
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown keys"):
        module.validate_catalog(catalog_path)
    payload["boards"][0] = {"id": "metolius.wood-grips-compact-ii", "path": "draft/example-board"}
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="single board-slug directory"):
        module.validate_catalog(catalog_path)


@pytest.mark.parametrize("extra_path", ["README.md", "review", "outline.json", "outline.approx.json"])
def test_registered_package_rejects_files_that_encode_review_state(
    tmp_path: Path,
    extra_path: str,
) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    package = tmp_path / "example-board"
    extra = package / extra_path
    if extra_path == "review":
        extra.mkdir()
    else:
        extra.write_text("review state", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown package file"):
        module.validate_catalog(catalog_path)


def test_registered_package_rejects_a_second_generated_png(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    package = tmp_path / "example-board"
    (package / "assets" / "alternate.png").write_bytes(b"second generated image")

    with pytest.raises(ValueError, match="only assets/primary.png may be a PNG"):
        module.validate_catalog(catalog_path)


def test_registered_package_rejects_nested_assets(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    package = tmp_path / "example-board"
    nested = package / "assets" / "source"
    nested.mkdir()
    (nested / "manufacturer.jpg").write_bytes(b"source image")

    with pytest.raises(ValueError, match="package assets must be flat"):
        module.validate_catalog(catalog_path)


def test_registered_package_allows_at_most_one_original_source_photo(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    assets = tmp_path / "example-board" / "assets"
    (assets / "manufacturer-front.jpg").write_bytes(b"front source")
    (assets / "manufacturer-side.jpg").write_bytes(b"side source")

    with pytest.raises(ValueError, match="at most one original source photo"):
        module.validate_catalog(catalog_path)
