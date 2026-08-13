from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import load_board_catalog_module


def _write_catalog(root: Path, *, path: str = "example-board") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[3] / "Hangboards/metolius-wood-grips-compact-ii"
    import shutil
    shutil.copytree(source, root / "example-board")
    catalog_path = root / "catalog.json"
    catalog_path.write_text(json.dumps({"schemaVersion": 1, "boards": [{"id": "metolius.wood-grips-compact-ii", "path": path}]}), encoding="utf-8")
    return catalog_path


def test_catalog_requires_a_complete_package_for_every_entry(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    catalog = module.validate_catalog(catalog_path)
    assert catalog.entries[0].path == "example-board"


def test_catalog_rejects_status_and_nested_lifecycle_paths(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    payload["boards"][0]["status"] = "draft"
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown keys"):
        module.validate_catalog(catalog_path)
    payload["boards"][0] = {"id": "metolius.wood-grips-compact-ii", "path": "draft/example-board"}
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="single board-slug directory"):
        module.validate_catalog(catalog_path)
