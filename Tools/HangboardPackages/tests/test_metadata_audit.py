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
    "depth",
    "fingerCapacity",
    "handCapacity",
    "gripType",
    "shape",
)


def _scalar_depth(contact: object) -> int | float | None:
    depth = contact.depth
    if depth is None or depth.range is None or depth.range.minimum != depth.range.maximum:
        return None
    return depth.range.minimum


def _single_grip_type(contact: object) -> str | None:
    return next(iter(contact.grip_types)) if len(contact.grip_types) == 1 else None


def _rename_fixture_geometry(document: dict[str, Any], contact_id: str) -> list[dict[str, Any]]:
    geometry = document["presentations"][0]["media"]["contactGeometry"]
    pieces = geometry.pop("hold-left")
    geometry[contact_id] = pieces
    return pieces


def _copy_fixture_geometry(
    document: dict[str, Any], contact_id: str, pieces: list[dict[str, Any]]
) -> None:
    document["presentations"][0]["media"]["contactGeometry"][contact_id] = pieces


def _record(
    board_id: str,
    contact_id: str,
    field: str,
    outcome: str,
    *,
    value: object | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "boardID": board_id,
        "contactIDs": [contact_id],
        "field": field,
        "outcome": outcome,
        "reviewedAt": "2026-08-25",
        "source": {
            "kind": "manufacturer",
            "url": "https://example.com/fixture-source",
            "label": "Fixture manufacturer source",
        },
    }
    if outcome in {"verified", "adapted"}:
        record["value"] = value
    if outcome != "verified":
        record["reason"] = reason or "The manufacturer source does not establish this value."
    return record


def verified(board_id: str, contact_id: str, field: str, value: object) -> dict[str, object]:
    return _record(board_id, contact_id, field, "verified", value=value)


def unavailable(board_id: str, contact_id: str, field: str) -> dict[str, object]:
    return _record(board_id, contact_id, field, "unavailable")


def not_applicable(board_id: str, contact_id: str, field: str) -> dict[str, object]:
    return _record(board_id, contact_id, field, "notApplicable")


def test_adapted_record_matches_board_value(tmp_path: Path) -> None:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0].update({"id": "edge-left", "kind": "edge"})
    _rename_fixture_geometry(document, "edge-left")
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    records = _complete_records("fixture.board", "edge-left")
    records[0] = _record(
        "fixture.board",
        "edge-left",
        "kind",
        "adapted",
        value="edge",
        reason="Hang Ten adaptation",
    )

    report = validate_metadata_ledger(
        load_metadata_ledger(_write_ledger(tmp_path, records)),
        discover_board_packages(tmp_path / "boards"),
    )

    assert report.fields["kind"].adapted == 1


def test_parser_rejects_adapted_record_without_reason(tmp_path: Path) -> None:
    records = _complete_records("fixture.board", "hold-left")
    records[0] = _record(
        "fixture.board",
        "hold-left",
        "kind",
        "adapted",
        value="jug",
        reason="Adapted role",
    )
    records[0].pop("reason")

    with pytest.raises(MetadataAuditError, match=r"missing keys: \['reason'\]"):
        load_metadata_ledger(_write_ledger(tmp_path, records))


def test_parser_rejects_legacy_hold_ids_field(tmp_path: Path) -> None:
    records = _complete_records("fixture.board", "hold-left")
    records[0]["holdIDs"] = records[0].pop("contactIDs")

    with pytest.raises(MetadataAuditError, match="holdIDs"):
        load_metadata_ledger(_write_ledger(tmp_path, records))


def test_parser_rejects_adapted_record_with_blank_reason(tmp_path: Path) -> None:
    records = _complete_records("fixture.board", "hold-left")
    records[0] = _record(
        "fixture.board",
        "hold-left",
        "kind",
        "adapted",
        value="jug",
        reason="   ",
    )

    with pytest.raises(MetadataAuditError, match="reason must be a non-empty string"):
        load_metadata_ledger(_write_ledger(tmp_path, records))


def test_parser_rejects_adapted_record_without_value(tmp_path: Path) -> None:
    records = _complete_records("fixture.board", "hold-left")
    records[0] = _record(
        "fixture.board",
        "hold-left",
        "kind",
        "adapted",
        value="jug",
        reason="Adapted role",
    )
    records[0].pop("value")

    with pytest.raises(MetadataAuditError, match=r"missing keys: \['value'\]"):
        load_metadata_ledger(_write_ledger(tmp_path, records))


def test_validator_rejects_mismatched_adapted_value(tmp_path: Path) -> None:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0].update({"id": "edge-left", "kind": "edge"})
    _rename_fixture_geometry(document, "edge-left")
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    records = _complete_records("fixture.board", "edge-left")
    records[0] = _record(
        "fixture.board",
        "edge-left",
        "kind",
        "adapted",
        value="jug",
        reason="Adapted role",
    )

    with pytest.raises(MetadataAuditError, match="kind does not match"):
        validate_metadata_ledger(
            load_metadata_ledger(_write_ledger(tmp_path, records)),
            discover_board_packages(tmp_path / "boards"),
        )


