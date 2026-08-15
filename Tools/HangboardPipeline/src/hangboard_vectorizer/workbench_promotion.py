"""Promotion adapters for the workbench's active revision boundary."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import shutil
import stat
from typing import Iterator
from uuid import uuid4

from .board_library import RepositoryBoardLibrary
from .board_catalog import discover_board_packages, load_board_package


@dataclass(frozen=True, slots=True)
class PackagePublication:
    """The canonical files changed by a direct package publication."""

    paths: tuple[Path, ...]


def publish_package_candidate(
    repository_root: Path,
    candidate_root: Path,
    *,
    board_id: str,
) -> PackagePublication:
    """Install one package candidate into the direct-child board library.

    Candidates are copied only into ``Hangboards/<slug>``. Direct discovery is
    the final authority, so no native source or generated registry participates.
    """
    root = Path(repository_root).resolve(strict=True)
    hangboards_root = root / "Hangboards"
    candidate = Path(candidate_root).resolve(strict=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("package candidate must be a regular directory")
    slug = candidate.name
    if not slug or slug != Path(slug).name:
        raise ValueError("package candidate must use a flat directory name")
    if not hangboards_root.is_dir() or hangboards_root.is_symlink():
        raise ValueError("Hangboards directory must be a regular directory")

    with _package_publication_lock(hangboards_root):
        _publish_package_candidate_locked(
            hangboards_root,
            candidate,
            board_id=board_id,
            slug=slug,
        )
    return PackagePublication(
        paths=(Path("Hangboards") / slug,)
    )


@contextmanager
def _package_publication_lock(hangboards_root: Path) -> Iterator[None]:
    """Serialize package replacement transactions on the stable root inode."""
    descriptor = os.open(hangboards_root, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _publish_package_candidate_locked(
    hangboards_root: Path,
    candidate: Path,
    *,
    board_id: str,
    slug: str,
) -> None:
    """Commit one package while holding the direct-library lock."""
    inventory = discover_board_packages(hangboards_root)
    matching_id = [package for package in inventory.packages if package.board.id == board_id]
    if matching_id and matching_id[0].root.name != slug:
        raise ValueError("board ID already belongs to another package directory")

    destination = hangboards_root / slug
    replacing = bool(matching_id)
    if replacing:
        if not destination.is_dir() or destination.is_symlink():
            raise ValueError("canonical package destination must be a regular directory")
    elif destination.exists() or destination.is_symlink():
        raise ValueError("canonical package destination already exists")

    transaction_id = uuid4().hex
    transaction_root = (
        hangboards_root.parent
        / ".context"
        / "hangboard-package-transactions"
        / f"{slug}-{transaction_id}"
    )
    transaction_root.mkdir(parents=True)
    staging = transaction_root / "staging"
    package_backup = transaction_root / "previous"
    package_installed = False
    previous_package_moved = False
    try:
        shutil.copytree(candidate, staging, symlinks=True)
        _require_regular_tree(staging)
        package = load_board_package(staging)
        if package.board.id != board_id:
            raise ValueError("board package ID does not match requested ID")
        if replacing:
            os.replace(destination, package_backup)
            previous_package_moved = True
        os.replace(staging, destination)
        package_installed = True

        discover_board_packages(hangboards_root)
    except BaseException:
        if package_installed and destination.exists():
            shutil.rmtree(destination)
        if previous_package_moved and package_backup.exists():
            os.replace(package_backup, destination)
        _remove_transaction_tree(transaction_root)
        raise
    if previous_package_moved:
        _remove_transaction_tree(package_backup)
    _remove_transaction_tree(transaction_root)


def _remove_transaction_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _require_regular_tree(root: Path) -> None:
    for item in (root, *root.rglob("*")):
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError(f"package candidate contains a symlink: {item}")
        if item == root or item.is_dir():
            if not stat.S_ISDIR(mode):
                raise ValueError(f"package candidate directory is not regular: {item}")
        elif not stat.S_ISREG(mode):
            raise ValueError(f"package candidate file is not regular: {item}")


def repository_root(library: RepositoryBoardLibrary) -> Path:
    """Expose the repository boundary while keeping library internals local here."""
    return _repository_root(library)


def _repository_root(library: RepositoryBoardLibrary) -> Path:
    root = library.repository_root
    if not isinstance(root, Path) or not root.is_dir():
        raise ValueError("repository board library is not configured")
    return root
