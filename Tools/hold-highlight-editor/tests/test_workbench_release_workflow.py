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


def test_jobs_use_the_current_macos_runner_and_build_verifies_arm64():
    jobs = _workflow()["jobs"]
    build = jobs["build"]

    assert build["runs-on"] == "macos-26"
    assert jobs["release"]["runs-on"] == "macos-26"
    identity_script = _step(build, "Verify executable identity")["run"]
    assert 'test "$architecture" = "arm64"' in identity_script


def test_release_signs_notarizes_and_publishes_a_stapled_app_bundle():
    workflow = _workflow()
    build = workflow["jobs"]["build"]
    release = workflow["jobs"]["release"]
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    certificate_step = _step(release, "Import Developer ID Application certificate")
    assert certificate_step["uses"].startswith("Apple-Actions/import-codesign-certs@")
    assert certificate_step["with"] == {
        "keychain": "signing_temp",
        "p12-file-base64": "${{ secrets.DEVELOPER_ID_CERTIFICATE_FILE_BASE64 }}",
        "p12-password": "${{ secrets.DEVELOPER_ID_CERTIFICATE_PASSWORD }}",
    }

    signing_step = _step(release, "Sign, notarize, and validate workbench app")
    assert signing_step["env"] == {
        "APPSTORE_ISSUER_ID": "${{ vars.APPSTORE_ISSUER_ID }}",
        "APPSTORE_API_KEY_ID": "${{ vars.APPSTORE_API_KEY_ID }}",
        "APPSTORE_API_PRIVATE_KEY": "${{ secrets.APPSTORE_API_PRIVATE_KEY }}",
        "APPLE_TEAM_ID": "${{ vars.APPLE_TEAM_ID }}",
    }
    signing_script = signing_step["run"]
    for required_fragment in (
        "Developer ID Application:",
        "signing_temp.keychain",
        "hangboard-workbench",
        "Tools/hold-highlight-editor/packaging/macos_app.py",
        'python3 "$GITHUB_WORKSPACE/Tools/hold-highlight-editor/packaging/macos_app.py"',
        '--executable "$executable"',
        '--output "$app_bundle"',
        '--version "$GITHUB_RUN_NUMBER"',
        "GITHUB_RUN_NUMBER",
        "codesign --force --sign",
        "--options runtime",
        "--timestamp",
        "codesign --verify --deep --strict --verbose=2",
        "xcrun notarytool submit",
        "--wait",
        "xcrun stapler staple",
        "xcrun stapler validate",
        "spctl --assess --type execute --verbose=4",
        "hangboard-workbench-macos-arm64.zip",
        "hangboard-workbench-macos-arm64.sha256",
        "RUNNER_TEMP",
    ):
        assert required_fragment in signing_script
    archive_command = 'ditto -c -k --keepParent "$app_bundle" "$archive"'
    assert signing_script.count(archive_command) == 2
    assert 'ditto --keepParent "$app_bundle" "$archive"' not in signing_script
    for inline_packaging_fragment in (
        "mkdir -p \"$app_bundle/Contents/MacOS\"",
        "install -m 755",
        "CFBundleExecutable",
        "CFBundleIdentifier",
        "CFBundlePackageType",
        "<plist",
    ):
        assert inline_packaging_fragment not in signing_script

    release_checkout = _step(release, "Check out source")
    assert release_checkout["uses"].startswith("actions/checkout@")
    assert release_checkout["with"] == {"persist-credentials": False}

    release_script = _step(release, "Publish immutable GitHub release")["run"]
    assert "hangboard-workbench-macos-arm64.zip" in release_script
    assert "hangboard-workbench-macos-arm64.sha256" in release_script
    assert "hangboard-workbench-macos-arm64.tar.gz" not in release_script

    release_text = "\n".join(
        json.dumps(step, sort_keys=True) for step in release["steps"]
    )
    for credential in (
        "APPSTORE_ISSUER_ID",
        "APPSTORE_API_KEY_ID",
        "APPSTORE_API_PRIVATE_KEY",
        "APPLE_TEAM_ID",
        "DEVELOPER_ID_CERTIFICATE_FILE_BASE64",
        "DEVELOPER_ID_CERTIFICATE_PASSWORD",
    ):
        assert credential in release_text
        assert credential not in json.dumps(build, sort_keys=True)

    assert "hangboard-workbench-macos-arm64.tar.gz" in workflow_text


def test_release_signing_protects_api_key_and_allows_notarization_to_finish():
    release = _workflow()["jobs"]["release"]
    signing_script = _step(release, "Sign, notarize, and validate workbench app")["run"]

    assert release["timeout-minutes"] == 30
    write_key = "printf '%s' \"$APPSTORE_API_PRIVATE_KEY\" > \"$api_key_path\""
    assert "umask 077" in signing_script
    assert "chmod 600 \"$api_key_path\"" in signing_script
    assert signing_script.index("umask 077") < signing_script.index(write_key)
    assert signing_script.index(write_key) < signing_script.index(
        'chmod 600 "$api_key_path"'
    )


def test_existing_release_validation_checks_downloaded_zip_checksum():
    release = _workflow()["jobs"]["release"]
    script = _step(release, "Publish immutable GitHub release")["run"]

    assert "asset_names = sorted(asset[\"name\"] for asset in release[\"assets\"])" in script
    assert "required_asset_names = sorted([" in script
    assert 'existing_release_dir="$RUNNER_TEMP/hangboard-workbench-existing-release"' in script
    assert 'gh release download "$tag"' in script
    assert 'cd "$existing_release_dir"' in script
    assert "shasum -a 256 -c hangboard-workbench-macos-arm64.sha256" in script
    assert 'current_asset="$release_dir/$asset_name"' not in script
    assert "cmp -s" not in script
    assert script.index("asset_names = sorted") < script.index("gh release download")
    assert script.index("gh release download") < script.index(
        "shasum -a 256 -c hangboard-workbench-macos-arm64.sha256"
    ) < script.index("exit 0")


def test_final_release_checksum_uses_the_downloadable_zip_basename():
    release = _workflow()["jobs"]["release"]
    signing_script = _step(release, "Sign, notarize, and validate workbench app")["run"]

    assert (
        "shasum -a 256 hangboard-workbench-macos-arm64.zip "
        "> hangboard-workbench-macos-arm64.sha256"
    ) in signing_script
    assert (
        'shasum -a 256 "$archive" > hangboard-workbench-macos-arm64.sha256'
        not in signing_script
    )
    assert "shasum -a 256 -c hangboard-workbench-macos-arm64.sha256" in signing_script


def test_release_publication_requires_an_explicit_manual_dispatch():
    workflow = _workflow()
    triggers = workflow["true"]

    assert set(triggers) == {"pull_request", "workflow_dispatch"}
    assert workflow["jobs"]["release"]["if"] == (
        "github.event_name == 'workflow_dispatch' && "
        "github.ref == 'refs/heads/main'"
    )


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
