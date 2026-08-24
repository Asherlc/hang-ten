from __future__ import annotations

from pathlib import Path
import json


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PACKAGE = (
    REPOSITORY_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii"
)
PRIMARY_IMAGE = CANONICAL_PACKAGE / "assets" / "primary.png"


def board_document(
    board_id: str,
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "id": board_id,
        "manufacturer": manufacturer,
        "name": name,
        "subtitle": "A physical fixture board.",
        "productURL": f"https://example.com/{board_id}",
        "dimensions": "20 × 10 cm",
        "aspectRatio": 1774 / 457,
        "presentation": {"assetPath": "assets/primary.png"},
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
                "geometry": [
                    {
                        "frame": {
                            "x": 0.05,
                            "y": 0.2,
                            "width": 0.1,
                            "height": 0.3,
                        },
                        "shape": {
                            "type": "roundedRect",
                            "cornerRadiusFraction": 0.2,
                        },
                    },
                    {
                        "frame": {
                            "x": 0.35,
                            "y": 0.1,
                            "width": 0.1,
                            "height": 0.2,
                        },
                        "shape": {
                            "type": "roundedRect",
                            "cornerRadiusFraction": 0.1,
                        },
                        "treatment": {"type": "surface"},
                    },
                ],
            }
        ],
    }


def board_document_v2(board_id: str) -> dict[str, object]:
    board = board_document(board_id)
    board["schemaVersion"] = 2
    board.pop("presentation")
    board["presentations"] = [
        {
            "id": "front",
            "name": "Front",
            "assetPath": "assets/primary.png",
            "aspectRatio": 1774 / 457,
            "default": True,
        },
        {
            "id": "back",
            "name": "Back",
            "assetPath": "assets/back.png",
            "aspectRatio": 1774 / 457,
            "default": False,
        },
    ]
    first_hold = board["holds"][0]
    assert isinstance(first_hold, dict)
    first_hold["presentationID"] = "front"
    back_hold = json.loads(json.dumps(first_hold))
    back_hold.update(id="hold-back", name="Back hold", presentationID="back")
    board["holds"] = [first_hold, back_hold]
    return board
