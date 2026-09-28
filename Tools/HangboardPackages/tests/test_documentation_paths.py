from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
CI_PATH_FILTERS = REPO_ROOT / ".github/ci-paths.yml"
README = REPO_ROOT / "README.md"
ADDING_A_BOARD = REPO_ROOT / "docs/ADDING_A_BOARD.md"
TESTING = REPO_ROOT / "Tools/HangboardPackages/TESTING.md"
CAD_README = REPO_ROOT / "Tools/HangboardCAD/README.md"
DELIVERY_LOCK = REPO_ROOT / "docs/source-audits/2026-09-22-model-delivery-lock.json"


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


def _xctest_only_testing_selectors(job: dict[str, object]) -> list[str]:
    step = next(
        step for step in job["steps"] if step.get("name") == "Run XCTest suite"
    )
    value = str(step["env"]["XCTEST_ONLY_TESTING"])
    if value == "${{ matrix.only_testing }}":
        matrix = job["strategy"]["matrix"]
        return [
            selector
            for shard in matrix["include"]
            for selector in str(shard["only_testing"]).split()
        ]
    return value.split()


def _xctest_selector_target(selector: str) -> tuple[str, str | None]:
    """Return the class selector and optional method selector separately."""
    parts = selector.split("/")
    assert len(parts) in (1, 2, 3), f"invalid XCTest selector: {selector}"
    if len(parts) == 1:
        return selector, None
    return "/".join(parts[:2]), parts[2] if len(parts) == 3 else None


def _discovered_ui_test_methods() -> dict[str, set[str]]:
    """Map every UI-test class selector to its discovered test methods."""
    methods_by_class: dict[str, set[str]] = {}
    class_pattern = re.compile(
        r"^\s*(?:open\s+|final\s+)?class\s+(\w+UITests)\b",
        flags=re.MULTILINE,
    )
    method_pattern = re.compile(r"^\s*func\s+(test\w+)\s*\(", re.MULTILINE)
    for path in (REPO_ROOT / "HangTenUITests").glob("*.swift"):
        source = path.read_text(encoding="utf-8")
        classes = list(class_pattern.finditer(source))
        for index, match in enumerate(classes):
            end = classes[index + 1].start() if index + 1 < len(classes) else len(source)
            class_selector = f"HangTenUITests/{match.group(1)}"
            methods_by_class[class_selector] = {
                f"{class_selector}/{method}"
                for method in method_pattern.findall(source, match.end(), end)
            }
    return methods_by_class


def test_ui_test_changes_run_ios_and_python_contract_suites() -> None:
    """UI-test edits must exercise their XCTest shard and shard-assignment contract."""
    filters = yaml.safe_load(CI_PATH_FILTERS.read_text(encoding="utf-8"))
    ui_test_path = "HangTenUITests/**"
    missing_filters = {
        filter_name
        for filter_name in ("ios", "python")
        if ui_test_path not in filters[filter_name]
    }

    assert not missing_filters, (
        f"{ui_test_path} must trigger these CI filters: {sorted(missing_filters)}"
    )


