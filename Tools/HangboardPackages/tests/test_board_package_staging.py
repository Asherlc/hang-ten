from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from conftest import (
    ALTERNATE_PRIMARY_PNG_BYTES,
    PRIMARY_PNG_HEIGHT,
    PRIMARY_PNG_BYTES,
    PRIMARY_PNG_WIDTH,
    SECONDARY_PNG_BYTES,
    write_board_package,
    write_multi_presentation_board_package,
    write_primary_only_draft,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_BYTES = b"staging fixture model bytes\x00\xff"
LIVE_MODEL_PACKAGE_SLUGS = (
    "beastmaker-1000",
    "metolius-wood-grips-compact-ii",
    "tension-flash-board",
)


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


def make_v2_model_package(root: Path) -> Path:
    """Write a complete, parser-valid v2 model package without shared fixtures."""
    assets = root / "assets"
    assets.mkdir(parents=True)
    (assets / "primary.usdz").write_bytes(MODEL_BYTES)
    descriptor = {
        "schemaVersion": 1,
        "coordinateFrame": "hang-ten-board-v1",
        "modelSHA256": hashlib.sha256(MODEL_BYTES).hexdigest(),
        "modelBounds": {"min": [0, 0, 0], "max": [1, 1, 0.1]},
        "nodes": [
            {"nodeID": "Body", "role": "body"},
            {"nodeID": "Left", "role": "hold", "holdID": "hold-left"},
            {"nodeID": "Right", "role": "hold", "holdID": "hold-right"},
        ],
        "holds": {
            "hold-left": {
                "nodeIDs": ["Left"],
                "facePlaneAABB": {"min": [0.1, 0.2], "max": [0.4, 0.6]},
                "center": [0.25, 0.4],
            },
            "hold-right": {
                "nodeIDs": ["Right"],
                "facePlaneAABB": {"min": [0.6, 0.2], "max": [0.9, 0.6]},
                "center": [0.75, 0.4],
            },
        },
    }
    board = {
        "schemaVersion": 2,
        "id": "fixture.model",
        "manufacturer": "Fixture Maker",
        "name": "Model fixture",
        "subtitle": "A typed-media staging fixture.",
        "productURL": "https://example.com/fixture-model",
        "aspectRatio": 2,
        "presentations": [
            {
                "id": "primary",
                "name": "Primary",
                "aspectRatio": 2,
                "isDefault": True,
                "derivation": {"type": "original"},
                "media": {
                    "type": "model",
                    "assetPath": "assets/primary.usdz",
                    "descriptorPath": "assets/primary.model.json",
                    "display": {
                        "camera": {
                            "type": "orthographic",
                            "viewDirection": [0, 0, -1],
                            "up": [0, 1, 0],
                            "fitPadding": 0.08,
                        }
                    },
                },
            }
        ],
        "holds": [
            {"id": "hold-left", "name": "Left hold", "kind": "jug"},
            {"id": "hold-right", "name": "Right hold", "kind": "jug"},
        ],
    }
    (assets / "primary.model.json").write_text(
        json.dumps(descriptor), encoding="utf-8"
    )
    (root / "board.json").write_text(json.dumps(board), encoding="utf-8")
    return root


def stage_with_xcode_environment(
    source: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Stage the fixture's repository and return its staged package root."""
    repository_root = source.parents[1]
    package_source = REPO_ROOT / "Tools" / "HangboardPackages" / "src" / "hangboard_packages"
    package_destination = (
        repository_root / "Tools" / "HangboardPackages" / "src" / "hangboard_packages"
    )
    shutil.copytree(package_source, package_destination)
    destination = source.parents[2] / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    staged = load_staging_module().stage_board_packages(repository_root, destination)
    assert staged == (destination / source.name,)
    return staged[0]


def stage_live_model_packages(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """Stage the promoted model packages in an isolated build resource root."""
    repository_root = root / "repository"
    hangboards = repository_root / "Hangboards"
    hangboards.mkdir(parents=True)
    for slug in LIVE_MODEL_PACKAGE_SLUGS:
        shutil.copytree(REPO_ROOT / "Hangboards" / slug, hangboards / slug)
    package_source = REPO_ROOT / "Tools" / "HangboardPackages" / "src" / "hangboard_packages"
    shutil.copytree(
        package_source,
        repository_root / "Tools" / "HangboardPackages" / "src" / "hangboard_packages",
    )

    destination = root / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    module = load_staging_module()
    staged = module.stage_board_packages(repository_root, destination)
    assert tuple(path.name for path in staged) == tuple(
        sorted(LIVE_MODEL_PACKAGE_SLUGS)
    )
    return repository_root, destination, module


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
            if path.is_file() and not path.is_symlink()
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
    board_path = packages[0] / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    alternate_aspect_ratio = (PRIMARY_PNG_WIDTH + 2) / (PRIMARY_PNG_HEIGHT + 2)
    board["aspectRatio"] = alternate_aspect_ratio
    board["presentations"][0]["aspectRatio"] = alternate_aspect_ratio
    board_path.write_text(json.dumps(board), encoding="utf-8")
    module.stage_board_packages(repository_root, destination)

    assert staged_primary.read_bytes() == ALTERNATE_PRIMARY_PNG_BYTES


def test_staging_copies_the_exact_declared_asset_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root = tmp_path / "repository"
    hangboards = repository_root / "Hangboards"
    package_source = REPO_ROOT / "Tools" / "HangboardPackages" / "src" / "hangboard_packages"
    package_destination = (
        repository_root / "Tools" / "HangboardPackages" / "src" / "hangboard_packages"
    )
    shutil.copytree(package_source, package_destination)
    package = write_multi_presentation_board_package(hangboards / "dual-model")
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)

    module.stage_board_packages(repository_root, destination)

    staged_assets = destination / package.name / "assets"
    assert {path.name for path in staged_assets.iterdir()} == {"primary.png", "back.png"}
    assert (staged_assets / "primary.png").read_bytes() == PRIMARY_PNG_BYTES
    assert (staged_assets / "back.png").read_bytes() == SECONDARY_PNG_BYTES


def test_staging_copies_model_and_hash_bound_descriptor_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_v2_model_package(
        tmp_path / "repository" / "Hangboards" / "fixture-model"
    )

    staged = stage_with_xcode_environment(source, monkeypatch)

    assert (staged / "assets" / "primary.usdz").read_bytes() == (
        source / "assets" / "primary.usdz"
    ).read_bytes()
    assert (staged / "assets" / "primary.model.json").read_bytes() == (
        source / "assets" / "primary.model.json"
    ).read_bytes()
    assert {
        path.relative_to(staged).as_posix()
        for path in staged.rglob("*")
        if path.is_file() and not path.is_symlink()
    } == {"assets/primary.usdz", "assets/primary.model.json", "board.json"}


def test_staging_preserves_live_model_package_assets_and_hash_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, destination, module = stage_live_model_packages(
        tmp_path, monkeypatch
    )
    parser_module = module.load_board_package_module(repository_root)
    inventory = parser_module.discover_board_packages(
        repository_root / "Hangboards",
        require_complete_inventory=True,
    )
    packages = {package.root.name: package for package in inventory.packages}

    for slug in LIVE_MODEL_PACKAGE_SLUGS:
        source_package = repository_root / "Hangboards" / slug
        staged_package = destination / slug
        package = packages[slug]
        model_presentations = [
            presentation
            for presentation in package.board.presentations
            if isinstance(presentation.media, parser_module.PresentationMediaModel)
        ]
        assert len(model_presentations) == 1
        media = model_presentations[0].media
        declared_assets = {media.asset_path, media.descriptor_path}
        source_assets = {
            path.relative_to(source_package).as_posix()
            for path in source_package.rglob("*")
            if path.is_file() and not path.is_symlink() and path.relative_to(source_package).parts[:1] == ("assets",)
        }
        staged_assets = {
            path.relative_to(staged_package).as_posix()
            for path in staged_package.rglob("*")
            if path.is_file() and not path.is_symlink() and path.relative_to(staged_package).parts[:1] == ("assets",)
        }
        assert source_assets == declared_assets
        assert staged_assets == declared_assets
        for relative_path in declared_assets:
            assert (staged_package / relative_path).read_bytes() == (
                source_package / relative_path
            ).read_bytes()

        descriptor = json.loads(
            (staged_package / media.descriptor_path).read_text(encoding="utf-8")
        )
        assert descriptor["modelSHA256"] == hashlib.sha256(
            (staged_package / media.asset_path).read_bytes()
        ).hexdigest()


def test_staging_preserves_every_live_model_package_file_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, destination, _ = stage_live_model_packages(tmp_path, monkeypatch)
    for slug in LIVE_MODEL_PACKAGE_SLUGS:
        source_package = repository_root / "Hangboards" / slug
        staged_package = destination / slug
        source_files = {
            path.relative_to(source_package).as_posix(): path.read_bytes()
            for path in source_package.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        staged_files = {
            path.relative_to(staged_package).as_posix(): path.read_bytes()
            for path in staged_package.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        assert staged_files == source_files


def test_staging_preflights_recursive_file_types_before_creating_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, packages, _ = build_repository(tmp_path)
    special_path = packages[0] / "assets" / "nested-special"
    os.mkfifo(special_path)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)

    with pytest.raises(ValueError, match="regular and non-symlinked"):
        module.stage_board_packages(repository_root, destination)

    assert not destination.exists()
    assert not destination.parent.exists()


def test_staging_rejects_nested_symlink_before_copying_any_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_staging_module()
    repository_root, packages, _ = build_repository(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"must not be copied")
    (packages[0] / "assets" / "nested-link").symlink_to(outside)
    destination = tmp_path / "Build" / "HangTen.app" / "Hangboards"
    configure_xcode_destination(monkeypatch, destination)

    with pytest.raises(ValueError, match="symlink"):
        module.stage_board_packages(repository_root, destination)

    assert not destination.exists()
    assert not destination.parent.exists()


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
