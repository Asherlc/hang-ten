from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from conftest import write_board_package
from hangboard_packages.board_catalog import discover_board_packages
from hangboard_packages.metadata_audit import (
    MetadataAuditError,
    load_metadata_ledger,
    validate_metadata_ledger,
)


_FIELDS = (
    "kind",
    "sizeMillimeters",
    "depthRangeMillimeters",
    "fingerCapacity",
    "handCapacity",
    "gripType",
    "features",
)


def _record(
    board_id: str,
    hold_id: str,
    field: str,
    outcome: str,
    *,
    value: object | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "boardID": board_id,
        "holdIDs": [hold_id],
        "field": field,
        "outcome": outcome,
        "reviewedAt": "2026-08-25",
        "source": {
            "kind": "manufacturer",
            "url": "https://example.com/fixture-source",
            "label": "Fixture manufacturer source",
        },
    }
    if outcome == "verified":
        record["value"] = value
    else:
        record["reason"] = reason or "The manufacturer source does not establish this value."
    return record


def verified(board_id: str, hold_id: str, field: str, value: object) -> dict[str, object]:
    return _record(board_id, hold_id, field, "verified", value=value)


def unavailable(board_id: str, hold_id: str, field: str) -> dict[str, object]:
    return _record(board_id, hold_id, field, "unavailable")


def not_applicable(board_id: str, hold_id: str, field: str) -> dict[str, object]:
    return _record(board_id, hold_id, field, "notApplicable")


def _complete_records(
    board_id: str,
    hold_id: str,
    *,
    verified_values: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    values = {"kind": "jug", **(verified_values or {})}
    return [
        verified(board_id, hold_id, field, values[field])
        if field in values
        else unavailable(board_id, hold_id, field)
        for field in _FIELDS
    ]


def _write_ledger(
    tmp_path: Path,
    records: list[dict[str, object]],
    *,
    reviewed_board_ids: list[str] | None = None,
) -> Path:
    path = tmp_path / "metadata-ledger.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "reviewedBoardIDs": reviewed_board_ids or ["fixture.board"],
                "records": records,
            }
        ),
        encoding="utf-8",
    )
    return path


def _package_with_metadata(tmp_path: Path) -> Path:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["holds"][0].update(
        {
            "sizeMillimeters": 18,
            "depthRangeMillimeters": {"lowerBound": 10, "upperBound": 14.5},
            "fingerCapacity": 2,
            "handCapacity": 1,
            "gripType": "halfCrimp",
            "features": ["smallEdge", "incutEdge"],
        }
    )
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return package


def test_validates_exact_scalar_range_and_unavailable_metadata(tmp_path: Path) -> None:
    _package_with_metadata(tmp_path)
    records = _complete_records(
        "fixture.board",
        "hold-left",
        verified_values={
            "sizeMillimeters": 18,
            "depthRangeMillimeters": {"lowerBound": 10, "upperBound": 14.5},
            "fingerCapacity": 2,
            "handCapacity": 1,
            "gripType": "halfCrimp",
            "features": ["smallEdge", "incutEdge"],
        },
    )
    ledger_path = _write_ledger(tmp_path, records)

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path),
        discover_board_packages(tmp_path / "boards"),
    )

    assert report.reviewed_board_ids == ("fixture.board",)
    assert report.fields["sizeMillimeters"].populated == 1
    assert report.fields["sizeMillimeters"].verified == 1
    assert report.fields["depthRangeMillimeters"].populated == 1
    assert report.fields["depthRangeMillimeters"].verified == 1
    assert report.fields["features"].populated == 1
    assert report.boards[0].unaccounted_fields == 0
    assert report.to_json() == {
        "reviewedBoardIDs": ["fixture.board"],
        "fields": {
            field: {
                "populated": 1,
                "verified": 1,
                "unavailable": 0,
                "notApplicable": 0,
            }
            for field in _FIELDS
        },
        "boards": [
            {
                "boardID": "fixture.board",
                "populated": 7,
                "verified": 7,
                "unavailable": 0,
                "notApplicable": 0,
                "unaccountedFields": 0,
            }
        ],
    }


