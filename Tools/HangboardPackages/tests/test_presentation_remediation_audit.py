from __future__ import annotations

import copy
import hashlib
import json
import struct
from datetime import datetime
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import write_board_package, write_multi_presentation_board_package
from hangboard_packages.board_catalog import (
    BoardInventory,
    BoardPresentation,
    discover_board_packages,
)
import hangboard_packages.presentation_remediation_audit as presentation_audit
from hangboard_packages.presentation_remediation_audit import (
    PresentationRemediationAuditError,
    PresentationRemediationReport,
    load_presentation_remediation_manifest,
    validate_presentation_remediation_manifest,
)
from presentation_remediation_helpers import (
    empty_phase2_document as _empty_phase2_document,
    manifest as _manifest,
    record as _record,
    write_manifest as _write_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_PHASE2_MANIFEST = REPO_ROOT / "docs/source-audits/2026-08-30-hangboard-presentation-remediation-manifest.json"


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
    *,
    final_validation: bool = False,
) -> PresentationRemediationReport:
    path = _write_manifest(
        tmp_path, _manifest(package_ids=["fixture.board"], records=records)
    )
    options = {"final_validation": True} if final_validation else {}
    return validate_presentation_remediation_manifest(
        load_presentation_remediation_manifest(path),
        inventory,
        hangboards_root=boards,
        **options,
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


def _mark_phase1_checks_passed(document: dict[str, object]) -> None:
    for name in document["phase1Checks"]:
        document["phase1Checks"][name] = {
            "status": "passed",
            "command": f"rtk verify {name}",
        }


def _surface_unusable_statement(record: dict[str, object]) -> str:
    return f'Surface "{record["workingSurface"]}" is unusable.'


def _revision_conflict_statement(record: dict[str, object]) -> str:
    return (
        f'Surface "{record["workingSurface"]}" has conflicting physical revisions: '
        '"Revision A" versus "Revision B".'
    )


def _physical_revision_declaration() -> str:
    return 'Physical revisions: "Revision A" versus "Revision B".'


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
    ("field", "value"),
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


def test_evidence_rejects_duckduckgo_search_result_url(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["url"] = "https://duckduckgo.com/?q=fixture+board"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="must not be a search-result URL",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_evidence_rejects_www_duckduckgo_search_result_url(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["url"] = "https://www.duckduckgo.com/?q=fixture"

    with pytest.raises(PresentationRemediationAuditError, match="search-result URL"):
        _validate_document(tmp_path, boards, inventory, [record])


def test_evidence_accepts_searchlight_product_path(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["url"] = (
        "https://manufacturer.example/searchlight-board"
    )

    assert _validate_document(tmp_path, boards, inventory, [record]).to_json()[
        "decisions"
    ] == {"keep": 1}


def test_evidence_rejects_nested_search_result_path(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["url"] = (
        "https://manufacturer.example/products/search/fixture"
    )

    with pytest.raises(PresentationRemediationAuditError, match="search-result URL"):
        _validate_document(tmp_path, boards, inventory, [record])


def test_evidence_rejects_search_path_with_encoded_delimiters(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["url"] = (
        "https://manufacturer.example/products%2Fsearch%2Ffixture"
    )

    with pytest.raises(PresentationRemediationAuditError, match="search-result URL"):
        _validate_document(tmp_path, boards, inventory, [record])


def test_evidence_rejects_search_host_with_terminal_dot(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["url"] = "https://duckduckgo.com./?q=fixture"

    with pytest.raises(PresentationRemediationAuditError, match="search-result URL"):
        _validate_document(tmp_path, boards, inventory, [record])


def test_evidence_accepts_direct_product_url_with_unrelated_q_parameter(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["url"] = (
        "https://manufacturer.example/fixture-board?q=campaign"
    )

    report = _validate_document(tmp_path, boards, inventory, [record])

    assert report.to_json()["decisions"] == {"keep": 1}


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
        match="comparator reason must use canonical style-only statement",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_comparator_reason_cannot_claim_silhouette_or_contact_evidence(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["comparator"]["reason"] = (
        "This accepted cohort baseline proves the silhouette and contact layout."
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="comparator reason must use canonical style-only statement",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_comparator_reason_rejects_unlisted_geometry_proof_wording(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["comparator"]["reason"] = (
        "Accepted cohort baseline proves matching cutout arrangement and grip placement."
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="comparator reason must use canonical style-only statement",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_comparator_reason_rejects_geometry_claim_after_details_delimiter(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["comparator"]["reason"] = (
        "Accepted cohort baseline; style-only: framing.\n\nDetails:\n"
        "This baseline proves matching cutout arrangement."
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="comparator reason must use canonical style-only statement",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_comparator_cannot_target_a_non_kept_record(tmp_path: Path) -> None:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "accepted", board_id="accepted.board")
    write_board_package(boards / "repair", board_id="repair.board")
    inventory = discover_board_packages(boards, require_complete_inventory=True)
    accepted = _record(
        boards, "accepted", "accepted.board", "primary", "assets/primary.png"
    )
    repair = _record(boards, "repair", "repair.board", "primary", "assets/primary.png")
    _mark_phase_2_repair(repair, "regenerate")
    repair["findings"]["productLikeness"]["outcome"] = "nonconforming"
    accepted["comparator"].update(assetPath=repair["assetPath"])
    manifest = _write_manifest(
        tmp_path,
        _manifest(
            package_ids=["accepted.board", "repair.board"],
            records=[accepted, repair],
        ),
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="comparator must identify a ready accepted keep record",
    ):
        validate_presentation_remediation_manifest(
            load_presentation_remediation_manifest(manifest),
            inventory,
            hangboards_root=boards,
        )


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


@pytest.mark.parametrize(
    "finding_key",
    [
        "productLikeness",
        "material",
        "topology",
        "headOnPerspective",
        "smoothing",
        "framing",
        "crossCatalogConsistency",
    ],
)
@pytest.mark.parametrize("outcome", ["nonconforming", "uncertain", "notApplicable"])
def test_source_supported_accepted_keep_requires_all_seven_findings_to_conform(
    tmp_path: Path, finding_key: str, outcome: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["findings"][finding_key]["outcome"] = outcome

    with pytest.raises(
        PresentationRemediationAuditError,
        match="source-supported accepted keep requires all seven findings to conform",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_evidence_blocked_keep_cannot_claim_acceptance(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"] = []
    record["evidence"]["officialEvidenceGap"] = (
        "Exact manufacturer and archive searches did not establish the revision."
    )
    record["findings"]["productLikeness"]["outcome"] = "uncertain"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="evidence-blocked keep must remain blockedEvidence without accepted output",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize("finding_key", ["productLikeness", "topology"])
@pytest.mark.parametrize("outcome", ["nonconforming", "uncertain"])
def test_edit_requires_confirmed_product_likeness_and_topology(
    tmp_path: Path, finding_key: str, outcome: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "edit")
    record["findings"][finding_key]["outcome"] = outcome
    record["findings"]["crossCatalogConsistency"]["outcome"] = "nonconforming"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="edit requires conforming productLikeness and topology findings",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_edit_requires_a_bounded_failure_or_uncertainty(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "edit")

    with pytest.raises(
        PresentationRemediationAuditError,
        match="edit requires a bounded presentation failure or uncertainty",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize(
    "finding_key",
    [
        "material",
        "headOnPerspective",
        "smoothing",
        "framing",
        "crossCatalogConsistency",
    ],
)
@pytest.mark.parametrize("outcome", ["nonconforming", "uncertain"])
def test_edit_accepts_each_bounded_presentation_defect(
    tmp_path: Path, finding_key: str, outcome: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "edit")
    record["findings"][finding_key]["outcome"] = outcome

    report = _validate_document(tmp_path, boards, inventory, [record])

    assert report.to_json()["decisions"] == {"edit": 1}


@pytest.mark.parametrize("finding_key", ["material", "headOnPerspective", None])
def test_regenerate_requires_a_likeness_or_topology_failure(
    tmp_path: Path, finding_key: str | None
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "regenerate")
    if finding_key is not None:
        record["findings"][finding_key]["outcome"] = "nonconforming"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="regenerate requires a productLikeness or topology failure or uncertainty",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize("finding_key", ["productLikeness", "topology"])
@pytest.mark.parametrize("outcome", ["nonconforming", "uncertain"])
def test_regenerate_accepts_likeness_or_topology_failure_or_uncertainty(
    tmp_path: Path, finding_key: str, outcome: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "regenerate")
    record["findings"][finding_key]["outcome"] = outcome

    report = _validate_document(tmp_path, boards, inventory, [record])

    assert report.to_json()["decisions"] == {"regenerate": 1}


def test_comparator_cannot_target_a_keep_with_nonconforming_findings(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "consumer", board_id="consumer.board")
    write_board_package(boards / "baseline", board_id="baseline.board")
    inventory = discover_board_packages(boards, require_complete_inventory=True)
    consumer = _record(
        boards, "consumer", "consumer.board", "primary", "assets/primary.png"
    )
    baseline = _record(
        boards, "baseline", "baseline.board", "primary", "assets/primary.png"
    )
    consumer["comparator"]["assetPath"] = baseline["assetPath"]
    baseline["findings"]["material"]["outcome"] = "nonconforming"
    manifest = _write_manifest(
        tmp_path,
        _manifest(
            package_ids=["consumer.board", "baseline.board"],
            records=[consumer, baseline],
        ),
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="source-supported accepted keep requires all seven findings to conform",
    ):
        validate_presentation_remediation_manifest(
            load_presentation_remediation_manifest(manifest),
            inventory,
            hangboards_root=boards,
        )


@pytest.mark.parametrize(
    ("section", "check_name"),
    [("workbenchReview", "normal"), ("validation", "packageValidation")],
)
def test_source_reclassification_keep_cannot_claim_phase_2_checks(
    tmp_path: Path, section: str, check_name: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["final"][section][check_name] = {
        "status": "passed",
        "evidence": "fabricated Phase 2 result",
    }

    with pytest.raises(
        PresentationRemediationAuditError,
        match="sourceReclassification presentation checks must remain pending with null evidence",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_presentation_check_rejects_unknown_status(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["final"]["workbenchReview"]["normal"]["status"] = "invented"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="status must be one of",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize(
    ("status", "evidence"),
    [("pending", "premature evidence"), ("passed", None), ("failed", None)],
)
def test_presentation_check_rejects_invalid_status_evidence_pair(
    tmp_path: Path, status: str, evidence: str | None
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["final"]["validation"]["focusedTests"] = {
        "status": status,
        "evidence": evidence,
    }

    with pytest.raises(
        PresentationRemediationAuditError,
        match="status and evidence must be pending/null or passed-or-failed/non-empty",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize(
    ("status", "command"),
    [
        ("invented", None),
        ("pending", "rtk verify too-early"),
        ("passed", None),
    ],
)
def test_phase1_check_rejects_invalid_status_command_pair(
    tmp_path: Path, status: str, command: str | None
) -> None:
    document = _manifest(package_ids=[], records=[])
    document["phase1Checks"]["manifestValidation"] = {
        "status": status,
        "command": command,
    }

    with pytest.raises(PresentationRemediationAuditError, match="phase1Checks"):
        load_presentation_remediation_manifest(_write_manifest(tmp_path, document))


def test_final_validation_requires_all_four_phase1_checks_passed(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    document = _manifest(package_ids=["fixture.board"], records=[record])
    _mark_phase1_checks_passed(document)
    document["phase1Checks"]["hangboardsDiff"] = {
        "status": "pending",
        "command": None,
    }
    manifest = load_presentation_remediation_manifest(
        _write_manifest(tmp_path, document)
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="final Phase 1 validation requires all phase1Checks passed",
    ):
        validate_presentation_remediation_manifest(
            manifest,
            inventory,
            hangboards_root=boards,
            final_validation=True,
        )


def test_final_validation_accepts_all_four_passed_phase1_checks(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    document = _manifest(package_ids=["fixture.board"], records=[record])
    _mark_phase1_checks_passed(document)

    report = validate_presentation_remediation_manifest(
        load_presentation_remediation_manifest(_write_manifest(tmp_path, document)),
        inventory,
        hangboards_root=boards,
        final_validation=True,
    )

    assert report.to_json()["presentationCount"] == 1


def test_final_validation_rejects_lane_filter(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    document = _manifest(package_ids=["fixture.board"], records=[record])
    _mark_phase1_checks_passed(document)

    with pytest.raises(
        PresentationRemediationAuditError,
        match="final Phase 1 validation requires full-catalog coverage",
    ):
        validate_presentation_remediation_manifest(
            load_presentation_remediation_manifest(
                _write_manifest(tmp_path, document)
            ),
            inventory,
            hangboards_root=boards,
            selected_package_ids=frozenset({"fixture.board"}),
            final_validation=True,
        )


def test_manifest_review_date_must_equal_planned_audit_date(tmp_path: Path) -> None:
    document = _manifest(package_ids=[], records=[])
    document["reviewDate"] = "2026-08-29"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="reviewDate must equal planned audit date 2026-08-30",
    ):
        load_presentation_remediation_manifest(_write_manifest(tmp_path, document))


def test_evidence_reviewed_at_must_equal_manifest_review_date(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    record["evidence"]["official"][0]["reviewedAt"] = "2026-08-29"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="reviewedAt must equal manifest reviewDate 2026-08-30",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_repair_record_cannot_claim_phase_2_accepted_output(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "regenerate")
    record["final"]["acceptedAssetSHA256"] = record["currentAsset"]["sha256"]

    with pytest.raises(
        PresentationRemediationAuditError,
        match="regenerate must not claim accepted output or final validation in Phase 1",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_repair_record_cannot_claim_phase_2_final_validation(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "regenerate")
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
        match="removeUnsupportedPresentation requires canonical cited proof",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_removal_rejects_nonconforming_but_usable_surface(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "removeUnsupportedPresentation")
    record["findings"]["topology"] = {
        "outcome": "nonconforming",
        "explanation": "Published front working face is usable despite the topology mismatch.",
    }
    record["evidence"]["official"][0]["supportedClaim"] = (
        "The Published front working face is usable despite the topology mismatch."
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="removeUnsupportedPresentation requires canonical cited proof",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize(
    "denial",
    [
        'Not true: Surface "Published front working face" is not usable.',
        'Surface "Published front working face" is not usable, but it remains usable.',
        'The quote "Surface \\"Published front working face\\" is not usable." is false.',
    ],
)
def test_removal_rejects_negated_or_quoted_unusability_claim(
    tmp_path: Path, denial: str
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "removeUnsupportedPresentation")
    record["findings"]["topology"] = {
        "outcome": "nonconforming",
        "explanation": denial,
    }
    record["evidence"]["official"][0]["supportedClaim"] = denial

    with pytest.raises(
        PresentationRemediationAuditError,
        match="removeUnsupportedPresentation requires canonical cited proof",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_removal_accepts_cited_proof_that_surface_is_not_usable(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "removeUnsupportedPresentation")
    record["findings"]["topology"] = {
        "outcome": "nonconforming",
        "explanation": _surface_unusable_statement(record),
    }
    record["evidence"]["official"][0]["supportedClaim"] = _surface_unusable_statement(
        record
    )

    report = _validate_document(tmp_path, boards, inventory, [record])

    assert report.to_json()["decisions"] == {"removeUnsupportedPresentation": 1}


def test_removal_rejects_details_suffix_on_authorization_statement(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "removeUnsupportedPresentation")
    statement = _surface_unusable_statement(record) + "\n\nDetails:\nextra"
    record["findings"]["topology"] = {
        "outcome": "nonconforming",
        "explanation": statement,
    }
    record["evidence"]["official"][0]["supportedClaim"] = statement

    with pytest.raises(
        PresentationRemediationAuditError, match="canonical cited proof"
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_revision_split_requires_two_named_conflicting_revisions(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "splitPhysicalRevision")

    with pytest.raises(
        PresentationRemediationAuditError,
        match="splitPhysicalRevision requires canonical physicalRevision declaration",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_revision_split_rejects_distinct_but_nonconflicting_labels(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "splitPhysicalRevision")
    record["evidence"]["official"][0]["revisionApplicability"] = "Revision A"
    record["evidence"]["independent"][0]["revisionApplicability"] = "Revision B"
    record["physicalRevision"] = _physical_revision_declaration()

    with pytest.raises(
        PresentationRemediationAuditError,
        match="splitPhysicalRevision requires canonical cited conflict proof",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_revision_split_rejects_negated_conflict_claim(tmp_path: Path) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "splitPhysicalRevision")
    record["physicalRevision"] = _physical_revision_declaration()
    denial = 'Surface "Published front working face" has no conflict between Revision A and Revision B.'
    record["evidence"]["official"][0].update(
        revisionApplicability="Revision A",
        supportedClaim=denial,
    )
    record["evidence"]["independent"][0].update(
        revisionApplicability="Revision B",
        supportedClaim=denial,
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="splitPhysicalRevision requires canonical cited conflict proof",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_revision_split_accepts_cited_named_physical_revision_conflict(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "splitPhysicalRevision")
    record["physicalRevision"] = _physical_revision_declaration()
    statement = _revision_conflict_statement(record)
    record["evidence"]["official"][0].update(
        revisionApplicability="Revision A",
        supportedClaim=statement,
    )
    record["evidence"]["independent"][0].update(
        revisionApplicability="Revision B",
        supportedClaim=statement,
    )

    report = _validate_document(tmp_path, boards, inventory, [record])

    assert report.to_json()["decisions"] == {"splitPhysicalRevision": 1}


def test_revision_split_rejects_substring_physical_revision_linkage(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "splitPhysicalRevision")
    record["physicalRevision"] = "Revision Alphabet and Revision Beta"
    statement = _revision_conflict_statement(record)
    record["evidence"]["official"][0].update(
        revisionApplicability="Revision A", supportedClaim=statement
    )
    record["evidence"]["independent"][0].update(
        revisionApplicability="Revision B", supportedClaim=statement
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="canonical physicalRevision declaration",
    ):
        _validate_document(tmp_path, boards, inventory, [record])


def test_revision_split_rejects_details_suffix_on_conflict_statement(
    tmp_path: Path,
) -> None:
    boards, inventory, record = _single_board_fixture(tmp_path)
    _mark_phase_2_repair(record, "splitPhysicalRevision")
    record["physicalRevision"] = _physical_revision_declaration()
    statement = _revision_conflict_statement(record) + "\n\nDetails:\nextra"
    record["evidence"]["official"][0].update(
        revisionApplicability="Revision A", supportedClaim=statement
    )
    record["evidence"]["independent"][0].update(
        revisionApplicability="Revision B", supportedClaim=statement
    )

    with pytest.raises(
        PresentationRemediationAuditError, match="canonical cited conflict proof"
    ):
        _validate_document(tmp_path, boards, inventory, [record])


@pytest.mark.parametrize("schema_version", [1.0, True])
def test_manifest_schema_version_must_be_a_json_integer(
    tmp_path: Path, schema_version: object
) -> None:
    document = _manifest(package_ids=[], records=[])
    document["schemaVersion"] = schema_version

    with pytest.raises(
        PresentationRemediationAuditError,
        match="schemaVersion must be a JSON integer equal to 1",
    ):
        load_presentation_remediation_manifest(_write_manifest(tmp_path, document))


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


def test_phase2_public_loader_rejects_unknown_nested_keys(tmp_path: Path) -> None:
    document = _empty_phase2_document()
    document["phase2"]["extra"] = True

    with pytest.raises(
        PresentationRemediationAuditError,
        match="phase2 has unknown keys",
    ):
        load_presentation_remediation_manifest(_write_manifest(tmp_path, document))


def test_phase2_public_interfaces_are_available() -> None:
    assert tuple(presentation_audit.PresentationValidationMode) == (
        presentation_audit.PresentationValidationMode.SOURCE_RECLASSIFICATION,
        presentation_audit.PresentationValidationMode.PHASE2_PREFLIGHT,
        presentation_audit.PresentationValidationMode.PHASE2_PARTIAL,
        presentation_audit.PresentationValidationMode.PHASE2_FINAL,
    )
    assert callable(presentation_audit.render_phase2_generation_prompt)
    assert callable(presentation_audit.render_phase2_capability_probe_prompt)
    assert callable(presentation_audit.verify_transient_source_files)
    assert callable(presentation_audit.verify_transient_candidate_files)


def test_capability_prompt_renderer_is_exact_and_disposable() -> None:
    pending = presentation_audit.ByteVerification("pending", None, None, None)
    probe = presentation_audit.CanvasBehaviorProbe(
        "1000x1000-edit-mxedge-large",
        "edit",
        "lattice.mxedge-lift-large/primary",
        "stored later",
        (
            presentation_audit.GenerationSourceInput(
                "official-0-image-0",
                "officialEvidence",
                "/records/24/evidence/official/0",
                "https://manufacturer.example/mxedge",
                None,
                "Straight-on product evidence.",
                "0" * 64,
                True,
                pending,
            ),
        ),
        presentation_audit.PreflightComparatorSet(
            "preflightCapabilityOnly",
            None,
            None,
            ("compositionFramingScale", "materialTextureLighting"),
            ("official-0-image-0",),
            (),
            presentation_audit._PREFLIGHT_MATERIAL_CONTRACT,
            "forbidden",
            datetime.fromisoformat("2026-08-31T00:00:00+00:00"),
        ),
        (),
        "pending",
        None,
    )
    assert presentation_audit.render_phase2_capability_probe_prompt(
        probe,
        presentation_audit.RequiredCanvas(1000, 1000),
    ) == (
        "Purpose: disposable image-tool exact-canvas capability probe; never a production candidate, comparator, baseline, or accepted asset\n"
        "Behavior: edit-capability\n"
        "Representative: lattice.mxedge-lift-large/primary; identity cues come only from freshly reopened official/independent evidence\n"
        "Input images: official-0-image-0, officialEvidence, Straight-on product evidence., https://manufacturer.example/mxedge; for edit-capability only, the current target is tool input but not evidence or style reference\n"
        "Scene/backdrop: common off-white studio background; no wall or mounting scenery\n"
        "Composition reference: unavailable\n"
        "Material reference: unavailable; live evidence and the shared material contract govern material appearance\n"
        f"Material contract: {presentation_audit._PREFLIGHT_MATERIAL_CONTRACT}\n"
        "Canvas request: untouched PNG output exactly 1000 by 1000\n"
        "Disposition: every returned output is capabilityProbeRejected and must be hashed, recorded separately, and deleted\n"
        "Production authorization: forbidden\n"
        "Avoid: branding, labels, logos, text, watermark, transparent background, camera tilt, invented product detail, and every post-processing operation"
    )


def _transient_manifest(tmp_path: Path) -> tuple[object, Path, str]:
    boards, _, _ = _single_board_fixture(tmp_path)
    source_path = boards / "fixture-board" / "assets" / "primary.png"
    sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    width, height = struct.unpack(">II", source_path.read_bytes()[16:24])
    loaded = load_presentation_remediation_manifest(
        _write_manifest(
            tmp_path,
            _manifest(
                package_ids=["fixture.board"],
                records=[
                    _record(
                        boards,
                        "fixture-board",
                        "fixture.board",
                        "primary",
                        "assets/primary.png",
                    )
                ],
            ),
        )
    )
    record = replace(
        loaded.records[0],
        generation=presentation_audit.Phase2Generation(
            "builtInEdit",
            None,
            presentation_audit.RequiredCanvas(width, height),
            (
                presentation_audit.GenerationSourceInput(
                    "current-target",
                    "currentAsset",
                    None,
                    None,
                    str(source_path),
                    "Built-in edit target and topology/likeness invariant.",
                    sha,
                    True,
                    presentation_audit.ByteVerification("pending", None, None, None),
                ),
            ),
            "Built-in edit target and topology/likeness invariant.",
            (
                presentation_audit.GenerationCandidate(
                    1,
                    str(source_path),
                    sha,
                    width,
                    height,
                    "accepted",
                    "Fixture candidate.",
                    presentation_audit.CandidateProvenance(
                        "builtInImageGen", True, "none"
                    ),
                    presentation_audit.ByteVerification("pending", None, None, None),
                ),
            ),
        ),
    )
    return replace(loaded, schema_version=2, phase="assetRemediation", records=(record,)), source_path, sha


def test_transient_verifiers_hash_present_bytes_and_candidate_ihdr(tmp_path: Path) -> None:
    manifest, path, sha = _transient_manifest(tmp_path)

    assert presentation_audit.verify_transient_source_files(manifest, {sha: path}) == (sha,)
    assert presentation_audit.verify_transient_candidate_files(manifest, {sha: path}) == (sha,)

    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(PresentationRemediationAuditError, match="candidate SHA-256 mismatch"):
        presentation_audit.verify_transient_candidate_files(manifest, {sha: path})


def test_production_prompt_renderer_uses_exact_literal_record_fields(
    tmp_path: Path,
) -> None:
    manifest, path, sha = _transient_manifest(tmp_path)
    record = replace(
        manifest.records[0],
        decision="edit",
        phase2_comparator=presentation_audit.Phase2Comparator(
            presentation_audit.ComparatorSelection(
                "readyBaseline",
                str(path),
                "fixture.board/primary",
                sha,
                presentation_audit._SINGULAR_COMPARATOR_REASON,
                datetime.fromisoformat("2026-08-31T00:00:00+00:00"),
            ),
            None,
            None,
        ),
    )
    canvas = record.generation.required_canvas
    assert canvas is not None

    rendered = presentation_audit.render_phase2_generation_prompt(record)

    assert rendered == (
        "Use case: precise-object-edit\n"
        f"Asset type: Hang Ten package presentation PNG at {record.asset_path}\n"
        "Primary request: edit Fixture Board; physical revision: Revision named by the cited first-party page; working surface: Published front working face\n"
        f"Input images: current-target, currentAsset, Built-in edit target and topology/likeness invariant., {path}\n"
        "Scene/backdrop: common off-white studio background; no wall or mounting scenery\n"
        "Subject: The exact revision is a wood fixed board with the shown front working face.; The production finish and component inventory match the official revision.\n"
        "Style/medium: original simplified unbranded catalog product render, not a photograph\n"
        f"Composition/framing: orthographic head-on to Published front working face; centered; complete uncropped product; untouched output canvas exactly {canvas.width_pixels} by {canvas.height_pixels}\n"
        "Lighting/mood: neutral direction; restrained contact shadow; controlled depth relief\n"
        "Materials/textures: wood; preserve only evidence-supported finish and construction cues\n"
        "Repair findings: \n"
        f"Comparator: singular readyBaseline: {path}, fixture.board/primary, {sha}, {presentation_audit._SINGULAR_COMPARATOR_REASON}\n"
        "Bootstrap material ruling: not applicable; singular ready baseline selected\n"
        "Current asset role: Built-in edit target and topology/likeness invariant.\n"
        "Constraints: preserve every source-proved contact, component, silhouette, and usable-surface orientation; add no unsupported detail; output must already have exact dimensions\n"
        "Avoid: branding, labels, logos, text, watermark, transparent background, camera tilt, source-photo styling, invented contacts, invented hardware, and every forbidden post-processing operation"
    )


def _validate_historical_phase2_document(
    tmp_path: Path,
    document: dict[str, object],
) -> PresentationRemediationReport:
    historical_root = tmp_path / "Hangboards"
    live_inventory = discover_board_packages(
        REPO_ROOT / "Hangboards",
        require_complete_inventory=True,
    )
    historical_records_by_package = {
        package_id: [
            record
            for record in document["records"]
            if record["packageID"] == package_id
        ]
        for package_id in document["packageIDs"]
    }
    inventory = replace(
        live_inventory,
        packages=tuple(
            replace(
                package,
                board=replace(
                    package.board,
                    presentations=tuple(
                        BoardPresentation(
                            id=record["presentationID"],
                            name=record["workingSurface"],
                            asset_path=Path(record["assetPath"])
                            .relative_to(Path("Hangboards") / package.root.name)
                            .as_posix(),
                            aspect_ratio=(
                                record["currentAsset"]["widthPixels"]
                                / record["currentAsset"]["heightPixels"]
                            ),
                            is_default=index == 0,
                        )
                        for index, record in enumerate(
                            historical_records_by_package[package.board.id]
                        )
                    ),
                ),
            )
            for package in live_inventory.packages
        ),
    )
    for record in document["records"]:
        asset_path = historical_root / Path(record["assetPath"]).relative_to(
            "Hangboards"
        )
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.touch()
    historical_facts = {
        (
            historical_root
            / Path(record["assetPath"]).relative_to("Hangboards")
        ).resolve(): (
            record["currentAsset"]["sha256"],
            record["currentAsset"]["widthPixels"],
            record["currentAsset"]["heightPixels"],
        )
        for record in document["records"]
    }
    read_live_png_facts = presentation_audit._current_png_facts

    def read_historical_png_facts(path: Path) -> tuple[str, int, int]:
        facts = historical_facts.get(path.resolve())
        return facts if facts is not None else read_live_png_facts(path)

    # The schema-2 document is an intentionally immutable initial-state ledger.
    # Later bounded repairs deliberately leave it unchanged, so contract tests
    # reconstruct its presentation paths and replay its recorded PNG facts while
    # production validation remains strict against the live package bytes.
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            presentation_audit,
            "_current_png_facts",
            read_historical_png_facts,
        )
        return validate_presentation_remediation_manifest(
            load_presentation_remediation_manifest(
                _write_manifest(tmp_path, document)
            ),
            inventory,
            hangboards_root=historical_root,
            validation_mode=presentation_audit.PresentationValidationMode.PHASE2_PREFLIGHT,
        )


def test_initial_phase2_manifest_has_exact_pending_catalog_preflight(
    tmp_path: Path,
) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))

    report = _validate_historical_phase2_document(tmp_path, document)

    assert document["schemaVersion"] == 2
    assert document["phase"] == "assetRemediation"
    assert report.presentation_count == 85
    assert report.original_presentation_count == 85
    assert report.inventory_presentation_count == 85
    assert report.canvas_class_count == 20
    assert report.canvas_covered_repair_count == 65
    assert report.capability_probe_artifact_count == 0
    assert report.pending_phase2_action_count == 66
    assert report.historical_evidence_blocked_keeps == 2
    assert report.blocked_phase2_action_count == 0
    probes = [
        probe
        for canvas_class in document["phase2"]["canvasPreflight"]["classes"]
        for probe in canvas_class["behaviorProbes"]
    ]
    assert len(probes) == 22
    assert all(
        probe["preflightComparatorSet"]["materialTextureLighting"] is None
        and "materialTextureLighting"
        in probe["preflightComparatorSet"]["unavailableAxes"]
        for probe in probes
    )
    mini_primary = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "lattice.mini-bar/primary"
    )
    assert mini_primary["comparator"]["assetPath"] == mini_primary["assetPath"]
    live_mini_bar = next(
        package
        for package in discover_board_packages(
            REPO_ROOT / "Hangboards", require_complete_inventory=True
        ).packages
        if package.board.id == "lattice.mini-bar"
    )
    assert tuple(
        presentation.id for presentation in live_mini_bar.board.presentations
    ) == ("edge-10", "edge-20", "ergonomic-jug", "mini-pinch")


def test_production_action_requires_passed_canvas_preflight(tmp_path: Path) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    record = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "beastmaker-1000/primary"
    )
    comparator = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "beastmaker-2000/primary"
    )
    record["phase2Action"] = {"state": "inProgress", "blockedReason": None}
    record["phase2EvidenceReview"] = {
        "result": "confirmed",
        "reviewedAt": "2026-08-31T00:00:00+00:00",
        "officialURLsReopened": [
            source["url"] for source in record["evidence"]["official"]
        ],
        "independentURLsReopened": [
            source["url"] for source in record["evidence"]["independent"]
        ],
        "evidenceGapSearchesRepeated": [],
        "notes": "Evidence reopened for the production action.",
    }
    record["phase2Comparator"]["generationTime"] = {
        "mode": "readyBaseline",
        "assetPath": comparator["assetPath"],
        "sourceRecordKey": "beastmaker-2000/primary",
        "acceptedAssetSHA256": comparator["final"]["acceptedAssetSHA256"],
        "reason": presentation_audit._SINGULAR_COMPARATOR_REASON,
        "selectedAt": "2026-08-31T00:00:00+00:00",
    }

    with pytest.raises(
        PresentationRemediationAuditError,
        match="production actions require passed canvas preflight",
    ):
        _validate_historical_phase2_document(tmp_path, document)


def test_phase2_canonical_matrix_rejects_repair_reclassified_as_removal(
    tmp_path: Path,
) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    record = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "beastmaker-1000/primary"
    )
    record["decision"] = "removeUnsupportedPresentation"
    record["generation"] = {
        "mode": "none",
        "prompt": None,
        "requiredCanvas": None,
        "sourceInputs": [],
        "currentAssetRole": None,
        "candidates": [],
    }
    record["phase2Comparator"] = {
        "generationTime": None,
        "bootstrapComparatorSet": None,
        "final": None,
    }

    with pytest.raises(
        PresentationRemediationAuditError,
        match="Phase 2 remediation decision/batch matrix does not match canonical catalog",
    ):
        _validate_historical_phase2_document(tmp_path, document)


def test_started_production_requires_canonical_prompt_and_inputs(tmp_path: Path) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    document["phase2"]["canvasPreflight"]["status"] = "passed"
    for canvas_class in document["phase2"]["canvasPreflight"]["classes"]:
        canvas_class["status"] = "passed"
        for probe in canvas_class["behaviorProbes"]:
            probe["status"] = "passed"
    record = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "beastmaker-1000/primary"
    )
    comparator = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "beastmaker-2000/primary"
    )
    record["phase2Action"] = {"state": "inProgress", "blockedReason": None}
    record["phase2EvidenceReview"] = {
        "result": "confirmed",
        "reviewedAt": "2026-08-31T00:00:00+00:00",
        "officialURLsReopened": [
            source["url"] for source in record["evidence"]["official"]
        ],
        "independentURLsReopened": [
            source["url"] for source in record["evidence"]["independent"]
        ],
        "evidenceGapSearchesRepeated": [],
        "notes": "Evidence reopened for the production action.",
    }
    record["phase2Comparator"]["generationTime"] = {
        "mode": "readyBaseline",
        "assetPath": comparator["assetPath"],
        "sourceRecordKey": "beastmaker-2000/primary",
        "acceptedAssetSHA256": comparator["final"]["acceptedAssetSHA256"],
        "reason": presentation_audit._SINGULAR_COMPARATOR_REASON,
        "selectedAt": "2026-08-31T00:00:00+00:00",
    }

    with pytest.raises(
        PresentationRemediationAuditError,
        match="started production requires canonical prompt and complete inputs",
    ):
        _validate_historical_phase2_document(tmp_path, document)


def test_source_reclassification_rejects_schema2_manifest(tmp_path: Path) -> None:
    boards = tmp_path / "Hangboards"
    boards.mkdir()
    inventory = discover_board_packages(boards, require_complete_inventory=True)
    manifest = load_presentation_remediation_manifest(
        _write_manifest(tmp_path, _empty_phase2_document())
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="source reclassification requires schemaVersion 1",
    ):
        validate_presentation_remediation_manifest(
            manifest,
            inventory,
            hangboards_root=boards,
        )


def test_phase2_matrix_freezes_every_record_decision_and_batch(
    tmp_path: Path,
) -> None:
    inventory = discover_board_packages(
        REPO_ROOT / "Hangboards",
        require_complete_inventory=True,
    )

    def validate(document: dict[str, object]) -> None:
        validate_presentation_remediation_manifest(
            load_presentation_remediation_manifest(_write_manifest(tmp_path, document)),
            inventory,
            hangboards_root=REPO_ROOT / "Hangboards",
            validation_mode=presentation_audit.PresentationValidationMode.PHASE2_PREFLIGHT,
        )

    baseline = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    assert len(baseline["records"]) == 85

    for record_index in range(len(baseline["records"])):
        for field, original_replacement in (
            ("decision", "keep"),
            ("repairBatchID", "portable"),
        ):
            document = copy.deepcopy(baseline)
            record = document["records"][record_index]
            replacement = original_replacement
            if record[field] == original_replacement:
                replacement = "regenerate" if field == "decision" else None
            record[field] = replacement
            with pytest.raises(
                PresentationRemediationAuditError,
                match="Phase 2 remediation decision/batch matrix does not match canonical catalog",
            ):
                validate(document)


def test_pending_action_cannot_promote_accepted_final_bytes(tmp_path: Path) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    record = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "beastmaker-1000/primary"
    )
    record["final"]["acceptedAssetSHA256"] = record["currentAsset"]["sha256"]
    record["final"]["finalDimensions"] = {
        "widthPixels": record["currentAsset"]["widthPixels"],
        "heightPixels": record["currentAsset"]["heightPixels"],
    }
    record["final"]["visualReviewerDecision"] = "acceptedPhase2"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="only completed actions may promote accepted candidate or final bytes",
    ):
        _validate_historical_phase2_document(tmp_path, document)


def test_pending_batch_cannot_prewrite_passed_checks(tmp_path: Path) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    document["phase2"]["batches"][0]["checks"]["packageValidation"] = {
        "status": "passed",
        "evidence": "scripts/hangboard-packages.sh validate --root Hangboards",
    }

    with pytest.raises(
        PresentationRemediationAuditError,
        match="pending batch cannot prewrite passed checks",
    ):
        _validate_historical_phase2_document(tmp_path, document)


@pytest.mark.parametrize("path_bytes", [b"\x89PNG\r\n\x1a\n", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"])
def test_transient_candidate_truncated_png_is_domain_error(
    tmp_path: Path,
    path_bytes: bytes,
) -> None:
    manifest, path, sha = _transient_manifest(tmp_path)
    path.write_bytes(path_bytes)

    with pytest.raises(PresentationRemediationAuditError, match="asset is not a PNG"):
        presentation_audit.verify_transient_candidate_files(manifest, {sha: path})


def test_pending_preflight_reason_fields_fail_closed(tmp_path: Path) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    document["phase2"]["canvasPreflight"]["classes"][0]["behaviorProbes"][0][
        "blockedReason"
    ] = "not blocked"

    with pytest.raises(
        PresentationRemediationAuditError,
        match="pending/passed preflight probe cannot have blockedReason",
    ):
        _validate_historical_phase2_document(tmp_path, document)


def test_preflight_rejects_untracked_comparator_input(tmp_path: Path) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    probe = document["phase2"]["canvasPreflight"]["classes"][0][
        "behaviorProbes"
    ][0]
    unrelated = next(
        record
        for record in document["records"]
        if f'{record["packageID"]}/{record["presentationID"]}'
        == "soill.iron-palm-2/primary"
    )
    unrelated_path = REPO_ROOT / unrelated["assetPath"]
    probe["sourceInputs"].append(
        {
            "id": "untracked-comparator",
            "sourceType": "comparator",
            "evidencePointer": None,
            "sourceURL": None,
            "assetPath": str(unrelated_path),
            "role": "Unapproved material reference.",
            "sha256": hashlib.sha256(unrelated_path.read_bytes()).hexdigest(),
            "suppliedToImagegen": True,
            "byteVerification": {
                "status": "pending",
                "checkedAt": None,
                "command": None,
                "observedSHA256": None,
            },
        }
    )

    with pytest.raises(
        PresentationRemediationAuditError,
        match="preflight source input ID is not authorized",
    ):
        _validate_historical_phase2_document(tmp_path, document)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda d: d["phase2"].update(extra=True), "phase2 has unknown keys"),
        (
            lambda d: d["records"][0]["phase2Action"].update(state="pending"),
            "keep requires notRequired",
        ),
        (
            lambda d: d["phase2"]["canvasPreflight"]["classes"][0][
                "coveredRecordKeys"
            ].pop(),
            "canvas preflight must cover exactly 65 edit/regenerate record keys",
        ),
        (
            lambda d: d["records"][1]["phase2EvidenceReview"].update(
                result="notRequired"
            ),
            "repair evidence review cannot be notRequired",
        ),
        (
            lambda d: d["records"][1]["generation"].update(
                mode="builtInGenerate"
            ),
            "edit requires builtInEdit",
        ),
        (
            lambda d: d["records"][3]["generation"].update(mode="builtInEdit"),
            "regenerate requires builtInGenerate",
        ),
        (
            lambda d: d["records"][1]["final"]["workbenchReview"].pop(
                "hitTest"
            ),
            "workbenchReview is missing keys",
        ),
        (
            lambda d: d["records"][1]["phase2Comparator"].update(
                final={
                    "mode": "temporaryGap",
                    "assetPath": "Hangboards/beastmaker-2000/assets/primary.png",
                    "sourceRecordKey": "beastmaker-2000/primary",
                    "acceptedAssetSHA256": "0" * 64,
                    "reason": "Historical gap cannot authorize generation.",
                    "selectedAt": "2026-08-31T00:00:00+00:00",
                }
            ),
            "final comparator cannot be a gap",
        ),
        (
            lambda d: d["phase2"]["canvasPreflight"]["classes"][3][
                "behaviorProbes"
            ][0].update(bootstrapComparatorSet={}),
            "preflight probe has unknown keys",
        ),
        (
            lambda d: d["phase2"]["canvasPreflight"]["classes"][3][
                "behaviorProbes"
            ][0]["preflightComparatorSet"].update(materialTextureLighting={}),
            "preflight material comparator is always unavailable",
        ),
        (
            lambda d: d["phase2"]["canvasPreflight"]["classes"][5][
                "behaviorProbes"
            ][0]["preflightComparatorSet"].update(
                compositionFramingScale={
                    "axis": "compositionFramingScale",
                    "assetPath": "Hangboards/soill-iron-palm-2/assets/primary.png",
                    "sourceRecordKey": "soill.iron-palm-2/primary",
                    "acceptedAssetSHA256": "0" * 64,
                    "reason": presentation_audit._PREFLIGHT_COMPOSITION_REASON,
                }
            ),
            "preflight composition reference does not match the exact assignment table",
        ),
        (
            lambda d: d["records"][1]["generation"]["candidates"].append(
                {
                    "attempt": 1,
                    "transientOutputPath": "/tmp/rejected.png",
                    "sha256": "0" * 64,
                    "widthPixels": 1000,
                    "heightPixels": 259,
                    "disposition": "rejected",
                    "reason": "Rejected fixture.",
                    "provenance": {
                        "tool": "builtInImageGen",
                        "untouchedModelOutput": True,
                        "postProcessing": "resize",
                    },
                    "byteVerification": {
                        "status": "pending",
                        "checkedAt": None,
                        "command": None,
                        "observedSHA256": None,
                    },
                }
            ),
            "postProcessing must equal none",
        ),
        (
            lambda d: d["phase2"]["canvasPreflight"]["classes"][0][
                "behaviorProbes"
            ][0].update(
                prompt=d["phase2"]["canvasPreflight"]["classes"][0][
                    "behaviorProbes"
                ][0]["prompt"]
                + "x"
            ),
            "stored capability prompt does not equal canonical rendering",
        ),
    ],
)
def test_real_phase2_schema_and_coverage_fail_closed(
    tmp_path: Path,
    mutation: object,
    message: str,
) -> None:
    document = json.loads(REAL_PHASE2_MANIFEST.read_text(encoding="utf-8"))
    mutation(document)  # type: ignore[operator]

    with pytest.raises(PresentationRemediationAuditError, match=message):
        _validate_historical_phase2_document(tmp_path, document)
