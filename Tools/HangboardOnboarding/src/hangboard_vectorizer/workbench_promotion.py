"""Promotion adapters for the workbench's active revision boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .board_library import RepositoryBoardLibrary
from .ios_promotion import (
    IosPromotionProfile,
    PromotionPreview,
    PromotionSaveResult,
    build_promotion_preview,
    save_promotion_preview,
)


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
        or aspect_ratio <= 0
    ):
        raise ValueError("profile aspectRatio must be positive")
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
    root = getattr(library, "_repository_root", None)
    if not isinstance(root, Path) or not root.is_dir():
        raise ValueError("repository board library is not configured")
    return root
