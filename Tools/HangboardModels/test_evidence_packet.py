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
    for name in ("front.png", "hanging.jpg", "commerce-labelled-faces.jpg"):
        source = packet_dir / "sources" / name
        source.write_bytes(name.encode("ascii"))
        retained.append((f"sources/{name}", hashlib.sha256(source.read_bytes()).hexdigest()))
    user_evidence = []
    for name, view in (
        ("user-closeup-three-well-face.png", "three-well-face-closeup"),
        ("user-closeup-opposite-face.png", "opposite-face-closeup"),
        ("user-closeup-end-attachment.png", "end-attachment-closeup"),
    ):
        source = packet_dir / "sources" / name
        source.write_bytes(name.encode("ascii"))
        user_evidence.append(
            {
                "localPath": f"sources/{name}",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "sourceTier": "user",
                "view": view,
                "supports": "user-supplied visual context only",
                "limitations": "Not manufacturer authority; does not establish new logical holds or dimensions.",
            }
        )
    payload = _payload(path)
    payload["primarySources"][0]["localPath"] = retained[0][0]  # type: ignore[index]
    payload["primarySources"][0]["sha256"] = retained[0][1]  # type: ignore[index]
    payload["commerceSources"] = [
        {
            "localPath": local_path,
            "sha256": digest,
            "snapshotSHA256": digest,
            "sourceTier": "commerce",
            "url": f"https://retailer.example/{Path(local_path).stem}",
            "retailer": "Authorized Retailer",
        }
        for local_path, digest in retained[1:]
    ]
    payload["userEvidenceSources"] = user_evidence
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
        "faceInventoryNotes": [
            {
                "faceID": "three-well",
                "sourceLocalPaths": [retained[2][0], user_evidence[0]["localPath"]],
                "notes": "Three wells are visible; retailer labels are commerce-gap evidence only.",
            },
            {
                "faceID": "two-well",
                "sourceLocalPaths": [retained[0][0], user_evidence[1]["localPath"]],
                "notes": "Two wells and end features are visible in the retained views.",
            },
        ],
        "nonSelectableFeatures": [
            {
                "featureID": "lower-ledges",
                "faceID": "three-well",
                "sourceLocalPaths": [user_evidence[0]["localPath"]],
                "description": "Shallow lower grooves adjacent to the wells.",
                "reason": "Unresolved from imagery; retain as nonselectable display geometry.",
            }
        ],
        "logicalRuling": "no-new-logical-ids",
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
    payload["conflictsAndRulings"] = [
        {
            "claimID": "lower-ledge-interpretation",
            "conflict": "Supplied closeups show shallow lower grooves, but do not establish separate logical contacts.",
            "ruling": "Keep the grooves as nonselectable geometry and preserve the approved logical inventory.",
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def valid_flash_suspended_packet(tmp_path: Path) -> Path:
    path = valid_suspended_packet(tmp_path)
    payload = _payload(path)
    for name, view in (
        ("user-closeup-front-cord-and-wells.png", "front-face-and-cord-closeup"),
        ("user-closeup-two-well-face.png", "two-well-face-closeup"),
        ("user-closeup-two-well-face-wide.png", "two-well-face-wide"),
    ):
        source = path.parent / "sources" / name
        source.write_bytes(name.encode("ascii"))
        payload["userEvidenceSources"].append(  # type: ignore[union-attr]
            {
                "localPath": f"sources/{name}",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "sourceTier": "user",
                "view": view,
                "supports": "User-supplied visual context only.",
                "limitations": "User evidence, not manufacturer authority; does not establish new logical IDs.",
            }
        )
    payload["boardRevision"] = "tension-flash-board-2"
    payload["primarySources"][0]["url"] = "https://tensionclimbing.com/products/flash-board-2"  # type: ignore[index]
    payload["commerceSources"][0]["retailer"] = "Backcountry"  # type: ignore[index]
    payload["commerceSources"][0]["url"] = "https://www.backcountry.com/tension-flash-board"  # type: ignore[index]
    payload["commerceSources"][1]["retailer"] = "Amazon"  # type: ignore[index]
    payload["commerceSources"][1]["url"] = "https://www.amazon.com/Tension-Climbing-Flash-Board/dp/B07H8JYQ5G"  # type: ignore[index]
    payload["logicalInventory"] = [  # type: ignore[assignment]
        {"id": "three-edge-left", "kind": "edge", "sourceLocalPath": "sources/commerce-labelled-faces.jpg"},
        {"id": "three-edge-center", "kind": "edge", "sourceLocalPath": "sources/commerce-labelled-faces.jpg"},
        {"id": "three-edge-right", "kind": "edge", "sourceLocalPath": "sources/commerce-labelled-faces.jpg"},
        {"id": "two-edge-left", "kind": "edge", "sourceLocalPath": "sources/front.png"},
        {"id": "two-edge-right", "kind": "edge", "sourceLocalPath": "sources/front.png"},
        {"id": "small-crimp-left", "kind": "edge", "sourceLocalPath": "sources/front.png"},
        {"id": "small-crimp-right", "kind": "edge", "sourceLocalPath": "sources/front.png"},
    ]
    payload["suspendedPresentation"]["positionMappings"] = [  # type: ignore[index]
        {"positionID": "three-edge-upright", "holdIDs": ["three-edge-left", "three-edge-center", "three-edge-right"], "sourceLocalPath": "sources/commerce-labelled-faces.jpg"},
        {"positionID": "three-edge-inverted", "holdIDs": ["three-edge-left", "three-edge-center", "three-edge-right"], "sourceLocalPath": "sources/commerce-labelled-faces.jpg"},
        {"positionID": "two-edge-upright", "holdIDs": ["two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right"], "sourceLocalPath": "sources/front.png"},
        {"positionID": "two-edge-inverted", "holdIDs": ["two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right"], "sourceLocalPath": "sources/front.png"},
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_accepts_valid_suspended_presentation(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    assert validate_evidence_packet(packet).suspended_presentation["positionIDs"]


def test_accepts_amazon_face_map_only_as_commerce(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    parsed = validate_evidence_packet(packet)
    amazon = next(source for source in parsed.commerce_sources if source.retailer == "Amazon")
    assert amazon.source_tier == "commerce"
    assert amazon.url == "https://www.amazon.com/Tension-Climbing-Flash-Board/dp/B07H8JYQ5G"
    assert amazon.local_path == "sources/commerce-labelled-faces.jpg"
    assert {
        mapping["sourceLocalPath"]
        for mapping in parsed.suspended_presentation["positionMappings"]
        if mapping["positionID"].startswith("three-edge-")
    } == {amazon.local_path}


def test_rejects_flash_three_edge_mapping_without_amazon_provenance(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    for mapping in payload["suspendedPresentation"]["positionMappings"][:2]:  # type: ignore[index]
        mapping["sourceLocalPath"] = "sources/front.png"
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="three-edge mapping.*Amazon"):
        validate_evidence_packet(packet)


def test_accepts_user_closeups_with_explicit_limitations(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    parsed = validate_evidence_packet(packet)
    assert len(parsed.user_evidence_sources) == 6
    assert all(source["limitations"] for source in parsed.user_evidence_sources)


def test_rejects_user_closeup_without_evidence_limitations(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    del payload["userEvidenceSources"][0]["limitations"]  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="limitations"):
        validate_evidence_packet(packet)


def test_rejects_flash_missing_or_empty_user_evidence_block(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    del payload["userEvidenceSources"]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="six retained user closeups"):
        validate_evidence_packet(packet)

    empty_root = tmp_path / "empty-user"
    empty_root.mkdir()
    packet = valid_flash_suspended_packet(empty_root)
    payload = _payload(packet)
    payload["userEvidenceSources"] = []
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="six retained user closeups"):
        validate_evidence_packet(packet)


def test_rejects_user_photo_as_selectable_inventory_provenance(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    for item in payload["logicalInventory"]:
        item["sourceLocalPath"] = "sources/user-closeup-two-well-face.png"
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="cannot use user-evidence photos"):
        validate_evidence_packet(packet)


def test_rejects_claim_source_type_mismatch(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["sourcedClaims"][0]["sourceLocalPath"] = "sources/commerce-labelled-faces.jpg"  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="sourceType must match"):
        validate_evidence_packet(packet)


def test_rejects_flash_amazon_face_map_path_alias(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    original = packet.parent / "sources" / "commerce-labelled-faces.jpg"
    alias = packet.parent / "sources" / "amazon-face-map-copy.jpg"
    alias.write_bytes(original.read_bytes())
    alias_path = "sources/amazon-face-map-copy.jpg"
    digest = hashlib.sha256(alias.read_bytes()).hexdigest()
    payload["commerceSources"][1]["localPath"] = alias_path  # type: ignore[index]
    payload["commerceSources"][1]["sha256"] = digest  # type: ignore[index]
    payload["commerceSources"][1]["snapshotSHA256"] = digest  # type: ignore[index]
    for item in payload["logicalInventory"][:3]:
        item["sourceLocalPath"] = alias_path
    for mapping in payload["suspendedPresentation"]["positionMappings"][:2]:  # type: ignore[index]
        mapping["sourceLocalPath"] = alias_path
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="retained Amazon face-map"):
        validate_evidence_packet(packet)


def test_rejects_commerce_source_adding_logical_hold_id(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["logicalInventory"].append(  # type: ignore[union-attr]
        {"id": "commerce-only-lower-groove", "kind": "edge", "sourceLocalPath": "sources/hanging.jpg"}
    )
    payload["suspendedPresentation"]["positionMappings"][0]["holdIDs"].append("commerce-only-lower-groove")  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="approved logical inventory|logical hold"):
        validate_evidence_packet(packet)


def test_rejects_lower_groove_mapped_as_new_id(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["suspendedPresentation"]["positionMappings"][0]["holdIDs"].append("lower-groove")  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="unknown hold ID"):
        validate_evidence_packet(packet)


def test_requires_lower_ledge_conflict_ruling(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["conflictsAndRulings"] = []
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="lower-ledge-interpretation"):
        validate_evidence_packet(packet)


def test_rejects_flash_duplicate_or_reordered_inventory(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["logicalInventory"].append(dict(payload["logicalInventory"][0]))  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="seven IDs"):
        validate_evidence_packet(packet)

    reordered_root = tmp_path / "reordered"
    reordered_root.mkdir()
    packet = valid_flash_suspended_packet(reordered_root)
    payload = _payload(packet)
    payload["logicalInventory"][0], payload["logicalInventory"][1] = payload["logicalInventory"][1], payload["logicalInventory"][0]  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="seven IDs"):
        validate_evidence_packet(packet)


def test_rejects_flash_missing_or_arbitrary_position(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["suspendedPresentation"]["positionIDs"] = ["three-edge-upright"]  # type: ignore[index]
    payload["suspendedPresentation"]["positionMappings"] = [payload["suspendedPresentation"]["positionMappings"][0]]  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="four approved positions"):
        validate_evidence_packet(packet)


def test_rejects_flash_without_suspended_presentation(tmp_path: Path) -> None:
    packet = valid_flash_suspended_packet(tmp_path)
    payload = _payload(packet)
    del payload["suspendedPresentation"]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="requires suspendedPresentation"):
        validate_evidence_packet(packet)

    arbitrary_root = tmp_path / "arbitrary-position"
    arbitrary_root.mkdir()
    packet = valid_flash_suspended_packet(arbitrary_root)
    payload = _payload(packet)
    payload["suspendedPresentation"]["positionIDs"][0] = "arbitrary"  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="four approved positions"):
        validate_evidence_packet(packet)


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
    # Restore the first mapping before introducing the independent duplicate
    # mutation; do not let the prior unknown-position failure mask this case.
    payload["suspendedPresentation"]["positionMappings"][0]["positionID"] = "three-edge-upright"  # type: ignore[index]
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


def test_rejects_empty_position_mapping_hold_ids(tmp_path: Path) -> None:
    packet = valid_suspended_packet(tmp_path)
    payload = _payload(packet)
    payload["suspendedPresentation"]["positionMappings"][0]["holdIDs"] = []  # type: ignore[index]
    _rewrite(packet, payload)
    with pytest.raises(ValueError, match="holdIDs must be non-empty"):
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
