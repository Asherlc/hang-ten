"""Promotion adapters for the workbench's active revision boundary."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat
from typing import Iterator
from uuid import uuid4

from .board_library import RepositoryBoardLibrary
from .board_catalog import load_approved_package, validate_catalog


_PACKAGE_STATUSES = frozenset({"draft", "approved"})


@dataclass(frozen=True, slots=True)
class PackagePublication:
    """The canonical files changed by a direct package publication."""

    paths: tuple[Path, ...]


def publish_package_candidate(
    repository_root: Path,
    candidate_root: Path,
    *,
    board_id: str,
    status: str,
) -> PackagePublication:
    """Install one reviewed package candidate and register its shipping status.

    Candidates are copied only into ``Hangboards/<slug>``.  The catalog
    validator is the final authority, so no native source, Xcode asset, or
    legacy board-library artifact participates in this publication path.
    """
    if status not in _PACKAGE_STATUSES:
        raise ValueError("status must be either 'draft' or 'approved'")
    root = Path(repository_root).resolve(strict=True)
    hangboards_root = root / "Hangboards"
    catalog_path = hangboards_root / "catalog.json"
    candidate = Path(candidate_root).resolve(strict=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("package candidate must be a regular directory")
    slug = candidate.name
    if not slug or slug != Path(slug).name:
        raise ValueError("package candidate must use a flat directory name")
    if not hangboards_root.is_dir() or hangboards_root.is_symlink():
        raise ValueError("Hangboards directory must be a regular directory")
    if not catalog_path.is_file() or catalog_path.is_symlink():
        raise ValueError("Hangboards/catalog.json must be a regular file")

    with _catalog_publication_lock(hangboards_root):
        _publish_package_candidate_locked(
            hangboards_root,
            catalog_path,
            candidate,
            board_id=board_id,
            slug=slug,
            status=status,
        )
    return PackagePublication(
        paths=(Path("Hangboards/catalog.json"), Path("Hangboards") / slug)
    )


@contextmanager
def _catalog_publication_lock(hangboards_root: Path) -> Iterator[None]:
    """Serialize every package/catalog transaction on the stable root inode."""
    descriptor = os.open(hangboards_root, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _publish_package_candidate_locked(
    hangboards_root: Path,
    catalog_path: Path,
    candidate: Path,
    *,
    board_id: str,
    slug: str,
    status: str,
) -> None:
    """Commit one package and its catalog entry while holding the catalog lock."""
    validate_catalog(catalog_path)
    existing = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(existing, dict) or set(existing) != {"schemaVersion", "boards"}:
        raise ValueError("catalog.json must contain schemaVersion and boards")
    entries = existing.get("boards")
    if not isinstance(entries, list):
        raise ValueError("catalog.json boards must be an array")

    matching_id = [index for index, entry in enumerate(entries) if entry["id"] == board_id]
    matching_path = [index for index, entry in enumerate(entries) if entry["path"] == slug]
    replacing = bool(matching_id or matching_path)
    if replacing and (matching_id != matching_path or len(matching_id) != 1):
        raise ValueError("catalog already contains the package ID or path")

    updated_entry = {"id": board_id, "path": slug, "status": status}
    if replacing:
        updated_entries = list(entries)
        updated_entries[matching_id[0]] = updated_entry
    else:
        updated_entries = [*entries, updated_entry]

    destination = hangboards_root / slug
    if replacing:
        if not destination.is_dir() or destination.is_symlink():
            raise ValueError("canonical package destination must be a regular directory")
    elif destination.exists() or destination.is_symlink():
        raise ValueError("canonical package destination already exists")

    transaction_id = uuid4().hex
    staging = hangboards_root / f".{slug}.staging-{transaction_id}"
    package_backup = hangboards_root / f".{slug}.previous-{transaction_id}"
    catalog_staging = hangboards_root / f".catalog.json.staging-{transaction_id}"
    package_installed = False
    previous_package_moved = False
    catalog_committed = False
    try:
        shutil.copytree(candidate, staging, symlinks=True)
        _require_regular_tree(staging)
        if status == "approved":
            package = load_approved_package(staging)
            if package.board.id != board_id:
                raise ValueError("approved package board ID does not match registry ID")

        updated_catalog = {
            "schemaVersion": existing["schemaVersion"],
            "boards": updated_entries,
        }
        _write_new_file(
            catalog_staging,
            (json.dumps(updated_catalog, indent=2) + "\n").encode("utf-8"),
        )
        if replacing:
            os.replace(destination, package_backup)
            previous_package_moved = True
        os.replace(staging, destination)
        package_installed = True

        # Validate the proposed catalog against the newly installed canonical tree.
        # The live catalog stays untouched until this check has fully succeeded.
        validate_catalog(catalog_staging)
        os.replace(catalog_staging, catalog_path)
        catalog_committed = True
    except BaseException:
        if not catalog_committed:
            if package_installed and destination.exists():
                shutil.rmtree(destination)
            if previous_package_moved and package_backup.exists():
                os.replace(package_backup, destination)
        _remove_transaction_tree(staging)
        if catalog_staging.exists():
            catalog_staging.unlink()
        raise
    if previous_package_moved:
        _remove_transaction_tree(package_backup)


def _write_new_file(path: Path, contents: bytes) -> None:
    with path.open("xb") as output:
        output.write(contents)
        output.flush()
        os.fsync(output.fileno())


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
