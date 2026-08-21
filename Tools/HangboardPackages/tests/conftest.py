from __future__ import annotations

import io
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src"


def load_board_catalog_module() -> ModuleType:
    """Return the real ``hangboard_packages.board_catalog`` module."""
    if str(_SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(_SRC_ROOT))
    from hangboard_packages import board_catalog

    return board_catalog


def _encode_png(
    width: int, height: int, *, color: tuple[int, int, int] = (255, 255, 255)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


PRIMARY_PNG_WIDTH = 40
PRIMARY_PNG_HEIGHT = 20
PRIMARY_PNG_BYTES = _encode_png(PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT)
SECONDARY_PNG_BYTES = _encode_png(
    PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT, color=(0, 0, 0)
)
ALTERNATE_PRIMARY_PNG_BYTES = _encode_png(PRIMARY_PNG_WIDTH + 2, PRIMARY_PNG_HEIGHT + 2)


def board_document(
    board_id: str = "fixture.board",
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
        "dimensions": "20 x 10 cm",
        "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
        "presentation": {"assetPath": "assets/primary.png"},
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
                "geometry": [
                    {
                        "frame": {"x": 0.1, "y": 0.1, "width": 0.1, "height": 0.4},
                        "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
                    }
                ],
            }
        ],
    }


def multi_presentation_board_document(
    board_id: str = "fixture.board",
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, Any]:
    """Return a schema-v2 fixture with one hold on each declared surface."""
    document = board_document(board_id, manufacturer=manufacturer, name=name)
    document["schemaVersion"] = 2
    document.pop("presentation")
    document["presentations"] = [
        {
            "id": "front",
            "name": "Front",
            "assetPath": "assets/primary.png",
            "default": True,
        },
        {
            "id": "back",
            "name": "Back",
            "assetPath": "assets/back.png",
            "default": False,
        },
    ]
    document["holds"][0]["presentationID"] = "front"
    document["holds"].append(
        {
            "id": "hold-right",
            "name": "Right hold",
            "kind": "jug",
            "presentationID": "back",
            "geometry": [
                {
                    "frame": {"x": 0.8, "y": 0.1, "width": 0.1, "height": 0.4},
                    "shape": {"type": "roundedRect", "cornerRadiusFraction": 0.2},
                }
            ],
        }
    )
    return document


def write_board_package(
    root: Path,
    *,
    board_id: str = "fixture.board",
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> Path:
    """Write a complete direct-child board package at *root* and return it."""
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    document = board_document(board_id, manufacturer=manufacturer, name=name)
    (root / "board.json").write_text(
        __import__("json").dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    return root


def write_multi_presentation_board_package(
    root: Path,
    *,
    board_id: str = "fixture.board",
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> Path:
    """Write a complete schema-v2 package with its declared presentation assets."""
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    (assets / "back.png").write_bytes(SECONDARY_PNG_BYTES)
    document = multi_presentation_board_document(
        board_id, manufacturer=manufacturer, name=name
    )
    (root / "board.json").write_text(
        __import__("json").dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    return root


def write_primary_only_draft(root: Path) -> Path:
    """Write a primary-only migration draft at *root* and return it."""
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    return root
