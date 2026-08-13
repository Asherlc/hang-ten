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
PACKAGING_BUILD_PATH = EDITOR_ROOT / "packaging" / "build.py"
RELEASE_README_PATHS = (
    EDITOR_ROOT / "README.md",
    REPOSITORY_ROOT / "Tools" / "HangboardPipeline" / "README.md",
)
WORKFLOW_PATH = (
    REPOSITORY_ROOT / ".github" / "workflows" / "hangboard-workbench-release.yml"
)
PR_WORKFLOW_PATH = (
    REPOSITORY_ROOT / ".github" / "workflows" / "hangboard-workbench-pr.yml"
)
BUILD_ACTION_PATH = (
    REPOSITORY_ROOT / ".github" / "actions" / "build-hangboard-workbench" / "action.yml"
)
COMMENT_WORKFLOW_PATH = (
    REPOSITORY_ROOT / ".github" / "workflows" / "hangboard-workbench-pr-comment.yml"
)
sys.path.insert(0, str(EDITOR_ROOT))

from workbench_assets import STATIC_ASSETS  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("ruby") is None,
    reason="Ruby is required to parse the release workflow",
)


def _workflow(path: Path = WORKFLOW_PATH) -> dict[str, object]:
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


def _build_action() -> dict[str, object]:
    return _workflow(BUILD_ACTION_PATH)["runs"]


def _step(job: dict[str, object], name: str) -> dict[str, object]:
    return next(step for step in job["steps"] if step.get("name") == name)


def _normalized_expression(expression: str) -> str:
    return " ".join(expression.split())


def _jq_program(script: str, assignment: str) -> str:
    match = re.search(
        rf'{re.escape(assignment)}="\$\(jq.*?\n\s+\'(.*?)\' \\\n\s+<<<"\$[a-z_]+"\)"',
        script,
        re.DOTALL,
    )
    assert match is not None, f"Could not find jq program assigned to {assignment}"
    return match.group(1)


