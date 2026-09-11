"""Blender-free characterization of shipped model-first board packages."""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from compile_model_package import load_logical_hold_ids


def _sha256(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ValueError(f"cannot read package asset: {path}") from error
    return hashlib.sha256(data).hexdigest()


def _regular_assets(package: Path) -> list[str]:
    root = Path(package)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"package directory must be a regular directory: {root}")
    assets = root / "assets"
    if assets.is_symlink() or not assets.is_dir():
        raise ValueError(f"package assets must be a regular directory: {assets}")
    files: list[str] = []
    for path in assets.rglob("*"):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"package assets must contain regular files only: {path}")
        files.append(path.relative_to(root).as_posix())
    return sorted(files)


def _json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"descriptor is not readable valid JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"descriptor must be a JSON object: {path}")
    return value


def _ordered_hold_ids(board_json: Path) -> list[str]:
    valid_ids = load_logical_hold_ids(board_json)
    document = _json_object(Path(board_json))
    return [hold["id"] for hold in document["holds"] if hold["id"] in valid_ids]  # type: ignore[index]


def capture_model_baseline(package: Path, board_json: Path) -> dict[str, object]:
    """Capture package inventory, bytes, descriptor, and logical hold order."""
    package = Path(package)
    assets = _regular_assets(package)
    descriptor_path = package / "assets" / "primary.model.json"
    model_path = package / "assets" / "primary.usdz"
    expected_assets = ["assets/primary.model.json", "assets/primary.usdz"]
    if assets != expected_assets:
        raise ValueError(f"model package assets must equal {expected_assets!r}: {assets!r}")
    descriptor = _json_object(descriptor_path)
    return {
        "assets": assets,
        "logicalHoldIDs": _ordered_hold_ids(Path(board_json)),
        "modelSHA256": _sha256(model_path),
        "descriptorSHA256": _sha256(descriptor_path),
        "descriptor": descriptor,
    }


def assert_baseline_matches(
    actual: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    """Raise ValueError when any characterized baseline field differs."""
    for key in ("assets", "logicalHoldIDs", "modelSHA256", "descriptorSHA256", "descriptor"):
        if actual.get(key) != expected.get(key):
            raise ValueError(f"baseline mismatch for {key}")
