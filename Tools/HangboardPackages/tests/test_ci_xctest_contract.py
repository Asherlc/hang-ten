"""Keep required iOS UI test coverage complete as CI shards change."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

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
