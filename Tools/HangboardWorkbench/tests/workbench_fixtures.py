from __future__ import annotations

from pathlib import Path
import copy


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PACKAGE = REPOSITORY_ROOT / "Hangboards" / "trango-rock-prodigy-pivot"
PRIMARY_IMAGE = (
    REPOSITORY_ROOT
    / "Tools"
    / "HangboardPackages"
    / "tests"
    / "fixtures"
    / "metolius-contact-boundary.png"
)


def _piece(x: float, y: float, width: float, height: float, radius: float) -> dict[str, object]:
    return {
        "frame": {"x": x, "y": y, "width": width, "height": height},
        "shape": {"type": "roundedRect", "cornerRadiusFraction": radius},
        "treatment": {"type": "surface"},
    }


def _presentation(
    presentation_id: str,
    name: str,
    asset_path: str,
    contact_geometry: dict[str, list[dict[str, object]]],
    *,
    is_default: bool,
) -> dict[str, object]:
    return {
        "id": presentation_id,
        "name": name,
        "aspectRatio": 1774 / 887,
        "isDefault": is_default,
        "derivation": {"type": "original"},
        "media": {
            "type": "raster",
            "assetPath": asset_path,
            "contactGeometry": contact_geometry,
        },
    }


def _contact(contact_id: str, name: str, *, kind: str = "jug") -> dict[str, object]:
    return {
        "id": contact_id,
        "equipmentObjectID": "primary",
        "name": name,
        "kind": kind,
        "features": [],
        "gripTypes": [],
    }


def board_document(
    board_id: str,
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, object]:
    return {
        "schemaVersion": 3,
        "revisionID": "fixture-v3",
        "id": board_id,
        "manufacturer": manufacturer,
        "name": name,
        "subtitle": "A physical fixture board.",
        "productURL": f"https://example.com/{board_id}",
        "dimensions": "20 × 10 cm",
        "aspectRatio": 1774 / 887,
        "equipmentObjects": [{"id": "primary"}],
        "presentations": [_presentation(
            "primary",
            "Primary",
            "assets/primary.png",
            {
                "contact-left": [
                    _piece(0.05, 0.2, 0.1, 0.3, 0.2),
                    _piece(0.35, 0.1, 0.1, 0.2, 0.1),
                ]
            },
            is_default=True,
        )],
        "contacts": [_contact("contact-left", "Left contact")],
    }


def multi_presentation_board_document(board_id: str) -> dict[str, object]:
    board = board_document(board_id)
    board["presentations"] = [
        _presentation(
            "front", "Front", "assets/primary.png",
            {"contact-left": [
                _piece(0.05, 0.2, 0.1, 0.3, 0.2),
                _piece(0.35, 0.1, 0.1, 0.2, 0.1),
            ]},
            is_default=True,
        ),
        _presentation(
            "back", "Back", "assets/back.png",
            {"contact-back": [
                _piece(0.05, 0.2, 0.1, 0.3, 0.2),
                _piece(0.35, 0.1, 0.1, 0.2, 0.1),
            ]},
            is_default=False,
        ),
    ]
    contacts = board["contacts"]
    assert isinstance(contacts, list)
    contacts.append(_contact("contact-back", "Back contact"))
    return copy.deepcopy(board)


def geometry_for(
    board: dict[str, object], presentation_id: str | None = None
) -> dict[str, list[dict[str, object]]]:
    presentations = board["presentations"]
    assert isinstance(presentations, list)
    selected = next(
        item for item in presentations
        if isinstance(item, dict)
        and (item["id"] == presentation_id if presentation_id else item["isDefault"])
    )
    media = selected["media"]
    assert isinstance(media, dict)
    geometry = media["contactGeometry"]
    assert isinstance(geometry, dict)
    return geometry


def derived_presentation(
    board: dict[str, object], presentation_id: str, source_presentation_id: str,
    name: str, asset_path: str, *, is_default: bool = False, is_inverted: bool = True,
) -> dict[str, object]:
    presentations = board["presentations"]
    assert isinstance(presentations, list)
    source = next(
        item for item in presentations
        if isinstance(item, dict) and item["id"] == source_presentation_id
    )
    media = source["media"]
    assert isinstance(media, dict)
    return {
        "id": presentation_id,
        "name": name,
        "aspectRatio": source["aspectRatio"],
        "isDefault": is_default,
        "derivation": {
            "type": "derived",
            "sourcePresentationID": source_presentation_id,
            "isInverted": is_inverted,
        },
        "media": {
            "type": "raster",
            "assetPath": asset_path,
            "contactGeometry": copy.deepcopy(media["contactGeometry"]),
        },
    }
