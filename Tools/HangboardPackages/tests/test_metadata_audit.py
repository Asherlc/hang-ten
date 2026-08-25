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
        "escape.unlimited",
        "evolv-kilter-basic-long",
        "frictitious.doormount-pro-7",
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
    )
    assert all(board.unaccounted_fields == 0 for board in report.boards)


def test_resolved_independent_boards_keep_only_exact_source_mapped_metadata() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    lattice = packages["lattice-triple-rung"]
    assert {
        hold.id: (hold.kind, hold.size_millimeters)
        for hold in lattice.holds
    } == {
        "edge-45": ("edge", 45),
        "edge-10": ("edge", 10),
        "edge-20": ("edge", 20),
    }

    the_hangboard = packages["the-hangboard.the-hangboard"]
    assert {
        hold.id: hold.finger_capacity
        for hold in the_hangboard.holds
        if hold.kind == "edge"
    } == {
        f"edge-{depth}-{side}": 4
        for depth in (40, 30, 25, 20, 15, 10)
        for side in ("left", "right")
    }
    assert next(
        hold for hold in the_hangboard.holds if hold.id == "sloper-40-center"
    ).grip_type == "openHand"

    target = packages["target10a.linebreaker-base"]
    assert len(target.holds) == 24
    assert {
        hold.id: hold.grip_type
        for hold in target.holds
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
    assert len(nature.holds) == 7
    top_jug = next(hold for hold in nature.holds if hold.id == "top-jug")
    assert top_jug.kind == "jug"
    assert top_jug.size_millimeters is None
    assert top_jug.grip_type is None
    assert {
        hold.id: (
            hold.depth_range_millimeters.lower_bound,
            hold.depth_range_millimeters.upper_bound,
        )
        for hold in nature.holds
        if hold.depth_range_millimeters is not None
    } == {
        "gradient-edge-left": (10, 25),
        "gradient-edge-right": (10, 25),
        "lower-composite-left": (20, 30),
        "lower-composite-right": (20, 30),
    }
    assert next(
        hold for hold in nature.holds if hold.id == "lower-composite-center"
    ).size_millimeters == 30


def test_training_tiles_pockets_have_source_mapped_three_inch_depth() -> None:
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

    assert {
        hold.id: hold.size_millimeters
        for hold in package.board.holds
        if hold.id in {"pocket-left", "pocket-right"}
    } == {"pocket-left": 76.2, "pocket-right": 76.2}
    assert next(
        board for board in report.boards if board.board_id == "soill.training-tiles"
    ).populated == 18


def test_trango_metadata_matches_exact_manufacturer_hold_guides() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    forge = packages["trango.rock-prodigy-forge"]
    assert {
        hold.id: hold.grip_type
        for hold in forge.holds
        if hold.kind == "pocket"
    } == {
        f"{fingers}-{depth}-{side}": "twoFingerPocket"
        for fingers in ("mr", "im")
        for depth in ("deep", "shallow")
        for side in ("left", "right")
    }
    assert {
        hold.id: hold.grip_type
        for hold in forge.holds
        if hold.kind == "sloper"
    } == {
        f"sloper-{angle}-{side}": "sloper"
        for angle in (30, 40)
        for side in ("left", "right")
    }
    assert next(
        hold for hold in forge.holds if hold.id == "large-flat-edge-left"
    ).features == ("largeEdge", "flatEdge")

    natural = packages["trango.rock-prodigy-natural"]
    assert all(hold.finger_capacity == 4 for hold in natural.holds[:8])
    assert {
        hold.id: (hold.finger_capacity, hold.grip_type, hold.size_millimeters)
        for hold in natural.holds
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
        hold.grip_type == "fullCrimp"
        for hold in natural.holds
        if hold.id.startswith("closed-crimp-")
    )

    pivot = packages["trango.rock-prodigy-pivot"]
    assert all(hold.finger_capacity is not None for hold in pivot.holds)
    assert {
        hold.id: hold.size_millimeters
        for hold in pivot.holds
        if hold.id.startswith(("upper-sloped-crimp-", "outer-sloped-crimp-"))
    } == {
        "upper-sloped-crimp-left": 12.5,
        "upper-sloped-crimp-right": 12.5,
        "outer-sloped-crimp-left": 11.5,
        "outer-sloped-crimp-right": 11.5,
    }
    assert {
        hold.id: hold.grip_type for hold in pivot.holds if hold.kind == "pocket"
    } == {
        "two-finger-pocket-left": "twoFingerPocket",
        "two-finger-pocket-right": "twoFingerPocket",
        "three-finger-pocket-left": "threeFingerPocket",
        "three-finger-pocket-right": "threeFingerPocket",
    }

    training_center = packages["trango.rock-prodigy-training-center"]
    assert all(
        hold.finger_capacity is None
        and hold.grip_type is None
        and hold.features is None
        for hold in training_center.holds
        if hold.kind == "pocket"
    )
    assert next(
        hold for hold in training_center.holds if hold.id == "pinch-medium-left"
    ).features is None


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
