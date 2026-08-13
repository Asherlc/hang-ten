#!/usr/bin/env python3
"""Import one generated primary image into each flat board package."""

from __future__ import annotations

import argparse
import json
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


def _load_catalog(catalog_path: Path) -> dict[str, object]:
    if not catalog_path.exists():
        return {"schemaVersion": 1, "boards": []}
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"schemaVersion", "boards"}:
        raise ValueError("catalog.json must contain only schemaVersion and boards")
    if payload["schemaVersion"] != 1 or not isinstance(payload["boards"], list):
        raise ValueError("catalog.json must use schemaVersion 1 with a boards array")
    if not all(isinstance(entry, dict) for entry in payload["boards"]):
        raise ValueError("catalog.json boards entries must be objects")
    normalized_entries: list[dict[str, object]] = []
    for entry in payload["boards"]:
        if set(entry) != {"id", "path"}:
            raise ValueError("catalog.json boards entries must use id and path")
        if not isinstance(entry["id"], str) or not entry["id"]:
            raise ValueError("catalog.json board id must be a non-empty string")
        if not isinstance(entry["path"], str) or not entry["path"]:
            raise ValueError("catalog.json board path must be a non-empty string")
        normalized_entries.append(dict(entry))
    return {"schemaVersion": 1, "boards": normalized_entries}


def _write_catalog(catalog_path: Path, boards: list[dict[str, object]]) -> None:
    catalog = {"schemaVersion": 1, "boards": boards}
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def import_generated_catalog(source_root: Path, destination_root: Path) -> None:
    """Copy an existing generated catalog into flat board packages."""
    source_root = Path(source_root)
    destination_root = Path(destination_root)
    primary = _primary_sources(source_root)
    catalog_path = destination_root / "catalog.json"
    # Generated artwork has no factual package sidecars. It stays available in
    # its package directory but is not registered for the shipped runtime
    # catalog until a factual package is authored on its own branch.
    _load_catalog(catalog_path)

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
