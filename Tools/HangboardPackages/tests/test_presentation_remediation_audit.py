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
            "reason": "Accepted cohort baseline; style-only: framing, lighting.",
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
