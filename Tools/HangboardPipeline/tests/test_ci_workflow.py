from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
CODEQL_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "codeql.yml"

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
    workflow = load_yaml(CI_WORKFLOW_PATH)
    verification_step = next(
        step
        for step in workflow["jobs"]["python"]["steps"]
        if step["name"] == "Verify generated board library"
    )

    assert verification_step["working-directory"] == "${{ github.workspace }}"
    assert verification_step["run"] == "python3 scripts/export-board-library.py --check"


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
    stable_check_names = {
        "metadata": "Validate App Store metadata",
        "python": "Test (Python)",
        "build": "Build (${{ matrix.name }})",
        "test": "Test (iOS Simulator)",
    }
    for job_name, check_name in stable_check_names.items():
        assert jobs[job_name]["name"] == check_name
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


def test_ci_retriggers_on_pr_edits_and_keeps_release_device_push_only() -> None:
    workflow = load_yaml(CI_WORKFLOW_PATH)
    events = workflow["true"]
    release_device = workflow["jobs"]["build-release-device"]

    assert "edited" in events["pull_request"]["types"]
    assert "merge_group" in events
    assert release_device["name"] == "Build (Release device)"
    assert release_device["needs"] == ["changes"]
    assert release_device["if"] == "github.event_name == 'push'"


def test_codeql_workflow_uses_conditional_language_gate() -> None:
    workflow = load_yaml(CODEQL_WORKFLOW_PATH)
    jobs = workflow["jobs"]
    gate = jobs["codeql-gate"]

    actions_initialize = next(
        step
        for step in jobs["analyze-actions"]["steps"]
        if step["name"] == "Initialize CodeQL"
    )
    assert actions_initialize["with"]["languages"] == "actions"
    assert jobs["analyze-swift"]["if"] == "${{ needs.changes.outputs.swift == 'true' }}"
    assert jobs["analyze-python"]["if"] == "${{ needs.changes.outputs.python == 'true' }}"
    assert jobs["analyze-javascript"]["if"] == (
        "${{ needs.changes.outputs.javascript == 'true' }}"
    )
    assert gate["name"] == "CodeQL gate"
    assert gate["if"] == "${{ always() }}"
    assert gate["needs"] == [
        "changes",
        "analyze-actions",
        "analyze-swift",
        "analyze-python",
        "analyze-javascript",
    ]
    gate_step = gate["steps"][0]
    assert gate_step["env"] == {
        "CHANGES_RESULT": "${{ needs.changes.result }}",
        "ACTIONS_RESULT": "${{ needs.analyze-actions.result }}",
        "SWIFT_RESULT": "${{ needs.analyze-swift.result }}",
        "PYTHON_RESULT": "${{ needs.analyze-python.result }}",
        "JAVASCRIPT_RESULT": "${{ needs.analyze-javascript.result }}",
    }
    assert 'test "$CHANGES_RESULT" = success' in gate_step["run"]
    assert 'test "$ACTIONS_RESULT" = success' in gate_step["run"]
    assert 'test "$result" = success || test "$result" = skipped' in gate_step["run"]


def test_codeql_workflow_is_not_filtered_before_it_can_report_its_gate() -> None:
    workflow = load_yaml(CODEQL_WORKFLOW_PATH)
    events = workflow["true"]

    for event_name in ("pull_request", "push"):
        assert "paths" not in events[event_name]
        assert "paths-ignore" not in events[event_name]


def test_codeql_change_detector_checks_out_history_before_filtering() -> None:
    workflow = load_yaml(CODEQL_WORKFLOW_PATH)
    steps = workflow["jobs"]["changes"]["steps"]
    checkout_index = next(
        index for index, step in enumerate(steps) if step["name"] == "Check out source"
    )
    filter_index = next(
        index for index, step in enumerate(steps) if step.get("id") == "filter"
    )

    assert checkout_index < filter_index
    assert steps[checkout_index]["uses"] == (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    )
    assert steps[checkout_index]["with"] == {
        "persist-credentials": False,
        "fetch-depth": 0,
    }
    assert steps[filter_index]["uses"] == (
        "dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d"
    )
