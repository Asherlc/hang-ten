from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest
from conftest import write_board_package, write_multi_presentation_board_package
from hangboard_packages.board_catalog import BoardInventory, discover_board_packages
from hangboard_packages.presentation_remediation_audit import (
    PresentationRemediationAuditError,
    PresentationRemediationReport,
    load_presentation_remediation_manifest,
    validate_presentation_remediation_manifest,
)


def _manifest(
    *, package_ids: list[str], records: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "phase": "sourceReclassification",
        "reviewDate": "2026-08-30",
        "packageIDs": package_ids,
        "records": records,
        "phase1Checks": {
            name: {"status": "pending", "command": None}
            for name in (
                "manifestValidation",
                "packageValidation",
                "packageTestSuite",
                "hangboardsDiff",
            )
        },
    }


def _record(
    boards: Path,
    package_slug: str,
    package_id: str,
    presentation_id: str,
    asset_path: str,
) -> dict[str, object]:
    data = (boards / package_slug / asset_path).read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    asset = f"{boards.name}/{package_slug}/{asset_path}"
    digest = hashlib.sha256(data).hexdigest()
    findings = {
        key: {
            "outcome": "conforms",
            "explanation": f"Cited evidence establishes {key}.",
        }
        for key in (
            "productLikeness",
            "material",
            "topology",
            "headOnPerspective",
            "smoothing",
            "framing",
            "crossCatalogConsistency",
        )
    }
    return {
        "packageID": package_id,
        "productName": "Fixture Board",
        "presentationID": presentation_id,
        "assetPath": asset,
        "workingSurface": "Published front working face",
        "physicalRevision": "Revision named by the cited first-party page",
        "manufacturer": "Fixture Maker",
        "materials": ["wood"],
        "formFactor": "fullWidthFixedBoard",
        "currentAsset": {
            "sha256": digest,
            "widthPixels": width,
            "heightPixels": height,
        },
        "decision": "keep",
        "findings": findings,
        "evidence": {
            "official": [
                {
                    "url": "https://manufacturer.example/fixture-board",
                    "publisher": "Fixture Maker",
                    "sourceKind": "officialProductPage",
                    "reviewedAt": "2026-08-30",
                    "revisionApplicability": "Exact named revision",
                    "imageRole": "Straight-on view establishes silhouette and contact layout.",
                    "supportedClaim": "The exact revision is a wood fixed board with the shown front working face.",
                }
            ],
            "independent": [
                {
                    "url": "https://retailer.example/fixture-board",
                    "publisher": "Independent Retailer",
                    "sourceKind": "retailer",
                    "reviewedAt": "2026-08-30",
                    "revisionApplicability": "Exact named revision",
                    "imageRole": "Real-world oblique product view corroborates finish and construction.",
                    "supportedClaim": "The production finish and component inventory match the official revision.",
                }
            ],
            "officialEvidenceGap": None,
            "independentEvidenceGap": None,
        },
        "comparator": {
            "assetPath": asset,
            "materialMatch": "Warm diffuse wood with bounded face-grain detail",
            "formFactorMatch": "Full-width fixed board",
            "reason": "This record is the accepted cohort baseline for framing and lighting only.",
            "baselineGap": None,
        },
        "generation": {
            "prompt": None,
            "sourceImages": [],
            "currentAssetRole": None,
            "candidates": [],
        },
        "final": {
            "acceptedAssetSHA256": digest,
            "finalDimensions": {"widthPixels": width, "heightPixels": height},
            "visualReviewerDecision": "acceptedCurrentAsset",
            "workbenchReview": {
                name: {"status": "pending", "evidence": None}
                for name in ("normal", "allActive", "individualHolds")
            },
            "validation": {
                name: {"status": "pending", "evidence": None}
                for name in (
                    "packageValidation",
                    "focusedTests",
                    "fullPackageSuite",
                    "buildForTesting",
                    "simulatorReview",
                )
            },
        },
    }


def _write_manifest(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _single_board_fixture(
    tmp_path: Path,
) -> tuple[Path, BoardInventory, dict[str, object]]:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "fixture-board")
    inventory = discover_board_packages(boards, require_complete_inventory=True)
    return (
        boards,
        inventory,
        _record(
            boards, "fixture-board", "fixture.board", "primary", "assets/primary.png"
        ),
    )


