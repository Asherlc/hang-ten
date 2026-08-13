"""Promotion adapters for the workbench's active revision boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import shutil
from typing import Any, Mapping
from uuid import uuid4

from .board_library import RepositoryBoardLibrary
from .board_catalog import load_approved_package, validate_catalog
from .ios_promotion import (
    IosPromotionProfile,
    PromotionPreview,
    PromotionSaveResult,
    build_promotion_preview,
    save_promotion_preview,
)


_PACKAGE_STATUSES = frozenset({"draft", "approved"})


@dataclass(frozen=True, slots=True)
class PackagePublication:
    """The canonical files changed by a direct package publication."""

    paths: tuple[Path, ...]


def publish_package_candidate(
    repository_root: Path,
    candidate_root: Path,
    *,
    board_id: str,
    status: str,
) -> PackagePublication:
    """Install one reviewed package candidate and register its shipping status.

    Candidates are copied only into ``Hangboards/<slug>``.  The catalog
    validator is the final authority, so no native source, Xcode asset, or
    legacy board-library artifact participates in this publication path.
    """
    if status not in _PACKAGE_STATUSES:
        raise ValueError("status must be either 'draft' or 'approved'")
    root = Path(repository_root).resolve(strict=True)
    hangboards_root = root / "Hangboards"
    catalog_path = hangboards_root / "catalog.json"
    candidate = Path(candidate_root).resolve(strict=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("package candidate must be a regular directory")
    slug = candidate.name
    if not slug or slug != Path(slug).name:
        raise ValueError("package candidate must use a flat directory name")
    if not hangboards_root.is_dir() or hangboards_root.is_symlink():
        raise ValueError("Hangboards directory must be a regular directory")
    if not catalog_path.is_file() or catalog_path.is_symlink():
        raise ValueError("Hangboards/catalog.json must be a regular file")

    existing = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(existing, dict) or set(existing) != {"schemaVersion", "boards"}:
        raise ValueError("catalog.json must contain schemaVersion and boards")
    entries = existing.get("boards")
    if not isinstance(entries, list):
        raise ValueError("catalog.json boards must be an array")
    if any(
        not isinstance(entry, dict)
        or entry.get("id") == board_id
        or entry.get("path") == slug
        for entry in entries
    ):
        raise ValueError("catalog already contains the package ID or path")

    destination = hangboards_root / slug
    if destination.exists() or destination.is_symlink():
        raise ValueError("canonical package destination already exists")
    staging = hangboards_root / f".{slug}.staging-{uuid4().hex}"
    catalog_backup = catalog_path.read_bytes()
    try:
        shutil.copytree(candidate, staging, symlinks=True)
        _require_regular_tree(staging)
        if status == "approved":
            package = load_approved_package(staging)
            if package.board.id != board_id:
                raise ValueError("approved package board ID does not match registry ID")
        os.replace(staging, destination)
        updated_entries = [*entries, {"id": board_id, "path": slug, "status": status}]
        catalog_path.write_text(
            json.dumps(
                {"schemaVersion": existing["schemaVersion"], "boards": updated_entries},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        validate_catalog(catalog_path)
    except BaseException:
        if destination.exists():
            shutil.rmtree(destination)
        if staging.exists():
            shutil.rmtree(staging)
        catalog_path.write_bytes(catalog_backup)
        raise
    return PackagePublication(
        paths=(Path("Hangboards/catalog.json"), Path("Hangboards") / slug)
    )


def _require_regular_tree(root: Path) -> None:
    for item in (root, *root.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"package candidate contains a symlink: {item}")


def profile_from_payload(value: object) -> IosPromotionProfile:
    """Decode the explicit client-supplied profile without writing a run artifact."""
    if not isinstance(value, Mapping):
        raise ValueError("profile must be an object")
    expected = {
        "schemaVersion",
        "boardID",
        "manufacturer",
        "name",
        "subtitle",
        "dimensions",
        "aspectRatio",
        "productURL",
    }
    if set(value) != expected:
        raise ValueError("profile has unsupported or missing fields")
    if value["schemaVersion"] != 1:
        raise ValueError("unsupported iOS promotion profile schemaVersion")
    string_fields = {
        "boardID": "board_id",
        "manufacturer": "manufacturer",
        "name": "name",
        "subtitle": "subtitle",
        "dimensions": "dimensions",
        "productURL": "product_url",
    }
    decoded: dict[str, Any] = {"schema_version": 1}
    for source, destination in string_fields.items():
        field = value[source]
        if not isinstance(field, str) or not field.strip():
            raise ValueError(f"profile {source} must be a non-empty string")
        decoded[destination] = field.strip()
    aspect_ratio = value["aspectRatio"]
    if (
        isinstance(aspect_ratio, bool)
        or not isinstance(aspect_ratio, (int, float))
        or not math.isfinite(aspect_ratio)
        or aspect_ratio <= 0
    ):
        raise ValueError("profile aspectRatio must be finite positive")
    decoded["aspect_ratio"] = float(aspect_ratio)
    decoded["_source_bytes"] = json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return IosPromotionProfile(**decoded)


def preview_for_revision(
    library: RepositoryBoardLibrary,
    run_root: Path,
    profile: IosPromotionProfile,
    *,
    base_ref: str,
) -> PromotionPreview:
    """Render a preview against the exact repository that owns the package."""
    return build_promotion_preview(
        run_root,
        _repository_root(library),
        profile,
        expected_base_ref=base_ref,
    )


def save_for_revision(
    library: RepositoryBoardLibrary,
    preview: PromotionPreview,
    *,
    expected_preview_token: str,
) -> PromotionSaveResult:
    """Persist a verified preview only after its target fingerprints still match."""
    return save_promotion_preview(
        preview,
        _repository_root(library),
        expected_preview_token=expected_preview_token,
    )


def repository_root(library: RepositoryBoardLibrary) -> Path:
    """Expose the repository boundary while keeping library internals local here."""
    return _repository_root(library)


def _repository_root(library: RepositoryBoardLibrary) -> Path:
    root = library.repository_root
    if not isinstance(root, Path) or not root.is_dir():
        raise ValueError("repository board library is not configured")
    return root
