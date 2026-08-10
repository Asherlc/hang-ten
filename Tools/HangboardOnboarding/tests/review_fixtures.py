from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

from PIL import Image


def make_review_run(root: Path) -> Path:
    run = root.resolve(strict=False)
    stage1_dir = run / "stages/01/attempt-0001"
    stage2_dir = run / "stages/02/attempt-0001"
    stage1_dir.mkdir(parents=True, exist_ok=True)
    stage2_dir.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    image.putpixel((4, 4), (255, 117, 79, 255))
    image.putpixel((20, 5), (50, 187, 193, 255))
    image.save(stage1_dir / "stage-1-auto-rgba.png")

    _write_json(stage2_dir / "stage-2-regions.json", _baseline_regions())
    return run


def make_review_run_with_edit(
    root: Path,
    mutate_edited: Callable[[dict[str, object]], None] | None = None,
    mutate_corrections: bool = False,
) -> Path:
    run = make_review_run(root)
    stage2_dir = run / "stages/02/attempt-0001"

    edited = _edited_regions()
    if mutate_edited is not None:
        mutate_edited(edited)
    _write_json(stage2_dir / "stage-2-regions.edited.json", edited)

    corrections = {
        "schemaVersion": 1,
        "modified": [{"id": 1, "key": "left"}],
        "added": [],
        "deleted": [],
    }
    if mutate_corrections:
        corrections["modified"] = [{"id": 1, "key": "left", "notes": "mutated"}]
    _write_json(stage2_dir / "stage-2-human-corrections.json", corrections)
    return run
def _baseline_regions() -> dict[str, object]:
    return {
        "canvas": {"width": 32, "height": 16},
        "regions": [
            {
                "id": 1,
                "key": "left",
                "type": "edge",
                "mode": "surface",
                "contour": [[3, 3], [12, 3], [12, 8], [3, 8]],
            }
        ],
    }


def _edited_regions() -> dict[str, object]:
    return {
        "canvas": {"width": 32, "height": 16},
        "regions": [
            {
                "id": 1,
                "key": "left",
                "type": "edge",
                "mode": "surface",
                "contour": [[3, 3], [13, 3], [12, 8], [3, 8]],
            },
            {
                "id": 2,
                "key": "right",
                "type": "pocket",
                "mode": "aperture",
                "contour": [[18, 3], [27, 3], [27, 8], [18, 8]],
            },
        ],
    }


def _write_json(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
