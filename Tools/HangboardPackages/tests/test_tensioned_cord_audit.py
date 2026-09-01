from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from hangboard_packages.board_catalog import (
    BoardDocument,
    BoardInventory,
    BoardPackage,
    BoardPresentation,
)

try:
    from hangboard_packages.tensioned_cord_audit import (
        TensionedCordAuditError,
        load_tensioned_cord_ledger,
        validate_tensioned_cord_ledger,
    )
except ModuleNotFoundError:
    TensionedCordAuditError = ValueError
    load_tensioned_cord_ledger = None
    validate_tensioned_cord_ledger = None


_PRESENTATION_COUNTS = (1, 2, 1, 2, 4, 6, 2, 2, 3, 3, 2, 1, 2, 1, 1, 4, 5, 2, 1, 2)


def _inventory(root: Path) -> BoardInventory:
    packages: list[BoardPackage] = []
    for package_index, presentation_count in enumerate(_PRESENTATION_COUNTS):
        package_id = f"fixture.package-{package_index:02d}"
        package_root = root / package_id
        assets = package_root / "assets"
        assets.mkdir(parents=True)
        presentations: list[BoardPresentation] = []
        for presentation_index in range(presentation_count):
            presentation_id = f"presentation-{presentation_index}"
            asset_path = f"assets/{presentation_id}.png"
            (package_root / asset_path).write_bytes(
                f"fixture {package_id}/{presentation_id}".encode()
            )
            presentations.append(
                BoardPresentation(
                    id=presentation_id,
                    name=presentation_id,
                    asset_path=asset_path,
                    aspect_ratio=1.0,
                    is_default=presentation_index == 0,
                    source_presentation_id=(
                        "presentation-0" if presentation_index == 1 else None
                    ),
                    is_inverted=presentation_index == 1,
                )
            )
        packages.append(
            BoardPackage(
                root=package_root,
                board=BoardDocument(
                    id=package_id,
                    facts={"manufacturer": "Fixture", "name": package_id},
                    equipment_objects=(),
                    holds=(),
                    presentations=tuple(presentations),
                ),
            )
        )
    return BoardInventory(packages=tuple(packages), drafts=())


def _record(package: BoardPackage, presentation: BoardPresentation) -> dict[str, object]:
    asset = package.root / presentation.asset_path
    blocked = package.board.id == "fixture.package-05" and presentation.id == "presentation-2"
    return {
        "packageID": package.board.id,
        "presentationID": presentation.id,
        "assetPath": presentation.asset_path,
        "assetSHA256": hashlib.sha256(asset.read_bytes()).hexdigest(),
        "sourcePresentationID": presentation.source_presentation_id,
        "evidence": {
            "url": "https://manufacturer.example/products/fixture",
            "label": "Fixture manufacturer product page",
            "reviewedAt": "2026-09-01",
        },
        "orientation": "inverted" if presentation.is_inverted else "upright",
        "gravity": "canvasDown",
        "tensionDirection": "towardCanvasBottom",
        "visibleTopology": "visibleSegmentsOnly",
        "routing": "unknown",
        "terminals": "unknown",
        "knots": "unknown",
        "hardware": "unknown",
        "status": "blocked" if blocked else "accepted",
        "output": "blocked" if blocked else "accepted",
        "blocker": (
            "Fixture primary evidence does not establish the exact routing."
            if blocked
            else None
        ),
    }


def _ledger(inventory: BoardInventory) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "packageIDs": [package.board.id for package in inventory.packages],
        "records": [
            _record(package, presentation)
            for package in inventory.packages
            for presentation in package.board.presentations
        ],
    }


def _write_ledger(path: Path, ledger: dict[str, object]) -> Path:
    path.write_text(json.dumps(ledger), encoding="utf-8")
    return path


def _require_audit_api() -> None:
    assert load_tensioned_cord_ledger is not None, "the tensioned cord audit API is missing"
    assert validate_tensioned_cord_ledger is not None, "the tensioned cord validator is missing"


def test_load_rejects_missing_required_cord_fact_and_non_https_evidence_url(
    tmp_path: Path,
) -> None:
    """Catches a parser mutation that permits incomplete facts or indirect evidence."""
    _require_audit_api()
    inventory = _inventory(tmp_path / "packages")
    ledger = _ledger(inventory)
    record = ledger["records"][0]
    assert isinstance(record, dict)
    del record["tensionDirection"]
    record["evidence"] = {
        "url": "http://manufacturer.example/products/fixture",
        "label": "Fixture manufacturer product page",
        "reviewedAt": "2026-09-01",
    }

    with pytest.raises(TensionedCordAuditError, match="tensionDirection"):
        load_tensioned_cord_ledger(_write_ledger(tmp_path / "ledger.json", ledger))


def test_validator_reports_the_closed_20_package_47_presentation_inventory(
    tmp_path: Path,
) -> None:
    """Catches a validator mutation that accepts a partial or open inventory."""
    _require_audit_api()
    inventory = _inventory(tmp_path / "packages")
    ledger = load_tensioned_cord_ledger(_write_ledger(tmp_path / "ledger.json", _ledger(inventory)))

    assert validate_tensioned_cord_ledger(
        ledger, inventory, hangboards_root=tmp_path / "packages"
    ).to_json() == {
        "packageCount": 20,
        "presentationCount": 47,
        "acceptedCount": 46,
        "blockedCount": 1,
        "blockers": [
            {
                "packageID": "fixture.package-05",
                "presentationID": "presentation-2",
                "reason": "Fixture primary evidence does not establish the exact routing.",
            }
        ],
    }


