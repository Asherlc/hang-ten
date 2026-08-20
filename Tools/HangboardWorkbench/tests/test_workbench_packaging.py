from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


EDITOR_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EDITOR_ROOT.parents[1]
BUILD_PATH = EDITOR_ROOT / "packaging" / "build.py"
sys.path.insert(0, str(EDITOR_ROOT))

import workbench_assets  # noqa: E402


def _load_build_module():
    spec = importlib.util.spec_from_file_location("workbench_packaging", BUILD_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = _load_build_module()


def test_static_asset_routes_expose_only_the_packaged_bundle() -> None:
    assert workbench_assets.STATIC_ASSET_ROUTES == (
        ("/", "index.html"),
        ("/index.html", "index.html"),
        ("/styles.css", "styles.css"),
        ("/app.js", "app.js"),
    )
    routes = {route for route, _asset in workbench_assets.STATIC_ASSET_ROUTES}
    assert routes.isdisjoint(
        {"/workbench-client.js", "/workbench-controller.js", "/path-editor.js"}
    )


def test_authored_frontend_sources_are_typescript() -> None:
    frontend_suffixes = {".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx"}
    excluded_directories = {"node_modules", "dist", "build", ".venv", "__pycache__"}
    browser_sources = {
        path
        for path in EDITOR_ROOT.rglob("*")
        if path.is_file()
        and path.suffix in frontend_suffixes
        and excluded_directories.isdisjoint(path.relative_to(EDITOR_ROOT).parts)
    }
    authored_javascript = sorted(
        path.relative_to(EDITOR_ROOT).as_posix()
        for path in browser_sources
        if path != EDITOR_ROOT / "app.js" and path.suffix not in {".ts", ".tsx"}
    )

    assert (EDITOR_ROOT / "app.js") in browser_sources
    assert authored_javascript == []


def test_pyinstaller_arguments_embed_only_direct_workbench_runtime_inputs(tmp_path):
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")
    dist = tmp_path / "dist"
    work = tmp_path / "work"

    arguments = build._pyinstaller_arguments(REPOSITORY_ROOT, metadata, dist, work)
    joined = "\n".join(arguments)

    for asset in workbench_assets.STATIC_ASSETS:
        assert asset in joined
    hidden_imports = [
        arguments[index + 1]
        for index, value in enumerate(arguments)
        if value == "--hidden-import"
    ]
    assert hidden_imports == ["server", "board_package", "board_geometry"]

    embedded_operands = [
        arguments[index + 1]
        for index, value in enumerate(arguments)
        if value in {"--add-data", "--add-binary"}
    ]
    for operand in embedded_operands:
        source = Path(operand.split(os.pathsep, maxsplit=1)[0])
        assert "boards" not in source.parts, operand
        assert "tests" not in source.parts, operand


def test_pyinstaller_uses_onedir_and_includes_supplied_codesign_identity(tmp_path):
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")

    arguments = build._pyinstaller_arguments(
        REPOSITORY_ROOT,
        metadata,
        tmp_path / "dist",
        tmp_path / "work",
        codesign_identity="Developer ID Application: Test (TEAM)",
    )

    assert "--onedir" in arguments
    assert "--onefile" not in arguments
    identity_index = arguments.index("--codesign-identity")
    assert arguments[identity_index + 1] == "Developer ID Application: Test (TEAM)"
    for asset in workbench_assets.STATIC_ASSETS:
        assert asset in "\n".join(arguments)


def test_pyinstaller_omits_codesign_identity_when_not_supplied(tmp_path):
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")

    arguments = build._pyinstaller_arguments(
        REPOSITORY_ROOT,
        metadata,
        tmp_path / "dist",
        tmp_path / "work",
    )

    assert "--codesign-identity" not in arguments


@pytest.mark.parametrize("identity", ["", " ", "\t"])
def test_pyinstaller_rejects_empty_codesign_identity(identity, tmp_path):
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")

    with pytest.raises(build.BuildError, match="codesign identity"):
        build._pyinstaller_arguments(
            REPOSITORY_ROOT,
            metadata,
            tmp_path / "dist",
            tmp_path / "work",
            codesign_identity=identity,
        )


def test_pyinstaller_arguments_accept_a_workbench_and_board_library_without_other_tool_sources(
    tmp_path, monkeypatch
):
    repository = tmp_path / "repository"
    (repository / "Hangboards").mkdir(parents=True)
    editor_root = repository / "Tools" / "HangboardWorkbench"
    editor_root.mkdir(parents=True)
    (editor_root / "workbench_binary.py").write_text("", encoding="utf-8")
    (editor_root / "server.py").write_text("", encoding="utf-8")
    (editor_root / "board_package.py").write_text("", encoding="utf-8")
    (editor_root / "board_geometry.py").write_text("", encoding="utf-8")
    (editor_root / "workbench_assets.py").write_text("", encoding="utf-8")
    (editor_root / "manifest-only.js").write_text("", encoding="utf-8")
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")
    monkeypatch.setattr(workbench_assets, "STATIC_ASSETS", ("manifest-only.js",))

    arguments = build._pyinstaller_arguments(
        repository,
        metadata,
        tmp_path / "dist",
        tmp_path / "work",
    )
    joined = "\n".join(arguments)

    assert "manifest-only.js" in joined
    assert "index.html" not in joined


def test_pyinstaller_arguments_include_only_direct_workbench_imports(tmp_path):
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")

    arguments = build._pyinstaller_arguments(
        REPOSITORY_ROOT,
        metadata,
        tmp_path / "dist",
        tmp_path / "work",
    )
    assert "--collect-data" not in arguments
    assert [
        arguments[index + 1]
        for index, value in enumerate(arguments)
        if value == "--hidden-import"
    ] == ["server", "board_package", "board_geometry"]


@pytest.mark.parametrize("commit", ["A" * 40, "a" * 39, "a" * 41, "not-a-sha"])
def test_commit_must_be_exact_lowercase_sha(commit, tmp_path):
    with pytest.raises(build.BuildError, match="40-character lowercase SHA"):
        build._write_build_metadata(tmp_path, commit)


def test_build_metadata_contains_the_requested_commit_only(tmp_path):
    commit = "b" * 40

    metadata_path = build._write_build_metadata(tmp_path, commit)

    assert metadata_path == tmp_path / "build-commit.txt"
    assert metadata_path.read_bytes() == (commit + "\n").encode("ascii")


def test_expected_output_is_the_onedir_runtime_with_its_executable(tmp_path):
    runtime = tmp_path / "hangboard-workbench"
    runtime.mkdir()
    executable = runtime / "hangboard-workbench"
    executable.write_bytes(b"runtime")
    executable.chmod(0o751)

    assert build._require_expected_output(tmp_path) == runtime


@pytest.mark.parametrize("layout", ["flat", "missing-child"])
def test_expected_output_rejects_incomplete_onedir_runtime(layout, tmp_path):
    runtime = tmp_path / "hangboard-workbench"
    if layout == "flat":
        runtime.write_bytes(b"runtime")
        runtime.chmod(0o751)
    else:
        runtime.mkdir()

    with pytest.raises(build.BuildError, match="onedir runtime"):
        build._require_expected_output(tmp_path)
