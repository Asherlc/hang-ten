from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import load_board_catalog_module


def _write_catalog(root: Path, *, status: str = "draft", path: str = "example-board") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    catalog = {
        "schemaVersion": 1,
        "boards": [{"id": "example.board", "path": path, "status": status}],
    }
    catalog_path = root / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    (root / "example-board").mkdir(exist_ok=True)
    return catalog_path


def test_catalog_accepts_incomplete_draft_package(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)

    catalog = module.validate_catalog(catalog_path)

    assert catalog.entries[0].status == "draft"
    assert catalog.entries[0].path == "example-board"


def test_catalog_rejects_any_status_outside_the_two_state_registry(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["boards"][0]["status"] = "shipped"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    with pytest.raises(ValueError, match="status must be one of"):
        module.validate_catalog(catalog_path)


def test_catalog_requires_unique_ids_and_confined_relative_package_paths(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["boards"].append(dict(catalog["boards"][0]))
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate board id"):
        module.validate_catalog(catalog_path)

    catalog["boards"] = [{"id": "example.board", "path": "../escape", "status": "draft"}]
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(ValueError, match="relative path inside the catalog"):
        module.validate_catalog(catalog_path)


def test_approved_package_requires_board_manifest_while_the_same_draft_does_not(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path, status="approved")

    with pytest.raises(ValueError, match=r"approved package .*board\.json"):
        module.validate_catalog(catalog_path)


def test_catalog_and_entries_are_closed_immutable_models(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    catalog_path = _write_catalog(tmp_path)
    catalog = module.validate_catalog(catalog_path)

    assert isinstance(catalog.entries, tuple)
    with pytest.raises((AttributeError, TypeError)):
        catalog.entries[0].status = "approved"

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown keys"):
        module.validate_catalog(catalog_path)