@pytest.mark.parametrize("mutation", ("duplicate", "missing", "extra"))
def test_validator_rejects_duplicate_missing_or_extra_presentation_record(
    tmp_path: Path, mutation: str
) -> None:
    """Catches a validator mutation that stops enforcing closed record identity."""
    _require_audit_api()
    inventory = _inventory(tmp_path / "packages")
    document = _ledger(inventory)
    records = document["records"]
    assert isinstance(records, list)
    if mutation == "duplicate":
        records[-1] = dict(records[0])
    elif mutation == "missing":
        records.pop()
    else:
        extra = dict(records[0])
        extra["presentationID"] = "not-declared"
        records[-1] = extra

    ledger = load_tensioned_cord_ledger(_write_ledger(tmp_path / "ledger.json", document))
    expected = "tensioned cord ledger must cover exactly 47 presentations" if mutation == "missing" else "(duplicate|unknown presentation)"
    with pytest.raises(TensionedCordAuditError, match=expected):
        validate_tensioned_cord_ledger(ledger, inventory, hangboards_root=tmp_path / "packages")


def test_validator_rejects_stale_asset_identity(
    tmp_path: Path,
) -> None:
    """Catches a validator mutation that skips package asset-byte identity checks."""
    _require_audit_api()
    inventory = _inventory(tmp_path / "packages")
    document = _ledger(inventory)
    records = document["records"]
    assert isinstance(records, list)
    alias = next(record for record in records if record["presentationID"] == "presentation-1")
    alias["assetSHA256"] = "0" * 64
    ledger = load_tensioned_cord_ledger(_write_ledger(tmp_path / "ledger.json", document))

    with pytest.raises(TensionedCordAuditError, match="asset SHA-256"):
        validate_tensioned_cord_ledger(ledger, inventory, hangboards_root=tmp_path / "packages")


def test_validator_rejects_stale_alias_source_relationship(tmp_path: Path) -> None:
    """Catches a validator mutation that permits an alias to cite the wrong source presentation."""
    _require_audit_api()
    inventory = _inventory(tmp_path / "packages")
    document = _ledger(inventory)
    records = document["records"]
    assert isinstance(records, list)
    alias = next(record for record in records if record["presentationID"] == "presentation-1")
    alias["sourcePresentationID"] = None
    ledger = load_tensioned_cord_ledger(_write_ledger(tmp_path / "ledger.json", document))

    with pytest.raises(TensionedCordAuditError, match="source presentation"):
        validate_tensioned_cord_ledger(ledger, inventory, hangboards_root=tmp_path / "packages")


def test_validator_requires_presentation_specific_physics_and_blocker_contract(
    tmp_path: Path,
) -> None:
    """Catches a validator mutation that permits wrong gravity, tension, or blocker state."""
    _require_audit_api()
    inventory = _inventory(tmp_path / "packages")
    document = _ledger(inventory)
    records = document["records"]
    assert isinstance(records, list)
    inverted = next(record for record in records if record["presentationID"] == "presentation-1")
    inverted["gravity"] = "sourceImageDown"
    blocked = next(record for record in records if record["status"] == "blocked")
    blocked["blocker"] = None

    with pytest.raises(TensionedCordAuditError, match="gravity"):
        load_tensioned_cord_ledger(_write_ledger(tmp_path / "ledger.json", document))

    document = _ledger(inventory)
    records = document["records"]
    assert isinstance(records, list)
    blocked = next(record for record in records if record["status"] == "blocked")
    blocked["blocker"] = None
    with pytest.raises(TensionedCordAuditError, match="blocker is required"):
        load_tensioned_cord_ledger(_write_ledger(tmp_path / "blocked-ledger.json", document))


def test_cli_audits_the_checked_in_closed_ledger() -> None:
    """Catches a CLI mutation that omits the closed tensioned-cord audit command."""
    repository_root = Path(__file__).resolve().parents[3]
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = sys.executable
    result = subprocess.run(
        [
            str(repository_root / "scripts" / "hangboard-packages.sh"),
            "audit-tensioned-cords",
            "--root",
            str(repository_root / "Hangboards"),
            "--ledger",
            str(
                repository_root
                / "docs/source-audits/2026-09-01-tensioned-cord-presentations.json"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "acceptedCount": 41,
        "blockedCount": 6,
        "blockers": [
            {
                "packageID": "frictitious.port-a-board",
                "presentationID": "cord-option-4-20mm-incut",
                "reason": "Exact current-revision first-party evidence does not establish this option's routing.",
            },
            *[
                {
                    "packageID": "yy.baguette-evo",
                    "presentationID": presentation_id,
                    "reason": "Visible side strands are established, but hidden continuity, terminals, and hardware are not.",
                }
                for presentation_id in (
                    "central-20-6",
                    "central-30-25",
                    "paired-12-8-6",
                    "paired-25-20-15-10",
                    "rounded-tray",
                )
            ],
        ],
        "packageCount": 20,
        "presentationCount": 47,
    }
