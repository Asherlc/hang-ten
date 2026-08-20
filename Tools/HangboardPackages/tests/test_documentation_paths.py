from __future__ import annotations

import shlex
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
README = REPO_ROOT / "README.md"
ADDING_A_BOARD = REPO_ROOT / "docs/ADDING_A_BOARD.md"
TESTING = REPO_ROOT / "Tools/HangboardPackages/TESTING.md"


def _ci_workflow() -> dict[str, object]:
    document = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_active_delivery_guidance_uses_the_state_free_direct_package_contract() -> None:
    """Removing direct package validation would let unregistered content ship."""
    ci_workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    workflow = _ci_workflow()
    jobs = workflow["jobs"]
    test_job = jobs["test"]
    xctest_step = next(
        step for step in test_job["steps"] if step.get("name") == "Run XCTest suite"
    )
    xctest_command = xctest_step["run"]
    xctest_tokens = shlex.split(xctest_command)
    active_docs = "\n".join(
        path.read_text(encoding="utf-8") for path in (README, ADDING_A_BOARD)
    )

    assert "hangboard-packages.sh validate --root Hangboards" in ci_workflow_text
    assert "pytest tests -q" in ci_workflow_text
    assert "stage-board-packages.py" in ci_workflow_text
    assert "xcodebuild" in xctest_command
    assert "-only-testing" not in xctest_command
    assert "-skip-testing" not in xctest_command
    worker_flag = "-maximum-parallel-testing-workers"
    assert xctest_tokens.count(worker_flag) == 1
    assert xctest_tokens[xctest_tokens.index(worker_flag) + 1] == "1"
    assert "test 2>&1" in xctest_command
    assert "status: draft" not in active_docs
    assert "status: approved" not in active_docs
    assert "exactly two states" not in active_docs
    assert "bundles only approved packages" not in active_docs
    assert "directly discovered" in active_docs
    assert "assets/primary.png" in active_docs
    assert "GeneratedBoardCatalog" not in active_docs


def test_required_debug_build_check_is_reported_when_ios_build_is_skipped() -> None:
    """A path-gated test job must not leave branch protection waiting."""
    workflow = _ci_workflow()
    jobs = workflow["jobs"]
    test_job = jobs["test"]
    required_check = jobs["build-required"]

    required_name = "Build (Debug simulator)"
    assert [job["name"] for job in jobs.values()].count(required_name) == 1

    assert "build-ios" not in jobs
    assert test_job["name"] == "Test (iOS Simulator)"
    expected_predicate = (
        "github.event_name != 'pull_request' || "
        "needs.changes.outputs.ios == 'true' || "
        "needs.changes.outputs.workflow == 'true' || "
        "needs.changes.outputs.shared_board_content == 'true'"
    )
    assert " ".join(test_job["if"].split()) == expected_predicate
    assert required_check["name"] == required_name
    assert required_check["needs"] == ["changes", "test"]
    assert required_check["if"] == "always() && github.event.action != 'closed'"
    assert required_check["runs-on"] == "ubuntu-latest"

    report_step = next(
        step
        for step in required_check["steps"]
        if step.get("name") == "Report required build status"
    )
    assert report_step["env"]["CHANGES_RESULT"] == "${{ needs.changes.result }}"
    assert report_step["env"]["BUILD_RESULT"] == "${{ needs.test.result }}"
    assert report_step["env"]["BUILD_REQUIRED"] == "${{ " + expected_predicate + " }}"
    assert '[[ "$BUILD_RESULT" != "success" ]]' in report_step["run"]
    assert '[[ "$BUILD_RESULT" != "skipped" ]]' in report_step["run"]


def test_ci_pull_request_triggers_exclude_edited_events() -> None:
    """Editing PR metadata must not enqueue duplicate CI work."""
    workflow = _ci_workflow()
    triggers = workflow.get("on", workflow.get(True))
    pull_request = triggers["pull_request"]

    assert "edited" not in pull_request["types"]
    assert pull_request["types"] == [
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
        "closed",
    ]


def test_ci_concurrency_cancels_a_stale_synchronize_run() -> None:
    """A new push (or PR close) must cancel a build still running for that ref."""
    workflow = _ci_workflow()
    concurrency = workflow["concurrency"]

    assert concurrency["group"] == "ci-${{ github.workflow }}-${{ github.ref }}"
    assert concurrency["cancel-in-progress"] is True


def test_testing_guidance_uses_direct_discovery_not_lifecycle_inventory_terms() -> None:
    testing = TESTING.read_text(encoding="utf-8")

    assert "Draft packages" not in testing
    assert "status: approved" not in testing
    assert "review inventory" not in testing
    assert "direct-child packages" in testing
