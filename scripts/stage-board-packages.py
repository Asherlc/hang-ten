#!/usr/bin/env python3
"""Stage validated direct-child hangboard packages into an app resource bundle."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import stat
import sys
import uuid
from pathlib import Path


def load_board_package_module(repository_root: Path):
    module_path = (
        repository_root
        / "Tools"
        / "HangboardPipeline"
        / "src"
        / "hangboard_vectorizer"
        / "board_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("board_package_staging", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load board package module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _reject_symlinked_ancestors(path: Path, description: str) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as error:
            raise ValueError(f"cannot inspect {description}: {current}") from error
        if stat.S_ISLNK(mode):
            raise ValueError(f"{description} must not contain symlinks: {current}")


def _xcode_resource_root() -> Path:
    target_build_directory = os.environ.get("TARGET_BUILD_DIR")
    resource_folder_path = os.environ.get("UNLOCALIZED_RESOURCES_FOLDER_PATH")
    if not target_build_directory or resource_folder_path is None:
        raise ValueError("destination requires Xcode TARGET_BUILD_DIR and UNLOCALIZED_RESOURCES_FOLDER_PATH")
    relative_resource_folder = Path(resource_folder_path)
    if (
        relative_resource_folder.is_absolute()
        or not relative_resource_folder.parts
        or any(part in {".", ".."} for part in relative_resource_folder.parts)
    ):
        raise ValueError("UNLOCALIZED_RESOURCES_FOLDER_PATH must be a relative Xcode resource path")
    return _absolute_lexical(Path(target_build_directory) / relative_resource_folder)


def _validate_destination(repository_root: Path, destination: Path) -> None:
    resource_root = _xcode_resource_root()
    _reject_symlinked_ancestors(resource_root, "Xcode resource root")
    _reject_symlinked_ancestors(destination, "destination")
    expected_destination = resource_root / "Hangboards"
    if destination != expected_destination:
        raise ValueError(f"destination must equal the Xcode resource Hangboards directory: {expected_destination}")
    for checkout_path in (repository_root / "Hangboards", repository_root / "HangTen"):
        if _is_within(destination, checkout_path):
            raise ValueError(f"destination must not write into the checkout: {destination}")


def _regular_file(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as error:
        raise ValueError(f"cannot inspect package path: {path}") from error
    if not stat.S_ISREG(mode):
        raise ValueError(f"package file must be regular and non-symlinked: {path}")


def _regular_directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as error:
        raise ValueError(f"cannot inspect package path: {path}") from error
    if not stat.S_ISDIR(mode):
        raise ValueError(f"package directory must be regular and non-symlinked: {path}")


def _copy_regular_file(source: Path, destination: Path) -> None:
    _regular_file(source)
    shutil.copyfile(source, destination)
    _regular_file(destination)


def _copy_regular_tree(source: Path, destination: Path) -> None:
    _regular_directory(source)
    destination.mkdir()
    for source_child in sorted(source.iterdir(), key=lambda path: path.name):
        destination_child = destination / source_child.name
        mode = source_child.lstat().st_mode
        if stat.S_ISDIR(mode):
            _copy_regular_tree(source_child, destination_child)
        elif stat.S_ISREG(mode):
            _copy_regular_file(source_child, destination_child)
        else:
            raise ValueError(f"package paths must be regular and non-symlinked: {source_child}")
    _regular_directory(destination)


def _replace_destination(staging: Path, destination: Path) -> None:
    backup = destination.with_name(f".{destination.name}.previous-{uuid.uuid4().hex}")
    replaced_existing_destination = False
    if destination.exists():
        _regular_directory(destination)
        os.replace(destination, backup)
        replaced_existing_destination = True
    try:
        os.replace(staging, destination)
    except BaseException:
        if replaced_existing_destination and not destination.exists():
            os.replace(backup, destination)
        raise
    if replaced_existing_destination:
        # Installing the staged directory is the commit point. A failed
        # best-effort cleanup must not undo or hide the committed destination;
        # the backup remains recoverable alongside it.
        try:
            shutil.rmtree(backup)
        except OSError:
            pass


def stage_board_packages(repository_root: Path, destination: Path) -> tuple[Path, ...]:
    """Copy every validated direct-child package tree into *destination*."""
    repository_root = _absolute_lexical(Path(repository_root))
    destination = _absolute_lexical(Path(destination))
    _reject_symlinked_ancestors(repository_root, "repository root")
    _regular_directory(repository_root)
    _validate_destination(repository_root, destination)

    hangboards_root = repository_root / "Hangboards"
    _reject_symlinked_ancestors(hangboards_root, "Hangboards source root")
    _regular_directory(hangboards_root)
    inventory = load_board_package_module(repository_root).discover_board_packages(
        hangboards_root
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.staging-{uuid.uuid4().hex}")
    try:
        staging.mkdir()
        staged_paths: list[Path] = []
        for package in inventory.packages:
            package_source = package.root
            package_destination = staging / package.root.name
            _copy_regular_tree(package_source, package_destination)
            staged_paths.append(destination / package.root.name)
        _replace_destination(staging, destination)
        return tuple(staged_paths)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    stage_board_packages(arguments.repository_root, arguments.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
