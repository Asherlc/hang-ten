"""Discover and summarize hold-region review artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from hashlib import sha256


@dataclass(frozen=True)
class ReviewRun:
    root: Path
    stage1_image: Path
    stage2_regions: Path
    edited_regions: Path | None
    corrections: Path | None
    lint_report: Path | None
    acceptance: Path | None
    promotion_report: Path | None


_OPTIONAL_ARTIFACTS = {
    "stage-2-regions.edited.json": "edited_regions",
    "stage-2-human-corrections.json": "corrections",
    "lint-report.json": "lint_report",
    "stage-2-review-acceptance.json": "acceptance",
}

_INSPECT_PATH_FIELDS = {
    "stage1Image": "stage1_image",
    "stage2Regions": "stage2_regions",
    "editedRegions": "edited_regions",
    "corrections": "corrections",
    "lintReport": "lint_report",
    "acceptance": "acceptance",
    "promotionReport": "promotion_report",
}

_NEXT_ACTIONS = {
    "automatic": "edit",
    "edited": "lint",
    "lint-passed": "accept",
    "accepted": "promote",
    "promoted": "release-check",
}


def discover_review_run(root: Path) -> ReviewRun:
    """Return the current review-artifact set rooted under *root*."""
    resolved_root = root.resolve(strict=False)
    if not resolved_root.is_dir():
        raise ValueError(f"review run root must be a directory: {resolved_root}")

    stage1_image = _require_one(resolved_root, "stage-1-auto-rgba.png")
    stage2_regions = _require_one(resolved_root, "stage-2-regions.json")
    stage2_dir = stage2_regions.parent

    optional: dict[str, Path | None] = {}
    for artifact_name, field_name in _OPTIONAL_ARTIFACTS.items():
        optional[field_name] = _discover_optional_in_directory(
            resolved_root, stage2_dir, artifact_name
        )
    optional["promotion_report"] = _discover_optional_in_directory(
        resolved_root, stage2_dir / "promotion", "board-promotion-report.json"
    )

    return ReviewRun(
        root=resolved_root,
        stage1_image=stage1_image,
        stage2_regions=stage2_regions,
        edited_regions=optional["edited_regions"],
        corrections=optional["corrections"],
        lint_report=optional["lint_report"],
        acceptance=optional["acceptance"],
        promotion_report=optional["promotion_report"],
    )


def sha256_file(path: Path) -> str:
    """Return the exact-byte SHA-256 digest for *path*."""
    return sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, label: str) -> dict[str, object]:
    """Load one object-valued JSON document with path-specific failures."""
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is not valid JSON: {path}") from error
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return document


def review_state(run: ReviewRun) -> str:
    """Derive the current review lifecycle state from persisted artifacts."""
    if _acceptance_decision(run) == "accepted":
        if _is_successful_promotion_report(run):
            return "promoted"
        return "accepted"
    if run.lint_report is not None and load_json(run.lint_report, "lint report").get(
        "passed"
    ) is True:
        return "lint-passed"
    if run.edited_regions is not None or run.corrections is not None:
        return "edited"
    return "automatic"


def inspect_run(run: ReviewRun) -> dict[str, object]:
    """Return the compact inspect payload for *run*."""
    state = review_state(run)
    artifacts = {
        output_name: _relative_path(run.root, getattr(run, field_name))
        for output_name, field_name in _INSPECT_PATH_FIELDS.items()
    }
    hashes = {
        output_name: sha256_file(path)
        for output_name, field_name in _INSPECT_PATH_FIELDS.items()
        if (path := getattr(run, field_name)) is not None
    }
    return {
        "state": state,
        "nextAction": _NEXT_ACTIONS[state],
        "artifacts": artifacts,
        "hashes": hashes,
    }


def _is_successful_promotion_report(run: ReviewRun) -> bool:
    if run.promotion_report is None:
        return False
    return load_json(run.promotion_report, "promotion report").get("status") in {
        "ready",
        "applied",
    }


def _acceptance_decision(run: ReviewRun) -> object:
    if run.acceptance is None:
        return None
    return load_json(run.acceptance, "review acceptance").get("decision")


def _discover_optional_in_directory(root: Path, directory: Path, name: str) -> Path | None:
    matches = []
    for path in root.rglob(name):
        if not path.is_file():
            continue
        resolved = _confined_artifact(root, path)
        if resolved.parent == directory:
            matches.append(resolved)
    if len(matches) > 1:
        raise ValueError(f"expected at most one {name} beside {directory}")
    return matches[0] if matches else None


def _relative_path(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    return path.relative_to(root).as_posix()


def _require_one(root: Path, name: str) -> Path:
    matches = [
        _confined_artifact(root, path)
        for path in root.rglob(name)
        if path.is_file()
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name} under {root}")
    return matches[0]


def _confined_artifact(root: Path, path: Path) -> Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"artifact resolves outside review run root: {path} -> {resolved}"
        ) from error
    return resolved
