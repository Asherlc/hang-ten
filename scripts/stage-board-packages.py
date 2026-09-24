#!/usr/bin/env python3
"""Stage validated direct-child hangboard packages into an app resource bundle.

Two targets share one loader (``board_catalog.discover_board_packages``):

* ``--target xcode`` (default, the Xcode "Stage Board Packages" phase): the
  destination must be the Xcode resource ``Hangboards`` directory, and each
  package's model asset (``assets/primary.usdz``) is split out into the
  On-Demand Resource staging directory under ``DERIVED_FILE_DIR``.
* ``--target android`` (the Gradle ``stageCanonicalAssets`` task): no Xcode
  environment and no ODR split; model assets stay inline in the package, as the
  Android app bundles them.

For both, a CAD-backed package's FCStd authoring source is never staged, and
its ``board.json`` (generated from the FCStd manifest at build time, never
committed) is written into the staged package.
"""

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
        / "HangboardPackages"
        / "src"
        / "hangboard_packages"
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


def _xcode_odr_staging_root() -> Path:
    derived_file_directory = os.environ.get("DERIVED_FILE_DIR")
    if not derived_file_directory:
        raise ValueError("ODR staging requires Xcode DERIVED_FILE_DIR")
    root = _absolute_lexical(Path(derived_file_directory))
    _reject_symlinked_ancestors(root, "Xcode derived file directory")
    return root / "HangTenModelODR"


TARGET_XCODE = "xcode"
TARGET_ANDROID = "android"
TARGETS = (TARGET_XCODE, TARGET_ANDROID)


def _validate_destination(repository_root: Path, destination: Path, target: str) -> None:
    _reject_symlinked_ancestors(destination, "destination")
    if target == TARGET_XCODE:
        resource_root = _xcode_resource_root()
        _reject_symlinked_ancestors(resource_root, "Xcode resource root")
        expected_destination = resource_root / "Hangboards"
        if destination != expected_destination:
            raise ValueError(f"destination must equal the Xcode resource Hangboards directory: {expected_destination}")
    elif destination.name != "Hangboards":
        raise ValueError(f"destination must be a directory named Hangboards: {destination}")
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


def _iter_regular_children(source: Path):
    """Yield direct children in staging order with one lstat classification."""
    for source_child in sorted(source.iterdir(), key=lambda path: path.name):
        yield source_child, source_child.lstat().st_mode


def _validate_regular_tree(source: Path) -> None:
    """Reject unsupported filesystem entries before creating staging output."""
    _regular_directory(source)
    for source_child, mode in _iter_regular_children(source):
        if stat.S_ISDIR(mode):
            _validate_regular_tree(source_child)
        elif stat.S_ISREG(mode):
            _regular_file(source_child)
        else:
            raise ValueError(
                f"package paths must be regular and non-symlinked: {source_child}"
            )


def _copy_regular_tree(
    source: Path,
    destination: Path,
    excluded_paths: frozenset[Path] = frozenset(),
    relative_path: Path = Path(),
) -> None:
    _regular_directory(source)
    destination.mkdir()
    for source_child, mode in _iter_regular_children(source):
        child_relative_path = relative_path / source_child.name
        if child_relative_path in excluded_paths:
            continue
        destination_child = destination / source_child.name
        if stat.S_ISDIR(mode):
            _copy_regular_tree(
                source_child,
                destination_child,
                excluded_paths,
                child_relative_path,
            )
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


def _resolve_model_asset(
    package_source: Path,
    model_asset_path: Path,
    compiled_assets: Path | None,
    package: str,
) -> Path:
    """Locate a model asset, preferring the committed copy.

    A board whose runtime asset is compiled rather than committed (it has a CAD
    authoring source) will not have the file in its package, so fall back to a
    directory of assets produced by Tools/HangboardCAD/prepare_assets.py.
    """
    committed = package_source / model_asset_path
    if committed.is_file():
        return committed
    if compiled_assets is not None:
        prepared = compiled_assets / package / model_asset_path
        if prepared.is_file():
            return prepared
    raise ValueError(
        f"missing model asset for {package}: {model_asset_path} is neither committed "
        "in the package nor present in --compiled-assets"
    )


def _write_generated_board_json(package_destination: Path, document: bytes) -> None:
    """Write a CAD-backed package's generated board.json into its staged copy."""
    board_destination = package_destination / "board.json"
    if board_destination.exists() or board_destination.is_symlink():
        raise ValueError(f"staged CAD package already has a board.json: {board_destination}")
    board_destination.write_bytes(document)
    _regular_file(board_destination)


