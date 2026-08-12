#!/usr/bin/env python3
"""Import generated hangboard artwork as review-only draft packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Iterable


_CONTACT_SHEET = "contact-sheet"
_ASSET_NAMES = {
    "primary": "primary.png",
    "flat": "flat.png",
    "ai-v2": "ai-v2.png",
}
_DRAFT_README = """# {slug} generated-catalog review material

This directory retains the following **unreviewed-generated-catalog** material:
{materials}

These files are review material only. They must not be used as factual metadata,
evidence, physical geometry, hold truth, runtime artwork, or runtime geometry.
"""


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


def _variant_sources(source_root: Path, directory: str, suffix: str) -> dict[str, Path]:
    variants: dict[str, Path] = {}
    for source in _unique_files(source_root / directory, f"*{suffix}.png", recursive=True):
        slug = source.name[: -len(f"{suffix}.png")]
        if not slug:
            raise ValueError(f"invalid generated-catalog variant basename: {source.name}")
        if slug in variants:
            raise ValueError(f"duplicate generated-catalog variant basename: {source.name}")
        variants[slug] = source
    return variants


def _outline_sources(source_root: Path) -> dict[str, Path]:
    outlines: dict[str, Path] = {}
    for source in _unique_files(source_root / "outlines", "*.json", recursive=True):
        if source.stem in outlines:
            raise ValueError(f"duplicate generated-catalog outline basename: {source.name}")
        outlines[source.stem] = source
    return outlines


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _retained_sources(
    slug: str,
    primary: Path,
    flat: dict[str, Path],
    ai_v2: dict[str, Path],
    outlines: dict[str, Path],
) -> Iterable[tuple[Path, Path]]:
    yield primary, Path("assets") / _ASSET_NAMES["primary"]
    if slug in flat:
        yield flat[slug], Path("assets") / _ASSET_NAMES["flat"]
    if slug in ai_v2:
        yield ai_v2[slug], Path("assets") / _ASSET_NAMES["ai-v2"]
    if slug in outlines:
        yield outlines[slug], Path("review") / "outline.approx.json"


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
        if set(entry) == {"id", "path", "status"}:
            normalized_entries.append(dict(entry))
            continue
        if set(entry) == {"id", "path", "lifecycle"} and entry["lifecycle"] == "shipped":
            legacy_path = Path(str(entry["path"]))
            if len(legacy_path.parts) != 2 or legacy_path.name != "board.json":
                raise ValueError("legacy shipped catalog entry must point to a board.json package manifest")
            normalized_entries.append(
                {"id": entry["id"], "path": legacy_path.parent.as_posix(), "status": "draft"}
            )
            continue
        raise ValueError("catalog.json boards entries must use status or legacy shipped lifecycle")
    return {"schemaVersion": 1, "boards": normalized_entries}


def _write_catalog(catalog_path: Path, boards: list[dict[str, object]]) -> None:
    catalog = {"schemaVersion": 1, "boards": boards}
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def _is_approved_at_slug(entry: dict[str, object], slug: str) -> bool:
    return entry.get("path") == slug and entry.get("status") == "approved"


def _draft_readme(slug: str, sources: Iterable[tuple[Path, Path]], source_root: Path) -> str:
    material_lines = "\n".join(
        f"- `{source.relative_to(source_root).as_posix()}` retained as `{destination.as_posix()}`"
        for source, destination in sources
    )
    return _DRAFT_README.format(slug=slug, materials=material_lines)


def import_generated_catalog(source_root: Path, destination_root: Path) -> None:
    """Copy an existing generated catalog into flat, review-only board packages."""
    source_root = Path(source_root)
    destination_root = Path(destination_root)
    primary = _primary_sources(source_root)
    flat = _variant_sources(source_root, "flat-illustrations", "-flat")
    ai_v2 = _variant_sources(source_root, "ai-illustrations-v2", "-ai-v2")
    outlines = _outline_sources(source_root)
    catalog_path = destination_root / "catalog.json"
    catalog = _load_catalog(catalog_path)
    entries = list(catalog["boards"])

    approved_slugs = {
        str(entry["path"])
        for entry in entries
        if isinstance(entry, dict) and _is_approved_at_slug(entry, str(entry.get("path", "")))
    }
    imported_slugs = set(primary)
    retained_entries = [
        entry
        for entry in entries
        if not (
            isinstance(entry, dict)
            and entry.get("status") == "draft"
            and entry.get("path") in imported_slugs
        )
    ]

    for slug in sorted(primary):
        sources = tuple(_retained_sources(slug, primary[slug], flat, ai_v2, outlines))
        package_root = destination_root / slug
        if slug in approved_slugs:
            quarantine_root = package_root / "review" / "unreviewed-generated-catalog"
            for source, relative_destination in sources:
                _copy(source, quarantine_root / relative_destination)
            continue

        for source, relative_destination in sources:
            _copy(source, package_root / relative_destination)
        (package_root / "README.md").write_text(
            _draft_readme(slug, sources, source_root), encoding="utf-8"
        )
        retained_entries.append({"id": slug, "path": slug, "status": "draft"})

    deterministic_entries = sorted(
        retained_entries,
        key=lambda entry: (str(entry.get("path", "")), str(entry.get("id", ""))),
    )
    destination_root.mkdir(parents=True, exist_ok=True)
    _write_catalog(catalog_path, deterministic_entries)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    import_generated_catalog(args.source, args.destination)


if __name__ == "__main__":
    main()
