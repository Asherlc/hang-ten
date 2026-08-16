from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from conftest import load_board_catalog_module

REPO_ROOT = Path(__file__).resolve().parents[3]
IMPORTER = REPO_ROOT / "scripts/import-generated-board-catalog.py"

SOURCE_AUDITS = (
    "2026-08-12-beastmaker-board-packages.md",
    "2026-08-12-dewoodstok-escape-board-packages.md",
    "2026-08-12-evolv-frictitious-board-packages.md",
    "2026-08-12-metolius-board-packages.md",
    "2026-08-12-single-board-documentation-packages.md",
    "2026-08-12-soill-tension-board-packages.md",
    "2026-08-12-trango-board-packages.md",
    "2026-08-12-rock-prodigy-board-package.md",
    "2026-08-12-yy-vertical-board-packages.md",
    "2026-08-12-zlagboard-board-packages.md",
)
BLOCKER_HEADING = re.compile(r"^### `(?P<slug>[a-z0-9-]+)`$", re.MULTILINE)


def test_importer_retains_only_one_primary_image_without_reading_or_generating_a_catalog(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.png").write_bytes(b"primary")
    (source / "flat-illustrations").mkdir()
    (source / "flat-illustrations/sample-flat.png").write_bytes(b"duplicate")
    destination = tmp_path / "Hangboards"
    destination.mkdir()
    legacy_catalog = b"not valid JSON and no longer authoritative"
    (destination / "catalog.json").write_bytes(legacy_catalog)
    result = subprocess.run([sys.executable, str(IMPORTER), "--source", str(source), "--destination", str(destination)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (destination / "sample/assets/primary.png").read_bytes() == b"primary"
    assert not (destination / "sample/assets/flat.png").exists()
    assert not (destination / "sample/README.md").exists()
    assert (destination / "catalog.json").read_bytes() == legacy_catalog


def test_repository_generated_packages_are_primary_only_and_unregistered() -> None:
    registered = {
        package.name
        for package in (REPO_ROOT / "Hangboards").iterdir()
        if package.is_dir() and (package / "board.json").is_file()
    }
    package_directories = {
        package.name for package in (REPO_ROOT / "Hangboards").iterdir() if package.is_dir()
    }
    unregistered = package_directories - registered
    documented_blockers = {
        match.group("slug")
        for audit in SOURCE_AUDITS
        for match in BLOCKER_HEADING.finditer(
            (REPO_ROOT / "docs/source-audits" / audit).read_text(encoding="utf-8")
        )
    }

    inventory = load_board_catalog_module().discover_board_packages(
        REPO_ROOT / "Hangboards"
    )
    assert {package.root.name for package in inventory.packages} == registered
    candidate_slugs = documented_blockers & unregistered
    assert package_directories == candidate_slugs | registered
    assert len(package_directories) == 33
    assert unregistered == candidate_slugs

    for slug in package_directories:
        assert (REPO_ROOT / "Hangboards" / slug / "assets/primary.png").is_file()

    for slug in unregistered:
        package = REPO_ROOT / "Hangboards" / slug
        relative_paths = {
            path.relative_to(package).as_posix() for path in package.rglob("*")
        }
        relative_files = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_file()
        }
        relative_directories = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_dir()
        }

        assert relative_paths == {"assets", "assets/primary.png"}
        assert relative_files == {"assets/primary.png"}
        assert relative_directories == {"assets"}
