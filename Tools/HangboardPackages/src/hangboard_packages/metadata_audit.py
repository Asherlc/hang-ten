"""Source-audited metadata ledger parsing and package cross-checking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .board_catalog import BoardHold, BoardInventory, is_board_identifier


_FIELDS = frozenset(
    {
        "kind",
        "sizeMillimeters",
        "depthRangeMillimeters",
        "fingerCapacity",
        "handCapacity",
        "gripType",
        "features",
    }
)
_OUTCOMES = frozenset({"verified", "unavailable", "notApplicable"})


class MetadataAuditError(ValueError):
    """Raised when a metadata audit ledger is malformed or disagrees with packages."""


@dataclass(frozen=True)
class MetadataSource:
    kind: str
    url: str
    label: str


@dataclass(frozen=True)
class MetadataRecord:
    board_id: str
    hold_ids: tuple[str, ...]
    field: str
    outcome: str
    reviewed_at: date
    source: MetadataSource
    value: object | None
    reason: str | None


@dataclass(frozen=True)
class MetadataLedger:
    schema_version: int
    reviewed_board_ids: tuple[str, ...]
    records: tuple[MetadataRecord, ...]


@dataclass(frozen=True)
class MetadataFieldCoverage:
    populated: int
    verified: int
    unavailable: int
    not_applicable: int

    def to_json(self) -> dict[str, int]:
        return {
            "populated": self.populated,
            "verified": self.verified,
            "unavailable": self.unavailable,
            "notApplicable": self.not_applicable,
        }


@dataclass(frozen=True)
class BoardMetadataCoverage:
    board_id: str
    populated: int
    verified: int
    unavailable: int
    not_applicable: int
    unaccounted_fields: int

    def to_json(self) -> dict[str, int | str]:
        return {
            "boardID": self.board_id,
            "populated": self.populated,
            "verified": self.verified,
            "unavailable": self.unavailable,
            "notApplicable": self.not_applicable,
            "unaccountedFields": self.unaccounted_fields,
        }


@dataclass(frozen=True)
class MetadataCoverageReport:
    reviewed_board_ids: tuple[str, ...]
    fields: Mapping[str, MetadataFieldCoverage]
    boards: tuple[BoardMetadataCoverage, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "reviewedBoardIDs": list(self.reviewed_board_ids),
            "fields": {
                field: self.fields[field].to_json() for field in sorted(self.fields)
            },
            "boards": [board.to_json() for board in self.boards],
        }


def _mapping(value: Any, source: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MetadataAuditError(f"{source} must be an object")
    return value


def _closed(payload: Mapping[str, Any], required: set[str], source: str) -> None:
    unknown = set(payload) - required
    missing = required - set(payload)
    if unknown:
        raise MetadataAuditError(f"{source} has unknown keys: {sorted(unknown)}")
    if missing:
        raise MetadataAuditError(f"{source} is missing keys: {sorted(missing)}")


def _nonempty_string(value: Any, source: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MetadataAuditError(f"{source} must be a non-empty string")
    return value


def _identifier(value: Any, source: str) -> str:
    result = _nonempty_string(value, source)
    if not is_board_identifier(result):
        raise MetadataAuditError(f"{source} must be identifier-shaped")
    return result


def _number(value: Any, source: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MetadataAuditError(f"{source} must be a JSON number")
    if not math.isfinite(value):
        raise MetadataAuditError(f"{source} must be a finite JSON number")
    return value


def _load_source(value: Any, source: str) -> MetadataSource:
    payload = _mapping(value, source)
    _closed(payload, {"kind", "url", "label"}, source)
    if payload["kind"] != "manufacturer":
        raise MetadataAuditError(f"{source}.kind must be manufacturer")
    url = _nonempty_string(payload["url"], f"{source}.url")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise MetadataAuditError(f"{source}.url must be an HTTPS URL")
    return MetadataSource(
        kind="manufacturer",
        url=url,
        label=_nonempty_string(payload["label"], f"{source}.label"),
    )


def _load_date(value: Any, source: str) -> date:
    text = _nonempty_string(value, source)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise MetadataAuditError(f"{source} must be an ISO date") from error
    if parsed.isoformat() != text:
        raise MetadataAuditError(f"{source} must be an ISO date")
    return parsed


def _load_hold_ids(value: Any, source: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise MetadataAuditError(f"{source} must be a non-empty array")
    hold_ids = tuple(
        _identifier(hold_id, f"{source}[{index}]")
        for index, hold_id in enumerate(value)
    )
    if len(hold_ids) != len(set(hold_ids)):
        raise MetadataAuditError(f"{source} must not contain duplicate hold IDs")
    return hold_ids


def _load_verified_value(value: Any, field: str, source: str) -> object:
    if field == "kind":
        return _nonempty_string(value, source)
    if field in {"sizeMillimeters", "fingerCapacity", "handCapacity"}:
        return _number(value, source)
    if field == "depthRangeMillimeters":
        payload = _mapping(value, source)
        _closed(payload, {"lowerBound", "upperBound"}, source)
        lower = _number(payload["lowerBound"], f"{source}.lowerBound")
        upper = _number(payload["upperBound"], f"{source}.upperBound")
        return {"lowerBound": lower, "upperBound": upper}
    if field == "gripType":
        return _nonempty_string(value, source)
    assert field == "features"
    if not isinstance(value, list):
        raise MetadataAuditError(f"{source} must be an array")
    return [
        _nonempty_string(feature, f"{source}[{index}]")
        for index, feature in enumerate(value)
    ]


def _load_record(value: Any, source: str) -> MetadataRecord:
    payload = _mapping(value, source)
    base_keys = {
        "boardID",
        "holdIDs",
        "field",
        "outcome",
        "reviewedAt",
        "source",
    }
    outcome = payload.get("outcome")
    if outcome == "verified":
        _closed(payload, base_keys | {"value"}, source)
    elif outcome in {"unavailable", "notApplicable"}:
        _closed(payload, base_keys | {"reason"}, source)
    else:
        _closed(payload, base_keys, source)
        raise MetadataAuditError(f"{source}.outcome must be one of {sorted(_OUTCOMES)}")

    field = _nonempty_string(payload["field"], f"{source}.field")
    if field not in _FIELDS:
        raise MetadataAuditError(f"{source}.field is unsupported")
    if field == "kind" and outcome != "verified":
        raise MetadataAuditError(f"{source}.kind must be verified")
    return MetadataRecord(
        board_id=_identifier(payload["boardID"], f"{source}.boardID"),
        hold_ids=_load_hold_ids(payload["holdIDs"], f"{source}.holdIDs"),
        field=field,
        outcome=outcome,
        reviewed_at=_load_date(payload["reviewedAt"], f"{source}.reviewedAt"),
        source=_load_source(payload["source"], f"{source}.source"),
        value=(
            _load_verified_value(payload["value"], field, f"{source}.value")
            if outcome == "verified"
            else None
        ),
        reason=(
            _nonempty_string(payload["reason"], f"{source}.reason")
            if outcome != "verified"
            else None
        ),
    )


def load_metadata_ledger(path: Path) -> MetadataLedger:
    """Load a closed-schema metadata ledger without inspecting packages."""
    ledger_path = Path(path)
    if ledger_path.is_symlink() or not ledger_path.is_file():
        raise MetadataAuditError(f"metadata ledger must be a regular file: {ledger_path}")
    try:
        payload = _mapping(
            json.loads(ledger_path.read_text(encoding="utf-8")), "metadata ledger"
        )
    except json.JSONDecodeError as error:
        raise MetadataAuditError(f"metadata ledger is invalid JSON: {ledger_path}") from error
    _closed(payload, {"schemaVersion", "reviewedBoardIDs", "records"}, "metadata ledger")
    if (
        isinstance(payload["schemaVersion"], bool)
        or not isinstance(payload["schemaVersion"], int)
        or payload["schemaVersion"] != 1
    ):
        raise MetadataAuditError("metadata ledger.schemaVersion must be 1")
    reviewed_value = payload["reviewedBoardIDs"]
    if not isinstance(reviewed_value, list) or not reviewed_value:
        raise MetadataAuditError("metadata ledger.reviewedBoardIDs must be a non-empty array")
    reviewed_board_ids = tuple(
        _identifier(board_id, f"metadata ledger.reviewedBoardIDs[{index}]")
        for index, board_id in enumerate(reviewed_value)
    )
    if len(reviewed_board_ids) != len(set(reviewed_board_ids)):
        raise MetadataAuditError("metadata ledger.reviewedBoardIDs must be unique")
    records_value = payload["records"]
    if not isinstance(records_value, list):
        raise MetadataAuditError("metadata ledger.records must be an array")
    records = tuple(
        _load_record(record, f"metadata ledger.records[{index}]")
        for index, record in enumerate(records_value)
    )
    unreviewed = sorted({record.board_id for record in records} - set(reviewed_board_ids))
    if unreviewed:
        raise MetadataAuditError(
            f"metadata ledger has records for unreviewed board IDs: {unreviewed}"
        )
    return MetadataLedger(
        schema_version=1,
        reviewed_board_ids=tuple(sorted(reviewed_board_ids)),
        records=records,
    )


def _hold_value(hold: BoardHold, field: str) -> object | None:
    if field == "kind":
        return hold.kind
    if field == "sizeMillimeters":
        return hold.size_millimeters
    if field == "depthRangeMillimeters":
        if hold.depth_range_millimeters is None:
            return None
        return {
            "lowerBound": hold.depth_range_millimeters.lower_bound,
            "upperBound": hold.depth_range_millimeters.upper_bound,
        }
    if field == "fingerCapacity":
        return hold.finger_capacity
    if field == "handCapacity":
        return hold.hand_capacity
    if field == "gripType":
        return hold.grip_type
    assert field == "features"
    return list(hold.features) if hold.features is not None else None


def _values_match(expected: object, actual: object) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return False
    return expected == actual


def validate_metadata_ledger(
    ledger: MetadataLedger, inventory: BoardInventory
) -> MetadataCoverageReport:
    """Cross-check every reviewed source record against its discovered package hold."""
    packages = {package.board.id: package.board for package in inventory.packages}
    unknown_boards = sorted(set(ledger.reviewed_board_ids) - set(packages))
    if unknown_boards:
        raise MetadataAuditError(f"unknown reviewed board IDs: {unknown_boards}")

    records_by_key: dict[tuple[str, str, str], MetadataRecord] = {}
    holds_by_board = {
        board_id: {hold.id: hold for hold in packages[board_id].holds}
        for board_id in ledger.reviewed_board_ids
    }
    for record in ledger.records:
        holds = holds_by_board[record.board_id]
        for hold_id in record.hold_ids:
            if hold_id not in holds:
                raise MetadataAuditError(f"unknown hold ID: {hold_id}")
            key = (record.board_id, hold_id, record.field)
            if key in records_by_key:
                raise MetadataAuditError(
                    "duplicate record for " + "/".join(key)
                )
            records_by_key[key] = record

    field_totals = {
        field: {"populated": 0, "verified": 0, "unavailable": 0, "notApplicable": 0}
        for field in _FIELDS
    }
    board_reports: list[BoardMetadataCoverage] = []
    for board_id in ledger.reviewed_board_ids:
        board_totals = {"populated": 0, "verified": 0, "unavailable": 0, "notApplicable": 0}
        for hold_id, hold in sorted(holds_by_board[board_id].items()):
            for field in sorted(_FIELDS):
                key = (board_id, hold_id, field)
                record = records_by_key.get(key)
                if record is None:
                    raise MetadataAuditError(f"missing record for {'/'.join(key)}")
                actual = _hold_value(hold, field)
                if record.outcome == "verified":
                    if actual is None:
                        raise MetadataAuditError(
                            f"{field} is absent for {board_id}/{hold_id}"
                        )
                    if not _values_match(record.value, actual):
                        raise MetadataAuditError(
                            f"{field} does not match for {board_id}/{hold_id}"
                        )
                    outcome = "verified"
                else:
                    if actual is not None:
                        raise MetadataAuditError(
                            f"{field} must be absent for {board_id}/{hold_id}"
                        )
                    outcome = record.outcome
                field_totals[field]["populated"] += actual is not None
                field_totals[field][outcome] += 1
                board_totals["populated"] += actual is not None
                board_totals[outcome] += 1
        board_reports.append(
            BoardMetadataCoverage(
                board_id=board_id,
                populated=board_totals["populated"],
                verified=board_totals["verified"],
                unavailable=board_totals["unavailable"],
                not_applicable=board_totals["notApplicable"],
                unaccounted_fields=0,
            )
        )
    return MetadataCoverageReport(
        reviewed_board_ids=ledger.reviewed_board_ids,
        fields={
            field: MetadataFieldCoverage(
                populated=field_totals[field]["populated"],
                verified=field_totals[field]["verified"],
                unavailable=field_totals[field]["unavailable"],
                not_applicable=field_totals[field]["notApplicable"],
            )
            for field in sorted(_FIELDS)
        },
        boards=tuple(sorted(board_reports, key=lambda report: report.board_id)),
    )
