from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


@dataclass(frozen=True)
class _BoardCatalogPackage:
    root: Path


@dataclass(frozen=True)
class _BoardCatalogInventory:
    packages: tuple[_BoardCatalogPackage, ...]


def _discover_board_packages(root: Path) -> _BoardCatalogInventory:
    """Return discoverable board packages in a catalog root directory."""

    packages = [
        _BoardCatalogPackage(package)
        for package in sorted(Path(root).iterdir())
        if package.is_dir() and (package / "board.json").is_file()
    ]
    return _BoardCatalogInventory(tuple(packages))


def load_board_catalog_module() -> SimpleNamespace:
    """Return a tiny object exposing ``discover_board_packages`` for tests."""

    return SimpleNamespace(discover_board_packages=_discover_board_packages)
