from __future__ import annotations

import importlib.util
import json
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[3]


def _primary_png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (512, 256), color=(180, 140, 90)).save(output, format="PNG")
    return output.getvalue()


PRIMARY_PNG_BYTES = _primary_png_bytes()


def load_board_catalog_module():
    module_path = REPO_ROOT / "Tools" / "HangboardPipeline" / "src" / "hangboard_vectorizer" / "board_catalog.py"
    spec = importlib.util.spec_from_file_location("board_catalog_under_test", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise AssertionError("unable to load hangboard_vectorizer.board_catalog")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def board_document(
    *,
    board_id: str = "fixture.board",
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
        "aspectRatio": 2,
        "presentation": {"assetPath": "assets/primary.png"},
        "holds": [
            {
                "id": "hold-left",
                "name": "Left hold",
                "kind": "jug",
                "geometry": [
                    {
                        "frame": {
                            "x": 0.1,
                            "y": 0.2,
                            "width": 0.2,
                            "height": 0.3,
                        },
                        "shape": {
                            "type": "roundedRect",
                            "cornerRadiusFraction": 0.2,
                        },
                        "treatment": {"type": "surface"},
                    }
                ],
            }
        ],
    }


def write_board_package(
    root: Path,
    *,
    board_id: str = "fixture.board",
    manufacturer: str = "Fixture Maker",
    name: str = "Fixture Board",
) -> Path:
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    (root / "board.json").write_text(
        json.dumps(
            board_document(
                board_id=board_id,
                manufacturer=manufacturer,
                name=name,
            )
        ),
        encoding="utf-8",
    )
    return root


def write_primary_only_draft(root: Path) -> Path:
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    return root