def _run_jq(program: str, payload: object, *arguments: str) -> str:
    result = subprocess.run(
        ["jq", "-r", *arguments, program],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _native_release_quick_start(path: Path) -> str:
    readme = path.read_text(encoding="utf-8")
    _, marker, remainder = readme.partition("## Run the Apple Silicon macOS")
    assert marker
    quick_start, _, _ = remainder.partition("\n## ")
    return " ".join(quick_start.split())


def test_release_readmes_document_the_native_checkout_workflow():
    for path in RELEASE_README_PATHS:
        quick_start = _native_release_quick_start(path)

        for required_fragment in (
            'open "Hangboard Workbench.app"',
            "native window",
            "first launch",
            "last valid checkout",
            "Choose Hang Ten Checkout…",
            "selected checkout",
            "normal Git review",
            "**Choose Another Checkout…**",
            "Remote hosting is not yet shipped",
        ):
            assert required_fragment in quick_start, path

        for forbidden_fragment in (
            "http://localhost",
            "default browser",
            "from inside a Hang Ten checkout",
            "run the app from a Hang Ten checkout",
            "launch this from your checkout",
            "--repository-root",
            "xattr",
            "quarantine",
        ):
            assert forbidden_fragment not in quick_start, path


def test_every_workflow_shell_step_has_valid_bash_syntax(tmp_path):
    jobs = {
        **_workflow()["jobs"],
        **_workflow(PR_WORKFLOW_PATH)["jobs"],
        **_workflow(COMMENT_WORKFLOW_PATH)["jobs"],
        "composite-build": _build_action(),
    }
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


def test_pr_build_and_main_release_share_the_composite_build_action():
    pr = _workflow(PR_WORKFLOW_PATH)
    release = _workflow()
    action = _workflow(BUILD_ACTION_PATH)

    assert set(pr["true"]) == {"pull_request", "merge_group"}
    assert set(release["true"]) == {"push", "workflow_dispatch"}
    assert release["true"]["push"] == {"branches": ["main"]}
    assert release["jobs"]["build"]["if"] == "github.ref == 'refs/heads/main'"
    assert release["jobs"]["release"]["if"] == "github.ref == 'refs/heads/main'"
    uses = "./.github/actions/build-hangboard-workbench"
    assert (
        _step(pr["jobs"]["build"], "Build and upload verified unsigned app")["uses"]
        == uses
    )
    assert (
        _step(release["jobs"]["build"], "Build and upload verified unsigned app")[
            "uses"
        ]
        == uses
    )
    release_build = release["jobs"]["build"]
    release_build_step = _step(
        release_build, "Build and upload verified unsigned app"
    )
    assert release_build_step["id"] == "build"
    assert release_build["outputs"]["artifact-name"] == (
        "${{ steps.build.outputs.artifact-name }}"
    )
    assert _step(release["jobs"]["release"], "Download verified unsigned app")[
        "with"
    ]["name"] == "${{ needs.build.outputs.artifact-name }}"
    assert (
        action["outputs"]["artifact-url"]["value"]
        == "${{ steps.upload.outputs.artifact-url }}"
    )
    assert (
        action["outputs"]["artifact-id"]["value"]
        == "${{ steps.upload.outputs.artifact-id }}"
    )
    assert "${{ github.run_attempt }}" in action["outputs"]["artifact-name"]["value"]
    upload = _step(action["runs"], "Upload verified unsigned app")
    assert upload["id"] == "upload"
    assert upload["with"]["name"] == action["outputs"]["artifact-name"]["value"]
    assert upload["with"]["compression-level"] == 0


def test_composite_build_uses_sha_pinned_setup_uv_before_python_tests():
    steps = _build_action()["steps"]
    uv_index = next(
        index for index, step in enumerate(steps) if step.get("name") == "Set up uv"
    )
    python_suite_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Run focused Python suite"
    )

    # The suite includes a packaging regression test that invokes `uv build`.
    assert steps[uv_index]["uses"] == (
        "astral-sh/setup-uv@d0d8abe699bfb85fec6de9f7adb5ae17292296ff"
    )
    assert uv_index < python_suite_index


