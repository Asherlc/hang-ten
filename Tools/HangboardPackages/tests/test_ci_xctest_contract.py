"""Keep required iOS UI test coverage complete as CI shards change."""

from __future__ import annotations

import os
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
METHOD_PATTERN = re.compile(
    r"^\s*(?:@\w+(?:\s*\([^)]*\))?\s+)*func\s+(test\w+)\s*\(",
    flags=re.MULTILINE,
)
CLASS_PATTERN = re.compile(
    r"^\s*(?:open\s+|final\s+)?class\s+(\w+UITests)\b",
    flags=re.MULTILINE,
)


def test_ci_model_asset_guard_matches_staging_inventory() -> None:
    staging = (REPO_ROOT / "scripts/stage-board-packages.py").read_text()
    inventory = re.search(r"CI_DEBUG_SIMULATOR_MODEL_SLUGS = frozenset\(\{(.*?)\}\)", staging, re.DOTALL)
    assert inventory is not None
    expected = set(re.findall(r'"([^"\n]+)"', inventory.group(1)))
    runner = (REPO_ROOT / "scripts/ci-run-xctest.sh").read_text()
    guard = re.search(r"for model in\s+(.*?); do", runner, re.DOTALL)
    assert guard is not None
    actual = guard.group(1).replace("\\", "").split()
    assert len(actual) == len(set(actual))
    assert set(actual) == expected


def test_android_staging_check_uses_flat_native_sources() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    step = next(step for step in workflow["jobs"]["python"]["steps"]
                if step.get("name") == "Stage board packages as the Android build does")
    assert "for source in Hangboards/*.FCStd; do" in step["run"]
    assert 'slug=$(basename "$source" .FCStd)' in step["run"]
    assert "Hangboards/*/*.FCStd" not in step["run"]


def test_required_ui_shards_select_every_method_exactly_once() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    jobs = workflow["jobs"]
    shard_jobs = {
        name: job
        for name, job in jobs.items()
        if name.startswith("test-ui-") and name != "test-ui"
    }
    assert shard_jobs
    assert set(jobs["test-ui"]["needs"]) == {"changes", *shard_jobs}

    discovered: dict[str, set[str]] = {}
    for path in (REPO_ROOT / "HangTenUITests").glob("*.swift"):
        source = path.read_text()
        classes = list(CLASS_PATTERN.finditer(source))
        for index, match in enumerate(classes):
            end = classes[index + 1].start() if index + 1 < len(classes) else len(source)
            class_name = f"HangTenUITests/{match.group(1)}"
            discovered[class_name] = {
                f"{class_name}/{method}"
                for method in METHOD_PATTERN.findall(source[match.end() : end])
            }

    selected: list[str] = []
    for job in shard_jobs.values():
        step = next(step for step in job["steps"] if step.get("id") == "xctest")
        assert step["env"]["XCTEST_PARALLEL_WORKERS"] == "1"
        assert "XCTEST_MAX_ATTEMPTS" not in step["env"]
        selectors = step["env"]["XCTEST_ONLY_TESTING"]
        if selectors == "${{ matrix.only_testing }}":
            selectors = " ".join(
                str(shard["only_testing"])
                for shard in job["strategy"]["matrix"]["include"]
            )
        for selector in selectors.split():
            parts = selector.split("/")
            assert len(parts) in (2, 3), f"invalid selector: {selector}"
            class_name = "/".join(parts[:2])
            assert class_name in discovered, f"unknown UI test class: {class_name}"
            if len(parts) == 2:
                selected.extend(discovered[class_name])
            else:
                assert selector in discovered[class_name], f"unknown UI test: {selector}"
                selected.append(selector)

    counts = Counter(selected)
    all_methods = set().union(*discovered.values())
    assert set(counts) == all_methods
    assert all(count == 1 for count in counts.values())


