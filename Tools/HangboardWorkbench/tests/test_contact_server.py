from __future__ import annotations

from pathlib import Path

import board_package
import server


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_raster_board_payload_is_contact_first() -> None:
    package = board_package.load_board_package(
        REPOSITORY_ROOT / "Hangboards" / "lattice-mini-bar"
    )

    payload = server._board_payload(
        package, include_document=True, presentation_id="edge-10"
    )

    assert payload["contactCount"] == len(package.contact_ids)
    assert payload["contactIDs"] == list(package.contact_ids)
    document = payload["document"]
    assert document["contacts"] == package.board["contacts"]
    assert all(set(region["metadata"]) == {
        "contactID", "pieceIndex", "presentationID"
    } for region in document["regions"])
    assert "holds" not in payload


def test_model_board_payload_is_explicitly_read_only() -> None:
    package = board_package.load_board_package(
        REPOSITORY_ROOT / "Hangboards" / "yy-baguette-evo"
    )

    payload = server._board_payload(package, include_document=False)

    assert payload["contactCount"] == len(package.contact_ids)
    assert payload["editorAvailable"] is False
    assert payload["unavailableReason"] == "3D model editing is not supported"
    assert "imageUrl" not in payload


def test_attention_is_computed_from_factual_contacts_not_media_geometry() -> None:
    assert server._contact_needs_attention({"kind": "edge"}) is True
    assert server._contact_needs_attention({
        "kind": "edge",
        "depth": {"range": {"minimum": 10, "maximum": 12}},
    }) is False
    assert server._contact_needs_attention({"kind": "sloper"}) is False


def test_payload_presentation_contact_ids_come_from_media_geometry() -> None:
    package = board_package.load_board_package(
        REPOSITORY_ROOT / "Hangboards" / "lattice-mini-bar"
    )
    payload = server._board_payload(
        package, include_document=True, presentation_id="edge-20"
    )
    presentation = next(
        item for item in payload["presentations"]
        if item["presentationID"] == "edge-20"
    )
    raw = next(
        item for item in package.board["presentations"]
        if item["id"] == "edge-20"
    )
    assert presentation["contactIDs"] == [
        contact_id for contact_id in package.contact_ids
        if contact_id in raw["media"]["contactGeometry"]
    ]
