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


@pytest.mark.parametrize(
    ("failed_phase", "expected_calls"),
    [
        ("build-for-testing", ["build-for-testing"]),
        ("test-without-building", ["build-for-testing", "test-without-building"]),
    ],
)
def test_xctest_runner_stops_after_first_failed_phase(
    tmp_path: Path, failed_phase: str, expected_calls: list[str]
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "xcodebuild-calls.txt"
    mock_xcodebuild = bin_dir / "xcodebuild"
    mock_xcodebuild.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "with open(os.environ['MOCK_XCODEBUILD_CALLS'], 'a') as log:\n"
        "    log.write(sys.argv[-1] + '\\n')\n"
        "sys.exit(23 if sys.argv[-1] == os.environ['MOCK_FAIL_PHASE'] else 0)\n"
    )
    mock_xcodebuild.chmod(0o755)
    # The watchdog polls every five seconds in production. Keep this contract
    # test focused on invocation counts rather than waiting for its poll period.
    mock_sleep = bin_dir / "sleep"
    mock_sleep.write_text("#!/bin/sh\nexec /bin/sleep 0.01\n")
    mock_sleep.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        PATH=f"{bin_dir}{os.pathsep}{environment['PATH']}",
        MOCK_XCODEBUILD_CALLS=str(calls),
        MOCK_FAIL_PHASE=failed_phase,
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