def test_xctest_runner_does_not_retry() -> None:
    runner = (REPO_ROOT / "scripts/ci-run-xctest.sh").read_text()
    assert "XCTEST_MAX_ATTEMPTS" not in runner
    assert 'run_xcodebuild_with_watchdog "build-for-testing" "build-for-testing"' in runner
    assert 'run_xcodebuild_with_watchdog "test-without-building" "test-without-building"' in runner


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("required", "first", "second", "expected"),
    [
        ("true", "success", "success", 0),
        ("true", "success", "failure", 1),
        ("true", "cancelled", "failure", 1),
        ("true", "success", "skipped", 1),
        ("true", "success", "cancelled", 1),
        ("true", "cancelled", "cancelled", 1),
        ("false", "skipped", "skipped", 0),
        ("false", "skipped", "failure", 1),
        ("false", "skipped", "success", 1),
        ("false", "skipped", "cancelled", 1),
    ],
)
def test_ui_required_gate_reports_both_groups(
    reverse: bool, required: str, first: str, second: str, expected: int
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    step = workflow["jobs"]["test-ui"]["steps"][0]
    results = [second, first] if reverse else [first, second]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            **os.environ,
            "CHANGES_RESULT": "success",
            "BUILD_REQUIRED": required,
            "BOARD_ASSETS_REQUIRED": "true",
            "BOARD_ASSETS_RESULT": "success",
            "PAYWALL_RESULT": results[0],
            "MAP_RESULT": results[1],
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize("job", ["build-required", "test-ui"])
@pytest.mark.parametrize("changes", ["cancelled", "failure", "skipped"])
@pytest.mark.parametrize("required", ["true", "false"])
def test_required_gates_reject_incomplete_change_classification(
    job: str, changes: str, required: str
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    step = workflow["jobs"][job]["steps"][0]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            **os.environ,
            "CHANGES_RESULT": changes,
            "BUILD_REQUIRED": required,
            "UNIT_TEST_RESULT": "success",
            "UI_TEST_RESULT": "success",
            "PAYWALL_RESULT": "success",
            "MAP_RESULT": "success",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("required", "unit", "ui", "expected"),
    [
        ("true", "success", "success", 0),
        ("true", "success", "failure", 1),
        ("true", "failure", "success", 1),
        ("true", "success", "cancelled", 1),
        ("true", "cancelled", "success", 1),
        ("true", "cancelled", "cancelled", 1),
        ("true", "cancelled", "failure", 1),
        ("true", "success", "skipped", 1),
        ("true", "skipped", "success", 1),
        ("false", "skipped", "success", 0),
        ("false", "success", "success", 1),
        ("false", "skipped", "failure", 1),
        ("false", "skipped", "skipped", 1),
        ("false", "skipped", "cancelled", 1),
    ],
)
@pytest.mark.parametrize(
    ("native_required", "native_result"),
    [("true", "success"), ("false", "skipped")],
)
def test_build_required_gate_rejects_missing_required_validation(
    required: str,
    unit: str,
    ui: str,
    expected: int,
    native_required: str,
    native_result: str,
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    step = workflow["jobs"]["build-required"]["steps"][0]
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        env={
            **os.environ,
            "CHANGES_RESULT": "success",
            "BUILD_REQUIRED": required,
            "UNIT_TEST_RESULT": unit,
            "UI_TEST_RESULT": ui,
            "BOARD_ASSETS_REQUIRED": "true",
            "BOARD_ASSETS_RESULT": "success",
            "NATIVE_CAD_REQUIRED": native_required,
            "NATIVE_CAD_RESULT": native_result,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("failed_phase", "expected_calls"),
    [
        ("build-for-testing", ["build-for-testing"]),
        ("test-without-building", ["build-for-testing", "test-without-building"]),
    ],
)
@pytest.mark.parametrize("toolchain", ["", "com.apple.dt.toolchain.Metal.123"])
def test_xctest_runner_stops_after_first_failed_phase(
    tmp_path: Path, failed_phase: str, expected_calls: list[str], toolchain: str
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "xcodebuild-calls.txt"
    events = tmp_path / "tool-events.txt"
    mock_xcodebuild = bin_dir / "xcodebuild"
    mock_xcodebuild.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "with open(os.environ['MOCK_XCODEBUILD_CALLS'], 'a') as log:\n"
        "    log.write(sys.argv[-1] + '\\n')\n"
        "with open(os.environ['MOCK_TOOL_EVENTS'], 'a') as log:\n"
        "    log.write('xcodebuild:' + ' '.join(sys.argv[1:]) + '\\n')\n"
        "sys.exit(23 if sys.argv[-1] == os.environ['MOCK_FAIL_PHASE'] else 0)\n"
    )
    mock_xcodebuild.chmod(0o755)
    mock_xcrun = bin_dir / "xcrun"
    mock_xcrun.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "with open(os.environ['MOCK_TOOL_EVENTS'], 'a') as log:\n"
        "    log.write('xcrun:' + ' '.join(args) + '\\n')\n"
        "if args == ['--sdk', 'iphonesimulator', '--show-sdk-version']:\n"
        "    print('26.5')\n"
        "elif args == ['simctl', 'list', 'devices', 'available', '--json']:\n"
        "    print(json.dumps({'devices': {'com.apple.CoreSimulator.SimRuntime.iOS-26-5': [{\n"
        "        'udid': '22452A91-4697-4369-8812-53ADB77EB73B',\n"
        "        'name': 'iPhone 17 Pro', 'state': 'Shutdown', 'isAvailable': True\n"
        "    }]}}))\n"
        "elif args[0:2] not in (['simctl', 'boot'], ['simctl', 'bootstatus'], ['simctl', 'spawn']):\n"
        "    raise SystemExit('unexpected xcrun arguments: ' + repr(args))\n"
    )
    mock_xcrun.chmod(0o755)
    # The watchdog polls every five seconds in production. Keep this contract
    # test focused on invocation counts rather than waiting for its poll period.
    mock_sleep = bin_dir / "sleep"
    mock_sleep.write_text("#!/bin/sh\nexec /bin/sleep 0.01\n")
    mock_sleep.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        PATH=f"{bin_dir}{os.pathsep}{environment['PATH']}",
        MOCK_XCODEBUILD_CALLS=str(calls),
        MOCK_TOOL_EVENTS=str(events),
        MOCK_FAIL_PHASE=failed_phase,
        XCTEST_TOOLCHAIN=toolchain,
        XCTEST_LABEL="mock-xctest",
        XCTEST_DERIVED_DATA=str(tmp_path / "derived-data"),
        XCTEST_LOG_ROOT=str(tmp_path / "logs"),
        XCTEST_RESULT_ROOT=str(tmp_path / "results"),
        XCTEST_XCCONFIG=str(tmp_path / "analytics.xcconfig"),
        XCTEST_ONLY_TESTING="HangTenTests",
        XCTEST_PARALLEL_WORKERS="1",
        XCTEST_RUN_TIMEOUT_SECONDS="20",
    )
    result = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/ci-run-xctest.sh")],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 23, result.stdout + result.stderr
    assert calls.read_text().splitlines() == expected_calls
    event_lines = events.read_text().splitlines()
    build_for_testing = next(
        index for index, event in enumerate(event_lines) if event.startswith("xcodebuild:")
    )
    assert any(
        event.startswith("xcrun:simctl bootstatus 22452A91-4697-4369-8812-53ADB77EB73B -b")
        for event in event_lines[:build_for_testing]
    )
    assert any(
        event.startswith("xcrun:simctl spawn 22452A91-4697-4369-8812-53ADB77EB73B launchctl print system")
        for event in event_lines[:build_for_testing]
    )
    for event in event_lines:
        if event.startswith("xcodebuild:"):
            assert ("-toolchain " in event) == bool(toolchain)
            if toolchain:
                assert f"-toolchain {toolchain} " in event
    assert sum(event.startswith("xcrun:simctl boot ") for event in event_lines) == 1
    assert "-destination platform=iOS Simulator,id=22452A91-4697-4369-8812-53ADB77EB73B" in event_lines[build_for_testing]