def _complete_records(
    board_id: str,
    contact_id: str,
    *,
    verified_values: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    values = {"kind": "jug", **(verified_values or {})}
    records: list[dict[str, object]] = []
    for field in _FIELDS:
        if field in values:
            records.append(verified(board_id, contact_id, field, values[field]))
        else:
            records.append(unavailable(board_id, contact_id, field))
    return records


def _write_ledger(
    tmp_path: Path,
    records: list[dict[str, object]],
    *,
    reviewed_board_ids: list[str] | None = None,
    sloper_only_board_ids: list[str] | None = None,
) -> Path:
    path = tmp_path / "metadata-ledger.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "reviewedBoardIDs": (
                    ["fixture.board"]
                    if reviewed_board_ids is None
                    else reviewed_board_ids
                ),
                "sloperOnlyBoardIDs": sloper_only_board_ids or [],
                "records": records,
            }
        ),
        encoding="utf-8",
    )
    return path


def _supplemental_sloper_package(tmp_path: Path) -> None:
    package = write_board_package(
        tmp_path / "boards" / "supplemental", board_id="supplemental.board"
    )
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0].update({"id": "sloper-left", "kind": "sloper"})
    pieces = _rename_fixture_geometry(document, "sloper-left")
    non_sloper = dict(document["contacts"][0])
    non_sloper.update({"id": "edge-right", "kind": "edge"})
    document["contacts"].append(non_sloper)
    _copy_fixture_geometry(document, "edge-right", pieces)
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")


def _supplemental_sloper_records() -> list[dict[str, object]]:
    return [
        unavailable("supplemental.board", "sloper-left", "shape"),
        unavailable("supplemental.board", "edge-right", "shape"),
    ]


def test_parser_declares_a_disjoint_sloper_only_board_scope(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        [unavailable("supplemental.board", "sloper-left", "shape")],
        reviewed_board_ids=["fixture.board"],
        sloper_only_board_ids=["supplemental.board"],
    )

    ledger = load_metadata_ledger(ledger_path)

    assert ledger.reviewed_board_ids == ("fixture.board",)
    assert ledger.sloper_only_board_ids == ("supplemental.board",)


def test_parser_preserves_secondary_source_provenance(tmp_path: Path) -> None:
    record = verified("fixture.board", "hold-left", "kind", "jug")
    source = record["source"]
    assert isinstance(source, dict)
    source["kind"] = "secondary"
    source["label"] = "Fixture community measurement"

    ledger = load_metadata_ledger(_write_ledger(tmp_path, [record]))

    assert ledger.records[0].source.kind == "secondary"
    assert ledger.records[0].source.label == "Fixture community measurement"


def test_parser_rejects_board_in_full_and_sloper_only_scopes(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        [],
        reviewed_board_ids=["fixture.board"],
        sloper_only_board_ids=["fixture.board"],
    )

    with pytest.raises(MetadataAuditError, match="board scopes must be disjoint"):
        load_metadata_ledger(ledger_path)


def test_parser_rejects_unrelated_field_for_sloper_only_board(tmp_path: Path) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        [unavailable("supplemental.board", "sloper-left", "depth")],
        sloper_only_board_ids=["supplemental.board"],
    )

    with pytest.raises(
        MetadataAuditError,
        match="sloper-only board supplemental.board must use field shape",
    ):
        load_metadata_ledger(ledger_path)


def test_sloper_only_scope_requires_exactly_one_record_per_hold(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "full", board_id="fixture.board")
    _supplemental_sloper_package(tmp_path)
    records = [
        *_complete_records("fixture.board", "hold-left"),
        *_supplemental_sloper_records(),
    ]
    ledger_path = _write_ledger(
        tmp_path,
        records,
        sloper_only_board_ids=["supplemental.board"],
    )

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path), discover_board_packages(tmp_path / "boards")
    )

    assert report.sloper_only_board_ids == ("supplemental.board",)
    supplemental = next(
        board for board in report.boards if board.board_id == "supplemental.board"
    )
    assert supplemental.to_json() == {
        "boardID": "supplemental.board",
        "populated": 0,
        "verified": 0,
        "adapted": 0,
        "unavailable": 2,
        "notApplicable": 0,
        "unaccountedFields": 0,
    }


def test_sloper_only_scope_rejects_swapped_sloper_outcomes(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "full", board_id="fixture.board")
    package = tmp_path / "boards" / "supplemental"
    _supplemental_sloper_package(tmp_path)
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0]["shape"] = "flat"
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    records = [
        *_complete_records("fixture.board", "hold-left"),
        not_applicable("supplemental.board", "sloper-left", "shape"),
        unavailable("supplemental.board", "edge-right", "shape"),
    ]
    ledger_path = _write_ledger(
        tmp_path,
        records,
        sloper_only_board_ids=["supplemental.board"],
    )

    with pytest.raises(
        MetadataAuditError,
        match="shape must be absent for supplemental.board/sloper-left",
    ):
        validate_metadata_ledger(
            load_metadata_ledger(ledger_path),
            discover_board_packages(tmp_path / "boards"),
        )


