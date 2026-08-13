from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_staging_module():
    module_path = REPO_ROOT / "scripts" / "stage-approved-board-packages.py"
    spec = importlib.util.spec_from_file_location("board_package_staging", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise AssertionError("unable to load board package staging script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    vectorizer_source = REPO_ROOT / "Tools" / "HangboardPipeline" / "src" / "hangboard_vectorizer"
    vectorizer_destination = (
        repository_root
        / "Tools"
        / "HangboardPipeline"
        / "src"
        / "hangboard_vectorizer"
    )
    shutil.copytree(vectorizer_source, vectorizer_destination)
    approved_source = REPO_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii"
    approved_package = hangboards / "approved-board"
    shutil.copytree(approved_source, approved_package)
    catalog = hangboards / "catalog.json"
    catalog.write_bytes(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [
                    {"id": "metolius.wood-grips-compact-ii", "path": "approved-board"},
                ],
            },
            indent=2,
        ).encode("utf-8"),
    )
    return repository_root, catalog, approved_package


def configure_xcode_destination(monkeypatch: pytest.MonkeyPatch, destination: Path) -> None:
    monkeypatch.setenv("TARGET_BUILD_DIR", str(destination.parent.parent))
    monkeypatch.setenv("UNLOCALIZED_RESOURCES_FOLDER_PATH", destination.parent.name)


def test_staging_copies_catalog_package_bytes_and_replaces_stale_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, catalog, approved_package = build_repository(tmp_path)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    (destination / "stale").mkdir(parents=True)
    (destination / "stale" / "previous-build.txt").write_bytes(b"stale")
    sibling_marker = destination.parent / "keep-this-sibling.txt"
    sibling_marker.write_bytes(b"must remain")

    staged = module.stage_board_packages(repository_root, destination)

    assert staged == (destination / "catalog.json", destination / "approved-board")
    assert destination.joinpath("catalog.json").read_bytes() == catalog.read_bytes()
    assert not destination.joinpath("stale").exists()
    assert sibling_marker.read_bytes() == b"must remain"
    for source_path in approved_package.rglob("*"):
        if source_path.is_file():
            relative_path = source_path.relative_to(approved_package)
            assert destination.joinpath("approved-board", relative_path).read_bytes() == source_path.read_bytes()


def test_repeated_staging_refreshes_nested_package_file_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every staging invocation must replace previously staged nested bytes."""
    module = load_staging_module()
    repository_root, _, approved_package = build_repository(tmp_path)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    nested_source = approved_package / "review" / "incremental-marker.txt"
    nested_source.parent.mkdir(exist_ok=True)
    nested_source.write_bytes(b"first nested revision")

    module.stage_board_packages(repository_root, destination)
    nested_destination = destination / "approved-board" / "review" / nested_source.name
    assert nested_destination.read_bytes() == b"first nested revision"

    nested_source.write_bytes(b"second nested revision")
    module.stage_board_packages(repository_root, destination)

    assert nested_destination.read_bytes() == b"second nested revision"


def test_xcode_staging_phase_intentionally_runs_for_every_build() -> None:
    """Always-running staging makes every nested JSON/PNG edit an effective input."""
    project = (REPO_ROOT / "HangTen.xcodeproj" / "project.pbxproj").read_text(
        encoding="utf-8"
    )
    phase_start = project.index(
        "CC0000000000000000000007 /* Stage Approved Board Packages */ = {"
    )
    phase_end = project.index("\n\t\t};", phase_start)
    phase = project[phase_start:phase_end]

    assert "alwaysOutOfDate = 1;" in phase


def test_staging_rejects_symlinked_destination_and_leaves_its_target_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, _, _ = build_repository(tmp_path)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    destination.parent.mkdir(parents=True)
    external_destination = tmp_path / "external-destination"
    external_destination.mkdir()
    marker = external_destination / "must-not-change.txt"
    marker.write_bytes(b"protected")
    destination.symlink_to(external_destination, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        module.stage_board_packages(repository_root, destination)

    assert marker.read_bytes() == b"protected"


def test_staging_rejects_symlinked_destination_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, _, _ = build_repository(tmp_path)
    linked_build = tmp_path / "linked-build"
    linked_build.symlink_to(tmp_path / "external-build", target_is_directory=True)
    destination = linked_build / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)

    with pytest.raises(ValueError, match="symlink"):
        module.stage_board_packages(repository_root, destination)


def test_staging_rejects_symlinked_hangboards_source_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, _, _ = build_repository(tmp_path)
    hangboards = repository_root / "Hangboards"
    external_hangboards = tmp_path / "external-hangboards"
    hangboards.rename(external_hangboards)
    hangboards.symlink_to(external_hangboards, target_is_directory=True)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)

    with pytest.raises(ValueError, match="symlink"):
        module.stage_board_packages(repository_root, destination)


def test_staging_rejects_checkout_and_non_xcode_destinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, _, _ = build_repository(tmp_path)
    checkout_destination = repository_root / "HangTen" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, checkout_destination)

    with pytest.raises(ValueError, match="checkout"):
        module.stage_board_packages(repository_root, checkout_destination)

    trusted_destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, trusted_destination)
    arbitrary_destination = tmp_path / "scratch" / "Hangboards"
    with pytest.raises(ValueError, match="Xcode resource"):
        module.stage_board_packages(repository_root, arbitrary_destination)
