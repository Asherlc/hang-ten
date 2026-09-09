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


def _encode_transparent_png(width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), color=(255, 255, 255, 255))
    image.putpixel((0, 0), (255, 255, 255, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


PRIMARY_PNG_WIDTH = 40
PRIMARY_PNG_HEIGHT = 20
OPAQUE_PRIMARY_PNG_BYTES = _encode_png(PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT)
TRANSPARENT_PRIMARY_PNG_BYTES = _encode_transparent_png(
    PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT
)
PRIMARY_PNG_BYTES = TRANSPARENT_PRIMARY_PNG_BYTES
SECONDARY_PNG_BYTES = _encode_png(
    PRIMARY_PNG_WIDTH, PRIMARY_PNG_HEIGHT, color=(0, 0, 0)
)
ALTERNATE_PRIMARY_PNG_BYTES = _encode_transparent_png(
    PRIMARY_PNG_WIDTH + 2, PRIMARY_PNG_HEIGHT + 2
)


def board_document(
    board_id: str = "fixture.board",
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, Any]:
    return {
        "schemaVersion": 2,
        "id": board_id,
        "manufacturer": manufacturer,
        "name": name,
        "subtitle": "A physical fixture board.",
        "productURL": f"https://example.com/{board_id}",
        "dimensions": "20 x 10 cm",
        "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
        "presentations": [
            {
                "id": "primary",
                "name": "Primary",
                "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
                "isDefault": True,
                "derivation": {"type": "original"},
                "media": {
                    "type": "raster",
                    "assetPath": "assets/primary.png",
                    "holdGeometry": {
                        "hold-left": [
                            {
                                "frame": {
                                    "x": 0.1,
                                    "y": 0.1,
                                    "width": 0.1,
                                    "height": 0.4,
                                },
                                "shape": {
                                    "type": "roundedRect",
                                    "cornerRadiusFraction": 0.2,
                                },
                            }
                        ]
                    },
                },
            }
        ],
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
            }
        ],
    }


def multi_presentation_board_document(
    board_id: str = "fixture.board",
    *,
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> dict[str, Any]:
    """Return a fixture with one hold on each declared presentation."""
    document = board_document(board_id, manufacturer=manufacturer, name=name)
    document["presentations"] = [
        {
            "id": "front",
            "name": "Front",
            "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
            "isDefault": True,
            "derivation": {"type": "original"},
            "media": {
                "type": "raster",
                "assetPath": "assets/primary.png",
                "holdGeometry": {
                    "hold-left": document["presentations"][0]["media"][
                        "holdGeometry"
                    ]["hold-left"]
                },
            },
        },
        {
            "id": "back",
            "name": "Back",
            "aspectRatio": PRIMARY_PNG_WIDTH / PRIMARY_PNG_HEIGHT,
            "isDefault": False,
            "derivation": {"type": "original"},
            "media": {
                "type": "raster",
                "assetPath": "assets/back.png",
                "holdGeometry": {
                    "hold-right": [
                        {
                            "frame": {
                                "x": 0.8,
                                "y": 0.1,
                                "width": 0.1,
                                "height": 0.4,
                            },
                            "shape": {
                                "type": "roundedRect",
                                "cornerRadiusFraction": 0.2,
                            },
                        }
                    ]
                },
            },
        },
    ]
    document["holds"].append(
        {
            "id": "hold-right",
            "name": "Right hold",
            "kind": "jug",
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
    """Write a complete package with its declared presentation assets."""
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
