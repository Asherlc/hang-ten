"""Behavioral tests for the Stage 0 manufacturer evidence packet contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evidence_packet import validate_evidence_packet


def _write_source(packet_dir: Path, relative_path: str = "sources/manufacturer.html") -> tuple[str, str]:
    source = packet_dir / relative_path
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"retained source snapshot\n")
    return relative_path, hashlib.sha256(source.read_bytes()).hexdigest()


def valid_packet(tmp_path: Path) -> Path:
    packet_dir = tmp_path / "evidence"
    packet_dir.mkdir()
    local_path, digest = _write_source(packet_dir)
    packet = {
        "boardRevision": "compact-ii-revision-3",
        "boardRevisionDate": "2026-09-08",
        "locale": "en-US",
        "primarySources": [
            {
                "localPath": local_path,
                "sha256": digest,
                "sourceTier": "manufacturer",
                "url": "https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards",
            }
        ],
        "commerceSources": [],
        "logicalInventory": [
            {"id": "jug-left", "kind": "jug", "sourceLocalPath": local_path},
            {"id": "jug-right", "kind": "jug", "sourceLocalPath": local_path},
        ],
        "sourcedClaims": [
            {
                "claimID": "material-and-width",
                "claim": "The board is made from wood and is 610 mm wide.",
                "sourceLocalPath": local_path,
                "sourceType": "manufacturer",
            }
        ],
        "conflictsAndRulings": [],
        "unknownsForAstra": ["back profile", "cavity sections"],
        "deliberateOmissions": ["screw holes", "mounting hardware"],
        "materialFidelity": {
            "status": "source-backed",
            "notes": "Wood is recorded as the source-backed material; specimen grain is unknown.",
        },
        "requiredReviewViews": ["front", "three-quarter", "clay-detail"],
    }
    path = packet_dir / "packet.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    return path


def valid_suspended_packet(tmp_path: Path) -> Path:
    path = valid_packet(tmp_path)
    packet_dir = path.parent
    retained = []
    for name in ("front.png", "hanging.jpg", "labelled-faces.jpg"):
        source = packet_dir / "sources" / name
        source.write_bytes(name.encode("ascii"))
        retained.append((f"sources/{name}", hashlib.sha256(source.read_bytes()).hexdigest()))
    payload = _payload(path)
    payload["primarySources"][0]["localPath"] = retained[0][0]  # type: ignore[index]
    payload["primarySources"][0]["sha256"] = retained[0][1]  # type: ignore[index]
    for item in payload["logicalInventory"]:  # type: ignore[index]
        item["sourceLocalPath"] = retained[0][0]
    for claim in payload["sourcedClaims"]:  # type: ignore[index]
        claim["sourceLocalPath"] = retained[0][0]
    payload["suspendedPresentation"] = {
        "positionIDs": ["three-edge-upright", "three-edge-inverted", "two-edge-upright", "two-edge-inverted"],
        "positionMappings": [
            {"positionID": "three-edge-upright", "holdIDs": ["jug-left"], "sourceLocalPath": retained[0][0]},
            {"positionID": "three-edge-inverted", "holdIDs": ["jug-left"], "sourceLocalPath": retained[0][0]},
            {"positionID": "two-edge-upright", "holdIDs": ["jug-right"], "sourceLocalPath": retained[1][0]},
            {"positionID": "two-edge-inverted", "holdIDs": ["jug-right"], "sourceLocalPath": retained[1][0]},
        ],
        "attachmentEvidence": {"sourceLocalPath": retained[1][0], "view": "attachment-region", "supports": "paired cord passages"},
        "visualApproval": {
            "approvedSnapshotPaths": [retained[0][0], retained[1][0]],
            "materiallyDistinct": True,
            "decisionDate": "2026-09-09",
        },
        "displayEstimates": [
            {"name": "anchor", "value": "fixed invisible anchor", "provenance": "displayEstimate"},
            {"name": "cord", "value": "rest length and radius", "provenance": "displayEstimate"},
            {"name": "pose", "value": "canonical pose", "provenance": "estimatedFromApprovedModel"},
            {"name": "camera", "value": "canonical camera", "provenance": "displayEstimate"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_accepts_valid_suspended_presentation(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    assert validate_evidence_packet(packet).suspended_presentation["positionIDs"]


def test_rejects_suspended_presentation_without_distinct_snapshots(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["suspendedPresentation"]["visualApproval"]["approvedSnapshotPaths"] = ["sources/front.png"]  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="two.*distinct"):
        validate_evidence_packet(packet)


def test_rejects_unretained_attachment_view(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["suspendedPresentation"]["attachmentEvidence"]["sourceLocalPath"] = "sources/missing.jpg"  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="retained"):
        validate_evidence_packet(packet)


def test_rejects_unknown_or_duplicate_position_mapping(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["suspendedPresentation"]["positionMappings"][0]["positionID"] = "unknown"  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="unknown position"):
        validate_evidence_packet(packet)
    payload = _payload(packet)
    payload["suspendedPresentation"]["positionMappings"][1]["positionID"] = "three-edge-upright"  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="duplicate position"):
        validate_evidence_packet(packet)


def test_rejects_unlabelled_suspended_estimate(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    payload = _payload(packet)
    del payload["suspendedPresentation"]["displayEstimates"][0]["provenance"]  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="provenance"):
        validate_evidence_packet(packet)


def test_rejects_missing_visual_approval_and_geometry_proposal(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    payload = _payload(packet)
    del payload["suspendedPresentation"]["visualApproval"]  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="visualApproval"):
        validate_evidence_packet(packet)
    payload = _payload(packet)
    payload["suspendedPresentation"]["geometry"] = "proposal"
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="proposal field"):
        validate_evidence_packet(packet)


def _payload(packet: Path) -> dict[str, object]:
    return json.loads(packet.read_text(encoding="utf-8"))


def _rewrite(packet: Path, payload: dict[str, object]) -> None:
    packet.write_text(json.dumps(payload), encoding="utf-8")


def test_accepts_retained_manufacturer_media_and_rejects_geometry_proposal(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)

    assert validate_evidence_packet(packet).primary_sources[0].source_tier == "manufacturer"

    payload = _payload(packet)
    payload["unknownsForAstra"] = ["radius 8 mm"]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="numeric shape prescription"):
        validate_evidence_packet(packet)


def test_rejects_stale_retained_source_hash(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    source = packet.parent / payload["primarySources"][0]["localPath"]  # type: ignore[index]
    source.write_bytes(b"changed source snapshot\n")

    with pytest.raises(ValueError, match="SHA-256"):
        validate_evidence_packet(packet)


def test_requires_each_logical_inventory_item_to_reference_retained_source(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    del payload["logicalInventory"][0]["sourceLocalPath"]  # type: ignore[index]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="logicalInventory.*sourceLocalPath"):
        validate_evidence_packet(packet)


def test_rejects_logical_inventory_reference_to_unknown_source(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    payload["logicalInventory"][0]["sourceLocalPath"] = "sources/not-retained.html"  # type: ignore[index]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="logicalInventory.*source"):
        validate_evidence_packet(packet)


def test_rejects_invalid_revision_date_and_locale(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    payload["boardRevisionDate"] = "09/08/2026"
    payload["locale"] = "english"
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="boardRevisionDate"):
        validate_evidence_packet(packet)


def test_requires_manufacturer_primary_sources(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    payload["primarySources"][0]["sourceTier"] = "commerce"  # type: ignore[index]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="primarySources.*manufacturer"):
        validate_evidence_packet(packet)


def test_rejects_search_snippet_url_labeled_as_manufacturer_source(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    payload["primarySources"][0]["url"] = "https://www.google.com/search?q=wood+grips"  # type: ignore[index]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="manufacturer source URL must not be a search result"):
        validate_evidence_packet(packet)


def test_rejects_duplicate_retained_path_across_manufacturer_and_commerce_sources(
    tmp_path: Path,
) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    manufacturer_source = payload["primarySources"][0]  # type: ignore[index]
    payload["commerceSources"] = [
        {
            "localPath": manufacturer_source["localPath"],
            "sha256": manufacturer_source["sha256"],
            "snapshotSHA256": manufacturer_source["sha256"],
            "sourceTier": "commerce",
            "url": "https://authorized.example/board",
            "retailer": "Authorized Retailer",
        }
    ]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="duplicate retained localPath"):
        validate_evidence_packet(packet)


def test_requires_authorized_retailer_identity_and_snapshot_hash_for_commerce_gap(
    tmp_path: Path,
) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    local_path, digest = _write_source(packet.parent, "sources/retailer.html")
    payload["commerceSources"] = [
        {
            "localPath": local_path,
            "sha256": digest,
            "sourceTier": "commerce",
            "url": "https://authorized.example/board",
        }
    ]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="retailer"):
        validate_evidence_packet(packet)

    payload["commerceSources"][0]["retailer"] = "Authorized Retailer"  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="snapshotSHA256"):
        validate_evidence_packet(packet)

    payload["commerceSources"][0]["snapshotSHA256"] = digest  # type: ignore[index]
    _rewrite(packet, payload)
    assert validate_evidence_packet(packet).commerce_sources[0].retailer == "Authorized Retailer"


def test_rejects_same_claim_id_across_manufacturer_and_commerce_without_ruling(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    local_path, digest = _write_source(packet.parent, "sources/retailer.html")
    payload["commerceSources"] = [
        {
            "localPath": local_path,
            "sha256": digest,
            "snapshotSHA256": digest,
            "sourceTier": "commerce",
            "url": "https://authorized.example/board",
            "retailer": "Authorized Retailer",
        }
    ]
    payload["sourcedClaims"].append(  # type: ignore[union-attr]
        {
            "claimID": "material-and-width",
            "claim": "The board is made from a different material.",
            "sourceLocalPath": local_path,
            "sourceType": "commerce",
        }
    )
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="material-and-width.*ruling"):
        validate_evidence_packet(packet)


def test_accepts_same_claim_id_across_tiers_with_matching_ruling(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    local_path, digest = _write_source(packet.parent, "sources/retailer.html")
    payload["commerceSources"] = [
        {
            "localPath": local_path,
            "sha256": digest,
            "snapshotSHA256": digest,
            "sourceTier": "commerce",
            "url": "https://authorized.example/board",
            "retailer": "Authorized Retailer",
        }
    ]
    payload["sourcedClaims"].append(  # type: ignore[union-attr]
        {
            "claimID": "material-and-width",
            "claim": "The board is made from a different material.",
            "sourceLocalPath": local_path,
            "sourceType": "commerce",
        }
    )
    payload["conflictsAndRulings"] = [
        {"claimID": "material-and-width", "ruling": "Retain the manufacturer claim."}
    ]
    _rewrite(packet, payload)

    assert validate_evidence_packet(packet).conflicts_and_rulings[0]["claimID"] == "material-and-width"


def test_allows_commerce_only_gap_claim_with_unique_claim_id(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    local_path, digest = _write_source(packet.parent, "sources/retailer.html")
    payload["commerceSources"] = [
        {
            "localPath": local_path,
            "sha256": digest,
            "snapshotSHA256": digest,
            "sourceTier": "commerce",
            "url": "https://authorized.example/board",
            "retailer": "Authorized Retailer",
        }
    ]
    payload["sourcedClaims"].append(  # type: ignore[union-attr]
        {
            "claimID": "retailer-only-gap",
            "claim": "Retailer-only packaging detail.",
            "sourceLocalPath": local_path,
            "sourceType": "commerce",
        }
    )
    _rewrite(packet, payload)

    assert validate_evidence_packet(packet).commerce_sources[0].source_tier == "commerce"


def test_requires_stable_claim_id_and_retained_source_reference(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    del payload["sourcedClaims"][0]["claimID"]  # type: ignore[index]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="sourcedClaims.*claimID"):
        validate_evidence_packet(packet)


@pytest.mark.parametrize("field", ["geometry", "coordinates", "contours", "masks", "vectors", "trace", "alignment"])
def test_rejects_proposal_fields_in_closed_packet(tmp_path: Path, field: str) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    payload[field] = "proposal"
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="proposal field"):
        validate_evidence_packet(packet)


def test_allows_measurements_in_cited_claims_and_source_backed_metadata(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    payload["sourcedClaims"][0]["measurement"] = "610 mm"  # type: ignore[index]
    payload["sourcedClaims"][0]["sourceBackedMetadata"] = {"publishedWidth": "610 mm"}  # type: ignore[index]
    _rewrite(packet, payload)

    assert validate_evidence_packet(packet).logical_inventory[0]["id"] == "jug-left"


def test_requires_omissions_and_review_views(tmp_path: Path) -> None:
    packet = valid_packet(tmp_path)
    payload = _payload(packet)
    payload["deliberateOmissions"] = ["screw holes"]
    payload["requiredReviewViews"] = ["front"]
    _rewrite(packet, payload)

    with pytest.raises(ValueError, match="deliberateOmissions"):
        validate_evidence_packet(packet)