def test_pr_build_uses_one_auditable_component_gate():
    jobs = _workflow(PR_WORKFLOW_PATH)["jobs"]
    changes = jobs["changes"]
    assert changes["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert _step(changes, "Check out source")["with"]["persist-credentials"] is False
    assert jobs["build"]["needs"] == "changes"
    condition = _normalized_expression(jobs["build"]["if"])
    assert changes["outputs"] == {"workbench": "${{ steps.filter.outputs.workbench }}"}
    assert condition == "needs.changes.outputs.workbench == 'true'"
    assert "outputs" not in jobs["build"]


def test_successful_pr_build_posts_one_updatable_artifact_download_comment():
    workflow = _workflow(COMMENT_WORKFLOW_PATH)
    comment = workflow["jobs"]["comment-pr-artifact"]
    assert workflow["on"]["workflow_run"]["workflows"] == [
        "Build Hangboard Workbench for pull requests"
    ]
    assert comment["permissions"] == {
        "actions": "read",
        "pull-requests": "write",
    }
    assert comment["timeout-minutes"] == 5
    assert _normalized_expression(comment["if"]) == (
        "github.event.workflow_run.event == 'pull_request' && "
        "github.event.workflow_run.conclusion == 'success'"
    )
    script = _step(comment, "Post workbench download link")["run"]
    for fragment in (
        'pulls/$PR_NUMBER',
        'current_head_sha" != "$HEAD_SHA',
        "actions/workflows/hangboard-workbench-pr.yml/runs",
        ".run_number > $run_number",
        ".run_attempt > $run_attempt",
        'newer_run_exists" == "true"',
        "actions/runs/$RUN_ID/artifacts?per_page=100",
        "actions/runs/$RUN_ID/jobs?per_page=100",
        'select(.name == "Build verified arm64 workbench")',
        'if [[ "$build_conclusion" == "skipped" ]]',
        "did not change relevant paths",
        "<!-- hangboard-workbench-artifact -->",
        '.user.login == "github-actions[bot]"',
        "issues/comments/$comment_id",
    ):
        assert fragment in script
    assert script.index('if [[ "$build_conclusion" == "skipped" ]]') < script.index(
        "Expected unexpired artifact"
    )
    assert script.index('current_head_sha" != "$HEAD_SHA') < script.index(
        'artifact_name="hangboard-workbench'
    )
    assert script.index('newer_run_exists" == "true"') < script.index(
        'artifact_name="hangboard-workbench'
    )
    assert "pull_request_target" not in COMMENT_WORKFLOW_PATH.read_text(
        encoding="utf-8"
    )


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq is required")
def test_pr_comment_jq_programs_handle_slurped_paginated_api_responses():
    workflow = _workflow(COMMENT_WORKFLOW_PATH)
    script = _step(
        workflow["jobs"]["comment-pr-artifact"], "Post workbench download link"
    )["run"]

    runs_program = _jq_program(script, "newer_run_exists")
    assert ".[].workflow_runs[]" in runs_program
    runs = [
        {
            "total_count": 2,
            "workflow_runs": [
                {
                    "run_number": 41,
                    "run_attempt": 1,
                    "pull_requests": [{"number": 127}],
                }
            ],
        },
        {
            "total_count": 2,
            "workflow_runs": [
                {
                    "run_number": 42,
                    "run_attempt": 2,
                    "pull_requests": [{"number": 127}],
                }
            ],
        },
    ]
    assert (
        _run_jq(
            runs_program,
            runs,
            "--argjson",
            "pr",
            "127",
            "--argjson",
            "run_number",
            "42",
            "--argjson",
            "run_attempt",
            "1",
        )
        == "true"
    )

    artifacts_program = _jq_program(script, "artifact_id")
    assert ".[].artifacts[]" in artifacts_program
    artifacts = [
        {
            "total_count": 2,
            "artifacts": [
                {"id": 10, "name": "wanted", "expired": True},
            ],
        },
        {
            "total_count": 2,
            "artifacts": [
                {"id": 20, "name": "wanted", "expired": False},
            ],
        },
    ]
    assert _run_jq(artifacts_program, artifacts, "--arg", "name", "wanted") == "20"

    jobs_program = _jq_program(script, "build_conclusion")
    assert ".[].jobs[]" in jobs_program
    jobs = [
        {"total_count": 2, "jobs": [{"name": "Classify", "conclusion": "success"}]},
        {
            "total_count": 2,
            "jobs": [
                {
                    "name": "Build verified arm64 workbench",
                    "conclusion": "skipped",
                }
            ],
        },
    ]
    assert _run_jq(jobs_program, jobs) == "skipped"

    comments_program = _jq_program(script, "comment_id")
    assert ".[][]" in comments_program
    comments = [
        [
            {
                "id": 30,
                "user": {"login": "contributor"},
                "body": "<!-- hangboard-workbench-artifact -->",
            }
        ],
        [
            {
                "id": 40,
                "user": {"login": "github-actions[bot]"},
                "body": "<!-- hangboard-workbench-artifact -->\nready",
            }
        ],
    ]
    assert (
        _run_jq(
            comments_program,
            comments,
            "--arg",
            "marker",
            "<!-- hangboard-workbench-artifact -->",
        )
        == "40"
    )


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
        ("release", "Publish immutable GitHub release"),
    ]
    comment_jobs = _workflow(COMMENT_WORKFLOW_PATH)["jobs"]
    assert [
        (job_name, step["name"])
        for job_name, job in comment_jobs.items()
        for step in job["steps"]
        if "GH_TOKEN" in step.get("env", {})
    ] == [("comment-pr-artifact", "Post workbench download link")]
    assert "immutable-releases" not in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_build_uses_the_macos_latest_runner_required_by_arm64_verification():
    jobs = _workflow()["jobs"]
    build = jobs["build"]

    assert build["runs-on"] == "macos-latest"
    identity_script = _step(_build_action(), "Verify executable identity")["run"]
    assert 'test "$architecture" = "arm64"' in identity_script


