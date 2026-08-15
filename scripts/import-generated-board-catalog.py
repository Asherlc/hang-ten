#!/usr/bin/env python3
"""Import one generated primary image into each flat board package."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


_CONTACT_SHEET = "contact-sheet"
_PRIMARY_ASSET = Path("assets") / "primary.png"


def _unique_files(directory: Path, pattern: str, *, recursive: bool = False) -> list[Path]:
    """Return matching files, rejecting ambiguous duplicate source basenames."""
    candidates = directory.rglob(pattern) if recursive else directory.glob(pattern)
    files = sorted(path for path in candidates if path.is_file())
    names: set[str] = set()
    for path in files:
        if path.name in names:
            raise ValueError(f"duplicate generated-catalog source basename: {path.name}")
        names.add(path.name)
    return files


def _primary_sources(source_root: Path) -> dict[str, Path]:
    primary: dict[str, Path] = {}
    for source in _unique_files(source_root, "*.png"):
        if _CONTACT_SHEET in source.name:
            continue
        if source.stem in primary:
            raise ValueError(f"duplicate generated-catalog primary basename: {source.name}")
        primary[source.stem] = source
    return primary


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def import_generated_catalog(source_root: Path, destination_root: Path) -> None:
    """Copy an existing generated catalog into flat board packages."""
    source_root = Path(source_root)
    destination_root = Path(destination_root)
    primary = _primary_sources(source_root)
    # Generated artwork has no physical board document. It stays primary-only
    # until a complete board.json is authored and direct discovery can load it.

    for slug in sorted(primary):
        package_root = destination_root / slug
        _copy(primary[slug], package_root / _PRIMARY_ASSET)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    import_generated_catalog(args.source, args.destination)


if __name__ == "__main__":
    main()
