"""Closed, source-backed ledger validation for tensioned-cord presentations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .board_catalog import BoardInventory, is_board_identifier


_PACKAGE_COUNT = 20
_PRESENTATION_COUNT = 47
_ORIENTATIONS = frozenset({"upright", "inverted", "rotated"})
_GRAVITY = "canvasDown"
_TENSION_DIRECTIONS = frozenset({"towardCanvasBottom", "unknown"})
_TOPOLOGIES = frozenset(
    {
        "visibleSegmentsOnly",
        "singleLanyard",
        "pairedSideStrands",
        "pairedEndCords",
        "perimeterRoutedCords",
        "adjustableDualCord",
    }
)
_ROUTING = frozenset({"unknown", "visibleOnly", "endOpenings", "perimeterGroove", "bodyChannel"})
_COMPONENTS = frozenset({"unknown", "none", "visibleOnly"})
_STATUSES = frozenset({"accepted", "blocked"})


class TensionedCordAuditError(ValueError):
    """Raised when a closed cord ledger is malformed or disagrees with inventory."""


@dataclass(frozen=True)
class TensionedCordEvidence:
    url: str
    label: str
    reviewed_at: date


@dataclass(frozen=True)
class TensionedCordRecord:
    package_id: str
    presentation_id: str
    asset_path: str
    asset_sha256: str
    source_presentation_id: str | None
    evidence: TensionedCordEvidence
    orientation: str
    gravity: str
    tension_direction: str
    visible_topology: str
    routing: str
    terminals: str
    knots: str
    hardware: str
    status: str
    output: str
    blocker: str | None


@dataclass(frozen=True)
class TensionedCordLedger:
    schema_version: int
    package_ids: tuple[str, ...]
    records: tuple[TensionedCordRecord, ...]


@dataclass(frozen=True)
class TensionedCordAuditReport:
    package_count: int
    presentation_count: int
    accepted_count: int
    blocked_count: int
    blockers: tuple[tuple[str, str, str], ...]

    def to_json(self) -> dict[str, object]:
        return {
            "packageCount": self.package_count,
            "presentationCount": self.presentation_count,
            "acceptedCount": self.accepted_count,
            "blockedCount": self.blocked_count,
            "blockers": [
                {
                    "packageID": package_id,
                    "presentationID": presentation_id,
                    "reason": reason,
                }
                for package_id, presentation_id, reason in self.blockers
            ],
        }


def _mapping(value: Any, source: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TensionedCordAuditError(f"{source} must be an object")
    return value


def _closed(payload: Mapping[str, Any], keys: set[str], source: str) -> None:
    unknown = sorted(set(payload) - keys)
    missing = sorted(keys - set(payload))
    if unknown:
        raise TensionedCordAuditError(f"{source} has unknown keys: {unknown}")
    if missing:
        raise TensionedCordAuditError(f"{source} is missing keys: {missing}")


def _nonempty_string(value: Any, source: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TensionedCordAuditError(f"{source} must be a non-empty string")
    return value


def _identifier(value: Any, source: str) -> str:
    result = _nonempty_string(value, source)
    if not is_board_identifier(result):
        raise TensionedCordAuditError(f"{source} must be identifier-shaped")
    return result


def _date(value: Any, source: str) -> date:
    text = _nonempty_string(value, source)
    try:
        result = date.fromisoformat(text)
    except ValueError as error:
        raise TensionedCordAuditError(f"{source} must be an ISO date") from error
    if result.isoformat() != text:
        raise TensionedCordAuditError(f"{source} must be an ISO date")
    return result


def _enum(value: Any, values: frozenset[str], source: str) -> str:
    result = _nonempty_string(value, source)
    if result not in values:
        raise TensionedCordAuditError(f"{source} must be one of {sorted(values)}")
    return result


def _nullable_identifier(value: Any, source: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, source)


def _nullable_string(value: Any, source: str) -> str | None:
    if value is None:
        return None
    return _nonempty_string(value, source)


def _asset_path(value: Any, source: str) -> str:
    result = _nonempty_string(value, source)
    path = Path(result)
    if path.is_absolute() or path.suffix != ".png" or ".." in path.parts:
        raise TensionedCordAuditError(f"{source} must name a relative PNG asset")
    return result


def _sha256(value: Any, source: str) -> str:
    result = _nonempty_string(value, source)
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise TensionedCordAuditError(f"{source} must be a lowercase SHA-256 hex digest")
    return result


def _load_evidence(value: Any, source: str) -> TensionedCordEvidence:
    payload = _mapping(value, source)
    _closed(payload, {"url", "label", "reviewedAt"}, source)
    url = _nonempty_string(payload["url"], f"{source}.url")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise TensionedCordAuditError(f"{source}.url must be an HTTPS URL")
    return TensionedCordEvidence(
        url=url,
        label=_nonempty_string(payload["label"], f"{source}.label"),
        reviewed_at=_date(payload["reviewedAt"], f"{source}.reviewedAt"),
    )


def _load_record(value: Any, source: str) -> TensionedCordRecord:
    payload = _mapping(value, source)
    _closed(
        payload,
        {
            "packageID", "presentationID", "assetPath", "assetSHA256",
            "sourcePresentationID", "evidence", "orientation", "gravity",
            "tensionDirection", "visibleTopology", "routing", "terminals",
            "knots", "hardware", "status", "output", "blocker",
        },
        source,
    )
    status = _enum(payload["status"], _STATUSES, f"{source}.status")
    output = _enum(payload["output"], _STATUSES, f"{source}.output")
    blocker = _nullable_string(payload["blocker"], f"{source}.blocker")
    if output != status:
        raise TensionedCordAuditError(f"{source}.output must match status")
    if status == "blocked" and blocker is None:
        raise TensionedCordAuditError(f"{source}.blocker is required for blocked records")
    if status == "accepted" and blocker is not None:
        raise TensionedCordAuditError(f"{source}.blocker is only allowed for blocked records")
    gravity = _nonempty_string(payload["gravity"], f"{source}.gravity")
    if gravity != _GRAVITY:
        raise TensionedCordAuditError(f"{source}.gravity must be {_GRAVITY}")
    return TensionedCordRecord(
        package_id=_identifier(payload["packageID"], f"{source}.packageID"),
        presentation_id=_identifier(payload["presentationID"], f"{source}.presentationID"),
        asset_path=_asset_path(payload["assetPath"], f"{source}.assetPath"),
        asset_sha256=_sha256(payload["assetSHA256"], f"{source}.assetSHA256"),
        source_presentation_id=_nullable_identifier(
            payload["sourcePresentationID"], f"{source}.sourcePresentationID"
        ),
        evidence=_load_evidence(payload["evidence"], f"{source}.evidence"),
        orientation=_enum(payload["orientation"], _ORIENTATIONS, f"{source}.orientation"),
        gravity=gravity,
        tension_direction=_enum(
            payload["tensionDirection"], _TENSION_DIRECTIONS, f"{source}.tensionDirection"
        ),
        visible_topology=_enum(
            payload["visibleTopology"], _TOPOLOGIES, f"{source}.visibleTopology"
        ),
        routing=_enum(payload["routing"], _ROUTING, f"{source}.routing"),
        terminals=_enum(payload["terminals"], _COMPONENTS, f"{source}.terminals"),
        knots=_enum(payload["knots"], _COMPONENTS, f"{source}.knots"),
        hardware=_enum(payload["hardware"], _COMPONENTS, f"{source}.hardware"),
        status=status,
        output=output,
        blocker=blocker,
    )


def load_tensioned_cord_ledger(path: Path) -> TensionedCordLedger:
    """Load a strict ledger without inspecting the live Hangboards directory."""
    ledger_path = Path(path)
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise TensionedCordAuditError(f"tensioned cord ledger must be a regular file: {ledger_path}")
    try:
        payload = _mapping(json.loads(ledger_path.read_text(encoding="utf-8")), "tensioned cord ledger")
    except json.JSONDecodeError as error:
        raise TensionedCordAuditError(f"tensioned cord ledger is invalid JSON: {ledger_path}") from error
    _closed(payload, {"schemaVersion", "packageIDs", "records"}, "tensioned cord ledger")
    if isinstance(payload["schemaVersion"], bool) or payload["schemaVersion"] != 1:
        raise TensionedCordAuditError("tensioned cord ledger.schemaVersion must be 1")
    package_values = payload["packageIDs"]
    if not isinstance(package_values, list):
        raise TensionedCordAuditError("tensioned cord ledger.packageIDs must be an array")
    package_ids = tuple(
        _identifier(value, f"tensioned cord ledger.packageIDs[{index}]")
        for index, value in enumerate(package_values)
    )
    if len(package_ids) != len(set(package_ids)):
        raise TensionedCordAuditError("tensioned cord ledger.packageIDs must be unique")
    records_value = payload["records"]
    if not isinstance(records_value, list):
        raise TensionedCordAuditError("tensioned cord ledger.records must be an array")
    records = tuple(_load_record(value, f"tensioned cord ledger.records[{index}]") for index, value in enumerate(records_value))
    if {record.package_id for record in records} - set(package_ids):
        raise TensionedCordAuditError("tensioned cord ledger has records outside packageIDs")
    return TensionedCordLedger(schema_version=1, package_ids=package_ids, records=records)


def validate_tensioned_cord_ledger(
    ledger: TensionedCordLedger,
    inventory: BoardInventory,
    *,
    hangboards_root: Path,
) -> TensionedCordAuditReport:
    """Cross-check the closed 20-package/47-presentation ledger against assets."""
    if len(ledger.package_ids) != _PACKAGE_COUNT:
        raise TensionedCordAuditError(f"tensioned cord ledger must cover exactly {_PACKAGE_COUNT} packages")
    if len(ledger.records) != _PRESENTATION_COUNT:
        raise TensionedCordAuditError(f"tensioned cord ledger must cover exactly {_PRESENTATION_COUNT} presentations")
    root = Path(hangboards_root)
    if root.is_symlink() or not root.is_dir():
        raise TensionedCordAuditError(f"Hangboards root must be a regular directory: {root}")
    packages = {package.board.id: package for package in inventory.packages}
    unknown_packages = sorted(set(ledger.package_ids) - set(packages))
    if unknown_packages:
        raise TensionedCordAuditError(f"unknown ledger package IDs: {unknown_packages}")
    package_ids = set(ledger.package_ids)
    expected_keys = {
        (package.board.id, presentation.id)
        for package in inventory.packages
        if package.board.id in package_ids
        for presentation in package.board.presentations
    }
    records_by_key: dict[tuple[str, str], TensionedCordRecord] = {}
    for record in ledger.records:
        key = (record.package_id, record.presentation_id)
        if key in records_by_key:
            raise TensionedCordAuditError(f"duplicate record for {'/'.join(key)}")
        if key not in expected_keys:
            raise TensionedCordAuditError(f"unknown presentation for {'/'.join(key)}")
        records_by_key[key] = record
    missing = sorted(expected_keys - set(records_by_key))
    if missing:
        raise TensionedCordAuditError("missing record for " + "/".join(missing[0]))
    root_resolved = root.resolve()
    blockers: list[tuple[str, str, str]] = []
    accepted_count = 0
    for package_id, presentation_id in sorted(expected_keys):
        record = records_by_key[(package_id, presentation_id)]
        package = packages[package_id]
        presentation = next(item for item in package.board.presentations if item.id == presentation_id)
        if record.asset_path != presentation.asset_path:
            raise TensionedCordAuditError(f"asset path does not match for {package_id}/{presentation_id}")
        if record.source_presentation_id != presentation.source_presentation_id:
            raise TensionedCordAuditError(f"source presentation does not match for {package_id}/{presentation_id}")
        if presentation.is_inverted != (record.orientation == "inverted"):
            raise TensionedCordAuditError(f"orientation does not match for {package_id}/{presentation_id}")
        asset = package.root / presentation.asset_path
        try:
            asset.resolve().relative_to(root_resolved)
        except ValueError as error:
            raise TensionedCordAuditError(f"asset escapes Hangboards root for {package_id}/{presentation_id}") from error
        if asset.is_symlink() or not asset.is_file():
            raise TensionedCordAuditError(f"asset is missing for {package_id}/{presentation_id}")
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if digest != record.asset_sha256:
            raise TensionedCordAuditError(f"asset SHA-256 does not match for {package_id}/{presentation_id}")
        if record.status == "blocked":
            assert record.blocker is not None
            blockers.append((package_id, presentation_id, record.blocker))
        else:
            accepted_count += 1
    return TensionedCordAuditReport(
        package_count=len(ledger.package_ids),
        presentation_count=len(ledger.records),
        accepted_count=accepted_count,
        blocked_count=len(blockers),
        blockers=tuple(blockers),
    )