def test_build_tests_and_assembles_the_unsigned_native_app():
    build = _build_action()

    swift_test = _step(build, "Run native shell tests")["run"]
    assert "swift test --package-path Tools/HangboardWorkbench/macos" in swift_test

    app_build = _step(build, "Build unsigned native app")["run"]
    for required_fragment in (
        "Tools/HangboardWorkbench/packaging/build.py",
        "swift build -c release --arch arm64",
        "--package-path Tools/HangboardWorkbench/macos",
        "Tools/HangboardWorkbench/packaging/macos_app.py",
        '--shell "$shell_executable"',
        '--runtime-dir "$runtime_dir"',
        '--output "$app_bundle"',
    ):
        assert required_fragment in app_build
    assert "--codesign-identity" not in app_build

    packaging_build = PACKAGING_BUILD_PATH.read_text(encoding="utf-8")
    assert '"--onedir"' in packaging_build
    assert '"--onefile"' not in packaging_build


def test_build_smokes_the_final_app_headlessly_and_stops_its_owned_backend():
    build = _build_action()
    script = _step(build, "Smoke test unsigned app and clean up")["run"]

    for required_fragment in (
        "Contents/MacOS/HangboardWorkbench",
        '"$app_executable" --headless',
        '--repository-root "$GITHUB_WORKSPACE"',
        "--port 41739",
    ):
        assert required_fragment in script
    assert "http://127.0.0.1:${port}/api/health" in script
    assert "http://127.0.0.1:${port}/" in script
    assert "http://127.0.0.1:${port}/api/library" in script
    assert 'payload == {"ok": True}' in script
    assert 'app_child_pid="$(pgrep -P "$app_pid" || true)"' in script
    assert 'kill -TERM "$app_pid"' in script
    assert 'wait "$app_pid"' in script
    assert 'kill -0 "$app_child_pid"' in script

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


def test_pull_request_build_has_no_apple_credentials_or_notarization():
    build_text = json.dumps(_build_action(), sort_keys=True)

    for forbidden_fragment in (
        "${{ secrets.",
        "APPSTORE_ISSUER_ID",
        "APPSTORE_API_KEY_ID",
        "APPSTORE_API_PRIVATE_KEY",
        "APPLE_TEAM_ID",
        "DEVELOPER_ID_CERTIFICATE_FILE_BASE64",
        "DEVELOPER_ID_CERTIFICATE_PASSWORD",
        "--codesign-identity",
        "notarytool",
    ):
        assert forbidden_fragment not in build_text


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
        "Tools/HangboardWorkbench/packaging/macos_app.py",
        '"$python_bin" "$GITHUB_WORKSPACE/Tools/HangboardWorkbench/packaging/macos_app.py"',
        '--shell "$built_shell"',
        '--runtime-dir "$runtime_dir"',
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
        'mkdir -p "$app_bundle/Contents/MacOS"',
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

    assert "hangboard-workbench-macos-arm64.tar.gz" in BUILD_ACTION_PATH.read_text(
        encoding="utf-8"
    )


