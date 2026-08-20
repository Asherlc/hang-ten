from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from conftest import (
    ALTERNATE_PRIMARY_PNG_BYTES,
    PRIMARY_PNG_BYTES,
    write_board_package,
    write_primary_only_draft,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_staging_module():
    module_path = REPO_ROOT / "scripts" / "stage-board-packages.py"
    spec = importlib.util.spec_from_file_location("board_package_staging", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise AssertionError("unable to load board package staging script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_repository(tmp_path: Path) -> tuple[Path, list[Path], Path]:
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    package_source = REPO_ROOT / "Tools" / "HangboardPackages" / "src" / "hangboard_packages"
    package_destination = (
        repository_root / "Tools" / "HangboardPackages" / "src" / "hangboard_packages"
    )
    shutil.copytree(package_source, package_destination)
    packages = [
        write_board_package(
            hangboards / "zeta-model",
            board_id="zeta.board",
            manufacturer="Zeta",
            name="Model",
        ),
        write_board_package(
            hangboards / "alpha-model",
            board_id="alpha.board",
            manufacturer="Alpha",
            name="Model",
        ),
    ]
    draft = write_primary_only_draft(hangboards / "draft-model")
    return repository_root, packages, draft


def configure_xcode_destination(monkeypatch: pytest.MonkeyPatch, destination: Path) -> None:
    monkeypatch.setenv("TARGET_BUILD_DIR", str(destination.parent.parent))
    monkeypatch.setenv("UNLOCALIZED_RESOURCES_FOLDER_PATH", destination.parent.name)


def test_staging_copies_discovered_packages_without_a_registry_and_replaces_stale_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, packages, draft = build_repository(tmp_path)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    (destination / "stale").mkdir(parents=True)
    (destination / "stale" / "previous.txt").write_bytes(b"stale")
    sibling = destination.parent / "keep.txt"
    sibling.write_bytes(b"keep")

    staged = module.stage_board_packages(repository_root, destination)

    assert staged == (destination / "alpha-model", destination / "zeta-model")
    assert {path.name for path in destination.iterdir()} == {"alpha-model", "zeta-model"}
    assert not (destination / "catalog.json").exists()
    assert not (destination / draft.name).exists()
    assert sibling.read_bytes() == b"keep"
    for source_package in packages:
        relative_files = {
            path.relative_to(source_package).as_posix(): path.read_bytes()
            for path in source_package.rglob("*")
            if path.is_file()
        }
        assert relative_files == {
            "assets/primary.png": PRIMARY_PNG_BYTES,
            "board.json": (source_package / "board.json").read_bytes(),
        }
        for relative, expected in relative_files.items():
            assert (destination / source_package.name / relative).read_bytes() == expected


def test_repeated_staging_refreshes_nested_package_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, packages, _ = build_repository(tmp_path)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    primary = packages[0] / "assets" / "primary.png"
    primary.write_bytes(PRIMARY_PNG_BYTES)
    module.stage_board_packages(repository_root, destination)
    staged_primary = destination / packages[0].name / "assets" / "primary.png"
    assert staged_primary.read_bytes() == PRIMARY_PNG_BYTES

    primary.write_bytes(ALTERNATE_PRIMARY_PNG_BYTES)
    module.stage_board_packages(repository_root, destination)

    assert staged_primary.read_bytes() == ALTERNATE_PRIMARY_PNG_BYTES


def test_staging_fails_closed_for_a_malformed_completed_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, packages, _ = build_repository(tmp_path)
    document = json.loads((packages[0] / "board.json").read_text(encoding="utf-8"))
    document["holds"][0]["geometry"] = []
    (packages[0] / "board.json").write_text(json.dumps(document), encoding="utf-8")
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)

    with pytest.raises(ValueError, match="geometry"):
        module.stage_board_packages(repository_root, destination)

    assert not destination.exists()


def test_staging_rejects_symlinked_destination_and_leaves_target_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, _, _ = build_repository(tmp_path)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    destination.parent.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    marker = external / "protected.txt"
    marker.write_bytes(b"protected")
    destination.symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        module.stage_board_packages(repository_root, destination)

    assert marker.read_bytes() == b"protected"


def test_staging_rejects_symlinked_source_and_destination_ancestors(
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

    hangboards.unlink()
    external_hangboards.rename(hangboards)
    linked_build = tmp_path / "linked-build"
    linked_build.symlink_to(tmp_path / "external-build", target_is_directory=True)
    linked_destination = linked_build / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, linked_destination)

    with pytest.raises(ValueError, match="symlink"):
        module.stage_board_packages(repository_root, linked_destination)


def test_staging_rejects_checkout_and_non_xcode_destinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, _, _ = build_repository(tmp_path)
    checkout = repository_root / "HangTen" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, checkout)
    with pytest.raises(ValueError, match="checkout"):
        module.stage_board_packages(repository_root, checkout)

    trusted = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, trusted)
    with pytest.raises(ValueError, match="Xcode resource"):
        module.stage_board_packages(repository_root, tmp_path / "scratch" / "Hangboards")


def test_xcode_staging_phase_intentionally_runs_for_every_build() -> None:
    project = (REPO_ROOT / "HangTen.xcodeproj" / "project.pbxproj").read_text(
        encoding="utf-8"
    )
    phase_start = project.index("CC0000000000000000000007 /* Stage Board Packages */ = {")
    phase_end = project.index("\n\t\t};", phase_start)
    assert "alwaysOutOfDate = 1;" in project[phase_start:phase_end]
