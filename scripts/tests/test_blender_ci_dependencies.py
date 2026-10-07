"""Exercise the real Blender setup step without changing host packages."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def run_setup(tmp_path, missing="libegl1", failures=()):
    binaries = tmp_path / "binaries"
    binaries.mkdir()
    events = tmp_path / "events.jsonl"
    for name, body in {
        "dpkg-query": (
            "print('install ok installed' if sys.argv[-1] != os.environ['MISSING'] "
            "else 'deinstall ok config-files', end='')\n"
        ),
        "sudo": (
            "events = Path(os.environ['EVENTS'])\n"
            "calls = events.read_text().splitlines() if events.exists() else []\n"
            "with events.open('a') as output:\n"
            "    output.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "failures = json.loads(os.environ['FAILURES'])\n"
            "sys.exit(failures[len(calls)] if len(calls) < len(failures) else 0)\n"
        ),
    }.items():
        command = binaries / name
        command.write_text(
            f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n" + body
        )
        command.chmod(0o755)
    workflow = yaml.safe_load((ROOT / ".github/workflows/runtime-assets.yml").read_text())
    step = next(step for step in workflow["jobs"]["assemble"]["steps"]
                if step["name"] == "Install headless Blender runtime libraries")
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]], cwd=ROOT, capture_output=True, text=True,
        env=dict(os.environ, PATH=f"{binaries}{os.pathsep}{os.environ['PATH']}",
                 MISSING=missing, EVENTS=str(events), FAILURES=json.dumps(failures)),
        timeout=10,
    )
    calls = [json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
    return result, calls


def assert_bounded(calls):
    for call in calls:
        assert call[:5] == ["timeout", "--kill-after=10s", "120s", "apt-get", "-o"]
        assert "Acquire::Retries=2" in call
        assert "Acquire::http::Timeout=15" in call
        assert "Acquire::https::Timeout=15" in call


def test_installed_libraries_do_not_contact_package_servers(tmp_path):
    result, calls = run_setup(tmp_path, missing="")
    assert result.returncode == 0, result.stderr
    assert calls == []


def test_missing_library_uses_existing_indexes_first(tmp_path):
    result, calls = run_setup(tmp_path)
    assert result.returncode == 0, result.stderr
    assert len(calls) == 1
    assert "install" in calls[0]
    assert calls[0][-1] == "libegl1"
    assert "libgl1" not in calls[0]
    assert_bounded(calls)


def test_stale_indexes_are_refreshed_once_before_retry(tmp_path):
    result, calls = run_setup(tmp_path, failures=[100])
    assert result.returncode == 0, result.stderr
    assert len(calls) == 3
    assert "install" in calls[0]
    assert "update" in calls[1]
    assert "APT::Update::Error-Mode=any" in calls[1]
    assert "install" in calls[2]
    assert_bounded(calls)


@pytest.mark.parametrize("failures, expected_calls, status", [
    ([124], 1, 124),
    ([137], 1, 137),
    ([100, 100], 2, 100),
    ([100, 0, 100], 3, 100),
])
def test_setup_failure_is_propagated_without_unbounded_retries(
    tmp_path, failures, expected_calls, status
):
    result, calls = run_setup(tmp_path, failures=failures)
    assert result.returncode == status, result.stderr
    assert len(calls) == expected_calls
    assert_bounded(calls)
