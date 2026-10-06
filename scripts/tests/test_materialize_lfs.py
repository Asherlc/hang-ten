"""LFS cache restoration must fetch only missing current objects and verify bytes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / ".github/actions/materialize-lfs/action.yml"
FIRST = b"first authored CAD document\n"
SECOND = b"revised authored CAD document\n"
UNCHANGED = b"unchanged authored CAD document\n"


def git(repository, *args, env=None):
    return subprocess.run(["git", *args], cwd=repository, env=env, check=True,
                          capture_output=True, text=True, timeout=30).stdout.strip()


@pytest.fixture
def repositories(tmp_path):
    environment = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    environment.pop("GH_TOKEN", None)
    environment.pop("GIT_CONFIG_COUNT", None)
    origin = tmp_path / f"{ROOT.name}-lfs-origin.git"
    source = tmp_path / f"{ROOT.name}-lfs-source"
    checkout = tmp_path / f"{ROOT.name}-lfs-checkout"
    git(tmp_path, "init", "--bare", str(origin), env=environment)
    git(tmp_path, "init", "-b", "main", str(source), env=environment)
    git(source, "config", "user.name", "LFS fixture", env=environment)
    git(source, "config", "user.email", "lfs-fixture@example.invalid", env=environment)
    git(source, "lfs", "install", "--local", env=environment)
    git(source, "lfs", "track", "Hangboards/*.FCStd", env=environment)
    boards = source / "Hangboards"
    boards.mkdir()
    (boards / "board.FCStd").write_bytes(FIRST)
    (boards / "unchanged.FCStd").write_bytes(UNCHANGED)
    git(source, "add", ".", env=environment)
    git(source, "commit", "-m", "Initial authored sources", env=environment)
    git(source, "remote", "add", "origin", str(origin), env=environment)
    git(source, "push", "origin", "main", env=environment)
    (boards / "board.FCStd").write_bytes(SECOND)
    git(source, "add", ".", env=environment)
    git(source, "commit", "-m", "Revise one source", env=environment)
    git(source, "push", "origin", "main", env=environment)
    git(tmp_path, "clone", "--branch", "main", str(origin), str(checkout), env=environment)
    return origin, source, checkout, environment


def object_path(repository, content, *, bare=False):
    digest = hashlib.sha256(content).hexdigest()
    return repository / ("lfs/objects" if bare else ".git/lfs/objects") / digest[:2] / digest[2:4] / digest


def restore_object(source, checkout, content):
    destination = object_path(checkout, content)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(object_path(source, content), destination)


def run_step(checkout, environment, step_id):
    assert ACTION.is_file(), "CI has no action to materialize cached LFS sources"
    action = yaml.safe_load(ACTION.read_text())
    step = next(step for step in action["runs"]["steps"] if step.get("id") == step_id)
    return subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step["run"]], cwd=checkout,
                          env=environment, capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("job", ["board-assets", "release"])
def test_legacy_release_loads_workflow_helper_without_changing_tested_head(repositories, job):
    _, source, checkout, environment = repositories
    revision = git(checkout, "rev-parse", "HEAD", env=environment)
    # The tested revision has no local action; the workflow revision supplies it.
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    step = next(step for step in workflow["jobs"][job]["steps"] if step.get("id") == "lfs-helper")
    binaries = checkout / "fixture-binaries"
    binaries.mkdir()
    gh = binaries / "gh"
    gh.write_text(
        "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
        "assert sys.argv[1:] == ['api', 'repos/fixture/repo/contents/.github/actions/"
        "materialize-lfs/action.yml?ref=workflow-revision', '-H', "
        "'Accept: application/vnd.github.raw+json']\n"
        f"sys.stdout.write(Path({json.dumps(str(ACTION))}).read_text())\n"
    )
    gh.chmod(0o755)
    environment.update(PATH=f"{binaries}{os.pathsep}{environment['PATH']}",
                       GITHUB_REPOSITORY="fixture/repo", WORKFLOW_REVISION="workflow-revision",
                       PASEO_WORKTREE_PATH=str(checkout))
    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step["run"]],
                            cwd=checkout, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (checkout / ".github/actions/materialize-lfs/action.yml").is_file()
    assert git(checkout, "rev-parse", "HEAD", env=environment) == revision
    assert not list((checkout / ".context").glob("*-release-lfs-helper"))
    for content in (SECOND, UNCHANGED):
        restore_object(source, checkout, content)
    # Execute the restored helper against the unchanged tested checkout.
    action = yaml.safe_load((checkout / ".github/actions/materialize-lfs/action.yml").read_text())
    script = next(step["run"] for step in action["runs"]["steps"] if step.get("id") == "materialize")
    materialized = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                                 cwd=checkout, env=environment, capture_output=True, text=True, timeout=30)
    assert materialized.returncode == 0, materialized.stdout + materialized.stderr
    assert_current_sources(checkout)


def assert_current_sources(checkout):
    assert (checkout / "Hangboards/board.FCStd").read_bytes() == SECOND
    assert (checkout / "Hangboards/unchanged.FCStd").read_bytes() == UNCHANGED


def test_complete_cache_materializes_sources_without_available_remote_objects(repositories):
    origin, source, checkout, environment = repositories
    for content in (SECOND, UNCHANGED):
        restore_object(source, checkout, content)
        object_path(origin, content, bare=True).unlink()
    environment.update(GH_TOKEN="fixture-token", GITHUB_SERVER_URL="https://github.com",
                       GITHUB_ACTIONS="true")
    result = run_step(checkout, environment, "materialize")
    assert result.returncode == 0, result.stdout + result.stderr
    assert_current_sources(checkout)
    assert "fixture-token" not in result.stdout + result.stderr
    assert "extraheader" not in (checkout / ".git/config").read_text().lower()


def test_older_cache_fetches_new_revision_without_redownloading_unchanged_object(repositories):
    origin, source, checkout, environment = repositories
    for content in (FIRST, UNCHANGED):
        restore_object(source, checkout, content)
    object_path(origin, UNCHANGED, bare=True).unlink()
    # A runner's fetch filters must not leave required CAD documents as pointers.
    git(checkout, "config", "lfs.fetchexclude", "Hangboards/*", env=environment)
    result = run_step(checkout, environment, "materialize")
    assert result.returncode == 0, result.stdout + result.stderr
    assert_current_sources(checkout)


def test_empty_cache_fetches_current_sources(repositories):
    _, _, checkout, environment = repositories
    result = run_step(checkout, environment, "materialize")
    assert result.returncode == 0, result.stdout + result.stderr
    assert_current_sources(checkout)


def test_corrupt_cache_fails_before_materializing_wrong_source(repositories):
    _, source, checkout, environment = repositories
    for content in (SECOND, UNCHANGED):
        restore_object(source, checkout, content)
    object_path(checkout, SECOND).write_bytes(b"!" * len(SECOND))
    result = run_step(checkout, environment, "materialize")
    assert result.returncode != 0
    assert "corrupt" in result.stdout + result.stderr
    assert (checkout / "Hangboards/board.FCStd").read_bytes().startswith(
        b"version https://git-lfs.github.com/spec/v1\n")


def test_missing_object_failure_does_not_report_materialized_sources(repositories):
    origin, source, checkout, environment = repositories
    restore_object(source, checkout, UNCHANGED)
    object_path(origin, SECOND, bare=True).unlink()
    result = run_step(checkout, environment, "materialize")
    assert result.returncode != 0
    assert (checkout / "Hangboards/board.FCStd").read_bytes().startswith(
        b"version https://git-lfs.github.com/spec/v1\n")


def cache_key(checkout, environment):
    output = checkout / "cache-outputs"
    output.write_text("")
    result = run_step(checkout, dict(environment, GITHUB_OUTPUT=str(output)), "keys")
    assert result.returncode == 0, result.stdout + result.stderr
    return dict(line.split("=", 1) for line in output.read_text().splitlines())["key"]


def test_cache_key_tracks_objects_instead_of_checkout_state_or_code_revision(repositories):
    _, source, checkout, environment = repositories
    environment["PASEO_WORKTREE_PATH"] = str(checkout)
    key = cache_key(checkout, environment)
    for content in (SECOND, UNCHANGED):
        restore_object(source, checkout, content)
    result = run_step(checkout, environment, "materialize")
    assert result.returncode == 0, result.stdout + result.stderr
    assert_current_sources(checkout)
    assert cache_key(checkout, environment) == key
    git(checkout, "-c", "user.name=LFS fixture", "-c", "user.email=lfs-fixture@example.invalid",
        "commit", "--allow-empty", "-m", "Only code changed", env=environment)
    assert cache_key(checkout, environment) == key
    git(checkout, "checkout", "HEAD~2", env=environment)
    assert cache_key(checkout, environment) != key