@pytest.mark.parametrize(
    ("required", "native_result", "expected"),
    [
        ("true", "success", 0),
        ("true", "failure", 1),
        ("true", "skipped", 1),
        ("true", "cancelled", 1),
        ("false", "skipped", 0),
    ],
)
def test_required_build_gate_rejects_missing_native_cad_checks(
    required: str, native_result: str, expected: int
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["build-required"]
    assert "transgression-native" in job["needs"]
    result = subprocess.run(
        ["bash", "-c", job["steps"][0]["run"]],
        env={
            **os.environ,
            "CHANGES_RESULT": "success",
            "BUILD_REQUIRED": "true",
            "BOARD_ASSETS_REQUIRED": "true",
            "BOARD_ASSETS_RESULT": "success",
            "UNIT_TEST_RESULT": "success",
            "UI_TEST_RESULT": "success",
            "NATIVE_CAD_REQUIRED": required,
            "NATIVE_CAD_RESULT": native_result,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("required", "asset_result", "expected"),
    [("true", "success", 0), ("true", "failure", 1),
     ("true", "skipped", 1), ("true", "cancelled", 1),
     ("false", "skipped", 0)],
)
def test_required_build_gate_rejects_missing_compiled_assets(required, asset_result, expected):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["build-required"]
    assert "board-assets" in job["needs"]
    result = subprocess.run(
        ["bash", "-c", job["steps"][0]["run"]],
        env={**os.environ, "CHANGES_RESULT": "success", "BUILD_REQUIRED": "false",
             "UNIT_TEST_RESULT": "skipped", "UI_TEST_RESULT": "success",
             "NATIVE_CAD_REQUIRED": "false", "NATIVE_CAD_RESULT": "skipped",
             "BOARD_ASSETS_REQUIRED": required, "BOARD_ASSETS_RESULT": asset_result},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr


def test_native_ci_runs_yy_persisted_edits_with_required_toolchain() -> None:
    """Require the YY native battery to execute rather than pass through toolchain skips."""
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    steps = workflow["jobs"]["transgression-native"]["steps"]
    run = next(step["run"] for step in steps if
               "test_verticalboards_native.py" in step.get("run", ""))
    assert "usd-core==26.8" in run
    assert 'export HANGTEN_CAD_PYTHONPATH="$cad_root/usd"' in run
    assert 'test -f "$HANGTEN_FREECAD_CMD"' in run
    assert 'test -f "$HANGTEN_CAD_PYTHONPATH/pxr/__init__.py"' in run
    assert "test_verticalboard_validation_reporting.py" in run
    cleanup = next(step for step in steps if step["name"] == "Delete owned CAD toolchain")
    assert cleanup["if"] == "always()"
    assert 'test ! -e "$cad_root"' in cleanup["run"]
def test_optimized_unit_lane_preserves_swift_debug_assertions() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    optimized_steps = [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "SWIFT_OPTIMIZATION_LEVEL = -O" in step.get("run", "")
    ]
    assert optimized_steps
    for run in optimized_steps:
        assert "OTHER_SWIFT_FLAGS = $(inherited) -assert-config Debug" in run


@pytest.mark.parametrize("mode", ["installed", "needs-selection", "download-fails", "unavailable", "missing-identifier"])
def test_metal_setup_selects_installed_component_and_verifies_compiler(tmp_path: Path, mode: str) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    step = next(step for step in workflow["jobs"]["test-ui-map"]["steps"]
                if step["name"] == "Ensure Metal compiler is available")
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    commands = {
        "xcrun": '\n'.join([
            '#!/usr/bin/env bash',
            'printf "xcrun %s\\n" "$*" >> "$METAL_TEST_LOG"',
            'if [[ "$*" == "--kill-cache" || "$*" == "swift --version" ]]; then exit 0; fi',
            'if [[ "$METAL_TEST_MODE" == "installed" ]]; then exit 0; fi',
            '[[ "$METAL_TEST_MODE" != "unavailable" && "${TOOLCHAINS:-}" == "com.apple.dt.toolchain.Metal.123,com.apple.dt.toolchain.XcodeDefault" ]]',
        ]),
        "xcodebuild": '\n'.join([
            '#!/usr/bin/env bash',
            'printf "xcodebuild %s\\n" "$*" >> "$METAL_TEST_LOG"',
            'case "$1" in',
            '  -downloadComponent) [[ "$METAL_TEST_MODE" != "download-fails" ]] || exit 7 ;;',
            '  -showComponent)',
            '    if [[ "$METAL_TEST_MODE" == "missing-identifier" ]]; then echo \'{}\';',
            '    else echo \'{"status":"installed","toolchainIdentifier":"com.apple.dt.toolchain.Metal.123"}\'; fi ;;',
            'esac',
        ]),
    }
    for name, source in commands.items():
        tool = bin_path / name
        tool.write_text(source + "\n")
        tool.chmod(0o755)
    log = tmp_path / "commands.log"
    github_env = tmp_path / "github-env"
    result = subprocess.run(
        ["bash", "-c", step["run"]], cwd=tmp_path,
        env={**os.environ, "PATH": f"{bin_path}:{os.environ['PATH']}",
             "METAL_TEST_LOG": str(log), "TOOLCHAINS": "",
             "METAL_TEST_MODE": mode, "GITHUB_ENV": str(github_env)},
        capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == (mode in {"installed", "needs-selection"}), result.stdout + result.stderr
    history = log.read_text().splitlines()
    expected = ["xcrun metal -v"]
    if mode != "installed":
        expected.append("xcodebuild -downloadComponent MetalToolchain")
    if mode not in {"installed", "download-fails"}:
        expected.append("xcodebuild -showComponent MetalToolchain -json")
    if mode in {"needs-selection", "unavailable"}:
        expected.extend(["xcrun --kill-cache", "xcrun metal -v"])
    if mode == "needs-selection":
        expected.append("xcrun swift --version")
        assert github_env.read_text() == "XCTEST_TOOLCHAIN=com.apple.dt.toolchain.Metal.123\n"
    else:
        assert not github_env.exists()
    assert history == expected
