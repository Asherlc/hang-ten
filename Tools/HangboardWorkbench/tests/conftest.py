from __future__ import annotations

from pathlib import Path
import json
import shutil

from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PACKAGE = (
    REPOSITORY_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii"
)
PRIMARY_IMAGE = CANONICAL_PACKAGE / "assets" / "primary.png"


def board_document(
    board_id: str,
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, Any]:
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
                        "frame": {"x": 0.05, "y": 0.2, "width": 0.1, "height": 0.3},
                        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
                    },
                    {
                        "frame": {"x": 0.35, "y": 0.1, "width": 0.1, "height": 0.2},
                        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.1},
                        "treatment": {"type": "surface"},
                    },
                ],
            }
        ],
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_finished_package(
    library: Path,
    slug: str,
    board_id: str,
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> Path:
    package = library / slug
    assets = package / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(PRIMARY_IMAGE, assets / "primary.png")
    write_json(package / "board.json", board_document(board_id, manufacturer=manufacturer, name=name))
    return package


def write_draft(library: Path, slug: str) -> Path:
    assets = library / slug / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(PRIMARY_IMAGE, assets / "primary.png")
    return assets.parent
