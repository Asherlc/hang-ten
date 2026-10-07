"""Flat CAD sources must stay visible when compiled package output is absent."""
from pathlib import Path
import shutil

import pytest

from conftest import load_board_catalog_module, write_board_package, write_cad_source


def test_flat_source_without_generated_package_is_reported(tmp_path: Path):
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "cad-board")
    source = write_cad_source(package)
    assert source == tmp_path / "cad-board.FCStd"
    shutil.rmtree(package)
    with pytest.raises(ValueError, match="generated package resources.*build-board-assets"):
        module.discover_board_packages(tmp_path)


def test_flat_source_and_raster_packages_are_discovered_together(tmp_path: Path):
    module = load_board_catalog_module()
    cad = write_board_package(tmp_path / "cad-board", board_id="fixture.cad")
    write_cad_source(cad)
    write_board_package(tmp_path / "raster-board", board_id="fixture.raster")
    inventory = module.discover_board_packages(tmp_path, require_complete_inventory=True)
    assert {package.board.id for package in inventory.packages} == {"fixture.cad", "fixture.raster"}


@pytest.mark.parametrize("name", ["Bad_Name.FCStd", "bad name.FCStd"])
def test_flat_source_slug_is_validated_even_when_output_is_missing(tmp_path: Path, name: str):
    module = load_board_catalog_module()
    (tmp_path / name).write_bytes(b"native source")
    with pytest.raises(ValueError, match="name is invalid"):
        module.discover_board_packages(tmp_path)


@pytest.mark.parametrize("name", ["suspension.json", "rope-physics.json", "cad-board.FCStd"])
def test_generated_package_rejects_authored_source_sidecars(tmp_path: Path, name: str):
    module = load_board_catalog_module()
    package = write_board_package(tmp_path / "cad-board")
    source = write_cad_source(package)
    (package / name).write_bytes(source.read_bytes() if name.endswith("FCStd") else b"{}")
    with pytest.raises(ValueError, match="unknown package entry"):
        module.load_board_package(package)
