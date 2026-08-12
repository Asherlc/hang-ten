from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image

from hangboard_vectorizer.generic_stage3 import GenericStage3Runner
from hangboard_vectorizer.generic_stage4 import GenericStage4Runner
from hangboard_vectorizer.onboarding_run import RunContext


def test_production_stages_preserve_sparse_accepted_region_ids(tmp_path: Path) -> None:
    context, labels = _accepted_stage2_context(tmp_path)

    stage3_root = tmp_path / "stages/03/attempt-0001"
    GenericStage3Runner().run(context, stage3_root)
    stage3_document = _read_json(stage3_root / "stage-3-vector-regions.json")

    expected_ids = (1, 3, 4)
    assert tuple(region["id"] for region in stage3_document["regions"]) == expected_ids
    assert tuple(
        region["sourceMaskSha256"] for region in stage3_document["regions"]
    ) == tuple(
        sha256((labels == region_id).astype(np.uint8).tobytes()).hexdigest()
        for region_id in expected_ids
    )

    _approve_stage3(context, stage3_root)
    stage4_root = tmp_path / "stages/04/attempt-0001"
    GenericStage4Runner().run(context, stage4_root)

    stage4_manifest = _read_json(stage4_root / "stage-4-manifest.json")
    highlights = _read_json(stage4_root / "stage-4-highlights.json")
    assert tuple(region["id"] for region in stage4_manifest["regions"]) == expected_ids
    assert _selected_ids(highlights, "all") == expected_ids


def _accepted_stage2_context(root: Path) -> tuple[RunContext, np.ndarray]:
    inputs = root / "inputs"
    inputs.mkdir()
    rgba = np.full((160, 1000, 4), 255, dtype=np.uint8)
    rgba_path = inputs / "stage-1-rgba.png"
    Image.fromarray(rgba, "RGBA").save(
        rgba_path, format="PNG", optimize=False, compress_level=9
    )
    stage1_acceptance = {
        "registered": {
            "fileSha256": _hash_file(rgba_path),
            "path": "inputs/stage-1-rgba.png",
            "pixelSha256": sha256(rgba.tobytes()).hexdigest(),
        },
        "runIdentitySha256": "sparse-stable-ids-test-run",
        "stage": 1,
    }
    stage1_acceptance_path = inputs / "stage-1-acceptance.json"
    _write_json(stage1_acceptance_path, stage1_acceptance)

    labels = np.zeros((160, 1000), dtype=np.uint16)
    labels[30:70, 100:220] = 1
    labels[80:120, 430:550] = 3
    labels[80:120, 760:880] = 4
    labels_path = inputs / "stage-2-labels.png"
    Image.fromarray(labels).save(
        labels_path, format="PNG", optimize=False, compress_level=9
    )
    regions_path = inputs / "stage-2-regions.json"
    _write_json(
        regions_path,
        {
            "canvas": {"height": 160, "width": 1000},
            "labelEncoding": "uint16-png",
            "regions": [
                _region(1, "grip-001", 100, 30),
                _region(3, "grip-003", 430, 80),
                _region(4, "grip-004", 760, 80),
            ],
            "schemaVersion": 1,
            "stage": 2,
        },
    )
    stage2_acceptance = {
        "regionCount": 3,
        "regions": {
            "fileSha256": _hash_file(regions_path),
            "path": "inputs/stage-2-regions.json",
        },
        "registered": {
            "fileSha256": _hash_file(labels_path),
            "path": "inputs/stage-2-labels.png",
        },
        "runIdentitySha256": "sparse-stable-ids-test-run",
        "stage": 2,
    }
    stage2_acceptance_path = inputs / "stage-2-acceptance.json"
    _write_json(stage2_acceptance_path, stage2_acceptance)
    manifest = {
        "pipeline": {"currentStage": 2, "status": "ready_for_next_stage"},
        "runIdentitySha256": "sparse-stable-ids-test-run",
        "stages": [
            {"stage": 0, "status": "approved"},
            {
                "acceptancePath": "inputs/stage-1-acceptance.json",
                "acceptanceSha256": _hash_file(stage1_acceptance_path),
                "stage": 1,
                "status": "approved",
            },
            {
                "acceptancePath": "inputs/stage-2-acceptance.json",
                "acceptanceSha256": _hash_file(stage2_acceptance_path),
                "stage": 2,
                "status": "approved",
            },
        ],
    }
    return RunContext(root, manifest), labels


def _approve_stage3(context: RunContext, artifact_root: Path) -> None:
    candidate = _read_json(artifact_root / "stage-3-candidate.json")
    acceptance_path = context.root / "inputs/stage-3-acceptance.json"
    _write_json(
        acceptance_path,
        {
            "runIdentitySha256": context.manifest["runIdentitySha256"],
            "stage": 3,
            "vectorRegions": {
                "fileSha256": candidate["vectorRegions"]["fileSha256"],
                "path": "stages/03/attempt-0001/stage-3-vector-regions.json",
            },
        },
    )
    context.manifest["stages"].append(
        {
            "acceptancePath": "inputs/stage-3-acceptance.json",
            "acceptanceSha256": _hash_file(acceptance_path),
            "stage": 3,
            "status": "approved",
        }
    )


def _region(region_id: int, key: str, left: int, top: int) -> dict[str, object]:
    return {
        "anchor": [left + 60, top + 20],
        "bounds": [left, top, left + 120, top + 40],
        "contour": [
            [left, top],
            [left + 120, top],
            [left + 120, top + 40],
            [left, top + 40],
        ],
        "id": region_id,
        "key": key,
        "metadata": {},
        "type": "pocket",
    }


def _selected_ids(highlights: dict[str, object], scenario: str) -> tuple[int, ...]:
    records = highlights["scenarios"]
    assert isinstance(records, list)
    record = next(value for value in records if value["id"] == scenario)
    selected = record["selectedIds"]
    assert isinstance(selected, list)
    return tuple(selected)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
