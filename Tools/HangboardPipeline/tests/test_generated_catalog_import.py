from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
IMPORTER = REPO_ROOT / "scripts/import-generated-board-catalog.py"


def test_importer_retains_only_one_primary_image_without_catalog_registration(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.png").write_bytes(b"primary")
    (source / "flat-illustrations").mkdir()
    (source / "flat-illustrations/sample-flat.png").write_bytes(b"duplicate")
    destination = tmp_path / "Hangboards"
    destination.mkdir()
    (destination / "catalog.json").write_text(json.dumps({"schemaVersion": 1, "boards": []}))
    result = subprocess.run([sys.executable, str(IMPORTER), "--source", str(source), "--destination", str(destination)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (destination / "sample/assets/primary.png").read_bytes() == b"primary"
    assert not (destination / "sample/assets/flat.png").exists()
    assert not (destination / "sample/README.md").exists()
    assert json.loads((destination / "catalog.json").read_text())["boards"] == []


def test_repository_generated_packages_are_primary_only_and_unregistered() -> None:
    catalog = json.loads((REPO_ROOT / "Hangboards/catalog.json").read_text())
    registered = {entry["path"] for entry in catalog["boards"]}
    for package in (REPO_ROOT / "Hangboards").iterdir():
        if not package.is_dir() or package.name in registered:
            continue
        assert (package / "assets/primary.png").is_file()
        assert not (package / "README.md").exists()
        assert not (package / "review").exists()
        assert not (package / "outline.json").exists()
        assert not (package / "outline.approx.json").exists()
        assert list(package.glob("*.json")) == []
        assert sorted(path.name for path in (package / "assets").iterdir()) == ["primary.png"]
