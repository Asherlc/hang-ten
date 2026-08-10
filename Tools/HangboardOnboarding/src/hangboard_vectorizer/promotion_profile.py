"""Load and validate promotion profiles for reviewed hold regions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .review_artifacts import load_json, sha256_file

_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RuntimeMapping:
    region_key: str
    runtime_hold_id: str
    grip_type: str
    interaction_mode: str
    notes: str | None = None


@dataclass(frozen=True)
class Destination:
    source_relative: str
    destination_relative: str


@dataclass(frozen=True)
class PromotionProfile:
    schema_version: int
    profile_id: str
    board_id: str
    required_region_keys: tuple[str, ...]
    runtime_mappings: tuple[RuntimeMapping, ...]
    destinations: tuple[Destination, ...]
    source_path: Path
    sha256: str


def load_promotion_profile(path: Path) -> PromotionProfile:
    """Load one version-1 promotion profile from *path*."""
    source_path = path.resolve(strict=False)
    document = load_json(source_path, "promotion profile")
    schema_version = document.get("schemaVersion")
    if schema_version != _SCHEMA_VERSION:
        raise ValueError("promotion profile schemaVersion must be 1")

    profile_id = _non_empty_string(document.get("profileId"), "profileId")
    board_id = _non_empty_string(document.get("boardId"), "boardId")
    required_region_keys = _required_region_keys(document.get("requiredRegionKeys"))
    runtime_mappings = _runtime_mappings(
        document.get("runtimeMappings"), required_region_keys
    )
    destinations = _destinations(document.get("destinations"))

    return PromotionProfile(
        schema_version=_SCHEMA_VERSION,
        profile_id=profile_id,
        board_id=board_id,
        required_region_keys=required_region_keys,
        runtime_mappings=runtime_mappings,
        destinations=destinations,
        source_path=source_path,
        sha256=sha256_file(source_path),
    )


def _required_region_keys(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("promotion profile requiredRegionKeys must be a non-empty list")
    keys = tuple(_non_empty_string(value, "requiredRegionKeys[]") for value in raw)
    if len(set(keys)) != len(keys):
        raise ValueError("promotion profile requiredRegionKeys must be unique")
    return keys


def _runtime_mappings(
    raw: object, required_region_keys: tuple[str, ...]
) -> tuple[RuntimeMapping, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("promotion profile runtimeMappings must be a non-empty list")

    mappings: list[RuntimeMapping] = []
    seen_region_keys: set[str] = set()
    seen_runtime_ids: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("promotion profile runtimeMappings entries must be objects")
        region_key = _non_empty_string(entry.get("regionKey"), "runtimeMappings[].regionKey")
        if region_key not in required_region_keys:
            raise ValueError(
                f"promotion profile runtime mapping references unknown requiredRegionKey: {region_key}"
            )
        runtime_hold_id = _non_empty_string(
            entry.get("runtimeHoldId"), "runtimeMappings[].runtimeHoldId"
        )
        if region_key in seen_region_keys:
            raise ValueError(f"duplicate promotion profile regionKey: {region_key}")
        if runtime_hold_id in seen_runtime_ids:
            raise ValueError(f"duplicate promotion profile runtimeHoldId: {runtime_hold_id}")
        seen_region_keys.add(region_key)
        seen_runtime_ids.add(runtime_hold_id)

        notes = entry.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise ValueError("promotion profile runtimeMappings[].notes must be a string")
        mappings.append(
            RuntimeMapping(
                region_key=region_key,
                runtime_hold_id=runtime_hold_id,
                grip_type=_non_empty_string(
                    entry.get("gripType"), "runtimeMappings[].gripType"
                ),
                interaction_mode=_non_empty_string(
                    entry.get("interactionMode"),
                    "runtimeMappings[].interactionMode",
                ),
                notes=notes,
            )
        )

    if set(required_region_keys) != seen_region_keys:
        missing = sorted(set(required_region_keys) - seen_region_keys)
        raise ValueError(
            "promotion profile runtimeMappings missing requiredRegionKeys: "
            + ", ".join(missing)
        )
    return tuple(mappings)


def _destinations(raw: object) -> tuple[Destination, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("promotion profile destinations must be a non-empty list")

    destinations: list[Destination] = []
    seen_destinations: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("promotion profile destinations entries must be objects")
        source_relative = _normalized_relative_path(
            entry.get("sourceRelative"),
            label="sourceRelative",
            outside_message="promotion profile sourceRelative must be a normalized relative path",
        )
        destination_relative = _normalized_relative_path(
            entry.get("destinationRelative"),
            label="destinationRelative",
            outside_message="promotion profile destinationRelative resolves outside repository root",
        )
        if destination_relative in seen_destinations:
            raise ValueError(
                f"duplicate promotion profile destinationRelative: {destination_relative}"
            )
        seen_destinations.add(destination_relative)
        destinations.append(
            Destination(
                source_relative=source_relative,
                destination_relative=destination_relative,
            )
        )
    return tuple(destinations)


def _normalized_relative_path(value: object, *, label: str, outside_message: str) -> str:
    path_string = _non_empty_string(value, label)
    path = Path(path_string)
    if path.is_absolute():
        raise ValueError(f"promotion profile {label} must be relative")
    if any(part in {"", "."} for part in path.parts):
        raise ValueError(f"promotion profile {label} must be normalized")
    if ".." in path.parts:
        raise ValueError(outside_message)
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise ValueError(f"promotion profile {label} must be a file path")
    return normalized


def _non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"promotion profile {label} must be a non-empty string")
    return value.strip()
