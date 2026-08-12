#!/usr/bin/env python3
"""Stage validated, approved hangboard packages into an app resource bundle."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import stat
import sys
import uuid
from pathlib import Path


def load_board_catalog_module(repository_root: Path):
    module_path = (
        repository_root
        / "Tools"
        / "HangboardPipeline"
        / "src"
        / "hangboard_vectorizer"
        / "board_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("approved_board_package_staging", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load board catalog module from {module_path}")
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


def _validate_destination(repository_root: Path, destination: Path) -> None:
    if destination.name != "Hangboards":
        raise ValueError("destination must be the app resource Hangboards directory")
    for checkout_path in (repository_root / "Hangboards", repository_root / "HangTen"):
        if _is_within(destination, checkout_path):
            raise ValueError(f"destination must not write into the checkout: {destination}")
    if destination.is_symlink():
        raise ValueError(f"destination must not be a symlink: {destination}")


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
        shutil.rmtree(backup)


def stage_approved_packages(repository_root: Path, destination: Path) -> tuple[Path, ...]:
    """Copy the validated catalog and approved package trees into *destination*."""
    repository_root = Path(repository_root).resolve(strict=True)
    destination = Path(destination).resolve(strict=False)
    _validate_destination(repository_root, destination)

    catalog_path = repository_root / "Hangboards" / "catalog.json"
    _regular_file(catalog_path)
    catalog = load_board_catalog_module(repository_root).validate_catalog(catalog_path)

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.staging-{uuid.uuid4().hex}")
    try:
        staging.mkdir()
        _copy_regular_file(catalog_path, staging / "catalog.json")
        staged_paths: list[Path] = [destination / "catalog.json"]
        for entry in catalog.entries:
            if entry.status != "approved":
                continue
            package_source = catalog_path.parent / entry.path
            package_destination = staging / entry.path
            _copy_regular_tree(package_source, package_destination)
            staged_paths.append(destination / entry.path)
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
    stage_approved_packages(arguments.repository_root, arguments.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
