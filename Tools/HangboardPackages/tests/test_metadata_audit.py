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
    "sloper",
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
            "fingerCapacity": 2,
            "handCapacity": 1,
            "gripType": "halfCrimp",
            "features": ["smallEdge", "incutEdge"],
        }
    )
    range_hold = dict(document["holds"][0])
    range_hold.update(
        {
            "id": "hold-range",
            "name": "Range hold",
            "depthRangeMillimeters": {"lowerBound": 10, "upperBound": 14.5},
        }
    )
    range_hold.pop("sizeMillimeters")
    document["holds"].append(range_hold)
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return package


def _package_with_flat_sloper(tmp_path: Path) -> Path:
    package = write_board_package(tmp_path / "boards" / "fixture")
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    document["holds"][0].update(
        {"kind": "sloper", "sloper": {"type": "flat", "angleDegrees": 20}}
    )
    (package / "board.json").write_text(json.dumps(document), encoding="utf-8")
    return package


def _sloper_ledger_records(
    value: object, *, source: dict[str, object] | None = None
) -> list[dict[str, object]]:
    records = [
        {
            "boardID": "fixture.board",
            "holdIDs": ["hold-left"],
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
            "holdIDs": ["hold-left"],
            "field": "sloper",
            "outcome": "verified",
            "reviewedAt": "2026-08-25",
            "source": source
            or {
                "kind": "manufacturer",
                "url": "https://example.com/fixture-source",
                "label": "Fixture manufacturer source",
            },
            "value": value,
        },
    ]
    records.extend(
        unavailable("fixture.board", "hold-left", field)
        for field in _FIELDS
        if field not in {"kind", "sloper"}
    )
    return records


def test_sloper_ledger_verified_value_matches_flat_hold(tmp_path: Path) -> None:
    _package_with_flat_sloper(tmp_path)
    ledger_path = _write_ledger(
        tmp_path,
        _sloper_ledger_records({"type": "flat", "angleDegrees": 20}),
    )

    report = validate_metadata_ledger(
        load_metadata_ledger(ledger_path), discover_board_packages(tmp_path / "boards")
    )

    assert report.fields["sloper"].to_json() == {
        "populated": 1,
        "verified": 1,
        "unavailable": 0,
        "notApplicable": 0,
    }