def test_reviewed_scope_rejects_shape_outcome_that_omits_a_populated_shape(
    tmp_path: Path,
) -> None:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0].update(
        {"id": "sloper-left", "kind": "sloper", "shape": "flat"}
    )
    pieces = _rename_fixture_geometry(document, "sloper-left")
    edge = dict(document["contacts"][0])
    edge.update({"id": "edge-right", "kind": "edge"})
    edge.pop("shape")
    document["contacts"].append(edge)
    _copy_fixture_geometry(document, "edge-right", pieces)
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")

    records = [
        *_complete_records(
            "fixture.board", "sloper-left", verified_values={"kind": "sloper"}
        ),
        *_complete_records(
            "fixture.board", "edge-right", verified_values={"kind": "edge"}
        ),
    ]
    for record in records:
        if record["field"] == "shape" and record["contactIDs"] == ["sloper-left"]:
            record.clear()
            record.update(_record("fixture.board", "sloper-left", "shape", "notApplicable"))
    ledger_path = _write_ledger(tmp_path, records)

    with pytest.raises(
        MetadataAuditError,
        match="shape must be absent for fixture.board/sloper-left",
    ):
        validate_metadata_ledger(
            load_metadata_ledger(ledger_path),
            discover_board_packages(tmp_path / "boards"),
        )


def test_sloper_only_scope_rejects_missing_record(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "full", board_id="fixture.board")
    _supplemental_sloper_package(tmp_path)
    records = [
        *_complete_records("fixture.board", "hold-left"),
        unavailable("supplemental.board", "sloper-left", "shape"),
    ]
    ledger_path = _write_ledger(
        tmp_path,
        records,
        sloper_only_board_ids=["supplemental.board"],
    )

    with pytest.raises(
        MetadataAuditError,
        match="missing record for supplemental.board/edge-right/shape",
    ):
        validate_metadata_ledger(
            load_metadata_ledger(ledger_path),
            discover_board_packages(tmp_path / "boards"),
        )


def test_sloper_only_scope_rejects_duplicate_record(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "full", board_id="fixture.board")
    _supplemental_sloper_package(tmp_path)
    records = [
        *_complete_records("fixture.board", "hold-left"),
        *_supplemental_sloper_records(),
        unavailable("supplemental.board", "sloper-left", "shape"),
    ]
    ledger_path = _write_ledger(
        tmp_path,
        records,
        sloper_only_board_ids=["supplemental.board"],
    )

    with pytest.raises(
        MetadataAuditError,
        match="duplicate record for supplemental.board/sloper-left/shape",
    ):
        validate_metadata_ledger(
            load_metadata_ledger(ledger_path),
            discover_board_packages(tmp_path / "boards"),
        )


def _package_with_metadata(tmp_path: Path) -> Path:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0].update(
        {
            "depth": {"range": {"minimum": 18, "maximum": 18}},
            "fingerCapacity": 2,
            "handCapacity": 1,
            "gripTypes": ["halfCrimp"],
            "shape": "incut",
        }
    )
    range_hold = dict(document["contacts"][0])
    range_hold.update(
        {
            "id": "hold-range",
            "name": "Range hold",
            "depth": {"range": {"minimum": 10, "maximum": 14.5}},
        }
    )
    document["contacts"].append(range_hold)
    _copy_fixture_geometry(
        document,
        "hold-range",
        document["presentations"][0]["media"]["contactGeometry"]["hold-left"],
    )
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return package


def _package_with_flat_sloper(tmp_path: Path, sloper: dict[str, object] | None = None) -> Path:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    sloper_type = (sloper or {"type": "flat"})["type"]
    document["contacts"][0].update(
        {
            "kind": "sloper",
            "shape": sloper_type,
        }
    )
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return package


def _package_with_sloper_without_subtype_metadata(tmp_path: Path) -> Path:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0]["kind"] = "sloper"
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return package


def _sloper_ledger_records(
    value: object, *, source: dict[str, object] | None = None
) -> list[dict[str, object]]:
    records = [
        {
            "boardID": "fixture.board",
            "contactIDs": ["hold-left"],
            "field": "kind",
            "outcome": "verified",
            "reviewedAt": "2026-08-25",
            "source": {
                "kind": "manufacturer",
                "url": "https://example.com/fixture-source",
                "label": "Fixture manufacturer source",
            },
            "value": "sloper",
        },
        {
            "boardID": "fixture.board",
            "contactIDs": ["hold-left"],
            "field": "shape",
            "outcome": "verified",
            "reviewedAt": "2026-08-25",
            "source": source
            or {
                "kind": "manufacturer",
                "url": "https://example.com/fixture-source",
                "label": "Fixture manufacturer source",
            },
            "value": value["type"],
        },
    ]
    records.extend(
        unavailable("fixture.board", "hold-left", field)
        for field in _FIELDS
        if field not in {"kind", "shape"}
    )
    return records


def test_sloper_ledger_verified_value_matches_flat_hold(tmp_path: Path) -> None:
    _package_with_flat_sloper(tmp_path)
    ledger_path = _write_ledger(
        tmp_path,
        _sloper_ledger_records({"type": "flat"}),
    )

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path), discover_board_packages(tmp_path / "boards")
    )

    assert report.fields["shape"].to_json() == {
        "populated": 1,
        "verified": 1,
        "adapted": 0,
        "unavailable": 0,
        "notApplicable": 0,
    }


