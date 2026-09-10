#!/usr/bin/env python3
"""Convert legacy raster board packages to the typed schema-v2 contract.

The converter deliberately operates on the JSON document only.  It never
changes assets or derives geometry: every legacy path piece is moved verbatim
under the canonical raster presentation that owned it.  Inverted/derived
presentations reuse that same typed geometry ownership, as the legacy loader
did for rendering and matching.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any


_SCRIPT_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _SCRIPT_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from hangboard_packages import board_catalog  # noqa: E402


class _DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _asset_is_raster(path: Any, source: str) -> None:
    if (
        not isinstance(path, str)
        or not path.startswith("assets/")
        or path.endswith("/")
        or "/../" in path
        or path.endswith("/..")
        or path.endswith(".usdz")
        or not path.endswith(".png")
    ):
        raise ValueError(f"{source} must name a raster PNG beneath assets/")


def _legacy_document(document: dict[str, Any]) -> dict[str, Any]:
    if "schemaVersion" in document:
        if document["schemaVersion"] == 2 and not isinstance(
            document["schemaVersion"], bool
        ):
            return _validate_v2_document(document)
        raise ValueError("only unversioned legacy documents can be migrated")

    # Validate each legacy geometry with the same reviewed shape parser used by
    # schema v2. The catalog parser intentionally no longer accepts v1 after
    # migration, so this one-way converter owns the legacy document boundary.
    presentations = document.get("presentations")
    holds = document.get("holds")
    if not isinstance(presentations, list) or not presentations:
        raise ValueError("board.json.presentations must be a non-empty array")
    if not isinstance(holds, list) or not holds:
        raise ValueError("board.json.holds must be a non-empty array")
    for index, hold in enumerate(holds):
        if not isinstance(hold, dict) or "geometry" not in hold:
            raise ValueError(f"holds[{index}].geometry must be present in legacy documents")
        board_catalog._load_geometry(hold["geometry"], f"board.json.holds[{index}].geometry")

    presentation_ids: set[str] = set()
    canonical_ids: set[str] = set()
    presentation_by_id: dict[str, dict[str, Any]] = {}
    default_count = 0
    for index, value in enumerate(presentations):
        if not isinstance(value, dict):
            raise ValueError(f"presentations[{index}] must be an object")
        allowed_keys = {
            "id",
            "name",
            "assetPath",
            "aspectRatio",
            "default",
            "sourcePresentationID",
            "isInverted",
        }
        unknown_keys = set(value) - allowed_keys
        if unknown_keys:
            raise ValueError(
                f"presentations[{index}] has unknown keys: {sorted(unknown_keys)}"
            )
        required_keys = {"id", "name", "assetPath", "aspectRatio", "default"}
        missing_keys = required_keys - set(value)
        if missing_keys:
            raise ValueError(
                f"presentations[{index}] is missing keys: {sorted(missing_keys)}"
            )
        presentation_id = value.get("id")
        if not isinstance(presentation_id, str) or not presentation_id:
            raise ValueError(f"presentations[{index}].id must be a non-empty string")
        if presentation_id in presentation_ids:
            raise ValueError(f"duplicate presentation ID: {presentation_id}")
        presentation_ids.add(presentation_id)
        presentation_by_id[presentation_id] = value
        _asset_is_raster(value.get("assetPath"), f"presentations[{index}].assetPath")
        default = value.get("default")
        if not isinstance(default, bool):
            raise ValueError(f"presentations[{index}].default must be a boolean")
        default_count += default
        source_id = value.get("sourcePresentationID")
        if source_id is None:
            if "isInverted" in value:
                raise ValueError(
                    f"presentations[{index}].isInverted requires sourcePresentationID"
                )
            canonical_ids.add(presentation_id)
        else:
            if not isinstance(source_id, str) or not source_id:
                raise ValueError(
                    f"presentations[{index}].sourcePresentationID must be a string"
                )
            if not isinstance(value.get("isInverted"), bool):
                raise ValueError(
                    f"presentations[{index}].isInverted must be a boolean"
                )
    if default_count != 1:
        raise ValueError("legacy presentations must have exactly one default")

    geometry_by_presentation: dict[str, dict[str, Any]] = {
        presentation_id: {} for presentation_id in presentation_ids
    }
    hold_ids: set[str] = set()
    for index, value in enumerate(holds):
        if not isinstance(value, dict):
            raise ValueError(f"holds[{index}] must be an object")
        hold_id = value.get("id")
        if not isinstance(hold_id, str) or not hold_id:
            raise ValueError(f"holds[{index}].id must be a non-empty string")
        if hold_id in hold_ids:
            raise ValueError(f"duplicate hold ID: {hold_id}")
        hold_ids.add(hold_id)
        owner = value.get("presentationID")
        if owner not in presentation_ids:
            raise ValueError(f"hold {hold_id} has unknown presentation ownership")
        if owner not in canonical_ids:
            raise ValueError(f"hold {hold_id} must be owned by a canonical presentation")
        geometry_by_presentation[owner][hold_id] = copy.deepcopy(value["geometry"])

    if not hold_ids:
        raise ValueError("legacy holds must not be empty")
    for presentation_id in canonical_ids:
        if not geometry_by_presentation[presentation_id]:
            raise ValueError(
                f"canonical presentation {presentation_id} has no owned hold geometry"
            )

    converted: dict[str, Any] = {}
    # schemaVersion is intentionally first in the canonical root order.
    converted["schemaVersion"] = 2
    for key, value in document.items():
        if key in {"schemaVersion"}:
            continue
        if key == "presentations":
            converted[key] = [
                _convert_presentation(
                    value,
                    geometry_by_presentation,
                    presentation_by_id,
                    canonical_ids,
                )
                for value in presentations
            ]
        elif key == "holds":
            converted[key] = [_convert_hold(value) for value in holds]
        else:
            converted[key] = copy.deepcopy(value)

    converted = _validate_v2_document(converted)
    return converted


def _convert_hold(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key not in {"geometry", "presentationID"}
    }


def _convert_presentation(
    value: dict[str, Any],
    geometry_by_presentation: dict[str, dict[str, Any]],
    presentation_by_id: dict[str, dict[str, Any]],
    canonical_ids: set[str],
) -> dict[str, Any]:
    presentation_id = value["id"]
    source_id = value.get("sourcePresentationID")
    if source_id is None:
        derivation: dict[str, Any] = {"type": "original"}
        geometry = geometry_by_presentation[presentation_id]
    else:
        if source_id not in canonical_ids or source_id == presentation_id:
            raise ValueError(
                f"presentation {presentation_id} must reference a canonical presentation"
            )
        source = presentation_by_id[source_id]
        if source.get("sourcePresentationID") is not None:
            raise ValueError(
                f"presentation {presentation_id} must not reference a derived presentation"
            )
        derivation = {
            "type": "derived",
            "sourcePresentationID": source_id,
            "isInverted": value["isInverted"],
        }
        geometry = geometry_by_presentation[source_id]

    # Rebuild the common presentation order expected by the schema, while
    # preserving every accepted scalar value and geometry command exactly.
    return {
        "id": copy.deepcopy(value["id"]),
        "name": copy.deepcopy(value["name"]),
        "aspectRatio": copy.deepcopy(value["aspectRatio"]),
        "isDefault": value["default"],
        "derivation": derivation,
        "media": {
            "type": "raster",
            "assetPath": copy.deepcopy(value["assetPath"]),
            "holdGeometry": copy.deepcopy(geometry),
        },
    }


def _validate_v2_document(document: dict[str, Any]) -> dict[str, Any]:
    if document.get("schemaVersion") != 2 or isinstance(
        document.get("schemaVersion"), bool
    ):
        raise ValueError("board.json.schemaVersion must be 2")
    for index, presentation in enumerate(document.get("presentations", [])):
        if not isinstance(presentation, dict):
            raise ValueError(f"presentations[{index}] must be an object")
        media = presentation.get("media")
        if not isinstance(media, dict) or media.get("type") != "raster":
            raise ValueError("migration accepts raster presentations only")
        _asset_is_raster(media.get("assetPath"), f"presentations[{index}].media.assetPath")
    # This independently checks the closed v2 package contract, including all
    # geometry path commands and scoped ownership.  Assets are intentionally
    # not needed to validate a document-level idempotence call.
    board_catalog._load_board(document)
    return copy.deepcopy(document)


def migrate_document(document: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic v2 copy; v2 documents are idempotent."""

    return _legacy_document(copy.deepcopy(document))


def _package_paths(root: Path) -> list[Path]:
    inventory = board_catalog.discover_board_packages(root)
    return [package.root / "board.json" for package in inventory.packages]


def migrate_root(root: Path, *, write: bool, check: bool) -> int:
    paths = _package_paths(root)
    converted: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    for path in paths:
        before = load_document(path)
        after = migrate_document(before)
        converted.append((path, before, after))
    if check:
        mismatches = [path for path, before, after in converted if before != after]
        if mismatches:
            raise ValueError(
                "schema-v2 migration required for: "
                + ", ".join(str(path) for path in mismatches)
            )
        print(f"checked {len(paths)} schema-v2 board packages")
        return 0
    if write:
        for path, _, after in converted:
            path.write_text(
                json.dumps(after, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
        print(f"migrated {len(paths)} board packages to schema v2")
        return 0
    raise ValueError("choose exactly one of --write or --check")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    migrate_root(arguments.root, write=arguments.write, check=arguments.check)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
