from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EDITOR_ROOT.parents[1]
WORKFLOW_PATH = (
    REPOSITORY_ROOT / ".github" / "workflows" / "hangboard-workbench-release.yml"
)
sys.path.insert(0, str(EDITOR_ROOT))

from workbench_assets import STATIC_ASSETS  # noqa: E402


pytestmark = pytest.mark.skipif(
    shutil.which("ruby") is None,
    reason="Ruby is required to parse the release workflow",
)


def _workflow() -> dict[str, object]:
    parsed = subprocess.run(
        [
            "ruby",
            "-ryaml",
            "-rjson",
            "-e",
            "print JSON.generate(YAML.load_file(ARGV.fetch(0)))",
            str(WORKFLOW_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert parsed.returncode == 0, parsed.stderr
    document = json.loads(parsed.stdout)
    assert isinstance(document, dict)
    return document


def _step(job: dict[str, object], name: str) -> dict[str, object]:
    return next(step for step in job["steps"] if step.get("name") == name)


def test_every_workflow_shell_step_has_valid_bash_syntax(tmp_path):
    jobs = _workflow()["jobs"]
    for job_name, job in jobs.items():
        for index, step in enumerate(job["steps"]):
            script = step.get("run")
            if script is None:
                continue
            shell = step.get("shell")
            if shell is not None and not shell.startswith("bash"):
                continue
            script_path = tmp_path / f"{job_name}-{index}.sh"
            script_path.write_text(script, encoding="utf-8")
            result = subprocess.run(
                ["bash", "-n", str(script_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr


def test_workflow_permissions_and_release_credentials_remain_narrow():
    workflow = _workflow()
    jobs = workflow["jobs"]

    assert workflow["permissions"] == {"contents": "read"}
    assert "permissions" not in jobs["build"]
    assert jobs["release"]["permissions"] == {"contents": "write"}

    credential_steps = [
        (job_name, step["name"])
        for job_name, job in jobs.items()
        for step in job["steps"]
        if "GH_TOKEN" in step.get("env", {})
    ]
    assert credential_steps == [
        ("release", "Publish immutable GitHub release")
    ]
    assert "immutable-releases" not in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_frozen_smoke_checks_all_assets_both_signals_and_owned_cleanup():
    build = _workflow()["jobs"]["build"]
    script = _step(build, "Smoke test executable and clean up")["run"]

    assert "smoke_signal INT 41739" in script
    assert "smoke_signal TERM 41740" in script
    assert 'kill -"$shutdown_signal" "$workbench_pid"' in script
    assert "trap cleanup EXIT" in script
    assert 'wait "$workbench_pid"' in script
    assert 'kill -0 "$workbench_child_pid"' in script
    assert "Traceback|Exception ignored in atexit callback|could not start" in script
    assert "http://127.0.0.1:${port}/" in script
    assert "http://127.0.0.1:${port}/api/library" in script

    manifest_program = re.search(
        r"python - <<'PY'\n(?P<program>.*?)\nPY",
        script,
        re.DOTALL,
    )
    assert manifest_program is not None
    result = subprocess.run(
        [sys.executable, "-c", manifest_program.group("program")],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [f"/{asset}" for asset in STATIC_ASSETS]


def _latest_function() -> str:
    release = _workflow()["jobs"]["release"]
    script = _step(release, "Publish immutable GitHub release")["run"]
    function = re.search(
        r"select_latest_flag\(\) \{\n.*?^\}",
        script,
        re.DOTALL | re.MULTILINE,
    )
    assert function is not None
    assert 'git/ref/heads/main' in script
    assert 'latest_flag="$(select_latest_flag "$main_sha" "$GITHUB_SHA")"' in script
    assert '"$latest_flag"' in script
    return function.group(0)


@pytest.mark.parametrize(
    ("main_sha", "built_sha", "expected"),
    [
        ("a" * 40, "a" * 40, "--latest"),
        ("b" * 40, "a" * 40, "--latest=false"),
        ("", "a" * 40, "--latest=false"),
    ],
)
def test_latest_flag_depends_on_the_current_main_tip(main_sha, built_sha, expected):
    script = f'{_latest_function()}\nselect_latest_flag "$1" "$2"\n'
    result = subprocess.run(
        ["bash", "-c", script, "latest-policy", main_sha, built_sha],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected
