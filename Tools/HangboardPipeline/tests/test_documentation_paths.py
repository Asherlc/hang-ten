from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
README = REPO_ROOT / "README.md"
ADDING_A_BOARD = REPO_ROOT / "docs/ADDING_A_BOARD.md"
TESTING = REPO_ROOT / "Tools/HangboardPipeline/TESTING.md"
_UV_ACTION = "astral-sh/setup-uv@d0d8abe699bfb85fec6de9f7adb5ae17292296ff"


def _ci_workflow() -> dict[str, object]:
    if shutil.which("ruby") is None:
        pytest.skip("Ruby is required to parse the CI workflow")
    result = subprocess.run(
        [
            "ruby",
            "-ryaml",
            "-rjson",
            "-e",
            "print JSON.generate(YAML.load_file(ARGV.fetch(0)))",
            str(CI_WORKFLOW),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert isinstance(document, dict)
    return document


def test_active_delivery_guidance_uses_the_state_free_direct_package_contract() -> None:
    """Removing direct package validation would let unregistered content ship."""
    ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    active_docs = "\n".join(
        path.read_text(encoding="utf-8") for path in (README, ADDING_A_BOARD)
    )

    assert "catalog validate --catalog Hangboards/catalog.json" in ci_workflow
    assert "test_generated_catalog_import.py" in ci_workflow
    assert "stage-approved-board-packages.py" in ci_workflow
    assert "BoardPackageStoreTests" in ci_workflow
    assert "status: draft" not in active_docs
    assert "status: approved" not in active_docs
    assert "exactly two states" not in active_docs
    assert "bundles only approved packages" not in active_docs
    assert "bundles only registered packages" in active_docs
    assert "assets/primary.png" in active_docs
    assert "GeneratedBoardCatalog" not in active_docs


def test_ci_python_job_provisions_uv_before_running_pipeline_tests() -> None:
    """The wheel-content test invokes uv from inside pytest."""
    workflow = _ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    python_job = jobs["python"]
    assert isinstance(python_job, dict)
    steps = python_job["steps"]
    assert isinstance(steps, list)

    uv_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Set up uv"
    )
    assert steps[uv_index]["uses"] == _UV_ACTION
    test_indices = [
        index
        for index, step in enumerate(steps)
        if "pytest" in str(step.get("run", "")) or "uv " in str(step.get("run", ""))
    ]
    assert test_indices
    assert uv_index < min(test_indices)


def test_staging_smoke_command_sets_the_required_xcode_destination() -> None:
    """The documented staging command must use the script's Xcode destination contract."""
    testing = TESTING.read_text(encoding="utf-8")

    assert 'stage_root="$(mktemp -d .context/stage-approved-board-packages.XXXXXX)"' in testing
    assert 'TARGET_BUILD_DIR="$stage_root"' in testing
    assert 'UNLOCALIZED_RESOURCES_FOLDER_PATH="HangTen.app"' in testing
    assert 'destination="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/Hangboards"' in testing


def test_testing_guidance_uses_registered_not_lifecycle_inventory_terms() -> None:
    testing = TESTING.read_text(encoding="utf-8")

    assert "Draft packages" not in testing
    assert "status: approved" not in testing
    assert "review inventory" not in testing
    assert "registered and staged" in testing
    assert "unregistered" in testing
