from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import hangboard_packages.cli as cli
from hangboard_packages.board_catalog import (
    BoardInventory,
    BoardModelSingleCordSuspension,
    BoardPackage,
    PresentationMediaModel,
    PresentationMediaRaster,
)
from hangboard_packages.cord_audit import (
    CordAuditError,
    load_cord_audit_manifest,
    validate_cord_audit_manifest,
)


def _model_package(package_id: str, *, suspension: object | None = None) -> BoardPackage:
    media = PresentationMediaModel(
        "assets/primary.usdz", "assets/primary.model.json", {}, suspension
    )
    presentation = SimpleNamespace(media=media)
    board = SimpleNamespace(id=package_id, presentations=(presentation,))
    return BoardPackage(Path(package_id), board)


def _raster_package(package_id: str) -> BoardPackage:
    media = PresentationMediaRaster("assets/primary.png", {})
    presentation = SimpleNamespace(media=media)
    board = SimpleNamespace(id=package_id, presentations=(presentation,))
    return BoardPackage(Path(package_id), board)


def _inventory(*packages: BoardPackage) -> BoardInventory:
    return BoardInventory(packages=packages, drafts=())


def _record(
    package_id: str,
    *,
    decision: str = "excluded",
    topology: str | None = None,
    ruling: str = "The primary product listing does not establish a supplied cord.",
    evidence: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "packageID": package_id,
        "decision": decision,
        "topology": topology,
        "ruling": ruling,
        "evidence": evidence
        if evidence is not None
        else [
            {"view": "front", "url": "https://example.com/front"},
            {"view": "side", "url": "https://example.com/side"},
        ],
    }


def _manifest_path(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "cord-audit.json"
    path.write_text(json.dumps({"schemaVersion": 1, "records": records}), encoding="utf-8")
    return path


def _validate(
    tmp_path: Path, inventory: BoardInventory, records: list[dict[str, object]]
) -> object:
    return validate_cord_audit_manifest(
        load_cord_audit_manifest(_manifest_path(tmp_path, records)), inventory
    )


def test_model_inventory_requires_one_record_for_each_model_package(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.one"), _model_package("fixture.two"))

    with pytest.raises(CordAuditError, match=r"missing model package record: fixture\.two"):
        _validate(tmp_path, inventory, [_record("fixture.one")])


def test_duplicate_model_record_is_rejected(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")

    with pytest.raises(CordAuditError, match="duplicate model package record"):
        _validate(tmp_path, inventory, [record, record.copy()])


def test_raster_package_record_is_rejected(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.model"), _raster_package("fixture.raster"))

    with pytest.raises(CordAuditError, match="unknown model package record: fixture.raster"):
        _validate(tmp_path, inventory, [_record("fixture.model"), _record("fixture.raster")])


def test_represented_record_requires_matching_package_suspension_topology(
    tmp_path: Path,
) -> None:
    inventory = _inventory(_model_package("fixture.board"))

    with pytest.raises(CordAuditError, match="does not match package suspension topology"):
        _validate(
            tmp_path,
            inventory,
            [
                _record(
                    "fixture.board",
                    decision="represented",
                    topology="singleCord",
                )
            ],
        )


def test_excluded_record_rejects_package_with_suspension(tmp_path: Path) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(CordAuditError, match="excluded record requires no package suspension"):
        _validate(tmp_path, inventory, [_record("fixture.board")])


def test_represented_record_requires_two_distinct_evidence_views(tmp_path: Path) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(CordAuditError, match="two distinct evidence views"):
        _validate(
            tmp_path,
            inventory,
            [
                _record(
                    "fixture.board",
                    decision="represented",
                    topology="singleCord",
                    evidence=[{"view": "front", "url": "https://example.com/front"}],
                )
            ],
        )


def test_represented_record_rejects_differently_labelled_duplicate_evidence_url(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(CordAuditError, match="distinct evidence URLs"):
        _validate(
            tmp_path,
            inventory,
            [
                _record(
                    "fixture.board",
                    decision="represented",
                    topology="singleCord",
                    evidence=[
                        {"view": "front", "url": "https://example.com/view"},
                        {"view": "oblique", "url": "https://example.com/view"},
                    ],
                )
            ],
        )


def test_represented_record_rejects_duplicate_normalized_evidence_view_labels(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(CordAuditError, match="distinct evidence views"):
        _validate(
            tmp_path,
            inventory,
            [
                _record(
                    "fixture.board",
                    decision="represented",
                    topology="singleCord",
                    evidence=[
                        {"view": "Front", "url": "https://example.com/front"},
                        {"view": " front ", "url": "https://example.com/oblique"},
                    ],
                )
            ],
        )


def test_manifest_rejects_unknown_record_keys(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["unreviewed"] = True

    with pytest.raises(CordAuditError, match="has unknown keys"):
        _validate(tmp_path, inventory, [record])


def test_manifest_rejects_non_string_topology_without_leaking_type_errors(
    tmp_path: Path,
) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["topology"] = []

    with pytest.raises(CordAuditError, match="topology must be null or one of"):
        _validate(tmp_path, inventory, [record])


def test_manifest_and_model_inventory_sets_must_be_equal(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))

    with pytest.raises(CordAuditError, match="manifest model package IDs must equal inventory"):
        _validate(tmp_path, inventory, [_record("unknown.board")])


def test_valid_represented_and_excluded_records_report_decisions(tmp_path: Path) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.represented",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        ),
        _model_package("fixture.excluded"),
        _raster_package("fixture.raster"),
    )

    report = _validate(
        tmp_path,
        inventory,
        [
            _record(
                "fixture.represented",
                decision="represented",
                topology="singleCord",
            ),
            _record("fixture.excluded"),
        ],
    )

    assert report.to_json() == {
        "modelPackageIDs": ["fixture.excluded", "fixture.represented"],
        "decisions": {"excluded": 1, "represented": 1},
    }


def test_cli_audit_cords_reports_model_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    manifest = _manifest_path(tmp_path, [_record("fixture.board")])
    observed_complete_inventory: list[bool] = []

    def discover(root: Path, *, require_complete_inventory: bool) -> BoardInventory:
        observed_complete_inventory.append(require_complete_inventory)
        return inventory

    monkeypatch.setattr(cli, "discover_board_packages", discover)

    assert cli.main(["audit-cords", "--root", str(tmp_path), "--manifest", str(manifest)]) == 0
    assert observed_complete_inventory == [True]
    assert json.loads(capsys.readouterr().out) == {
        "modelPackageIDs": ["fixture.board"],
        "decisions": {"excluded": 1},
    }