def test_metolius_contract_rejects_unavailable_kind(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    records = _complete_records("fixture.board", "hold-left")
    records[0] = unavailable("fixture.board", "hold-left", "kind")
    ledger_path = _write_ledger(tmp_path, records)

    with pytest.raises(MetadataAuditError, match="kind must be verified"):
        load_metadata_ledger(ledger_path)


def test_metolius_contract_verified_kind_must_match_package(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    records = _complete_records(
        "fixture.board", "hold-left", verified_values={"kind": "edge"}
    )
    ledger_path = _write_ledger(tmp_path, records)

    with pytest.raises(MetadataAuditError, match="kind does not match"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger_path),
            discover_board_packages(tmp_path / "boards"),
        )


def test_reviewed_catalog_ledger_has_complete_seven_field_coverage() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    ledger_path = (
        repository_root
        / "docs/source-audits/2026-08-25-hangboard-metadata-ledger.json"
    )

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path),
        discover_board_packages(repository_root / "Hangboards"),
    )

    assert report.reviewed_board_ids == (
        "metolius.climbers-edge",
        "metolius.contact",
        "metolius.foundry",
        "metolius.light-rail-2",
        "metolius.prime-rib",
        "metolius.project",
        "metolius.rock-rings-3d",
        "metolius.simulator-3d",
        "metolius.wood-grips-compact-ii",
        "metolius.wood-grips-deluxe-ii",
        "soill.iron-palm-2",
        "soill.split-palm",
        "soill.training-tiles",
        "tension.flash-board",
        "tension.grindstone",
        "tension.honestone",
        "tension.whetstone",
    )
    assert all(board.unaccounted_fields == 0 for board in report.boards)


def test_unavailable_value_must_be_absent_from_package(tmp_path: Path) -> None:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["holds"][0]["sizeMillimeters"] = 18
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    ledger = _write_ledger(tmp_path, _complete_records("fixture.board", "hold-left"))

    with pytest.raises(MetadataAuditError, match="sizeMillimeters must be absent"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_rejects_an_unknown_hold_id(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    ledger = _write_ledger(tmp_path, _complete_records("fixture.board", "unknown-hold"))

    with pytest.raises(MetadataAuditError, match="unknown hold ID: unknown-hold"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_rejects_duplicate_expanded_record_keys(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    records = _complete_records("fixture.board", "hold-left")
    records.append(unavailable("fixture.board", "hold-left", "sizeMillimeters"))
    ledger = _write_ledger(tmp_path, records)

    with pytest.raises(MetadataAuditError, match="duplicate record for fixture.board/hold-left/sizeMillimeters"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_verified_scalar_must_equal_the_package_value(tmp_path: Path) -> None:
    package = write_board_package(tmp_path / "boards" / "fixture", board_id="fixture.board")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["holds"][0]["sizeMillimeters"] = 20
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    ledger = _write_ledger(
        tmp_path,
        _complete_records(
            "fixture.board", "hold-left", verified_values={"sizeMillimeters": 18}
        ),
    )

    with pytest.raises(MetadataAuditError, match="sizeMillimeters does not match"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_rejects_incomplete_reviewed_board(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    ledger = _write_ledger(
        tmp_path,
        [unavailable("fixture.board", "hold-left", "sizeMillimeters")],
    )

    with pytest.raises(MetadataAuditError, match="missing record for fixture.board/hold-left/depthRangeMillimeters"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


@pytest.mark.parametrize("schema_version", [True, 1.0])
def test_parser_requires_schema_version_to_be_json_integer_one(
    tmp_path: Path, schema_version: object
) -> None:
    ledger = _write_ledger(tmp_path, _complete_records("fixture.board", "hold-left"))
    document = json.loads(ledger.read_text(encoding="utf-8"))
    document["schemaVersion"] = schema_version
    ledger.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(MetadataAuditError, match="schemaVersion must be 1"):
        load_metadata_ledger(ledger)


def test_parser_rejects_https_url_without_a_hostname(tmp_path: Path) -> None:
    ledger = _write_ledger(tmp_path, _complete_records("fixture.board", "hold-left"))
    document = json.loads(ledger.read_text(encoding="utf-8"))
    document["records"][0]["source"]["url"] = "https://@/source"
    ledger.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(MetadataAuditError, match="source.url must be an HTTPS URL"):
        load_metadata_ledger(ledger)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document.__setitem__("unexpected", True),
            "metadata ledger has unknown keys",
        ),
        (
            lambda document: document["records"][0]["source"].__setitem__("url", "http://example.com"),
            "source.url must be an HTTPS URL",
        ),
        (
            lambda document: document["records"][0].__setitem__("reviewedAt", "not-a-date"),
            "reviewedAt must be an ISO date",
        ),
    ],
)
def test_parser_rejects_non_auditable_ledger_shapes(
    tmp_path: Path, mutation: Any, message: str
) -> None:
    records = _complete_records("fixture.board", "hold-left")
    ledger = _write_ledger(tmp_path, records)
    document = json.loads(ledger.read_text(encoding="utf-8"))
    mutation(document)
    ledger.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(MetadataAuditError, match=message):
        load_metadata_ledger(ledger)