def test_sloper_ledger_verified_value_matches_round_hold(
    tmp_path: Path,
) -> None:
    _package_with_flat_sloper(tmp_path, {"type": "round"})
    ledger_path = _write_ledger(
        tmp_path,
        _sloper_ledger_records({"type": "round"}),
    )

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path), discover_board_packages(tmp_path / "boards")
    )

    assert report.fields["shape"].to_json()["verified"] == 1


def test_sloper_ledger_allows_unavailable_record_for_omitted_metadata(
    tmp_path: Path,
) -> None:
    _package_with_sloper_without_subtype_metadata(tmp_path)
    ledger_path = _write_ledger(
        tmp_path,
        [
            {
                "boardID": "fixture.board",
                "contactIDs": ["hold-left"],
                "field": "kind",
                "outcome": "verified",
                "reviewedAt": "2026-08-25",
                "source": {
                    "kind": "manufacturer",
                    "url": "https://example.com/fixture-source",
                    "label": "Fixture manufacturer source",
                },
                "value": "sloper",
            },
            *(
                unavailable("fixture.board", "hold-left", field)
                for field in _FIELDS
                if field != "kind"
            ),
        ],
    )

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path), discover_board_packages(tmp_path / "boards")
    )

    assert report.fields["shape"].to_json() == {
        "populated": 0,
        "verified": 0,
        "adapted": 0,
        "unavailable": 1,
        "notApplicable": 0,
    }


def test_shape_ledger_rejects_unsupported_shape(tmp_path: Path) -> None:
    _package_with_flat_sloper(tmp_path)
    ledger_path = _write_ledger(
        tmp_path,
        _sloper_ledger_records({"type": "oval"}),
    )

    with pytest.raises(MetadataAuditError, match="unsupported"):
        load_metadata_ledger(ledger_path)


@pytest.mark.parametrize(
    "source",
    [
        {
            "kind": "retailer",
            "url": "https://example.com/fixture-source",
            "label": "Retailer source",
        },
        {
            "kind": "manufacturer",
            "url": "http://example.com/fixture-source",
            "label": "Insecure source",
        },
    ],
)
def test_sloper_ledger_rejects_non_manufacturer_or_non_https_source(
    tmp_path: Path, source: dict[str, object]
) -> None:
    ledger_path = _write_ledger(
        tmp_path,
        _sloper_ledger_records({"type": "flat", "angleDegrees": 20}, source=source),
    )

    with pytest.raises(MetadataAuditError, match="source.(kind|url)"):
        load_metadata_ledger(ledger_path)