def stage_board_packages(
    repository_root: Path,
    destination: Path,
    compiled_assets: Path | None = None,
    target: str = TARGET_XCODE,
) -> tuple[Path, ...]:
    """Copy every validated direct-child package tree into *destination*."""
    if target not in TARGETS:
        raise ValueError(f"unknown staging target: {target!r}")
    split_model_assets = target == TARGET_XCODE
    repository_root = _absolute_lexical(Path(repository_root))
    destination = _absolute_lexical(Path(destination))
    _reject_symlinked_ancestors(repository_root, "repository root")
    _regular_directory(repository_root)
    _validate_destination(repository_root, destination, target)
    odr_destination: Path | None = None
    if split_model_assets:
        odr_destination = _xcode_odr_staging_root()
        _reject_symlinked_ancestors(odr_destination, "ODR staging destination")
        for checkout_path in (repository_root / "Hangboards", repository_root / "HangTen"):
            if _is_within(odr_destination, checkout_path):
                raise ValueError(f"ODR staging must not write into source paths: {odr_destination}")

    hangboards_root = repository_root / "Hangboards"
    _reject_symlinked_ancestors(hangboards_root, "Hangboards source root")
    _regular_directory(hangboards_root)
    package_module = load_board_package_module(repository_root)
    inventory = package_module.discover_board_packages(
        hangboards_root
    )
    package_sources = tuple(package.root for package in inventory.packages)
    for package_source in package_sources:
        if not _is_within(package_source, hangboards_root):
            raise ValueError(f"package must remain beneath Hangboards: {package_source}")
        _validate_regular_tree(package_source)

    model_asset_paths_by_slug: dict[str, frozenset[Path]] = {}
    # The CAD authoring source is neither a runtime resource nor an ODR asset: it
    # must be excluded from the bundle and must NOT be routed to ODR.
    authoring_source_paths_by_slug: dict[str, frozenset[Path]] = {}
    for package in inventory.packages:
        package_root = package.root
        model_asset_paths_by_slug[package.root.name] = frozenset(
            Path(presentation.media.asset_path)
            for presentation in package.board.presentations
            if isinstance(presentation.media, package_module.PresentationMediaModel)
        )
        authoring_source_paths_by_slug[package.root.name] = frozenset(
            path.relative_to(package_root)
            for path in package_root.rglob("*.FCStd")
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.staging-{uuid.uuid4().hex}")
    odr_staging: Path | None = None
    if odr_destination is not None:
        odr_destination.parent.mkdir(parents=True, exist_ok=True)
        odr_staging = odr_destination.with_name(
            f".{odr_destination.name}.staging-{uuid.uuid4().hex}"
        )
    try:
        staging.mkdir()
        if odr_staging is not None:
            odr_staging.mkdir()
        staged_paths: list[Path] = []
        for package, package_source in zip(inventory.packages, package_sources, strict=True):
            package_destination = staging / package.root.name
            model_asset_paths = model_asset_paths_by_slug[package.root.name]
            # Model assets are copied separately below: into the ODR staging
            # tree for Xcode, inline (committed or compiled) for Android.
            _copy_regular_tree(
                package_source,
                package_destination,
                excluded_paths=model_asset_paths
                | authoring_source_paths_by_slug[package.root.name],
            )
            if package.generated_board_json is not None:
                _write_generated_board_json(package_destination, package.generated_board_json)
            for model_asset_path in sorted(model_asset_paths):
                if odr_staging is not None:
                    model_destination = (
                        odr_staging
                        / package.root.name
                        / "Hangboards"
                        / package.root.name
                        / model_asset_path
                    )
                else:
                    model_destination = package_destination / model_asset_path
                model_destination.parent.mkdir(parents=True, exist_ok=True)
                _copy_regular_file(
                    _resolve_model_asset(
                        package_source,
                        model_asset_path,
                        compiled_assets,
                        package.root.name,
                    ),
                    model_destination,
                )
            staged_paths.append(destination / package.root.name)
        _replace_destination(staging, destination)
        if odr_staging is not None and odr_destination is not None:
            _replace_destination(odr_staging, odr_destination)
        return tuple(staged_paths)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        if odr_staging is not None and odr_staging.exists():
            shutil.rmtree(odr_staging)
        raise


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--compiled-assets",
        type=Path,
        default=None,
        help="directory produced by Tools/HangboardCAD/prepare_assets.py, used for "
        "boards whose runtime asset is compiled instead of committed",
    )
    parser.add_argument(
        "--target",
        choices=TARGETS,
        default=TARGET_XCODE,
        help="xcode (default): Xcode resource bundle with the On-Demand Resource model "
        "split; android: plain asset directory with model assets inline",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    stage_board_packages(
        arguments.repository_root,
        arguments.destination,
        arguments.compiled_assets,
        arguments.target,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
