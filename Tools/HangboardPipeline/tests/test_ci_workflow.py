from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"

pytestmark = pytest.mark.skipif(
    shutil.which("ruby") is None,
    reason="Ruby is required to parse the CI workflow",
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


def test_ci_checks_the_generated_board_library() -> None:
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: Verify generated board library" in workflow
    assert "working-directory: ${{ github.workspace }}" in workflow
    assert "python3 scripts/export-board-library.py --check" in workflow


def test_ci_classifies_changes_with_the_pinned_shared_taxonomy() -> None:
    workflow = load_yaml(CI_WORKFLOW_PATH)
    changes = workflow["jobs"]["changes"]

    assert changes["runs-on"] == "ubuntu-latest"
    assert changes["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert changes["outputs"]["ios"] == "${{ steps.filter.outputs.ios }}"
    assert changes["outputs"]["python"] == "${{ steps.filter.outputs.python }}"
    assert (
        changes["outputs"]["workbench_web"]
        == "${{ steps.filter.outputs.workbench_web }}"
    )
    assert (
        changes["outputs"]["workbench_native"]
        == "${{ steps.filter.outputs.workbench_native }}"
    )
    assert (
        changes["outputs"]["shared_board_content"]
        == "${{ steps.filter.outputs.shared_board_content }}"
    )
    assert changes["outputs"]["metadata"] == "${{ steps.filter.outputs.metadata }}"
    assert changes["outputs"]["workflow"] == "${{ steps.filter.outputs.workflow }}"
    checkout_step = next(
        step for step in changes["steps"] if step["name"] == "Check out source"
    )
    filter_step_index = next(
        index
        for index, step in enumerate(changes["steps"])
        if step.get("id") == "filter"
    )
    assert changes["steps"].index(checkout_step) < filter_step_index
    assert checkout_step["uses"] == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    assert checkout_step["with"]["persist-credentials"] is False
    filter_step = changes["steps"][filter_step_index]
    assert filter_step["uses"] == "dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d"
    assert filter_step["with"]["filters"] == ".github/ci-paths.yml"


def test_ci_keeps_existing_jobs_but_gates_only_pr_work_by_component() -> None:
    workflow = load_yaml(CI_WORKFLOW_PATH)
    jobs = workflow["jobs"]

    assert "merge_group" in workflow["true"]
    for job_name in ("metadata", "python", "build", "test"):
        assert jobs[job_name]["needs"] == ["changes"]
        assert jobs[job_name]["if"].startswith("github.event_name != 'pull_request' ||")

    assert "needs.changes.outputs.metadata == 'true'" in jobs["metadata"]["if"]
    assert "needs.changes.outputs.workflow == 'true'" in jobs["metadata"]["if"]
    assert "needs.changes.outputs.shared_board_content == 'true'" in jobs["metadata"]["if"]
    assert "needs.changes.outputs.python == 'true'" in jobs["python"]["if"]
    assert "needs.changes.outputs.workflow == 'true'" in jobs["python"]["if"]
    assert "needs.changes.outputs.shared_board_content == 'true'" in jobs["python"]["if"]
    assert "needs.changes.outputs.ios == 'true'" in jobs["build"]["if"]
    assert "needs.changes.outputs.workflow == 'true'" in jobs["build"]["if"]
    assert "needs.changes.outputs.shared_board_content == 'true'" in jobs["build"]["if"]
    assert "needs.changes.outputs.ios == 'true'" in jobs["test"]["if"]
    assert "needs.changes.outputs.workflow == 'true'" in jobs["test"]["if"]
    assert "needs.changes.outputs.shared_board_content == 'true'" in jobs["test"]["if"]
    assert jobs["build-release-device"]["needs"] == ["changes"]
    assert jobs["build-release-device"]["if"] == "github.event_name != 'pull_request'"


def test_merge_queue_runs_the_release_device_build_as_part_of_the_full_gate() -> None:
    workflow = load_yaml(CI_WORKFLOW_PATH)

    assert "merge_group" in workflow["true"]
    assert workflow["jobs"]["build-release-device"]["if"] == (
        "github.event_name != 'pull_request'"
    )