def test_validates_exact_scalar_range_and_unavailable_metadata(tmp_path: Path) -> None:
    _package_with_metadata(tmp_path)
    records = _complete_records(
        "fixture.board",
        "hold-left",
        verified_values={
            "depth": {"range": {"minimum": 18, "maximum": 18}},
            "fingerCapacity": 2,
            "handCapacity": 1,
            "gripType": "halfCrimp",
            "shape": "incut",
        },
    )
    records.extend(
        _complete_records(
            "fixture.board",
            "hold-range",
            verified_values={
                "depth": {"range": {"minimum": 10, "maximum": 14.5}},
                "fingerCapacity": 2,
                "handCapacity": 1,
                "gripType": "halfCrimp",
                "shape": "incut",
            },
        )
    )
    ledger_path = _write_ledger(tmp_path, records)

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path),
        discover_board_packages(tmp_path / "boards"),
    )

    assert report.reviewed_board_ids == ("fixture.board",)
    assert report.fields["depth"].populated == 2
    assert report.fields["depth"].verified == 2
    assert report.fields["shape"].populated == 2
    assert report.boards[0].unaccounted_fields == 0
    assert report.to_json() == {
        "reviewedBoardIDs": ["fixture.board"],
        "sloperOnlyBoardIDs": [],
        "fields": {
            "depth": {"populated": 2, "verified": 2, "adapted": 0, "unavailable": 0, "notApplicable": 0},
            "fingerCapacity": {"populated": 2, "verified": 2, "adapted": 0, "unavailable": 0, "notApplicable": 0},
            "gripType": {"populated": 2, "verified": 2, "adapted": 0, "unavailable": 0, "notApplicable": 0},
            "handCapacity": {"populated": 2, "verified": 2, "adapted": 0, "unavailable": 0, "notApplicable": 0},
            "kind": {"populated": 2, "verified": 2, "adapted": 0, "unavailable": 0, "notApplicable": 0},
            "shape": {"populated": 2, "verified": 2, "adapted": 0, "unavailable": 0, "notApplicable": 0},
        },
        "boards": [
            {
                "boardID": "fixture.board",
                "populated": 12,
                "verified": 12,
                "adapted": 0,
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


def test_reviewed_catalog_ledger_has_complete_eight_field_coverage() -> None:
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
        "beastmaker-1000",
        "beastmaker-2000",
        "dewoodstok-woodbord",
        "escape-beta-22",
        "escape.unlimited",
        "evolv-kilter-basic-long",
        "frictitious.doormount-pro-7",
        "frictitious.megalith",
        "lattice-triple-rung",
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
        "moon.armstrong",
        "nature.stoak-board-iii",
        "soill.iron-palm-2",
        "soill.split-palm",
        "soill.training-tiles",
        "target10a.linebreaker-base",
        "tension.flash-board",
        "tension.grindstone",
        "tension.honestone",
        "tension.whetstone",
        "the-hangboard.the-hangboard",
        "trango.rock-prodigy-forge",
        "trango.rock-prodigy-natural",
        "trango.rock-prodigy-pivot",
        "trango.rock-prodigy-training-center",
        "yy.baguette",
        "yy.baguette-evo",
        "yy.penta-evo",
        "yy.travelboard",
        "yy.verticalboard-evo",
        "yy.verticalboard-first",
        "yy.verticalboard-light",
        "yy.verticalboard-one",
        "zlagboard.evo",
        "zlagboard.pro",
    )
    assert report.sloper_only_board_ids == ()
    assert all(board.unaccounted_fields == 0 for board in report.boards)
    assert next(
        board for board in report.boards if board.board_id == "beastmaker-2000"
    ).to_json() == {
        "boardID": "beastmaker-2000",
        "populated": 65,
        "verified": 65,
        "adapted": 0,
        "unavailable": 86,
        "notApplicable": 11,
        "unaccountedFields": 0,
    }


def test_reconciled_kind_adaptations_remain_explicit_and_source_linked() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    ledger_path = (
        repository_root
        / "docs/source-audits/2026-08-25-hangboard-metadata-ledger.json"
    )
    records = json.loads(ledger_path.read_text(encoding="utf-8"))["records"]

    expected_training_tile_ids = {
        "top-jug-left",
        "top-jug-right",
        "top-pocket-outer-left",
        "top-pocket-inner-left",
        "top-pocket-inner-right",
        "top-pocket-outer-right",
        "upper-sloper-outer-left",
        "upper-sloper-inner-left",
        "upper-sloper-inner-right",
        "upper-sloper-outer-right",
        "middle-edge-outer-left",
        "middle-edge-inner-left",
        "middle-edge-inner-right",
        "middle-edge-outer-right",
        "bottom-edge-outer-left",
        "bottom-edge-center-left",
        "bottom-edge-inner-left",
        "bottom-edge-inner-right",
        "bottom-edge-center-right",
        "bottom-edge-outer-right",
    }
    training_tile_kind_records = [
        record
        for record in records
        if record["boardID"] == "soill.training-tiles" and record["field"] == "kind"
    ]
    assert {
        contact_id
        for record in training_tile_kind_records
        for contact_id in record["contactIDs"]
    } == expected_training_tile_ids
    assert all(
        record["outcome"] == "adapted"
        and record["source"]["url"]
        == "https://soill.ca/products/training-tiles-so-ill-x-meagan-martin"
        and "grouped family specifications" in record["reason"]
        and "20-contact ID map" in record["reason"]
        and "four top-pocket regions" in record["reason"]
        for record in training_tile_kind_records
    )

    expected_adaptations = {
        ("soill.training-tiles", contact_id) for contact_id in expected_training_tile_ids
    } | {
        ("tension.honestone", "macro-sloper-left"),
        ("tension.honestone", "macro-sloper-left-center"),
        ("tension.honestone", "macro-sloper-right-center"),
        ("tension.honestone", "macro-sloper-right"),
    }
    adapted_kind_ids = {
        (record["boardID"], contact_id)
        for record in records
        if record["field"] == "kind" and record["outcome"] == "adapted"
        for contact_id in record["contactIDs"]
    }
    assert adapted_kind_ids == expected_adaptations
    assert len(adapted_kind_ids) == 24

    training_tile_pocket_shape = next(
        record
        for record in records
        if record["boardID"] == "soill.training-tiles"
        and record["field"] == "shape"
        and "top-pocket-outer-left" in record["contactIDs"]
    )
    assert training_tile_pocket_shape["reason"] == (
        "The normalized contact schema intentionally omits this legacy feature label."
    )


def test_beastmaker_1000_keeps_source_backed_kinds_and_positioned_options() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    board = packages["beastmaker-1000"]
    assert len(board.contacts) == 22
    assert {
        hold.kind: {candidate.id for candidate in board.contacts if candidate.kind == hold.kind}
        for hold in board.contacts
    } == {
        "jug": {"jug-left", "jug-right"},
        "sloper": {"sloper-35-left", "sloper-center", "sloper-35-right"},
        "edge": {
            "pocket-top-outer-left",
            "pocket-top-outer-right",
            "pocket-top-left",
            "pocket-top-right",
            "pocket-middle-outer-left",
            "pocket-middle-center",
            "pocket-middle-outer-right",
            "pocket-bottom-outer-left",
            "pocket-bottom-outer-right",
        },
        "pocket": {
            "pocket-middle-mid-left",
            "pocket-middle-inner-left",
            "pocket-middle-inner-right",
            "pocket-middle-mid-right",
            "pocket-bottom-mid-left",
            "pocket-bottom-inner-left",
            "pocket-bottom-inner-right",
            "pocket-bottom-mid-right",
        },
    }
    assert next(hold for hold in board.contacts if hold.id == "sloper-center").name == (
        "20 Degree Center Sloper"
    )
    assert all(
        hold.depth is None
        or hold.depth.range is None
        or hold.depth.range.minimum == hold.depth.range.maximum
        for hold in board.contacts
    )
    assert all(hold.hand_capacity is None for hold in board.contacts)
    assert all(_single_grip_type(hold) is None for hold in board.contacts)
    assert all(hold.shape is None for hold in board.contacts)


def test_repaired_boards_keep_only_exact_source_mapped_metadata() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    moon = packages["moon.armstrong"]
    assert len(moon.contacts) == 21
    assert {
        hold.id: (_scalar_depth(hold), hold.finger_capacity, _single_grip_type(hold))
        for hold in moon.contacts
        if hold.kind == "pocket"
    } == {
        "two-finger-pocket-left": (22, 2, "twoFingerPocket"),
        "two-finger-pocket-right": (22, 2, "twoFingerPocket"),
        "mono-left": (22, 1, None),
        "mono-right": (22, 1, None),
    }
    assert {
        hold.id: hold.shape for hold in moon.contacts if hold.shape
    } == {
        "edge-25-left": "slot",
        "edge-25-right": "slot",
        "edge-20-left": "slot",
        "edge-20-right": "slot",
        "edge-15-left": "slot",
        "edge-15-right": "slot",
        "edge-10-left": "slot",
        "edge-10-right": "slot",
        "edge-8-left": "slot",
        "edge-8-right": "slot",
    }
    assert all(
        (
            hold.depth is None
            or hold.depth.range is None
            or hold.depth.range.minimum == hold.depth.range.maximum
        )
        and hold.hand_capacity is None
        for hold in moon.contacts
    )

    beta = packages["escape-beta-22"]
    assert len(beta.contacts) == 22
    assert {
        hold.id: hold.shape
        for hold in beta.contacts
        if hold.shape
    } == {
        "hold-05-left": "incut",
        "hold-05-right": "incut",
        "hold-06-left": "flat",
        "hold-06-right": "flat",
        "hold-07-left": "flat",
        "hold-07-right": "flat",
        "hold-08-left": "flat",
        "hold-08-right": "flat",
    }
    assert all(
        (
            hold.depth is None
            or hold.depth.range is None
            or hold.depth.range.minimum == hold.depth.range.maximum
        )
        and hold.finger_capacity is None
        and hold.hand_capacity is None
        and _single_grip_type(hold) is None
        for hold in beta.contacts
    )

    megalith = packages["frictitious.megalith"]
    assert len(megalith.contacts) == 18
    assert {
        hold.id: (hold.hand_capacity, hold.shape)
        for hold in megalith.contacts
        if hold.hand_capacity is not None or hold.shape
    } == {
        "center-edge-25": (1, "incut"),
    }
    assert all(
        hold.depth is None
        or hold.depth.range is None
        or hold.depth.range.minimum == hold.depth.range.maximum
        for hold in megalith.contacts
    )
    assert all(_single_grip_type(hold) is None for hold in megalith.contacts)


def test_resolved_independent_boards_keep_only_exact_source_mapped_metadata() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    lattice = packages["lattice-triple-rung"]
    assert {
        hold.id: (hold.kind, _scalar_depth(hold))
        for hold in lattice.contacts
    } == {
        "edge-45": ("edge", 45),
        "edge-10": ("edge", 10),
        "edge-20": ("edge", 20),
    }

    the_hangboard = packages["the-hangboard.the-hangboard"]
    assert {
        hold.id: hold.finger_capacity
        for hold in the_hangboard.contacts
        if hold.kind == "edge"
    } == {
        f"edge-{depth}-{side}": 4
        for depth in (40, 30, 25, 20, 15, 10)
        for side in ("left", "right")
    }
    assert next(
        hold for hold in the_hangboard.contacts if hold.id == "sloper-40-center"
    ).grip_types == frozenset({"openHand"})

    target = packages["target10a.linebreaker-base"]
    assert len(target.contacts) == 23
    assert {
        hold.id: _single_grip_type(hold)
        for hold in target.contacts
        if hold.kind == "pocket"
    } == {
        "pocket-28-left": "threeFingerPocket",
        "pocket-28-right": "threeFingerPocket",
        "pocket-37-left": "fourFingerPocket",
        "pocket-37-right": "fourFingerPocket",
        "pocket-45-left": "threeFingerPocket",
        "pocket-45-right": "threeFingerPocket",
        "pocket-50-left": "twoFingerPocket",
        "pocket-50-right": "twoFingerPocket",
        "pocket-30-left": "twoFingerPocket",
        "pocket-30-right": "twoFingerPocket",
        "pocket-24-left": "twoFingerPocket",
        "pocket-24-right": "twoFingerPocket",
    }

    nature = packages["nature.stoak-board-iii"]
    assert len(nature.contacts) == 7
    top_jug = next(hold for hold in nature.contacts if hold.id == "top-jug")
    assert top_jug.kind == "jug"
    assert _scalar_depth(top_jug) is None
    assert _single_grip_type(top_jug) is None
    assert {
        hold.id: (
            hold.depth.range.minimum,
            hold.depth.range.maximum,
        )
        for hold in nature.contacts
        if hold.depth is not None
        and hold.depth.range is not None
        and hold.depth.range.minimum != hold.depth.range.maximum
    } == {
        "gradient-edge-left": (10, 25),
        "gradient-edge-right": (10, 25),
        "lower-composite-left": (20, 30),
        "lower-composite-right": (20, 30),
    }
    assert _scalar_depth(next(
        hold for hold in nature.contacts if hold.id == "lower-composite-center"
    )) == 30


def test_yy_and_zlag_keep_exact_source_terms_without_type_inference() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    yy_ids = (
        "yy.baguette",
        "yy.baguette-evo",
        "yy.penta-evo",
        "yy.travelboard",
        "yy.verticalboard-evo",
        "yy.verticalboard-first",
        "yy.verticalboard-light",
        "yy.verticalboard-one",
    )
    yy_holds = [hold for board_id in yy_ids for hold in packages[board_id].contacts]
    zlag_holds = [
        hold
        for board_id in ("zlagboard.evo", "zlagboard.pro")
        for hold in packages[board_id].contacts
    ]

    assert sum(_single_grip_type(hold) == "sloper" for hold in yy_holds) == 14
    assert sum(_single_grip_type(hold) == "sloper" for hold in zlag_holds) == 24
    assert sum(_single_grip_type(hold) == "twoFingerPocket" for hold in yy_holds) == 10
    assert all(
        next(
            hold.hand_capacity
            for hold in packages[board_id].contacts
            if hold.id == "center-handle"
        )
        is None
        for board_id in ("yy.verticalboard-one", "yy.verticalboard-evo")
    )

    for board_id in ("zlagboard.evo", "zlagboard.pro"):
        sloper_jug = next(
            hold
            for hold in packages[board_id].contacts
            if hold.id == "top-sloper-jug-center"
        )
        assert sloper_jug.kind == "sloper"
        assert _single_grip_type(sloper_jug) == "sloper"
        assert sloper_jug.shape is None

    assert {
        hold.id: hold.shape
        for hold in packages["zlagboard.pro"].contacts
        if hold.id.startswith("edge-incut-")
    } == {
        "edge-incut-15-left": "incut",
        "edge-incut-30-left": "incut",
        "edge-incut-10-center": "incut",
        "edge-incut-30-right": "incut",
        "edge-incut-15-right": "incut",
    }


def test_training_tiles_contacts_keep_unsupported_measurements_absent() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    ledger_path = (
        repository_root
        / "docs/source-audits/2026-08-25-hangboard-metadata-ledger.json"
    )
    inventory = discover_board_packages(repository_root / "Hangboards")
    report = validate_metadata_ledger(load_metadata_ledger(ledger_path), inventory)
    package = next(
        package
        for package in inventory.packages
        if package.board.id == "soill.training-tiles"
    )

    assert all(
        _scalar_depth(hold) is None
        and hold.depth is None
        and hold.finger_capacity is None
        and hold.hand_capacity is None
        and _single_grip_type(hold) is None
        and hold.shape is None
        for hold in package.board.contacts
    )
    assert len(package.board.contacts) == 20
    assert next(
        board for board in report.boards if board.board_id == "soill.training-tiles"
    ).adapted == 20


def test_simulator_flat_sloper_hand_capacity_is_explicitly_audited() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    ledger_path = (
        repository_root
        / "docs/source-audits/2026-08-25-hangboard-metadata-ledger.json"
    )
    inventory = discover_board_packages(repository_root / "Hangboards")
    ledger = load_metadata_ledger(ledger_path)
    validate_metadata_ledger(ledger, inventory)

    simulator = next(
        package.board
        for package in inventory.packages
        if package.board.id == "metolius.simulator-3d"
    )
    contacts = {contact.id: contact for contact in simulator.contacts}
    assert contacts["flat-sloper-2-left"].hand_capacity == 1
    assert contacts["flat-sloper-2-right"].hand_capacity == 1
    assert contacts["round-sloper-3-center"].hand_capacity is None

    hand_capacity_records = [
        record
        for record in ledger.records
        if record.board_id == "metolius.simulator-3d" and record.field == "handCapacity"
    ]
    assert [
        (record.contact_ids, record.outcome, record.value)
        for record in hand_capacity_records
        if set(record.contact_ids) == {"flat-sloper-2-left", "flat-sloper-2-right"}
    ] == [(("flat-sloper-2-left", "flat-sloper-2-right"), "adapted", 1)]


def test_trango_metadata_matches_exact_manufacturer_hold_guides() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    forge = packages["trango.rock-prodigy-forge"]
    assert {
        hold.id: _single_grip_type(hold)
        for hold in forge.contacts
        if hold.kind == "pocket"
    } == {
        f"{fingers}-{depth}-{side}": "twoFingerPocket"
        for fingers in ("mr", "im")
        for depth in ("deep", "shallow")
        for side in ("left", "right")
    }
    assert {
        hold.id: _single_grip_type(hold)
        for hold in forge.contacts
        if hold.kind == "sloper"
    } == {
        f"sloper-{angle}-{side}": "sloper"
        for angle in (30, 40)
        for side in ("left", "right")
    }
    assert next(
        hold for hold in forge.contacts if hold.id == "large-flat-edge-left"
    ).shape == "flat"
    assert next(
        hold for hold in forge.contacts if hold.id == "large-flat-edge-left"
    ).depth.category == "large"

    natural = packages["trango.rock-prodigy-natural"]
    assert all(hold.finger_capacity == 4 for hold in natural.contacts[:8])
    assert {
        hold.id: (hold.finger_capacity, _single_grip_type(hold), _scalar_depth(hold))
        for hold in natural.contacts
        if hold.kind == "pocket"
    } == {
        "upper-pocket-left": (3, "threeFingerPocket", 38),
        "upper-pocket-right": (3, "threeFingerPocket", 38),
        "center-lower-pocket-left": (2, "twoFingerPocket", None),
        "center-lower-pocket-right": (2, "twoFingerPocket", None),
        "outer-supported-pocket-left": (3, "threeFingerPocket", None),
        "outer-supported-pocket-right": (3, "threeFingerPocket", None),
    }
    assert all(
        _single_grip_type(hold) == "fullCrimp"
        for hold in natural.contacts
        if hold.id.startswith("closed-crimp-")
    )

    pivot = packages["trango.rock-prodigy-pivot"]
    assert all(hold.finger_capacity is not None for hold in pivot.contacts)
    pivot_suffixes = ("", "-orientation-2", "-orientation-3", "-orientation-4")
    base_crimp_sizes = {
        "upper-sloped-crimp-left": 12.5,
        "upper-sloped-crimp-right": 12.5,
        "outer-sloped-crimp-left": 11.5,
        "outer-sloped-crimp-right": 11.5,
    }
    assert {
        hold.id: _scalar_depth(hold)
        for hold in pivot.contacts
        if hold.id.startswith(("upper-sloped-crimp-", "outer-sloped-crimp-"))
    } == {
        f"{contact_id}{suffix}": size
        for suffix in pivot_suffixes
        for contact_id, size in base_crimp_sizes.items()
    }
    base_pocket_grip_types = {
        "two-finger-pocket-left": "twoFingerPocket",
        "two-finger-pocket-right": "twoFingerPocket",
        "three-finger-pocket-left": "threeFingerPocket",
        "three-finger-pocket-right": "threeFingerPocket",
    }
    assert {
        hold.id: _single_grip_type(hold) for hold in pivot.contacts if hold.kind == "pocket"
    } == {
        f"{contact_id}{suffix}": grip_type
        for suffix in pivot_suffixes
        for contact_id, grip_type in base_pocket_grip_types.items()
    }

    training_center = packages["trango.rock-prodigy-training-center"]
    assert all(
        hold.finger_capacity is None
        and _single_grip_type(hold) is None
        and hold.shape is None
        for hold in training_center.contacts
        if hold.kind == "pocket"
    )
    assert next(
        hold for hold in training_center.contacts if hold.id == "pinch-medium-left"
    ).shape is None
    large_edge = next(
        hold for hold in training_center.contacts if hold.id == "edge-large-vder-left"
    )
    assert _single_grip_type(large_edge) is None
    assert large_edge.shape is None
    assert next(
        hold for hold in training_center.contacts if hold.id == "pinch-wide-left"
    ).shape is None


def test_unavailable_value_must_be_absent_from_package(tmp_path: Path) -> None:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0]["depth"] = {
        "range": {"minimum": 18, "maximum": 18},
    }
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    ledger = _write_ledger(tmp_path, _complete_records("fixture.board", "hold-left"))

    with pytest.raises(MetadataAuditError, match="depth must be absent"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_rejects_an_unknown_contact_id(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    ledger = _write_ledger(tmp_path, _complete_records("fixture.board", "unknown-hold"))

    with pytest.raises(MetadataAuditError, match="unknown contact ID: unknown-hold"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_rejects_duplicate_expanded_record_keys(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    records = _complete_records("fixture.board", "hold-left")
    records.append(unavailable("fixture.board", "hold-left", "depth"))
    ledger = _write_ledger(tmp_path, records)

    with pytest.raises(MetadataAuditError, match="duplicate record for fixture.board/hold-left/depth"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_verified_scalar_must_equal_the_package_value(tmp_path: Path) -> None:
    package = write_board_package(tmp_path / "boards" / "fixture", board_id="fixture.board")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["contacts"][0]["depth"] = {
        "range": {"minimum": 20, "maximum": 20},
    }
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    ledger = _write_ledger(
        tmp_path,
        _complete_records(
            "fixture.board",
            "hold-left",
            verified_values={"depth": {"range": {"minimum": 18, "maximum": 18}}},
        ),
    )

    with pytest.raises(MetadataAuditError, match="depth does not match"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger), discover_board_packages(tmp_path / "boards")
        )


def test_rejects_incomplete_reviewed_board(tmp_path: Path) -> None:
    write_board_package(tmp_path / "boards" / "fixture")
    ledger = _write_ledger(
        tmp_path,
        [unavailable("fixture.board", "hold-left", "depth")],
    )

    with pytest.raises(MetadataAuditError, match="missing record for fixture.board/hold-left/fingerCapacity"):
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