def test_paywall_methods_are_distributed_once_across_ci_shards() -> None:
    """Paywall sharding must keep every UI test method required exactly once."""
    workflow = _ci_workflow()
    paywall_job = workflow["jobs"]["test-ui-paywall"]
    shards = paywall_job["strategy"]["matrix"]["include"]
    selectors = [
        selector
        for shard in shards
        for selector in str(shard["only_testing"]).split()
    ]
    test_file = REPO_ROOT / "HangTenUITests/WorkoutPaywallUITests.swift"
    discovered_methods = {
        f"HangTenUITests/WorkoutPaywallUITests/{method}"
        for method in re.findall(
            r"^\s*func\s+(test\w+)\s*\(",
            test_file.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
    }

    assert len(shards) >= 2
    assert all(str(shard["only_testing"]).split() for shard in shards)
    assert len(selectors) == len(set(selectors))
    assert set(selectors) == discovered_methods


def test_grip_ui_classes_are_balanced_across_two_ci_shards() -> None:
    """The slow grip suite must use two class-balanced simulator jobs."""
    workflow = _ci_workflow()
    grip_job = workflow["jobs"]["test-ui-grip"]
    shards = grip_job["strategy"]["matrix"]["include"]
    shard_classes = [
        {
            _xctest_selector_target(selector)[0]
            for selector in str(shard["only_testing"]).split()
        }
        for shard in shards
    ]

    assert len(shards) == 2
    assert all(len(classes) == 2 for classes in shard_classes)
    assert set.union(*shard_classes) == {
        "HangTenUITests/GripCueDiagnosticScreenshotUITests",
        "HangTenUITests/InitialWeightSetupUITests",
        "HangTenUITests/DualMaxHangsHighlightUITests",
        "HangTenUITests/OneHandedHandChoiceUITests",
    }
    assert shard_classes[0].isdisjoint(shard_classes[1])


def test_free_workout_finish_cases_are_separated_across_ci_shards() -> None:
    """Long finish flows must not both sit in one simulator shard."""
    workflow = _ci_workflow()
    shards = workflow["jobs"]["test-ui-misc"]["strategy"]["matrix"]["include"]
    selectors = [
        selector
        for shard in shards
        for selector in str(shard["only_testing"]).split()
        if selector.startswith("HangTenUITests/FreeWorkoutUITests/")
    ]
    discovered_methods = {
        f"HangTenUITests/FreeWorkoutUITests/{method}"
        for method in re.findall(
            r"^\s*func\s+(test\w+)\s*\(",
            (REPO_ROOT / "HangTenUITests/FreeWorkoutUITests.swift").read_text(
                encoding="utf-8"
            ),
            flags=re.MULTILINE,
        )
    }
    finish_methods = {
        "HangTenUITests/FreeWorkoutUITests/testFreeWorkoutResumeAfterCloseAndLastAfterFinish",
        "HangTenUITests/FreeWorkoutUITests/testFreeWorkoutHangCompleteRestFinishUnlocksLastWorkout",
    }
    locations = {
        selector: str(shard["shard"])
        for shard in shards
        for selector in str(shard["only_testing"]).split()
        if selector in finish_methods
    }

    assert len(selectors) == len(set(selectors))
    assert set(selectors) == discovered_methods
    assert set(locations) == finish_methods
    assert len(set(locations.values())) == len(finish_methods)


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
    active_docs = "\n".join(
        path.read_text(encoding="utf-8") for path in (README, ADDING_A_BOARD)
    )
    xctest_runner = REPO_ROOT / "scripts/ci-run-xctest.sh"
    xctest_script = xctest_runner.read_text(encoding="utf-8")

    assert "hangboard-packages.sh validate --root Hangboards" in ci_workflow_text
    assert "pytest tests -q" in ci_workflow_text
    assert "stage-board-packages.py" in ci_workflow_text

    assert xctest_runner.is_file()
    assert "xcodebuild" in xctest_script
    assert "build-for-testing" in xctest_script
    assert "test-without-building" in xctest_script
    assert 'XCTEST_MAX_ATTEMPTS="${XCTEST_MAX_ATTEMPTS:-2}"' in xctest_script
    assert "while (( attempt <= XCTEST_MAX_ATTEMPTS )); do" in xctest_script
    assert "run_xctest_attempt \"$attempt\"" in xctest_script
    assert "mark_attempt_failed \"$attempt\"" in xctest_script
    assert "os.setsid()" in xctest_script
    assert "os.execvp(sys.argv[1], sys.argv[1:])" in xctest_script
    assert 'kill -TERM -- "-$xcodebuild_pid"' in xctest_script
    assert 'kill -KILL -- "-$xcodebuild_pid"' in xctest_script
    assert xctest_script.count('kill -0 -- "-$xcodebuild_pid"') == 2
    xctest_attempt_body = _shell_function_body(xctest_script, "run_xctest_attempt")
    assert "build-for-testing" in xctest_attempt_body
    assert "test-without-building" in xctest_attempt_body

    expected_suite_jobs = (
        ("test-unit", "HangTenTests", "1", None),
        ("test-ui-paywall", "HangTenUITests/WorkoutPaywallUITests", "1", "2"),
        (
            "test-ui-map",
            "\n".join(
                (
                    "HangTenUITests/OwlClimbPokerBoardMapInteractionUITests",
                    "HangTenUITests/Batch05BoardModelInteractionUITests",
                    "HangTenUITests/IronPalmBoardMapInteractionUITests",
                )
            ),
            "1",
            "2",
        ),
        (
            "test-ui-grip",
            "\n".join(
                (
                    "HangTenUITests/GripCueDiagnosticScreenshotUITests",
                    "HangTenUITests/InitialWeightSetupUITests",
                    "HangTenUITests/DualMaxHangsHighlightUITests",
                    "HangTenUITests/OneHandedHandChoiceUITests",
                )
            ),
            "1",
            "2",
        ),
        (
            "test-ui-picker",
            "HangTenUITests/BeastmakerBoardPickerInteractionUITests",
            "1",
            "2",
        ),
        (
            "test-ui-misc",
            "\n".join(
                (
                    "HangTenUITests/SettingsUITests",
                    "HangTenUITests/FreeWorkoutUITests",
                )
            ),
            "1",
            "2",
        ),
    )
    for job_name, only_testing, workers, max_attempts in expected_suite_jobs:
        test_job = jobs[job_name]
        xctest_step = next(
            step for step in test_job["steps"] if step.get("name") == "Run XCTest suite"
        )
        xctest_command = xctest_step["run"]

        assert test_job["timeout-minutes"] == 70
        assert xctest_step["env"]["XCTEST_ATTEMPT_TIMEOUT_SECONDS"] == "1800"
        assert xctest_step["env"]["XCTEST_PARALLEL_WORKERS"] == workers
        if max_attempts is None:
            assert "XCTEST_MAX_ATTEMPTS" not in xctest_step["env"]
        else:
            assert xctest_step["env"]["XCTEST_MAX_ATTEMPTS"] == max_attempts
        expected_targets = {
            _xctest_selector_target(selector)[0] for selector in only_testing.split()
        }
        actual_selectors = _xctest_only_testing_selectors(test_job)
        assert {
            _xctest_selector_target(selector)[0] for selector in actual_selectors
        } == expected_targets
        assert "scripts/ci-run-xctest.sh" in xctest_command
        assert "xcodebuild" not in xctest_command

    ui_shard_job_names = (
        "test-ui-paywall",
        "test-ui-map",
        "test-ui-grip",
        "test-ui-picker",
        "test-ui-misc",
    )
    ui_shard_targets: list[str] = []
    for job_name in ui_shard_job_names:
        xctest_step = next(
            step
            for step in jobs[job_name]["steps"]
            if step.get("name") == "Run XCTest suite"
        )
        ui_shard_targets.extend(_xctest_only_testing_selectors(jobs[job_name]))
    assert len(ui_shard_targets) == len(set(ui_shard_targets))
    discovered_ui_methods = _discovered_ui_test_methods()
    selected_ui_methods: list[str] = []
    for selector in ui_shard_targets:
        class_selector, method = _xctest_selector_target(selector)
        assert class_selector in discovered_ui_methods, (
            f"unknown UI-test class selector: {class_selector}"
        )
        if method is None:
            selected_ui_methods.extend(sorted(discovered_ui_methods[class_selector]))
        else:
            method_selector = f"{class_selector}/{method}"
            assert method_selector in discovered_ui_methods[class_selector], (
                f"unknown UI-test method selector: {method_selector}"
            )
            selected_ui_methods.append(method_selector)
    discovered_methods = {
        method
        for methods in discovered_ui_methods.values()
        for method in methods
    }
    assert len(selected_ui_methods) == len(set(selected_ui_methods))
    assert set(selected_ui_methods) == discovered_methods

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
    unit_test_job = jobs["test-unit"]
    ui_paywall_job = jobs["test-ui-paywall"]
    ui_map_job = jobs["test-ui-map"]
    ui_grip_job = jobs["test-ui-grip"]
    ui_picker_job = jobs["test-ui-picker"]
    ui_misc_job = jobs["test-ui-misc"]
    ui_test_job = jobs["test-ui"]
    required_check = jobs["build-required"]

    required_name = "Build (Debug simulator)"
    assert [job["name"] for job in jobs.values()].count(required_name) == 1

    assert "build-ios" not in jobs
    assert "test-ui-boards" not in jobs
    assert unit_test_job["name"] == "Test (iOS Simulator: HangTenTests)"
    assert ui_test_job["name"] == "Test (iOS Simulator: HangTenUITests)"
    expected_predicate = (
        "github.event_name != 'pull_request' || "
        "needs.changes.outputs.ios == 'true' || "
        "needs.changes.outputs.workflow == 'true'"
    )
    for path_gated_job in (
        unit_test_job,
        ui_paywall_job,
        ui_map_job,
        ui_grip_job,
        ui_picker_job,
        ui_misc_job,
    ):
        assert " ".join(path_gated_job["if"].split()) == expected_predicate
    assert ui_test_job["if"] == "always() && github.event.action != 'closed'"
    assert ui_test_job["needs"] == [
        "changes",
        "test-ui-paywall",
        "test-ui-map",
        "test-ui-grip",
        "test-ui-picker",
        "test-ui-misc",
    ]
    assert required_check["name"] == required_name
    assert required_check["needs"] == ["changes", "test-unit", "test-ui"]
    assert required_check["if"] == "always() && github.event.action != 'closed'"
    assert required_check["runs-on"] == "ubuntu-latest"

    report_step = next(
        step
        for step in required_check["steps"]
        if step.get("name") == "Report required build status"
    )
    assert report_step["env"]["CHANGES_RESULT"] == "${{ needs.changes.result }}"
    assert report_step["env"]["UNIT_TEST_RESULT"] == "${{ needs.test-unit.result }}"
    assert report_step["env"]["UI_TEST_RESULT"] == "${{ needs.test-ui.result }}"
    assert report_step["env"]["BUILD_REQUIRED"] == "${{ " + expected_predicate + " }}"
    assert '[[ "$UNIT_TEST_RESULT" != "success" ]]' in report_step["run"]
    assert '[[ "$UI_TEST_RESULT" != "success" ]]' in report_step["run"]
    assert '[[ "$UNIT_TEST_RESULT" != "skipped" ]]' in report_step["run"]

    ui_report_step = next(
        step
        for step in ui_test_job["steps"]
        if step.get("name") == "Report required UI test status"
    )
    assert ui_report_step["env"]["PAYWALL_RESULT"] == "${{ needs.test-ui-paywall.result }}"
    assert ui_report_step["env"]["MAP_RESULT"] == "${{ needs.test-ui-map.result }}"
    assert ui_report_step["env"]["GRIP_RESULT"] == "${{ needs.test-ui-grip.result }}"
    assert ui_report_step["env"]["PICKER_RESULT"] == "${{ needs.test-ui-picker.result }}"
    assert ui_report_step["env"]["MISC_RESULT"] == "${{ needs.test-ui-misc.result }}"
    assert '[[ "$PAYWALL_RESULT" == "failure"' in ui_report_step["run"]
    assert '[[ "$PAYWALL_RESULT" != "skipped" ]]' in ui_report_step["run"]


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


def test_testing_guidance_uses_direct_discovery_not_lifecycle_inventory_terms() -> None:
    testing = TESTING.read_text(encoding="utf-8")

    assert "Draft packages" not in testing
    assert "status: approved" not in testing
    assert "review inventory" not in testing
    assert "direct-child packages" in testing


def test_cad_readme_reports_the_derived_migration_count() -> None:
    """The migrated count must track the committed sources, not a frozen number."""
    readme = CAD_README.read_text(encoding="utf-8")
    migrated = len(list((REPO_ROOT / "Hangboards").glob("*/*.FCStd")))
    total = len(json.loads(DELIVERY_LOCK.read_text(encoding="utf-8"))["modelPackages"])

    assert 0 < migrated < total
    assert f"**Status: {migrated} of the {total} model-media boards are migrated**" in readme
    assert f"**{migrated} of {total} model-media boards are migrated.**" in readme
    assert f"The other {total - migrated} still ship" in readme
