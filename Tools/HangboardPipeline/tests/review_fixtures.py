from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import json
from pathlib import Path

from PIL import Image

from hangboard_vectorizer.review_acceptance import write_acceptance
from hangboard_vectorizer.review_artifacts import discover_review_run


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

    baseline_region = _baseline_regions()["regions"][0]
    corrections = {
        "schemaVersion": 1,
        "kind": "human-region-corrections",
        "source": {
            "image": "stage-1-auto-rgba.png",
            "regions": "stage-2-regions.json",
        },
        "summary": {"added": 1, "modified": 1, "deleted": 0},
        "modified": [
            {
                "before": _editor_export_region(baseline_region),
                "after": deepcopy(edited["regions"][0]),
            }
        ],
        "added": [deepcopy(edited["regions"][1])],
        "deleted": [],
    }
    if mutate_corrections:
        corrections["modified"][0]["before"]["key"] = "mutated"
    _write_json(stage2_dir / "stage-2-human-corrections.json", corrections)
    return run


def make_review_run_with_edit_and_acceptance(root: Path) -> Path:
    run = make_review_run_with_edit(root)
    write_acceptance(
        discover_review_run(run),
        "accepted",
        "fixture-reviewer",
        "Fixture acceptance",
    )
    return run


def make_profile(
    root: Path,
    destination_relative: str = "canonical/board.json",
    *,
    required_region_keys: tuple[str, ...] = ("left",),
    runtime_mappings: tuple[dict[str, object], ...] | None = None,
) -> Path:
    profile_root = root.resolve(strict=False)
    profile_root.mkdir(parents=True, exist_ok=True)
    if runtime_mappings is None:
        runtime_mappings = (
            {
                "regionKey": "left",
                "runtimeHoldId": "runtime-left",
                "gripType": "edge",
                "interactionMode": "surface",
            },
        )
    profile_path = profile_root / "promotion-profile.json"
    _write_json(
        profile_path,
        {
            "schemaVersion": 1,
            "profileId": "fixture-profile",
            "boardId": "fixture-board",
            "requiredRegionKeys": list(required_region_keys),
            "runtimeMappings": list(runtime_mappings),
            "destinations": [
                {
                    "sourceRelative": "edited-regions.json",
                    "destinationRelative": destination_relative,
                }
            ],
        },
    )
    return profile_path


def make_review_run_with_blocked_promotion(root: Path) -> Path:
    run = make_review_run_with_edit_and_acceptance(root)
    edited = run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    return run


def make_review_run_with_ready_promotion(root: Path) -> Path:
    from hangboard_vectorizer.promotion import promote_run
    from hangboard_vectorizer.promotion_profile import load_promotion_profile

    run = make_review_run_with_edit_and_acceptance(root)
    profile = load_promotion_profile(make_profile(run / ".context/profile"))
    repository_root = run.parent
    repository_root.mkdir(parents=True, exist_ok=True)
    report = promote_run(discover_review_run(run), profile, repository_root)
    source = run / "stages/02/attempt-0001/promotion/edited-regions.json"
    for planned_write in report.plannedWrites:
        destination = repository_root / planned_write["destination"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
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
            _editor_export_region({
                "id": 1,
                "key": "left",
                "type": "edge",
                "mode": "surface",
                "contour": [[3, 3], [13, 3], [12, 8], [3, 8]],
            }),
            _editor_export_region({
                "id": 2,
                "key": "right",
                "type": "pocket",
                "mode": "aperture",
                "contour": [[18, 3], [27, 3], [27, 8], [18, 8]],
            }),
        ],
    }


def _editor_export_region(region: dict[str, object]) -> dict[str, object]:
    exported = deepcopy(region)
    contour = exported["contour"]
    xs = [point[0] for point in contour]
    ys = [point[1] for point in contour]
    area = abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(
                contour, contour[1:] + contour[:1], strict=True
            )
        )
        / 2
    )
    exported["anchor"] = [
        round(sum(xs) / len(xs), 2),
        round(sum(ys) / len(ys), 2),
    ]
    exported["areaPixels"] = round(area)
    exported["bounds"] = [min(xs), min(ys), max(xs), max(ys)]
    exported["metadata"] = {
        "mode": exported["mode"],
        "shapeKind": "freeform",
        "pathStyle": "straight",
        "curveTension": 0.8,
        "humanNotes": "",
        "editedBy": "hold-highlight-editor",
    }
    return exported


def _write_json(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
