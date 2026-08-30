from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
README = REPO_ROOT / "README.md"
ADDING_A_BOARD = REPO_ROOT / "docs/ADDING_A_BOARD.md"
TESTING = REPO_ROOT / "Tools/HangboardPackages/TESTING.md"
ANDROID_APP_BUILD = REPO_ROOT / "Android/app/build.gradle.kts"


def _shell_function_body(script: str, function_name: str) -> str:
    """Return a top-level shell function body without consuming later code."""
    signature = re.search(
        rf"^(?P<indent>[ \t]*){re.escape(function_name)}\(\) \{{[ \t]*$",
        script,
        flags=re.MULTILINE,
    )
    assert signature, f"missing shell function {function_name}"
    closing_brace = re.compile(
        rf"^{re.escape(signature.group('indent'))}}}[ \t]*$", re.MULTILINE
    ).search(script, signature.end())
    assert closing_brace, f"unterminated shell function {function_name}"
    return script[signature.end() : closing_brace.start()]


def _ci_workflow() -> dict[str, object]:
    document = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_shell_function_body_ends_at_an_unindented_closing_brace() -> None:
    """Nested shell blocks must not require YAML source indentation to parse."""
    script = """\
run_xctest_attempt() {
  while true; do
    if should_retry; then
      break
    fi
  done
}
outside_function
"""

    assert _shell_function_body(script, "run_xctest_attempt") == """
  while true; do
    if should_retry; then
      break
    fi
  done
"""


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
    xctest_attempt_body = _shell_function_body(xctest_command, "run_xctest_attempt")
    assert "os.setsid()" in xctest_command
    assert "os.execvp(sys.argv[1], sys.argv[1:])" in xctest_command
    assert 'kill -TERM -- "-$xcodebuild_pid"' in xctest_command
    assert 'kill -KILL -- "-$xcodebuild_pid"' in xctest_command
    assert xctest_command.count('kill -0 -- "-$xcodebuild_pid"') == 2
    assert re.search(
        r"python3 -c .*?\\\n\s+xcodebuild \\.*?\n\s+test\s+>",
        xctest_attempt_body,
        flags=re.DOTALL,
    )
    assert "if ! run_xctest_attempt 1; then" in xctest_command
    assert "run_xctest_attempt 2" in xctest_command
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


def test_ci_concurrency_cancels_stale_work_only_within_same_event_ref_group() -> None:
    """cancel-in-progress cancels stale work only in the same event/ref group; push CI is intentionally isolated from merged-PR close events."""
    workflow = _ci_workflow()
    concurrency = workflow["concurrency"]

    assert concurrency["group"] == (
        "ci-${{ github.workflow }}-${{ github.event_name }}-${{ github.ref }}"
    )
    assert concurrency["cancel-in-progress"] is True


def test_android_instrumented_tests_use_a_published_api_36_x86_64_system_image() -> None:
    """API/build tooling tracks compileSdk 36; its published runner image is x86_64."""
    workflow = _ci_workflow()
    android_job = workflow["jobs"]["android"]
    emulator_step = next(
        step
        for step in android_job["steps"]
        if step.get("name") == "Run Android instrumented tests"
    )

    assert emulator_step["uses"] == (
        "reactivecircus/android-emulator-runner@"
        "e89f39f1abbbd05b1113a29cf4db69e7540cae5a"
    )
    assert re.search(r"^\s*compileSdk\s*=\s*36\s*$", ANDROID_APP_BUILD.read_text(encoding="utf-8"), re.MULTILINE)
    assert emulator_step["with"]["api-level"] == 36
    assert emulator_step["with"]["arch"] == "x86_64"


def test_testing_guidance_uses_direct_discovery_not_lifecycle_inventory_terms() -> None:
    testing = TESTING.read_text(encoding="utf-8")

    assert "Draft packages" not in testing
    assert "status: approved" not in testing
    assert "review inventory" not in testing
    assert "direct-child packages" in testing