def test_sloper_ledger_rejects_angle_that_differs_from_hold(tmp_path: Path) -> None:
    _package_with_flat_sloper(tmp_path)
    ledger_path = _write_ledger(
        tmp_path,
        _sloper_ledger_records({"type": "flat", "angleDegrees": 25}),
    )

    with pytest.raises(MetadataAuditError, match="sloper does not match"):
        validate_metadata_ledger(
            load_metadata_ledger(ledger_path), discover_board_packages(tmp_path / "boards")
        )


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
            "sizeMillimeters": 18,
            "fingerCapacity": 2,
            "handCapacity": 1,
            "gripType": "halfCrimp",
            "features": ["smallEdge", "incutEdge"],
        },
    )
    records.extend(
        _complete_records(
            "fixture.board",
            "hold-range",
            verified_values={
                "depthRangeMillimeters": {"lowerBound": 10, "upperBound": 14.5},
                "fingerCapacity": 2,
                "handCapacity": 1,
                "gripType": "halfCrimp",
                "features": ["smallEdge", "incutEdge"],
            },
        )
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
    assert report.fields["features"].populated == 2
    assert report.boards[0].unaccounted_fields == 0
    assert report.to_json() == {
        "reviewedBoardIDs": ["fixture.board"],
        "fields": {
            "kind": {"populated": 2, "verified": 2, "unavailable": 0, "notApplicable": 0},
            "sizeMillimeters": {"populated": 1, "verified": 1, "unavailable": 1, "notApplicable": 0},
            "depthRangeMillimeters": {"populated": 1, "verified": 1, "unavailable": 1, "notApplicable": 0},
            "fingerCapacity": {"populated": 2, "verified": 2, "unavailable": 0, "notApplicable": 0},
            "handCapacity": {"populated": 2, "verified": 2, "unavailable": 0, "notApplicable": 0},
            "gripType": {"populated": 2, "verified": 2, "unavailable": 0, "notApplicable": 0},
            "features": {"populated": 2, "verified": 2, "unavailable": 0, "notApplicable": 0},
            "sloper": {"populated": 0, "verified": 0, "unavailable": 2, "notApplicable": 0},
        },
        "boards": [
            {
                "boardID": "fixture.board",
                "populated": 12,
                "verified": 12,
                "unavailable": 4,
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
    assert all(board.unaccounted_fields == 0 for board in report.boards)


def test_beastmaker_1000_keeps_source_backed_kinds_and_no_guessed_options() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    board = packages["beastmaker-1000"]
    assert len(board.holds) == 22
    assert {
        hold.kind: {candidate.id for candidate in board.holds if candidate.kind == hold.kind}
        for hold in board.holds
    } == {
        "jug": {"jug-left", "jug-right"},
        "sloper": {"sloper-35-left", "sloper-center", "sloper-35-right"},
        "pocket": {
            "pocket-top-outer-left",
            "pocket-top-outer-right",
            "pocket-top-left",
            "pocket-top-right",
            "pocket-middle-outer-left",
            "pocket-middle-mid-left",
            "pocket-middle-inner-left",
            "pocket-middle-center",
            "pocket-middle-inner-right",
            "pocket-middle-mid-right",
            "pocket-middle-outer-right",
            "pocket-bottom-outer-left",
            "pocket-bottom-mid-left",
            "pocket-bottom-inner-left",
            "pocket-bottom-inner-right",
            "pocket-bottom-mid-right",
            "pocket-bottom-outer-right",
        },
    }
    assert next(hold for hold in board.holds if hold.id == "sloper-center").name == (
        "20 Degree Center Sloper"
    )
    assert all(
        hold.size_millimeters is None
        and hold.depth_range_millimeters is None
        and hold.finger_capacity is None
        and hold.hand_capacity is None
        and hold.grip_type is None
        and hold.features is None
        for hold in board.holds
    )


def test_repaired_boards_keep_only_exact_source_mapped_metadata() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = discover_board_packages(repository_root / "Hangboards")
    packages = {package.board.id: package.board for package in inventory.packages}

    moon = packages["moon.armstrong"]
    assert len(moon.holds) == 21
    assert {
        hold.id: (hold.size_millimeters, hold.finger_capacity, hold.grip_type)
        for hold in moon.holds
        if hold.kind == "pocket"
    } == {
        "two-finger-pocket-left": (22, 2, "twoFingerPocket"),
        "two-finger-pocket-right": (22, 2, "twoFingerPocket"),
        "mono-left": (22, 1, None),
        "mono-right": (22, 1, None),
    }
    assert {
        hold.id: hold.features for hold in moon.holds if hold.features is not None
    } == {
        "jug-left": ("jug",),
        "jug-right": ("jug",),
        "center-jug": ("jug",),
        "edge-25-left": ("slot",),
        "edge-25-right": ("slot",),
        "edge-20-left": ("slot",),
        "edge-20-right": ("slot",),
        "edge-15-left": ("slot",),
        "edge-15-right": ("slot",),
        "edge-10-left": ("slot",),
        "edge-10-right": ("slot",),
        "edge-8-left": ("slot",),
        "edge-8-right": ("slot",),
        "two-finger-pocket-left": ("pocket",),
        "two-finger-pocket-right": ("pocket",),
        "mono-left": ("pocket",),
        "mono-right": ("pocket",),
    }
    assert all(
        hold.depth_range_millimeters is None and hold.hand_capacity is None
        for hold in moon.holds
    )

    beta = packages["escape-beta-22"]
    assert len(beta.holds) == 22
    assert {
        hold.id: hold.features
        for hold in beta.holds
        if hold.features is not None
    } == {
        "hold-02-left": ("widePinch",),
        "hold-02-right": ("widePinch",),
        "hold-03-left": ("jug",),
        "hold-03-right": ("jug",),
        "hold-04-left": ("jug",),
        "hold-04-right": ("jug",),
        "hold-05-left": ("incutEdge",),
        "hold-05-right": ("incutEdge",),
        "hold-06-left": ("flatEdge",),
        "hold-06-right": ("flatEdge",),
        "hold-07-left": ("flatEdge",),
        "hold-07-right": ("flatEdge",),
        "hold-08-left": ("flatEdge",),
        "hold-08-right": ("flatEdge",),
    }
    assert all(
        hold.depth_range_millimeters is None
        and hold.finger_capacity is None
        and hold.hand_capacity is None
        and hold.grip_type is None
        for hold in beta.holds
    )

    megalith = packages["frictitious.megalith"]
    assert len(megalith.holds) == 18
    assert {
        hold.id: (hold.hand_capacity, hold.features)
        for hold in megalith.holds
        if hold.hand_capacity is not None or hold.features is not None
    } == {
        "top-jug": (None, ("jug",)),
        "center-edge-25": (1, ("incutEdge",)),
        "mono-left": (None, ("pocket",)),
        "mono-right": (None, ("pocket",)),
    }
    assert all(hold.depth_range_millimeters is None for hold in megalith.holds)
    assert all(hold.grip_type is None for hold in megalith.holds)


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
    yy_holds = [hold for board_id in yy_ids for hold in packages[board_id].holds]
    zlag_holds = [
        hold
        for board_id in ("zlagboard.evo", "zlagboard.pro")
        for hold in packages[board_id].holds
    ]

    assert sum(hold.grip_type == "sloper" for hold in yy_holds) == 14
    assert sum(hold.grip_type == "sloper" for hold in zlag_holds) == 24
    assert sum(hold.grip_type == "twoFingerPocket" for hold in yy_holds) == 10
    assert all(
        next(
            hold.hand_capacity
            for hold in packages[board_id].holds
            if hold.id == "center-handle"
        )
        is None
        for board_id in ("yy.verticalboard-one", "yy.verticalboard-evo")
    )

    for board_id in ("zlagboard.evo", "zlagboard.pro"):
        sloper_jug = next(
            hold
            for hold in packages[board_id].holds
            if hold.id == "top-sloper-jug-center"
        )
        assert sloper_jug.kind == "sloper"
        assert sloper_jug.grip_type == "sloper"
        assert sloper_jug.features == ("jug",)

    assert {
        hold.id: hold.features
        for hold in packages["zlagboard.pro"].holds
        if hold.id.startswith("edge-incut-")
    } == {
        "edge-incut-15-left": ("incutEdge",),
        "edge-incut-30-left": ("incutEdge",),
        "edge-incut-10-center": ("incutEdge",),
        "edge-incut-30-right": ("incutEdge",),
        "edge-incut-15-right": ("incutEdge",),
    }


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
    large_edge = next(
        hold for hold in training_center.holds if hold.id == "edge-large-vder-left"
    )
    assert large_edge.grip_type is None
    assert large_edge.features is None
    assert next(
        hold for hold in training_center.holds if hold.id == "pinch-wide-left"
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
