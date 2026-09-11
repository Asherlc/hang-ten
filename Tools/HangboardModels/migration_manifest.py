"""Fail-closed loader for the model migration bookkeeping manifest."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
_FORBIDDEN = {"geometry", "bounds", "modelbounds", "center", "coordinates", "contours", "masks", "vectors", "trace", "alignment"}
_REVIEW_VIEWS = ("front", "three-quarter", "clay-detail", "active-hold")


@dataclass(frozen=True)
class SourceBlend:
    path: str
    sha256: str


@dataclass(frozen=True)
class Presentation:
    id: str
    type: str
    asset_path: str
    descriptor_path: str


@dataclass(frozen=True)
class Position:
    id: str
    active_hold_ids: tuple[str, ...]


@dataclass(frozen=True)
class Verification:
    triangle_ceiling: int
    probe_ids: tuple[str, ...]


@dataclass(frozen=True)
class Artifacts:
    package_sha256: str
    descriptor_sha256: str


@dataclass(frozen=True)
class MigrationManifest:
    schema_version: int
    board_id: str
    revision: str
    board_json: str
    evidence_packet: str
    source_blend: SourceBlend
    logical_hold_ids: tuple[str, ...]
    presentation: Presentation
    positions: tuple[Position, ...]
    suspension_profile: str
    deliberate_omissions: tuple[str, ...]
    verification: Verification
    review_views: tuple[str, ...]
    artifacts: Artifacts


def _reject_constant(value: str) -> None:
    raise ValueError(f"manifest contains nonfinite number: {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"manifest contains duplicate key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"manifest is not valid JSON: {path}") from error


def _closed(value: Any, keys: set[str], label: str, required: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    unknown = set(value) - keys
    if unknown:
        raise ValueError(f"{label} contains unknown member: {sorted(unknown)[0]}")
    missing = (required if required is not None else keys) - set(value)
    if missing:
        raise ValueError(f"{label} is missing member: {sorted(missing)[0]}")
    return value


def _string(value: Any, label: str) -> str:
    if value is None or not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _path(value: Any, label: str) -> str:
    result = _string(value, label)
    if (
        result.startswith("/")
        or "\\" in result
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in result)
        or any(part in ("", ".", "..") for part in result.split("/"))
    ):
        raise ValueError(f"{label} is an invalid path")
    return result


def _sha(value: Any, label: str) -> str:
    result = _string(value, label)
    if not _HEX.fullmatch(result):
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    return result.lower()


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    values = tuple(_string(item, f"{label} item") for item in value)
    if len(values) != len(set(values)):
        raise ValueError(f"{label} contains duplicate values")
    return values


def _reject_nulls_and_forbidden(value: Any) -> None:
    if value is None:
        raise ValueError("manifest does not permit explicit null")
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in _FORBIDDEN:
                raise ValueError(f"manifest contains unknown forbidden geometry/bounds member: {key}")
            _reject_nulls_and_forbidden(child)
    elif isinstance(value, list):
        for child in value:
            _reject_nulls_and_forbidden(child)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("manifest contains nonfinite number")


def load_migration_manifest(path: Path) -> MigrationManifest:
    """Load and validate one closed model migration manifest."""
    manifest_path = Path(path)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"manifest must be a regular file: {manifest_path}")
    payload = _load_json(manifest_path)
    _reject_nulls_and_forbidden(payload)
    root = _closed(
        payload,
        {"schemaVersion", "boardID", "revision", "boardJSON", "evidencePacket", "sourceBlend", "logicalHoldIDs", "presentation", "positions", "suspensionProfile", "deliberateOmissions", "verification", "reviewViews", "artifacts"},
        "manifest",
    )
    if type(root["schemaVersion"]) is not int or root["schemaVersion"] != 1:
        raise ValueError("schemaVersion must be the integer 1")
    board_id = _string(root["boardID"], "boardID")
    revision = _string(root["revision"], "revision")
    board_json = _path(root["boardJSON"], "boardJSON")
    evidence_packet = _path(root["evidencePacket"], "evidencePacket")
    blend = _closed(root["sourceBlend"], {"path", "sha256"}, "sourceBlend")
    source_blend = SourceBlend(_path(blend["path"], "sourceBlend.path"), _sha(blend["sha256"], "sourceBlend.sha256"))
    logical_ids = _strings(root["logicalHoldIDs"], "logicalHoldIDs")
    presentation_payload = _closed(root["presentation"], {"id", "type", "assetPath", "descriptorPath"}, "presentation")
    presentation = Presentation(
        _string(presentation_payload["id"], "presentation.id"),
        _string(presentation_payload["type"], "presentation.type"),
        _path(presentation_payload["assetPath"], "presentation.assetPath"),
        _path(presentation_payload["descriptorPath"], "presentation.descriptorPath"),
    )
    if presentation.id != "primary" or presentation.type != "model" or presentation.asset_path != "assets/primary.usdz" or presentation.descriptor_path != "assets/primary.model.json":
        raise ValueError("presentation must declare exactly primary.usdz and primary.model.json")
    positions_raw = root["positions"]
    if not isinstance(positions_raw, list):
        raise ValueError("positions must be an array")
    positions_list: list[Position] = []
    position_ids: list[str] = []
    for item in positions_raw:
        position = _closed(item, {"id", "activeHoldIDs"}, "position")
        position_id = _string(position["id"], "position.id")
        active_ids = _strings(position["activeHoldIDs"], "position.activeHoldIDs")
        if any(hold_id not in logical_ids for hold_id in active_ids):
            raise ValueError("position activeHoldIDs contains an undeclared logical hold")
        position_ids.append(position_id)
        positions_list.append(Position(position_id, active_ids))
    if len(position_ids) != len(set(position_ids)):
        raise ValueError("positions contains duplicate IDs")
    suspension_profile = _string(root["suspensionProfile"], "suspensionProfile")
    if suspension_profile not in {"singleCord", "twoBranchCord", "none"}:
        raise ValueError("suspensionProfile is not supported")
    omissions = _strings(root["deliberateOmissions"], "deliberateOmissions")
    if {value.casefold() for value in omissions} != {"screw holes", "mounting hardware"}:
        raise ValueError("deliberate omission list must declare screw holes and mounting hardware exactly")
    verification_payload = _closed(root["verification"], {"triangleCeiling", "probeIDs"}, "verification")
    ceiling = verification_payload["triangleCeiling"]
    if type(ceiling) is not int or ceiling <= 0:
        raise ValueError("verification.triangleCeiling must be a positive integer")
    verification = Verification(ceiling, _strings(verification_payload["probeIDs"], "verification.probeIDs"))
    review_views = _strings(root["reviewViews"], "reviewViews")
    if not review_views or any(view not in _REVIEW_VIEWS for view in review_views):
        raise ValueError("reviewViews must contain one or more fixed gallery review views")
    artifacts_payload = _closed(root["artifacts"], {"packageSHA256", "descriptorSHA256"}, "artifacts")
    artifacts = Artifacts(_sha(artifacts_payload["packageSHA256"], "artifacts.packageSHA256"), _sha(artifacts_payload["descriptorSHA256"], "artifacts.descriptorSHA256"))
    return MigrationManifest(1, board_id, revision, board_json, evidence_packet, source_blend, logical_ids, presentation, tuple(positions_list), suspension_profile, omissions, verification, review_views, artifacts)
