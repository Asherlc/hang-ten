from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EDITOR_ROOT.parents[1]
BUILD_PATH = EDITOR_ROOT / "packaging" / "build.py"


def _load_build_module():
    spec = importlib.util.spec_from_file_location("workbench_packaging", BUILD_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = _load_build_module()


def test_pyinstaller_arguments_embed_only_runtime_inputs(tmp_path):
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")
    dist = tmp_path / "dist"
    work = tmp_path / "work"

    arguments = build._pyinstaller_arguments(REPOSITORY_ROOT, metadata, dist, work)
    joined = "\n".join(arguments)

    for asset in (
        "index.html",
        "styles.css",
        "app.js",
        "editor-model.js",
        "vector-path-model.js",
        "workbench-client.js",
        "workbench-controller.js",
        "workbench-model.js",
    ):
        assert asset in joined
    assert "hangboard_vectorizer" in joined
    assert "Tools/HangboardOnboarding/boards" not in joined
    assert "/tests/" not in joined


@pytest.mark.parametrize("commit", ["A" * 40, "a" * 39, "a" * 41, "not-a-sha"])
def test_commit_must_be_exact_lowercase_sha(commit, tmp_path):
    with pytest.raises(build.BuildError, match="40-character lowercase SHA"):
        build._write_build_metadata(tmp_path, commit)


def test_build_metadata_contains_the_requested_commit_only(tmp_path):
    commit = "b" * 40

    metadata_path = build._write_build_metadata(tmp_path, commit)

    assert metadata_path == tmp_path / "build-commit.txt"
    assert metadata_path.read_bytes() == (commit + "\n").encode("ascii")