def test_release_rebuilds_with_one_matching_identity_and_signs_inside_out():
    release = _workflow()["jobs"]["release"]

    setup_python = _step(release, "Set up Python")
    assert setup_python["uses"].startswith("actions/setup-python@")
    dependencies = _step(release, "Install workbench release dependencies")["run"]
    assert "pyinstaller==6.22.0" in dependencies

    signing_script = _step(release, "Sign, notarize, and validate workbench app")["run"]
    for required_fragment in (
        'grep -F "($APPLE_TEAM_ID)"',
        'if [[ "$identity_count" -ne 1 ]]',
        "Tools/HangboardWorkbench/packaging/build.py",
        '--codesign-identity "$signing_identity"',
        "swift build -c release --arch arm64",
        "Tools/HangboardWorkbench/packaging/macos_app.py",
        'find "$runtime_root" -type f -print0',
        'file -b "$candidate"',
        "Mach-O",
    ):
        assert required_fragment in signing_script

    runtime_sign = (
        'codesign --force --sign "$signing_identity" --options runtime --timestamp '
        '"$candidate"'
    )
    shell_sign = (
        'codesign --force --sign "$signing_identity" --options runtime --timestamp '
        '"$shell_executable"'
    )
    app_sign = (
        'codesign --force --sign "$signing_identity" --options runtime --timestamp '
        '"$app_bundle"'
    )
    assert (
        signing_script.index(runtime_sign)
        < signing_script.index(shell_sign)
        < signing_script.index(app_sign)
    )

    assert signing_script.index("xcrun stapler validate") < signing_script.index(
        '"$app_executable" --headless'
    )
    assert "spctl --assess --type execute --verbose=4" in signing_script
    assert "xcrun notarytool submit" in signing_script


def test_release_signing_protects_api_key_and_allows_notarization_to_finish():
    release = _workflow()["jobs"]["release"]
    signing_script = _step(release, "Sign, notarize, and validate workbench app")["run"]

    assert release["timeout-minutes"] == 30
    write_key = 'printf \'%s\' "$APPSTORE_API_PRIVATE_KEY" > "$api_key_path"'
    assert "umask 077" in signing_script
    assert 'chmod 600 "$api_key_path"' in signing_script
    assert signing_script.index("umask 077") < signing_script.index(write_key)
    assert signing_script.index(write_key) < signing_script.index(
        'chmod 600 "$api_key_path"'
    )


def test_existing_release_validation_checks_downloaded_zip_checksum():
    release = _workflow()["jobs"]["release"]
    script = _step(release, "Publish immutable GitHub release")["run"]

    assert (
        'asset_names = sorted(asset["name"] for asset in release["assets"])' in script
    )
    assert "required_asset_names = sorted([" in script
    assert (
        'existing_release_dir="$RUNNER_TEMP/hangboard-workbench-existing-release"'
        in script
    )
    assert 'gh release download "$tag"' in script
    assert 'cd "$existing_release_dir"' in script
    assert "shasum -a 256 -c hangboard-workbench-macos-arm64.sha256" in script
    assert 'current_asset="$release_dir/$asset_name"' not in script
    assert "cmp -s" not in script
    assert script.index("asset_names = sorted") < script.index("gh release download")
    assert (
        script.index("gh release download")
        < script.index("shasum -a 256 -c hangboard-workbench-macos-arm64.sha256")
        < script.index("exit 0")
    )


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


def test_signed_release_zip_uses_the_documented_top_level_app_basename():
    release = _workflow()["jobs"]["release"]
    signing_script = _step(release, "Sign, notarize, and validate workbench app")["run"]

    assert 'app_bundle="$release_dir/Hangboard Workbench.app"' in signing_script
    assert (
        'test "$(cat "$zip_top_levels")" = "Hangboard Workbench.app"' in signing_script
    )
    assert 'app_bundle="$release_dir/hangboard-workbench.app"' not in signing_script


def test_release_publication_only_runs_for_main_pushes_and_main_dispatches():
    workflow = _workflow()
    triggers = workflow["true"]
    assert set(triggers) == {"push", "workflow_dispatch"}
    assert triggers["push"] == {"branches": ["main"]}
    assert workflow["jobs"]["release"]["needs"] == "build"
    for job_name in ("build", "release"):
        assert workflow["jobs"][job_name]["if"] == "github.ref == 'refs/heads/main'"


def _latest_function() -> str:
    release = _workflow()["jobs"]["release"]
    script = _step(release, "Publish immutable GitHub release")["run"]
    function = re.search(
        r"select_latest_flag\(\) \{\n.*?^\}",
        script,
        re.DOTALL | re.MULTILINE,
    )
    assert function is not None
    assert "git/ref/heads/main" in script
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