def _validate_document(
    tmp_path: Path,
    boards: Path,
    inventory: BoardInventory,
    records: list[dict[str, object]],
) -> PresentationRemediationReport:
    path = _write_manifest(
        tmp_path, _manifest(package_ids=["fixture.board"], records=records)
    )
    return validate_presentation_remediation_manifest(
        load_presentation_remediation_manifest(path), inventory, hangboards_root=boards
    )


def _mark_phase_2_repair(record: dict[str, object], decision: str) -> None:
    record["decision"] = decision
    record["final"]["acceptedAssetSHA256"] = None
    record["final"]["finalDimensions"] = None
    record["final"]["visualReviewerDecision"] = "pendingPhase2"
    record["comparator"] = {
        "assetPath": None,
        "materialMatch": None,
        "formFactorMatch": None,
        "reason": None,
        "baselineGap": "No current accepted comparator is available for this Phase 2 repair.",
    }


def test_manifest_inventory_must_equal_every_declared_presentation(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    write_multi_presentation_board_package(boards / "fixture-board")
    inventory = discover_board_packages(boards, require_complete_inventory=True)
    document = _manifest(
        package_ids=["fixture.board"],
        records=[
            _record(
                boards, "fixture-board", "fixture.board", "front", "assets/primary.png"
            )
        ],
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match=r"missing presentation record: fixture\.board/back",
    ):
        validate_presentation_remediation_manifest(
            load_presentation_remediation_manifest(_write_manifest(tmp_path, document)),
            inventory,
            hangboards_root=boards,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda record: record.update(presentationID="unknown"),
            "unknown presentation record",
        ),
        (
            lambda record: record.update(packageID="unknown.board"),
            "unknown presentation record",
        ),
        (
            lambda record: record.update(productName="Different"),
            "productName does not match",
        ),
        (
            lambda record: record.update(
                assetPath="Hangboards/fixture-board/assets/wrong.png"
            ),
            "assetPath does not match",
        ),
        (
            lambda record: record["currentAsset"].update(sha256="0" * 64),
            "SHA-256 does not match",
        ),
        (
            lambda record: record["currentAsset"].update(widthPixels=1),
            "dimensions do not match",
        ),
        (lambda record: record.update(decision="invent"), "decision must be one of"),
    ],
)
def test_record_mismatches_fail_closed(
    tmp_path: Path, mutation: object, message: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    mutation(record)  # type: ignore[operator]
    with pytest.raises(PresentationRemediationAuditError, match=message):
        _validate_document(tmp_path, boards, inventory, [record])


def test_duplicate_presentation_record_is_rejected(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    with pytest.raises(
        PresentationRemediationAuditError, match="duplicate presentation record"
    ):
        _validate_document(tmp_path, boards, inventory, [record, record.copy()])


def test_missing_finding_is_rejected(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    del record["findings"]["framing"]
    with pytest.raises(
        PresentationRemediationAuditError, match="findings is missing keys"
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize(
    "field, value",
    [
        ("sourceKind", "wrong"),
        ("url", "http://manufacturer.example/fixture-board"),
        ("url", "https://www.google.com/search?q=fixture"),
    ],
)
def test_evidence_kind_and_url_must_be_direct_https(
    tmp_path: Path, field: str, value: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0][field] = value
    with pytest.raises(PresentationRemediationAuditError):
        _validate_document(tmp_path, boards, inventory, [record])


def test_each_evidence_class_requires_sources_or_gap(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"] = []
    with pytest.raises(
        PresentationRemediationAuditError, match="official evidence requires"
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record["comparator"].update(
            assetPath="Hangboards/nope/assets/primary.png"
        ),
        lambda record: record["comparator"].update(
            baselineGap="Mixed modes are invalid."
        ),
    ],
)
def test_comparator_requires_ready_compatible_kept_record(
    tmp_path: Path, mutation: object
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    mutation(record)  # type: ignore[operator]
    with pytest.raises(PresentationRemediationAuditError):
        _validate_document(tmp_path, boards, inventory, [record])


def test_comparator_material_must_match_the_ready_baseline(tmp_path: Path) -> None:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "metal-board", board_id="metal.board")
    write_board_package(boards / "wood-board", board_id="wood.board")
    inventory = discover_board_packages(boards, require_complete_inventory=True)
    metal = _record(
        boards, "metal-board", "metal.board", "primary", "assets/primary.png"
    )
    wood = _record(boards, "wood-board", "wood.board", "primary", "assets/primary.png")
    metal["materials"] = ["metal"]
    metal["comparator"].update(assetPath=wood["assetPath"])
    path = _write_manifest(
        tmp_path,
        _manifest(package_ids=["metal.board", "wood.board"], records=[metal, wood]),
    )

    with pytest.raises(
        PresentationRemediationAuditError, match="comparator material is incompatible"
    ):
        validate_presentation_remediation_manifest(
            load_presentation_remediation_manifest(path),
            inventory,
            hangboards_root=boards,
        )


def test_comparator_reason_cannot_claim_geometry_evidence(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["comparator"]["reason"] = (
        "This accepted cohort baseline supplies geometry evidence."
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="comparator reason must not claim geometry evidence",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_accepted_keep_cannot_claim_a_comparator_baseline_gap(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["comparator"] = {
        "assetPath": None,
        "materialMatch": None,
        "formFactorMatch": None,
        "reason": None,
        "baselineGap": "No accepted metal portable baseline exists in the current catalog.",
    }
    with pytest.raises(
        PresentationRemediationAuditError,
        match="accepted keep requires a ready comparator",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_phase_2_repair_may_record_an_exact_comparator_gap(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["decision"] = "regenerate"
    record["findings"]["productLikeness"] = {
        "outcome": "nonconforming",
        "explanation": "The cited views establish a different silhouette.",
    }
    record["comparator"] = {
        "assetPath": None,
        "materialMatch": None,
        "formFactorMatch": None,
        "reason": None,
        "baselineGap": "Every current wood fixed asset needs Phase 2 repair, so none is an accepted baseline.",
    }
    record["final"]["acceptedAssetSHA256"] = None
    record["final"]["finalDimensions"] = None
    record["final"]["visualReviewerDecision"] = "pendingPhase2"
    report = _validate_document(tmp_path, boards, inventory, [record])
    assert report.to_json()["decisions"] == {"regenerate": 1}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record["generation"].update(sourceImages=["fixture"]),
        lambda record: record["generation"].update(candidates=["fixture"]),
        lambda record: record["generation"].update(prompt="Generate"),
    ],
)
def test_keep_cannot_claim_phase_2_generation(tmp_path: Path, mutation: object) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    mutation(record)  # type: ignore[operator]
    with pytest.raises(PresentationRemediationAuditError, match="keep must not claim"):
        _validate_document(tmp_path, boards, inventory, [record])


def test_keep_accepted_hash_must_match_current_asset(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["final"]["acceptedAssetSHA256"] = "0" * 64
    with pytest.raises(
        PresentationRemediationAuditError, match="keep accepted hash must match"
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_repair_record_cannot_claim_phase_2_output_or_validation(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["decision"] = "regenerate"
    record["final"]["validation"]["packageValidation"] = {
        "status": "passed",
        "evidence": "fixture",
    }
    with pytest.raises(
        PresentationRemediationAuditError,
        match="regenerate must not claim accepted output or final validation in Phase 1",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_removal_requires_sourced_nonconforming_findings(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "removeUnsupportedPresentation")

    with pytest.raises(
        PresentationRemediationAuditError,
        match="removeUnsupportedPresentation requires sourced nonconforming findings",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_revision_split_requires_two_named_conflicting_revisions(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "splitPhysicalRevision")

    with pytest.raises(
        PresentationRemediationAuditError,
        match="splitPhysicalRevision requires conflicting sources tied to named physical revisions",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_lane_filter_keeps_full_manifest_contract_and_reports_selected_board(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "first", board_id="first.board")
    write_board_package(boards / "second", board_id="second.board")
    inventory = discover_board_packages(boards, require_complete_inventory=True)
    first = _record(boards, "first", "first.board", "primary", "assets/primary.png")
    second = _record(boards, "second", "second.board", "primary", "assets/primary.png")
    second["productName"] = "Fixture Board"
    report = validate_presentation_remediation_manifest(
        load_presentation_remediation_manifest(
            _write_manifest(
                tmp_path,
                _manifest(
                    package_ids=["first.board", "second.board"], records=[first, second]
                ),
            )
        ),
        inventory,
        hangboards_root=boards,
        selected_package_ids=frozenset({"first.board"}),
    )
    assert report.to_json()["packageIDs"] == ["first.board"]
