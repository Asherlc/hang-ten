from __future__ import annotations

from pathlib import Path


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
