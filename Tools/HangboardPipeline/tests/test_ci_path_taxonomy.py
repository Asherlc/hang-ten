from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PATHS_PATH = REPOSITORY_ROOT / ".github" / "ci-paths.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("ruby") is None,
    reason="Ruby is required to parse the CI path taxonomy",
)


def load_yaml(path: Path) -> dict[str, object]:
    parsed = subprocess.run(
        [
            "ruby",
            "-ryaml",
            "-rjson",
            "-e",
            "print JSON.generate(YAML.load_file(ARGV.fetch(0)))",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert parsed.returncode == 0, parsed.stderr
    document = json.loads(parsed.stdout)
    assert isinstance(document, dict)
    return document


def test_taxonomy_has_each_required_component_filter() -> None:
    filters = load_yaml(PATHS_PATH)

    assert set(filters) == {
        "ios",
        "python",
        "workbench_web",
        "workbench_native",
        "workbench",
        "shared_board_content",
        "metadata",
        "workflow",
    }


def test_taxonomy_assigns_editor_python_ios_and_shared_paths_conservatively() -> None:
    filters = load_yaml(PATHS_PATH)

    assert "Tools/HangboardWorkbench/*.js" in filters["workbench_web"]
    assert "Tools/HangboardPipeline/**" in filters["python"]
    assert "Tools/HangboardPipeline/**" in filters["workbench"]
    assert "Tools/HangboardWorkbench/**" in filters["workbench"]
    assert "Hangboards/**" in filters["workbench"]
    assert ".github/actions/**" in filters["workbench"]
    assert "HangTen/**" in filters["ios"]
    assert "Hangboards/**" in filters["shared_board_content"]
    assert "scripts/export-board-library.py" in filters["shared_board_content"]
    assert "scripts/stage-board-packages.py" in filters["shared_board_content"]
    assert "HangTen.xcodeproj/**" in filters["metadata"]
    assert (
        "HangTen/Resources/Assets.xcassets/AppIcon.appiconset/**"
        in filters["metadata"]
    )
    assert ".github/workflows/**" in filters["workflow"]
