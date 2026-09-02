"""Deterministic evidence and transparency gates for cord-render candidates.

Atlas construction is lossless input preparation. Chroma removal plus its
narrow boundary-edge decontamination is the only output transform here.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import secrets
import stat
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from enum import Enum
from pathlib import Path

import PIL
from PIL import Image, UnidentifiedImageError

_TOOL_VERSION = "cord-render-assets/5"
_SCHEMA_VERSION = 2
_DIGEST_VERSION = 1
_OWNER_PREFIX = "joyful-donkey-"
_ATLAS_BASE_DIMENSION = 2048
_ATLAS_PADDING = 8
_ATLAS_NEUTRAL_RGBA = (128, 128, 128, 255)
_ATLAS_PACKING_ALGORITHM = "maxrects-bottom-left-exact-mode-aware/2"
_ATLAS_SEARCH_NODE_LIMIT = 250_000
_ATLAS_MODES = frozenset({"RGB", "RGBA"})
_OPAQUE_FLOOD_MIN_PIXELS = 16
_OPAQUE_FLOOD_MIN_AREA_FRACTION = 0.05
_OPAQUE_FLOOD_MIN_BOUNDARY_FRACTION = 0.10
_MATTE_MIN_MEAN_OPACITY = 0.95
_INSET_MATTE_MIN_EFFECTIVE_AREA = 0.70
_INSET_MATTE_MIN_ALPHA_FILL = 0.85
_INSET_MATTE_MIN_DENSE_AXIS_FRACTION = 0.80
_INSET_MATTE_DENSE_LINE_FRACTION = 0.90
_INSET_MATTE_CORE_PERIMETER = 3
_INSET_MATTE_DEFICIT_WEIGHT = 18.0
_INSET_MATTE_MAX_DEFICIT_BOOST = 0.10
_SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ATLAS_PAGE_NAME = re.compile(r"page-([0-9]{2})\.png\Z")

_DIRECTORY_FLAGS = os.O_RDONLY
if hasattr(os, "O_DIRECTORY"):
    _DIRECTORY_FLAGS |= os.O_DIRECTORY
if hasattr(os, "O_NOFOLLOW"):
    _DIRECTORY_FLAGS |= os.O_NOFOLLOW
if hasattr(os, "O_CLOEXEC"):
    _DIRECTORY_FLAGS |= os.O_CLOEXEC

_READ_FLAGS = os.O_RDONLY
if hasattr(os, "O_NOFOLLOW"):
    _READ_FLAGS |= os.O_NOFOLLOW
if hasattr(os, "O_CLOEXEC"):
    _READ_FLAGS |= os.O_CLOEXEC

_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL
if hasattr(os, "O_NOFOLLOW"):
    _CREATE_FLAGS |= os.O_NOFOLLOW
if hasattr(os, "O_CLOEXEC"):
    _CREATE_FLAGS |= os.O_CLOEXEC


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


@dataclass
class _HeldParent:
    path: Path
    parent_fd: int
    leaf: str
    chain: tuple[tuple[str, int, int], ...]
    created_directories: tuple[Path, ...] = ()

    def close(self) -> None:
        if self.parent_fd >= 0:
            os.close(self.parent_fd)
            self.parent_fd = -1


@dataclass
class _CreatedDirectory:
    path: Path
    parent_fd: int
    name: str
    created: bool = False
    identity: tuple[int, int] | None = None

    def close(self) -> None:
        if self.parent_fd >= 0:
            os.close(self.parent_fd)
            self.parent_fd = -1


def _path_parts(path: Path) -> tuple[Path, tuple[str, ...]]:
    absolute = _absolute(path)
    if not absolute.is_absolute() or absolute == Path(absolute.anchor):
        raise ValueError(f"path must identify a leaf: {absolute}")
    parts = absolute.parts[1:]
    if not parts or any(part in {"", ".", ".."} or "/" in part for part in parts):
        raise ValueError(f"path contains an unsafe component: {absolute}")
    return absolute, parts


def _open_parent(
    path: Path,
    *,
    create: bool = False,
    creation_ledger: list[_CreatedDirectory] | None = None,
) -> _HeldParent:
    absolute, parts = _path_parts(path)
    descriptor = -1
    owns_ledger = creation_ledger is None
    ledger = creation_ledger if creation_ledger is not None else []
    created_paths: list[Path] = []
    current = Path(absolute.anchor)
    try:
        descriptor = os.open(absolute.anchor, _DIRECTORY_FLAGS)
        root_metadata = os.fstat(descriptor)
        chain: list[tuple[str, int, int]] = [
            (absolute.anchor, root_metadata.st_dev, root_metadata.st_ino)
        ]
        for component in parts[:-1]:
            current /= component
            try:
                next_descriptor = os.open(
                    component, _DIRECTORY_FLAGS, dir_fd=descriptor
                )
            except FileNotFoundError:
                if not create:
                    raise
                creation = _CreatedDirectory(
                    current,
                    os.dup(descriptor),
                    component,
                )
                ledger.append(creation)
                try:
                    os.mkdir(component, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    ledger.remove(creation)
                    creation.close()
                else:
                    creation.created = True
                    created_paths.append(current)
                next_descriptor = os.open(
                    component, _DIRECTORY_FLAGS, dir_fd=descriptor
                )
            except OSError as error:
                raise ValueError(
                    f"symlink or non-directory path component is rejected: {current}"
                ) from error
            metadata = os.fstat(next_descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(next_descriptor)
                raise ValueError(f"path component is not a directory: {current}")
            if create and ledger:
                latest = ledger[-1]
                if latest.path == current and latest.created:
                    latest.identity = _identity(metadata)
            chain.append((component, metadata.st_dev, metadata.st_ino))
            os.close(descriptor)
            descriptor = next_descriptor
        anchor = _HeldParent(
            absolute,
            descriptor,
            parts[-1],
            tuple(chain),
            tuple(created_paths),
        )
        descriptor = -1
        return anchor
    except BaseException as error:
        if descriptor >= 0:
            os.close(descriptor)
            descriptor = -1
        if owns_ledger:
            failures = _rollback_created_directories(ledger)
            if failures:
                raise RuntimeError(
                    "rollback state is unproven: " + "; ".join(failures)
                ) from error
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if owns_ledger:
            for creation in ledger:
                creation.close()


def _revalidate_anchor(
    anchor: _HeldParent,
    *,
    leaf_identity: tuple[int, int] | None = None,
) -> None:
    descriptor = os.open(anchor.path.anchor, _DIRECTORY_FLAGS)
    try:
        root = os.fstat(descriptor)
        expected_root = anchor.chain[0]
        if _identity(root) != (expected_root[1], expected_root[2]):
            raise ValueError(f"path changed during operation: {anchor.path}")
        for component, expected_device, expected_inode in anchor.chain[1:]:
            try:
                next_descriptor = os.open(
                    component, _DIRECTORY_FLAGS, dir_fd=descriptor
                )
            except OSError as error:
                raise ValueError(
                    f"path changed during operation: {anchor.path}"
                ) from error
            metadata = os.fstat(next_descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
            if _identity(metadata) != (expected_device, expected_inode):
                raise ValueError(f"path changed during operation: {anchor.path}")
        if _identity(os.fstat(descriptor)) != _identity(os.fstat(anchor.parent_fd)):
            raise ValueError(f"path changed during operation: {anchor.path}")
        if leaf_identity is not None:
            try:
                metadata = os.stat(
                    anchor.leaf, dir_fd=descriptor, follow_symlinks=False
                )
            except OSError as error:
                raise ValueError(
                    f"path changed during operation: {anchor.path}"
                ) from error
            if stat.S_ISLNK(metadata.st_mode) or _identity(metadata) != leaf_identity:
                raise ValueError(f"path changed during operation: {anchor.path}")
    finally:
        os.close(descriptor)


def _reject_symlink_components(path: Path) -> None:
    absolute = _absolute(path)
    try:
        anchor = _open_parent(absolute)
    except FileNotFoundError:
        return
    try:
        try:
            metadata = os.stat(
                anchor.leaf, dir_fd=anchor.parent_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlink path components are rejected: {absolute}")
        _revalidate_anchor(anchor)
    finally:
        anchor.close()


def _owner_context(path: Path) -> Path:
    absolute = _absolute(path)
    parts = absolute.parts
    for index, part in enumerate(parts):
        if (
            part == ".context"
            and index + 1 < len(parts)
            and parts[index + 1].startswith(_OWNER_PREFIX)
            and len(parts[index + 1]) > len(_OWNER_PREFIX)
        ):
            root = Path(*parts[: index + 2])
            if absolute == root:
                raise ValueError("output path must be below its owner context")
            try:
                anchor = _open_parent(root / ".owner-root-check")
            except FileNotFoundError:
                return root
            try:
                _revalidate_anchor(anchor)
            finally:
                anchor.close()
            return root
    raise ValueError(
        "path must be inside an owner-named .context/joyful-donkey-* directory"
    )


def _maybe_owner_context(path: Path) -> Path | None:
    try:
        return _owner_context(path)
    except ValueError as error:
        if "owner-named .context" not in str(error):
            raise
        return None


def _workspace_root() -> Path:
    configured = os.environ.get("PASEO_WORKTREE_PATH")
    if configured:
        root = _absolute(Path(configured))
        _reject_symlink_components(root)
        return root
    return Path(__file__).resolve().parents[4]


def _read_regular_bytes(path: Path, label: str) -> tuple[Path, bytes, os.stat_result]:
    absolute = _absolute(path)
    try:
        anchor = _open_parent(absolute)
    except (FileNotFoundError, OSError) as error:
        raise ValueError(f"unable to read {label}: {absolute}") from error
    descriptor = -1
    try:
        try:
            descriptor = os.open(anchor.leaf, _READ_FLAGS, dir_fd=anchor.parent_fd)
        except OSError as error:
            raise ValueError(f"unable to read {label}: {absolute}") from error
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"expected a readable regular file: {absolute}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            _identity(before) != _identity(after)
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise ValueError(f"source changed while it was being read: {absolute}")
        data = b"".join(chunks)
        if len(data) != before.st_size:
            raise ValueError(f"source changed while it was being read: {absolute}")
        _revalidate_anchor(anchor, leaf_identity=_identity(before))
        return absolute, data, before
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        anchor.close()


def _existing_leaf_metadata(path: Path) -> os.stat_result | None:
    absolute = _absolute(path)
    try:
        anchor = _open_parent(absolute)
    except FileNotFoundError:
        return None
    try:
        try:
            metadata = os.stat(
                anchor.leaf, dir_fd=anchor.parent_fd, follow_symlinks=False
            )
        except FileNotFoundError:
            _revalidate_anchor(anchor)
            return None
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlink path components are rejected: {absolute}")
        _revalidate_anchor(anchor, leaf_identity=_identity(metadata))
        return metadata
    finally:
        anchor.close()


@dataclass(frozen=True)
class PathRole:
    name: str
    path: Path
    kind: str  # input, output, or directory


def preflight_path_roles(roles: Sequence[PathRole]) -> None:
    lexical: dict[Path, str] = {}
    identities: dict[tuple[int, int], str] = {}
    for role in roles:
        absolute = _absolute(role.path)
        if absolute in lexical:
            raise ValueError(f"path roles alias: {lexical[absolute]} and {role.name}")
        lexical[absolute] = role.name
        if role.kind in {"output", "directory"}:
            _owner_context(absolute)
        metadata = _existing_leaf_metadata(absolute)
        if role.kind == "input":
            if metadata is None or not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"input must be a regular file: {role.name}")
        elif role.kind == "output":
            if metadata is not None and not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    f"output target must be absent or a regular file: {absolute.name}"
                )
        elif role.kind == "directory":
            if metadata is not None and not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(
                    f"output directory target is not a directory: {absolute.name}"
                )
        else:
            raise ValueError(f"unknown path role kind: {role.kind}")
        if metadata is not None:
            identity = _identity(metadata)
            if identity in identities:
                raise ValueError(
                    f"path roles alias: {identities[identity]} and {role.name}"
                )
            identities[identity] = role.name


@dataclass(frozen=True)
class _LeafExpectation:
    identity: tuple[int, int]
    payload: bytes
    byte_sha256: str


@dataclass(frozen=True)
class _Publication:
    path: Path
    payload: bytes | None
    role: str
    expected_prior: _LeafExpectation | None = None


class _PublicationPhase(Enum):
    UNTOUCHED = "untouched"
    EXPECTED_ABSENT = "expected-absent"
    PRIOR_CAPTURED = "prior-captured"
    NEW_VISIBLE = "new-visible"
    EXTERNAL_CAPTURED = "external-captured"


@dataclass
class _ScratchLeaf:
    name: str
    purpose: str
    present: bool = False
    identity: tuple[int, int] | None = None
    payload: bytes | None = None
    removable: bool = False


@dataclass
class _StagedPublication:
    publication: _Publication
    anchor: _HeldParent
    phase: _PublicationPhase = _PublicationPhase.UNTOUCHED
    prior_payload: bytes | None = None
    prior_identity: tuple[int, int] | None = None
    temporary: _ScratchLeaf | None = None
    prior: _ScratchLeaf | None = None
    scratch_name: str | None = None
    scratch_fd: int = -1
    scratch_identity: tuple[int, int] | None = None
    scratch_created: bool = False
    scratch_leaves: list[_ScratchLeaf] = field(default_factory=list)

    def close(self) -> None:
        if self.scratch_fd >= 0:
            os.close(self.scratch_fd)
            self.scratch_fd = -1
        self.anchor.close()


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("short write while staging artifact")
        offset += written
    os.fsync(descriptor)


def _read_from_fd(
    parent_fd: int,
    name: str,
    *,
    label: str = "artifact",
) -> tuple[bytes, os.stat_result]:
    descriptor = os.open(name, _READ_FLAGS, dir_fd=parent_fd)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"{label} is not regular: {name}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        payload = b"".join(chunks)
        if (
            _identity(before) != _identity(after)
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or len(payload) != before.st_size
        ):
            raise ValueError(f"{label} changed while it was being read: {name}")
        return payload, before
    finally:
        os.close(descriptor)


def _read_relative(anchor: _HeldParent, name: str) -> tuple[bytes, os.stat_result]:
    return _read_from_fd(anchor.parent_fd, name)


def _fsync_directory(descriptor: int) -> None:
    try:
        os.fsync(descriptor)
    except OSError as error:
        if error.errno not in {22, 45, 95}:
            raise


def _rollback_created_directories(
    ledger: Sequence[_CreatedDirectory],
) -> list[str]:
    failures: list[str] = []
    for creation in sorted(
        ledger,
        key=lambda value: len(value.path.parts),
        reverse=True,
    ):
        if not creation.created:
            continue
        try:
            try:
                metadata = os.stat(
                    creation.name,
                    dir_fd=creation.parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            if (
                creation.identity is None
                or _identity(metadata) != creation.identity
                or not stat.S_ISDIR(metadata.st_mode)
            ):
                raise RuntimeError("created directory identity changed")
            os.rmdir(creation.name, dir_fd=creation.parent_fd)
        except BaseException as error:
            failures.append(f"created directory cleanup {creation.path}: {error}")
    for creation in ledger:
        if not creation.created:
            continue
        try:
            os.stat(
                creation.name,
                dir_fd=creation.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        except BaseException as error:
            failures.append(f"created directory verification {creation.path}: {error}")
        else:
            failures.append(
                f"created directory remains after rollback: {creation.path}"
            )
    return failures


def _leaf_metadata(anchor: _HeldParent) -> os.stat_result | None:
    try:
        metadata = os.stat(
            anchor.leaf,
            dir_fd=anchor.parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"artifact leaf is not a regular file: {anchor.leaf}")
    return metadata


def _validate_expected_prior(
    publication: _Publication,
    payload: bytes | None,
    identity: tuple[int, int] | None,
) -> None:
    expected = publication.expected_prior
    if expected is None:
        return
    if (
        payload is None
        or identity != expected.identity
        or payload != expected.payload
        or hashlib.sha256(payload).hexdigest() != expected.byte_sha256
    ):
        raise ValueError(f"{publication.role} changed during operation")


def _ensure_scratch(item: _StagedPublication) -> None:
    if item.scratch_fd >= 0:
        return
    if item.scratch_created:
        if item.scratch_name is None or item.scratch_identity is None:
            raise RuntimeError("transaction scratch ownership is unproven")
        descriptor = os.open(
            item.scratch_name,
            _DIRECTORY_FLAGS,
            dir_fd=item.anchor.parent_fd,
        )
        try:
            metadata = os.fstat(descriptor)
            visible = os.stat(
                item.scratch_name,
                dir_fd=item.anchor.parent_fd,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or _identity(metadata) != item.scratch_identity
                or _identity(visible) != item.scratch_identity
            ):
                raise RuntimeError("transaction scratch identity changed")
        except BaseException:
            os.close(descriptor)
            raise
        item.scratch_fd = descriptor
        return
    _revalidate_anchor(item.anchor)
    scratch_name = f".{item.anchor.leaf}.txn-{secrets.token_hex(8)}"
    item.scratch_name = scratch_name
    try:
        os.mkdir(scratch_name, 0o700, dir_fd=item.anchor.parent_fd)
    except BaseException:
        # A hook may create the name and then fail. Rollback verifies that an
        # unowned name is not silently removed.
        raise
    item.scratch_created = True
    item.scratch_fd = os.open(
        scratch_name,
        _DIRECTORY_FLAGS,
        dir_fd=item.anchor.parent_fd,
    )
    metadata = os.fstat(item.scratch_fd)
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"transaction scratch is not a directory: {scratch_name}")
    item.scratch_identity = _identity(metadata)
    visible = os.stat(
        scratch_name,
        dir_fd=item.anchor.parent_fd,
        follow_symlinks=False,
    )
    if _identity(visible) != item.scratch_identity:
        raise ValueError(f"transaction scratch changed: {scratch_name}")


def _register_scratch_leaf(
    item: _StagedPublication,
    prefix: str,
    purpose: str,
) -> _ScratchLeaf:
    _ensure_scratch(item)
    entry = _ScratchLeaf(
        f".{item.anchor.leaf}.{prefix}-{secrets.token_hex(8)}",
        purpose,
    )
    item.scratch_leaves.append(entry)
    return entry


def _refresh_scratch_leaf(
    item: _StagedPublication,
    entry: _ScratchLeaf,
) -> tuple[bytes, os.stat_result]:
    if item.scratch_fd < 0 or not entry.present:
        raise FileNotFoundError(entry.name)
    payload, metadata = _read_from_fd(
        item.scratch_fd,
        entry.name,
        label=entry.purpose,
    )
    entry.identity = _identity(metadata)
    entry.payload = payload
    return payload, metadata


def _create_scratch_payload(
    item: _StagedPublication,
    prefix: str,
    purpose: str,
    payload: bytes,
    *,
    register_as_temporary: bool = False,
) -> _ScratchLeaf:
    entry = _register_scratch_leaf(item, prefix, purpose)
    if register_as_temporary:
        item.temporary = entry
    descriptor = -1
    try:
        descriptor = os.open(
            entry.name,
            _CREATE_FLAGS,
            0o600,
            dir_fd=item.scratch_fd,
        )
        entry.present = True
        entry.identity = _identity(os.fstat(descriptor))
        _write_all(descriptor, payload)
        if _identity(os.fstat(descriptor)) != entry.identity:
            raise ValueError(f"{purpose} changed while it was staged")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    staged_bytes, staged_metadata = _refresh_scratch_leaf(item, entry)
    if staged_bytes != payload or _identity(staged_metadata) != entry.identity:
        raise ValueError(f"{purpose} verification failed")
    return entry


def _capture_visible_to_scratch(
    item: _StagedPublication,
    prefix: str,
    purpose: str,
) -> _ScratchLeaf | None:
    """Atomically quarantine whichever inode is visible, then inspect it."""

    entry = _register_scratch_leaf(item, prefix, purpose)
    try:
        os.rename(
            item.anchor.leaf,
            entry.name,
            src_dir_fd=item.anchor.parent_fd,
            dst_dir_fd=item.scratch_fd,
        )
    except FileNotFoundError:
        return None
    entry.present = True
    item.phase = _PublicationPhase.EXTERNAL_CAPTURED
    metadata = os.stat(
        entry.name,
        dir_fd=item.scratch_fd,
        follow_symlinks=False,
    )
    entry.identity = _identity(metadata)
    return entry


def _scratch_leaf_matches(
    item: _StagedPublication,
    entry: _ScratchLeaf,
    identity: tuple[int, int] | None,
    payload: bytes | None,
) -> bool:
    if identity is None or not entry.present:
        return False
    try:
        actual_payload, metadata = _refresh_scratch_leaf(item, entry)
    except (FileNotFoundError, OSError, ValueError):
        return False
    return _identity(metadata) == identity and actual_payload == payload


def _link_scratch_leaf_visible(
    item: _StagedPublication,
    entry: _ScratchLeaf,
) -> None:
    if item.scratch_fd < 0 or not entry.present:
        raise FileNotFoundError(entry.name)
    os.link(
        entry.name,
        item.anchor.leaf,
        src_dir_fd=item.scratch_fd,
        dst_dir_fd=item.anchor.parent_fd,
        follow_symlinks=False,
    )


def _visible_leaf(
    item: _StagedPublication,
) -> tuple[bytes, os.stat_result] | None:
    try:
        return _read_relative(item.anchor, item.anchor.leaf)
    except FileNotFoundError:
        return None


def _visible_matches(
    item: _StagedPublication,
    payload: bytes | None,
) -> bool:
    current = _visible_leaf(item)
    if payload is None:
        return current is None
    return current is not None and current[0] == payload


def _capture_initial_leaf(item: _StagedPublication) -> None:
    expected_payload = item.prior_payload
    expected_identity = item.prior_identity
    captured = _capture_visible_to_scratch(item, "backup", "captured prior leaf")
    if captured is None:
        if expected_identity is None:
            item.phase = _PublicationPhase.EXPECTED_ABSENT
            return
        # Preserve a concurrent deletion instead of recreating stale data.
        item.prior_payload = None
        item.prior_identity = None
        item.phase = _PublicationPhase.EXTERNAL_CAPTURED
        raise ValueError(f"output changed during operation: {item.anchor.leaf}")

    try:
        captured_payload, captured_metadata = _refresh_scratch_leaf(item, captured)
    except BaseException:
        try:
            _link_scratch_leaf_visible(item, captured)
        except BaseException:
            pass
        raise
    captured_identity = _identity(captured_metadata)
    item.prior = captured
    if captured_identity != expected_identity or captured_payload != expected_payload:
        # The capture is the linearization point: retain and later restore the
        # concurrent value that was actually moved, never the stale snapshot.
        item.prior_payload = captured_payload
        item.prior_identity = captured_identity
        raise ValueError(f"output changed during operation: {item.anchor.leaf}")
    _validate_expected_prior(item.publication, captured_payload, captured_identity)
    item.phase = _PublicationPhase.PRIOR_CAPTURED


def _verify_published_artifacts(staged: Sequence[_StagedPublication]) -> None:
    for item in staged:
        _revalidate_anchor(item.anchor)
        if item.publication.payload is None:
            try:
                os.stat(
                    item.anchor.leaf,
                    dir_fd=item.anchor.parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            raise ValueError(
                f"deleted artifact remains visible: {item.publication.role}"
            )
        published_bytes, published_metadata = _read_relative(
            item.anchor, item.anchor.leaf
        )
        if (
            published_bytes != item.publication.payload
            or item.temporary is None
            or _identity(published_metadata) != item.temporary.identity
        ):
            raise ValueError(
                f"published artifact verification failed: {item.publication.role}"
            )


def _verify_transaction_debris_absent(staged: Sequence[_StagedPublication]) -> None:
    for item in staged:
        if item.scratch_name is None:
            continue
        try:
            os.stat(
                item.scratch_name,
                dir_fd=item.anchor.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        raise ValueError(
            f"transaction debris remains for {item.publication.role}: "
            f"{item.scratch_name}"
        )


def _quarantine_and_remove_scratch_leaf(
    item: _StagedPublication,
    entry: _ScratchLeaf,
) -> None:
    if not entry.present:
        return
    if not entry.removable or entry.identity is None:
        raise RuntimeError(f"recoverable {entry.purpose} remains: {entry.name}")
    expected_identity = entry.identity
    expected_payload = entry.payload
    quarantine = f"{entry.name}.cleanup-{secrets.token_hex(8)}"
    try:
        os.rename(
            entry.name,
            quarantine,
            src_dir_fd=item.scratch_fd,
            dst_dir_fd=item.scratch_fd,
        )
    except FileNotFoundError:
        entry.present = False
        return
    entry.name = quarantine
    payload, metadata = _read_from_fd(
        item.scratch_fd,
        entry.name,
        label=entry.purpose,
    )
    if _identity(metadata) != expected_identity or (
        expected_payload is not None and payload != expected_payload
    ):
        entry.removable = False
        entry.purpose = f"external replacement of {entry.purpose}"
        raise RuntimeError(f"scratch entry identity changed: {entry.name}")
    os.unlink(entry.name, dir_fd=item.scratch_fd)
    entry.present = False


def _remove_scratch_directory(item: _StagedPublication) -> None:
    if not item.scratch_created or item.scratch_name is None:
        return
    if any(entry.present for entry in item.scratch_leaves):
        raise RuntimeError("transaction scratch retains recoverable entries")
    if item.scratch_fd < 0 or item.scratch_identity is None:
        raise RuntimeError("transaction scratch ownership is unproven")
    quarantine = f"{item.scratch_name}.cleanup-{secrets.token_hex(8)}"
    try:
        os.rename(
            item.scratch_name,
            quarantine,
            src_dir_fd=item.anchor.parent_fd,
            dst_dir_fd=item.anchor.parent_fd,
        )
    except FileNotFoundError:
        item.scratch_created = False
        item.scratch_name = None
        os.close(item.scratch_fd)
        item.scratch_fd = -1
        return
    item.scratch_name = quarantine
    metadata = os.stat(
        quarantine,
        dir_fd=item.anchor.parent_fd,
        follow_symlinks=False,
    )
    if _identity(metadata) != item.scratch_identity:
        raise RuntimeError("transaction scratch identity changed")
    os.close(item.scratch_fd)
    item.scratch_fd = -1
    os.rmdir(quarantine, dir_fd=item.anchor.parent_fd)
    item.scratch_created = False
    item.scratch_name = None
    item.scratch_identity = None


def _cleanup_scratch(item: _StagedPublication) -> None:
    for entry in item.scratch_leaves:
        if entry.present:
            _quarantine_and_remove_scratch_leaf(item, entry)
    _remove_scratch_directory(item)


def _restore_prior_with_no_clobber_link(item: _StagedPublication) -> None:
    if item.prior_payload is None:
        if _visible_leaf(item) is not None:
            raise RuntimeError(
                f"rollback would overwrite a concurrent artifact: {item.anchor.leaf}"
            )
        return
    if _visible_matches(item, item.prior_payload):
        return
    if _visible_leaf(item) is not None:
        raise RuntimeError(
            f"rollback would overwrite a concurrent artifact: {item.anchor.leaf}"
        )

    backup_error: BaseException | None = None
    if item.prior is not None and _scratch_leaf_matches(
        item,
        item.prior,
        item.prior_identity,
        item.prior_payload,
    ):
        try:
            _link_scratch_leaf_visible(item, item.prior)
        except BaseException as error:
            backup_error = error
        else:
            if _visible_matches(item, item.prior_payload):
                item.prior.removable = True
                return

    if _visible_leaf(item) is not None:
        raise RuntimeError(
            f"rollback would overwrite a concurrent artifact: {item.anchor.leaf}"
        ) from backup_error
    retained = _create_scratch_payload(
        item,
        "restore",
        "retained rollback payload",
        item.prior_payload,
    )
    retained.removable = True
    try:
        _link_scratch_leaf_visible(item, retained)
    except BaseException as fallback_error:
        detail = f"retained-byte restore failed ({fallback_error})"
        if backup_error is not None:
            detail = f"backup restore failed ({backup_error}); {detail}"
        raise RuntimeError(
            f"rollback could not restore {item.publication.role}: {detail}"
        ) from fallback_error
    if not _visible_matches(item, item.prior_payload):
        raise RuntimeError(f"rollback verification failed: {item.publication.role}")


def _rollback_item(item: _StagedPublication) -> None:
    original_phase = item.phase
    captured = _capture_visible_to_scratch(
        item,
        "rollback",
        "rollback visible capture",
    )
    concurrent_capture = False
    if captured is not None:
        try:
            captured_payload, captured_metadata = _refresh_scratch_leaf(item, captured)
        except BaseException as error:
            try:
                _link_scratch_leaf_visible(item, captured)
            except BaseException as restore_error:
                raise RuntimeError(
                    "rollback captured an unreadable visible artifact and could not "
                    "restore it"
                ) from restore_error
            raise RuntimeError(
                "rollback captured an unreadable visible artifact"
            ) from error
        captured_identity = _identity(captured_metadata)
        transaction_owned = (
            original_phase is _PublicationPhase.NEW_VISIBLE
            and item.temporary is not None
            and captured_identity == item.temporary.identity
        )
        prior_already_visible = (
            item.prior_payload is not None and captured_payload == item.prior_payload
        )
        if transaction_owned:
            captured.removable = True
        elif prior_already_visible:
            _link_scratch_leaf_visible(item, captured)
            captured.removable = True
        else:
            concurrent_capture = original_phase in {
                _PublicationPhase.EXPECTED_ABSENT,
                _PublicationPhase.PRIOR_CAPTURED,
                _PublicationPhase.NEW_VISIBLE,
            }
            item.phase = _PublicationPhase.EXTERNAL_CAPTURED
            item.prior_payload = captured_payload
            item.prior_identity = captured_identity
            item.prior = captured
            _link_scratch_leaf_visible(item, captured)

    _restore_prior_with_no_clobber_link(item)
    if not _visible_matches(item, item.prior_payload):
        raise RuntimeError(f"rollback verification failed: {item.publication.role}")
    if item.prior is not None and not concurrent_capture:
        item.prior.removable = True
    if item.temporary is not None:
        item.temporary.removable = True
    if concurrent_capture:
        raise RuntimeError(
            f"rollback preserved a concurrent artifact for {item.publication.role}"
        )


def _rollback_artifacts(
    staged: Sequence[_StagedPublication],
    created_directories: Sequence[_CreatedDirectory],
) -> list[str]:
    failures: list[str] = []
    for item in reversed(staged):
        try:
            _rollback_item(item)
        except BaseException as error:
            failures.append(f"{item.publication.role} restore: {error}")

        try:
            _cleanup_scratch(item)
        except BaseException as error:
            failures.append(f"{item.publication.role} scratch cleanup: {error}")
        try:
            _fsync_directory(item.anchor.parent_fd)
        except BaseException as error:
            failures.append(f"{item.publication.role} directory sync: {error}")

    for item in staged:
        try:
            if not _visible_matches(item, item.prior_payload):
                raise RuntimeError("prior leaf bytes or absence do not match")
            _verify_transaction_debris_absent([item])
        except BaseException as error:
            failures.append(f"{item.publication.role} rollback verification: {error}")

    failures.extend(_rollback_created_directories(created_directories))
    return failures


def _publish_artifacts(
    publications: Sequence[_Publication],
    *,
    validate_before_commit: Callable[[], None] | None = None,
) -> tuple[Path, ...]:
    output_roles = [
        PathRole(publication.role, publication.path, "output")
        for publication in publications
    ]
    preflight_path_roles(output_roles)
    staged: list[_StagedPublication] = []
    created_directories: list[_CreatedDirectory] = []
    try:
        for publication in publications:
            anchor = _open_parent(
                publication.path,
                create=True,
                creation_ledger=created_directories,
            )
            item = _StagedPublication(publication, anchor)
            staged.append(item)
            _ensure_scratch(item)
            existing = _leaf_metadata(anchor)
            if existing is not None:
                prior_payload, prior_metadata = _read_relative(anchor, anchor.leaf)
                item.prior_payload = prior_payload
                item.prior_identity = _identity(prior_metadata)
                if item.prior_identity != _identity(existing):
                    raise ValueError(f"output changed during operation: {anchor.leaf}")
            _validate_expected_prior(
                publication,
                item.prior_payload,
                item.prior_identity,
            )
            if publication.payload is not None:
                item.temporary = _create_scratch_payload(
                    item,
                    "tmp",
                    f"staged artifact for {publication.role}",
                    publication.payload,
                    register_as_temporary=True,
                )
            _revalidate_anchor(anchor)

        for item in staged:
            _capture_initial_leaf(item)
            if item.publication.payload is not None:
                if item.temporary is None:
                    raise RuntimeError("missing staged artifact")
                _link_scratch_leaf_visible(item, item.temporary)
                item.phase = _PublicationPhase.NEW_VISIBLE
            _fsync_directory(item.anchor.parent_fd)
            _revalidate_anchor(item.anchor)

        _verify_published_artifacts(staged)
        if validate_before_commit is not None:
            validate_before_commit()
            _verify_published_artifacts(staged)

        for item in staged:
            for entry in item.scratch_leaves:
                entry.removable = True
            _cleanup_scratch(item)
            _fsync_directory(item.anchor.parent_fd)
        _verify_published_artifacts(staged)
        _verify_transaction_debris_absent(staged)
        return tuple(_absolute(item.publication.path) for item in staged)
    except BaseException as error:
        rollback_failures = _rollback_artifacts(staged, created_directories)
        if rollback_failures:
            detail = "; ".join(rollback_failures)
            raise RuntimeError(f"rollback state is unproven: {detail}") from error
        raise
    finally:
        for item in staged:
            item.close()
        for creation in created_directories:
            creation.close()


def _atomic_write_bytes(path: Path, payload: bytes) -> Path:
    return _publish_artifacts([_Publication(path, payload, "output")])[0]


def write_owner_json(path: Path, payload: object) -> Path:
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"
    ).encode("utf-8")
    return _atomic_write_bytes(path, encoded)


@dataclass(frozen=True)
class _ImageSnapshot:
    path: Path
    data: bytes
    byte_sha256: str
    image: Image.Image
    format: str | None
    decoded_pixel_sha256: str


@dataclass(frozen=True)
class ImageMetadata:
    format: str | None
    mode: str
    width: int
    height: int


def _decoded_hash_image(image: Image.Image) -> str:
    digest = hashlib.sha256()
    digest.update(image.mode.encode("ascii"))
    digest.update(b"\0")
    digest.update(f"{image.width}x{image.height}".encode("ascii"))
    digest.update(b"\0")
    if image.mode in {"P", "PA"}:
        digest.update(b"visible-rgba\0")
        digest.update(image.convert("RGBA").tobytes())
    else:
        digest.update(b"native\0")
        digest.update(image.tobytes())
    return digest.hexdigest()


def _decode_image(data: bytes, source: Path) -> tuple[Image.Image, str | None]:
    try:
        with Image.open(io.BytesIO(data)) as opened:
            image_format = opened.format
            opened.load()
            return opened.copy(), image_format
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError(f"expected a readable image: {source}") from error


def _snapshot_image(path: Path) -> _ImageSnapshot:
    try:
        source, data, _ = _read_regular_bytes(path, "image")
    except ValueError as error:
        if "changed" in str(error):
            raise ValueError(
                f"source changed while it was being locked: {_absolute(path)}"
            ) from error
        if "symlink" in str(error):
            raise
        raise ValueError(
            f"expected a readable regular image: {_absolute(path)}"
        ) from error
    image, image_format = _decode_image(data, source)
    return _ImageSnapshot(
        source,
        data,
        hashlib.sha256(data).hexdigest(),
        image,
        image_format,
        _decoded_hash_image(image),
    )


def _snapshot_image_bytes(path: Path, data: bytes) -> _ImageSnapshot:
    source = _absolute(path)
    image, image_format = _decode_image(data, source)
    return _ImageSnapshot(
        source,
        data,
        hashlib.sha256(data).hexdigest(),
        image,
        image_format,
        _decoded_hash_image(image),
    )


def read_image_metadata(path: Path) -> ImageMetadata:
    snapshot = _snapshot_image(path)
    return ImageMetadata(
        snapshot.format,
        snapshot.image.mode,
        snapshot.image.width,
        snapshot.image.height,
    )


def decoded_pixel_sha256(path: Path) -> str:
    return _snapshot_image(path).decoded_pixel_sha256


def _validate_source_id(source_id: str, label: str = "source_id") -> str:
    if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
        raise ValueError(f"{label} must be a safe path component")
    return source_id


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _required_integer(value: object, label: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if positive and value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _required_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class LockedSource:
    source_id: str
    url: str
    publisher: str
    role: str
    revision: str
    reviewed_at: str
    byte_sha256: str
    decoded_pixel_sha256: str
    mode: str
    width: int
    height: int
    original_path: Path
    cache_path: Path
    canonical_digest: str

    def to_json(self) -> dict[str, object]:
        return {
            "sourceID": self.source_id,
            "url": self.url,
            "publisher": self.publisher,
            "role": self.role,
            "revision": self.revision,
            "reviewedAt": self.reviewed_at,
            "byteSHA256": self.byte_sha256,
            "decodedPixelSHA256": self.decoded_pixel_sha256,
            "mode": self.mode,
            "width": self.width,
            "height": self.height,
            "originalPath": str(self.original_path),
            "cachePath": str(self.cache_path),
            "canonicalDigest": self.canonical_digest,
        }


def _source_canonical_fields(source: LockedSource) -> dict[str, object]:
    payload = source.to_json()
    payload.pop("canonicalDigest")
    return payload


def _source_canonical_digest(source: LockedSource) -> str:
    return _canonical_sha256(
        {
            "digestVersion": _DIGEST_VERSION,
            "kind": "cordLockedSource",
            "source": _source_canonical_fields(source),
        }
    )


def _cache_suffix(original_path: Path) -> str:
    suffix = original_path.suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) else ".image"


def _canonical_cache_path(
    owner: Path, source_id: str, byte_sha256: str, original_path: Path
) -> Path:
    return _absolute(
        owner
        / "sources"
        / "locked"
        / f"{source_id}-{byte_sha256}{_cache_suffix(original_path)}"
    )


def _locked_source_from_snapshot(
    snapshot: _ImageSnapshot,
    owner: Path,
    *,
    source_id: str,
    url: str,
    publisher: str,
    role: str,
    revision: str,
    reviewed_at: date,
) -> LockedSource:
    cache_path = _canonical_cache_path(
        owner, source_id, snapshot.byte_sha256, snapshot.path
    )
    provisional = LockedSource(
        source_id,
        url,
        publisher,
        role,
        revision,
        reviewed_at.isoformat(),
        snapshot.byte_sha256,
        snapshot.decoded_pixel_sha256,
        snapshot.image.mode,
        snapshot.image.width,
        snapshot.image.height,
        snapshot.path,
        cache_path,
        "0" * 64,
    )
    return replace(provisional, canonical_digest=_source_canonical_digest(provisional))


def _validate_lock_metadata(
    *,
    source_id: str,
    url: str,
    publisher: str,
    role: str,
    revision: str,
    reviewed_at: date,
) -> None:
    _validate_source_id(source_id)
    for label, value in (
        ("url", url),
        ("publisher", publisher),
        ("role", role),
        ("revision", revision),
    ):
        _required_string(value, label)
    if type(reviewed_at) is not date:
        raise ValueError("reviewed_at must be an immutable date")


def _lock_snapshot(
    snapshot: _ImageSnapshot,
    owner: Path,
    *,
    source_id: str,
    url: str,
    publisher: str,
    role: str,
    revision: str,
    reviewed_at: date,
) -> LockedSource:
    _validate_lock_metadata(
        source_id=source_id,
        url=url,
        publisher=publisher,
        role=role,
        revision=revision,
        reviewed_at=reviewed_at,
    )
    locked = _locked_source_from_snapshot(
        snapshot,
        owner,
        source_id=source_id,
        url=url,
        publisher=publisher,
        role=role,
        revision=revision,
        reviewed_at=reviewed_at,
    )
    preflight_path_roles(
        [
            PathRole("source", snapshot.path, "input"),
            PathRole("cache", locked.cache_path, "output"),
        ]
    )
    _publish_artifacts([_Publication(locked.cache_path, snapshot.data, "cache")])
    return locked


def lock_source(
    path: Path,
    *,
    source_id: str,
    url: str,
    publisher: str,
    role: str,
    revision: str,
    reviewed_at: date,
) -> LockedSource:
    """Freeze one source from a single snapshot into a workspace-owned cache.

    Sources already in an owner context use that context. External sources use
    the deterministic workspace cache at
    ``.context/joyful-donkey-cord-assets/sources/locked``. CLI manifests use
    their own owner root through :func:`freeze_source_manifest`.
    """

    _validate_lock_metadata(
        source_id=source_id,
        url=url,
        publisher=publisher,
        role=role,
        revision=revision,
        reviewed_at=reviewed_at,
    )
    snapshot = _snapshot_image(path)
    owner = _maybe_owner_context(snapshot.path)
    if owner is None:
        owner = _workspace_root() / ".context" / "joyful-donkey-cord-assets"
    return _lock_snapshot(
        snapshot,
        owner,
        source_id=source_id,
        url=url,
        publisher=publisher,
        role=role,
        revision=revision,
        reviewed_at=reviewed_at,
    )


def load_json_file(path: Path, label: str) -> object:
    try:
        _, data, _ = _read_regular_bytes(path, label)
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"unable to read {label}: {_absolute(path)}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is not valid JSON") from error


def _exact_object(
    value: object, *, label: str, required: set[str]
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    keys = set(value)
    missing = required - keys
    unknown = keys - required
    if missing:
        raise ValueError(f"{label} is missing fields")
    if unknown:
        raise ValueError(f"{label} has unknown fields")
    return value


_SOURCE_INPUT_FIELDS = {
    "path",
    "sourceID",
    "url",
    "publisher",
    "role",
    "revision",
    "reviewedAt",
}
_LOCKED_SOURCE_FIELDS = {
    "sourceID",
    "url",
    "publisher",
    "role",
    "revision",
    "reviewedAt",
    "byteSHA256",
    "decodedPixelSHA256",
    "mode",
    "width",
    "height",
    "originalPath",
    "cachePath",
    "canonicalDigest",
}


def _parse_reviewed_at(value: object, label: str) -> date:
    text = _required_string(value, label)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO calendar date") from error
    if parsed.isoformat() != text:
        raise ValueError(f"{label} must be an ISO calendar date")
    return parsed


def freeze_source_manifest(
    manifest: Path, *, report_path: Path | None = None
) -> tuple[LockedSource, ...]:
    """Freeze a complete manifest as one handled-return transaction."""

    owner = _owner_context(manifest)
    manifest_path, manifest_bytes, manifest_metadata = _read_regular_bytes(
        manifest, "manifest"
    )
    try:
        manifest_json = json.loads(manifest_bytes.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError(f"unable to read manifest: {manifest_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError("manifest is not valid JSON") from error
    payload = _exact_object(
        manifest_json,
        label="manifest",
        required={"sources"},
    )
    records = payload["sources"]
    if not isinstance(records, list) or not records:
        raise ValueError("manifest.sources must be a non-empty array")
    parsed: list[tuple[Path, str, str, str, str, str, date]] = []
    seen: set[str] = set()
    for index, raw_record in enumerate(records):
        label = f"sources[{index}]"
        record = _exact_object(raw_record, label=label, required=_SOURCE_INPUT_FIELDS)
        source_id = _validate_source_id(record["sourceID"], f"{label}.sourceID")  # type: ignore[arg-type]
        if source_id in seen:
            raise ValueError(f"duplicate source ID: {source_id}")
        seen.add(source_id)
        parsed.append(
            (
                Path(_required_string(record["path"], f"{label}.path")),
                source_id,
                _required_string(record["url"], f"{label}.url"),
                _required_string(record["publisher"], f"{label}.publisher"),
                _required_string(record["role"], f"{label}.role"),
                _required_string(record["revision"], f"{label}.revision"),
                _parse_reviewed_at(record["reviewedAt"], f"{label}.reviewedAt"),
            )
        )
    initial_roles = [PathRole("manifest", manifest, "input")]
    if report_path is not None:
        initial_roles.append(PathRole("report", report_path, "output"))
    initial_roles.extend(
        PathRole(f"source[{index}]", record[0], "input")
        for index, record in enumerate(parsed)
    )
    preflight_path_roles(initial_roles)

    locked: list[LockedSource] = []
    snapshots: list[_ImageSnapshot] = []
    for source_path, source_id, url, publisher, role, revision, reviewed_at in parsed:
        snapshot = _snapshot_image(source_path)
        snapshots.append(snapshot)
        locked.append(
            _locked_source_from_snapshot(
                snapshot,
                owner,
                source_id=source_id,
                url=url,
                publisher=publisher,
                role=role,
                revision=revision,
                reviewed_at=reviewed_at,
            )
        )
    ordered = tuple(sorted(locked, key=lambda source: source.source_id))
    artifact = source_lock_artifact(ordered)
    complete_roles = list(initial_roles)
    complete_roles.extend(
        PathRole(f"cache[{index}]", source.cache_path, "output")
        for index, source in enumerate(ordered)
    )
    preflight_path_roles(complete_roles)
    snapshot_by_path = {snapshot.path: snapshot for snapshot in snapshots}
    publications = [
        _Publication(
            source.cache_path,
            snapshot_by_path[source.original_path].data,
            f"cache[{index}]",
        )
        for index, source in enumerate(ordered)
    ]
    encoded = (
        json.dumps(artifact, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"
    ).encode("utf-8")
    if report_path is not None:
        publications.append(_Publication(report_path, encoded, "report"))
    publications.append(
        _Publication(
            manifest,
            encoded,
            "manifest",
            expected_prior=_LeafExpectation(
                _identity(manifest_metadata),
                manifest_bytes,
                hashlib.sha256(manifest_bytes).hexdigest(),
            ),
        )
    )
    _publish_artifacts(publications)
    return ordered


def _source_lock_digest_records(records: Sequence[object]) -> str:
    return _canonical_sha256(
        {
            "digestVersion": _DIGEST_VERSION,
            "kind": "cordSourceLock",
            "schemaVersion": _SCHEMA_VERSION,
            "toolVersion": _TOOL_VERSION,
            "sources": list(records),
        }
    )


def _source_lock_digest(sources: Sequence[LockedSource]) -> str:
    return _source_lock_digest_records([source.to_json() for source in sources])


def source_lock_artifact(sources: Sequence[LockedSource]) -> dict[str, object]:
    ordered = tuple(sorted(sources, key=lambda source: source.source_id))
    return {
        "schemaVersion": _SCHEMA_VERSION,
        "toolVersion": _TOOL_VERSION,
        "kind": "cordSourceLock",
        "digestVersion": _DIGEST_VERSION,
        "sourceLockSHA256": _source_lock_digest(ordered),
        "sources": [source.to_json() for source in ordered],
    }


def _locked_source_from_json(
    raw: object, *, label: str, manifest_owner: Path
) -> LockedSource:
    record = _exact_object(raw, label=label, required=_LOCKED_SOURCE_FIELDS)
    source_id = _validate_source_id(record["sourceID"], f"{label}.sourceID")  # type: ignore[arg-type]
    reviewed = _parse_reviewed_at(record["reviewedAt"], f"{label}.reviewedAt")
    original_text = _required_string(record["originalPath"], f"{label}.originalPath")
    cache_text = _required_string(record["cachePath"], f"{label}.cachePath")
    original_path = Path(original_text)
    cache_path = Path(cache_text)
    if not original_path.is_absolute() or not cache_path.is_absolute():
        raise ValueError(f"{label} paths must be absolute")
    cache_resolved = _absolute(cache_path)
    expected_cache_root = _absolute(manifest_owner / "sources" / "locked")
    if cache_resolved.parent != expected_cache_root:
        raise ValueError(f"{label}.cachePath escapes the manifest owner cache")
    source = LockedSource(
        source_id,
        _required_string(record["url"], f"{label}.url"),
        _required_string(record["publisher"], f"{label}.publisher"),
        _required_string(record["role"], f"{label}.role"),
        _required_string(record["revision"], f"{label}.revision"),
        reviewed.isoformat(),
        _required_sha256(record["byteSHA256"], f"{label}.byteSHA256"),
        _required_sha256(record["decodedPixelSHA256"], f"{label}.decodedPixelSHA256"),
        _required_string(record["mode"], f"{label}.mode"),
        _required_integer(record["width"], f"{label}.width", positive=True),
        _required_integer(record["height"], f"{label}.height", positive=True),
        _absolute(original_path),
        cache_resolved,
        _required_sha256(record["canonicalDigest"], f"{label}.canonicalDigest"),
    )
    _validate_locked_source(source)
    return source


def load_locked_sources(manifest: Path) -> list[LockedSource]:
    owner = _owner_context(manifest)
    payload = _exact_object(
        load_json_file(manifest, "locked source manifest"),
        label="locked source manifest",
        required={
            "schemaVersion",
            "toolVersion",
            "kind",
            "digestVersion",
            "sourceLockSHA256",
            "sources",
        },
    )
    schema_version = _required_integer(
        payload["schemaVersion"], "locked source manifest.schemaVersion"
    )
    if schema_version != _SCHEMA_VERSION:
        raise ValueError("locked source manifest has unsupported schemaVersion")
    if payload["toolVersion"] != _TOOL_VERSION:
        raise ValueError("locked source manifest has unsupported toolVersion")
    if payload["kind"] != "cordSourceLock":
        raise ValueError("locked source manifest has wrong kind")
    digest_version = _required_integer(
        payload["digestVersion"], "locked source manifest.digestVersion"
    )
    if digest_version != _DIGEST_VERSION:
        raise ValueError("locked source manifest has unsupported digestVersion")
    records = payload["sources"]
    if not isinstance(records, list) or not records:
        raise ValueError("locked source manifest.sources must be a non-empty array")
    supplied_digest = _required_sha256(
        payload["sourceLockSHA256"], "locked source manifest.sourceLockSHA256"
    )
    if supplied_digest != _source_lock_digest_records(records):
        raise ValueError("source lock digest mismatch")
    sources = [
        _locked_source_from_json(
            record, label=f"sources[{index}]", manifest_owner=owner
        )
        for index, record in enumerate(records)
    ]
    identifiers = [source.source_id for source in sources]
    if len(set(identifiers)) != len(identifiers):
        duplicate = next(
            identifier
            for identifier in identifiers
            if identifiers.count(identifier) > 1
        )
        raise ValueError(f"duplicate source ID: {duplicate}")
    if identifiers != sorted(identifiers):
        raise ValueError("locked source manifest sources must be sorted by sourceID")
    if supplied_digest != _source_lock_digest(sources):
        raise ValueError("source lock digest mismatch")
    return sources


def _validate_snapshot_against_source(
    snapshot: _ImageSnapshot, source: LockedSource, kind: str
) -> None:
    if snapshot.byte_sha256 != source.byte_sha256:
        raise ValueError(f"{kind} source hash mismatch: {source.source_id}")
    if snapshot.decoded_pixel_sha256 != source.decoded_pixel_sha256:
        raise ValueError(f"{kind} source pixel hash mismatch: {source.source_id}")
    if (
        snapshot.image.mode,
        snapshot.image.width,
        snapshot.image.height,
    ) != (source.mode, source.width, source.height):
        raise ValueError(f"{kind} source metadata mismatch: {source.source_id}")


def _validate_locked_source(
    source: LockedSource,
) -> tuple[_ImageSnapshot, _ImageSnapshot]:
    _validate_source_id(source.source_id)
    for label, value in (
        ("url", source.url),
        ("publisher", source.publisher),
        ("role", source.role),
        ("revision", source.revision),
        ("mode", source.mode),
    ):
        _required_string(value, label)
    _parse_reviewed_at(source.reviewed_at, "reviewed_at")
    _required_sha256(source.byte_sha256, "byte_sha256")
    _required_sha256(source.decoded_pixel_sha256, "decoded_pixel_sha256")
    _required_sha256(source.canonical_digest, "canonical_digest")
    _required_integer(source.width, "width", positive=True)
    _required_integer(source.height, "height", positive=True)
    if not isinstance(source.original_path, Path) or not isinstance(
        source.cache_path, Path
    ):
        raise ValueError("locked source paths must be Path values")
    original = _snapshot_image(source.original_path)
    _validate_snapshot_against_source(original, source, "original")
    expected_digest = _source_canonical_digest(source)
    if source.canonical_digest != expected_digest:
        raise ValueError(f"locked source canonical digest mismatch: {source.source_id}")
    cache_owner = _owner_context(source.cache_path)
    expected_cache_root = _absolute(cache_owner / "sources" / "locked")
    cache_resolved = _absolute(source.cache_path)
    expected_cache = _canonical_cache_path(
        cache_owner,
        source.source_id,
        source.byte_sha256,
        source.original_path,
    )
    if cache_resolved.parent != expected_cache_root or cache_resolved != expected_cache:
        raise ValueError(f"locked source cache path mismatch: {source.source_id}")
    cache = _snapshot_image(source.cache_path)
    _validate_snapshot_against_source(cache, source, "locked")
    if original.data != cache.data:
        raise ValueError(
            f"locked source bytes differ from original: {source.source_id}"
        )
    return original, cache


@dataclass(frozen=True)
class AtlasPage:
    number: int
    path: Path
    byte_sha256: str
    decoded_pixel_sha256: str
    mode: str
    width: int
    height: int


@dataclass(frozen=True)
class AtlasPanel:
    source_id: str
    page_number: int
    x: int
    y: int
    width: int
    height: int
    mode: str
    decoded_pixel_sha256: str


@dataclass(frozen=True)
class AtlasIndex:
    sources: tuple[LockedSource, ...]
    pages: tuple[AtlasPage, ...]
    panels: tuple[AtlasPanel, ...]
    output_root: Path
    source_lock_sha256: str
    max_dimension: int
    layout_sha256: str
    atlas_index_sha256: str
    digest_version: int = _DIGEST_VERSION
    base_max_dimension: int = _ATLAS_BASE_DIMENSION
    padding: int = _ATLAS_PADDING
    neutral_rgba: tuple[int, int, int, int] = _ATLAS_NEUTRAL_RGBA
    packing_algorithm: str = _ATLAS_PACKING_ALGORITHM
    search_node_limit: int = _ATLAS_SEARCH_NODE_LIMIT

    def to_json(self) -> dict[str, object]:
        return {
            "schemaVersion": _SCHEMA_VERSION,
            "toolVersion": _TOOL_VERSION,
            "pillowVersion": PIL.__version__,
            "digestVersion": self.digest_version,
            "sourceLockSHA256": self.source_lock_sha256,
            "outputRoot": str(self.output_root),
            "packingAlgorithm": self.packing_algorithm,
            "searchNodeLimit": self.search_node_limit,
            "baseMaxDimension": self.base_max_dimension,
            "maxDimension": self.max_dimension,
            "padding": self.padding,
            "neutralRGBA": list(self.neutral_rgba),
            "layoutSHA256": self.layout_sha256,
            "atlasIndexSHA256": self.atlas_index_sha256,
            "sources": [source.to_json() for source in self.sources],
            "pages": [
                {
                    "number": page.number,
                    "path": str(page.path),
                    "byteSHA256": page.byte_sha256,
                    "decodedPixelSHA256": page.decoded_pixel_sha256,
                    "mode": page.mode,
                    "width": page.width,
                    "height": page.height,
                }
                for page in self.pages
            ],
            "panels": [
                {
                    "sourceID": panel.source_id,
                    "pageNumber": panel.page_number,
                    "x": panel.x,
                    "y": panel.y,
                    "width": panel.width,
                    "height": panel.height,
                    "mode": panel.mode,
                    "decodedPixelSHA256": panel.decoded_pixel_sha256,
                }
                for panel in self.panels
            ],
        }


@dataclass(frozen=True)
class AtlasVerification:
    valid: bool
    verified_panels: int


@dataclass
class _PagePlan:
    panels: list[AtlasPanel]


@dataclass(frozen=True)
class _FreeRectangle:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class _PackedRectangle:
    source: LockedSource
    x: int
    y: int
    width: int
    height: int


def _atlas_dimension(sources: Sequence[LockedSource]) -> int:
    return max(
        _ATLAS_BASE_DIMENSION,
        max(
            max(source.width, source.height) + _ATLAS_PADDING * 2 for source in sources
        ),
    )


def _free_intersects(left: _FreeRectangle, right: _FreeRectangle) -> bool:
    return not (
        left.x + left.width <= right.x
        or right.x + right.width <= left.x
        or left.y + left.height <= right.y
        or right.y + right.height <= left.y
    )


def _contains(outer: _FreeRectangle, inner: _FreeRectangle) -> bool:
    return (
        outer.x <= inner.x
        and outer.y <= inner.y
        and outer.x + outer.width >= inner.x + inner.width
        and outer.y + outer.height >= inner.y + inner.height
    )


def _split_free_rectangles(
    rectangles: list[_FreeRectangle], used: _FreeRectangle
) -> list[_FreeRectangle]:
    split: list[_FreeRectangle] = []
    for free in rectangles:
        if not _free_intersects(free, used):
            split.append(free)
            continue
        if used.x > free.x:
            split.append(_FreeRectangle(free.x, free.y, used.x - free.x, free.height))
        if used.x + used.width < free.x + free.width:
            split.append(
                _FreeRectangle(
                    used.x + used.width,
                    free.y,
                    free.x + free.width - used.x - used.width,
                    free.height,
                )
            )
        if used.y > free.y:
            split.append(_FreeRectangle(free.x, free.y, free.width, used.y - free.y))
        if used.y + used.height < free.y + free.height:
            split.append(
                _FreeRectangle(
                    free.x,
                    used.y + used.height,
                    free.width,
                    free.y + free.height - used.y - used.height,
                )
            )
    split = [rectangle for rectangle in split if rectangle.width and rectangle.height]
    pruned: list[_FreeRectangle] = []
    for index, rectangle in enumerate(split):
        if any(
            index != other_index and _contains(other, rectangle)
            for other_index, other in enumerate(split)
        ):
            continue
        pruned.append(rectangle)
    return sorted(
        set(pruned),
        key=lambda rectangle: (
            rectangle.y,
            rectangle.x,
            rectangle.height,
            rectangle.width,
        ),
    )


def _plans_from_packed(pages: Sequence[Sequence[_PackedRectangle]]) -> list[_PagePlan]:
    plans: list[_PagePlan] = []
    for page_number, placements in enumerate(pages, start=1):
        modes = {placement.source.mode for placement in placements}
        if len(modes) != 1:
            raise ValueError("atlas page cannot mix source modes")
        panels = [
            AtlasPanel(
                placement.source.source_id,
                page_number,
                placement.x + _ATLAS_PADDING,
                placement.y + _ATLAS_PADDING,
                placement.source.width,
                placement.source.height,
                placement.source.mode,
                placement.source.decoded_pixel_sha256,
            )
            for placement in placements
        ]
        panels.sort(key=lambda panel: (panel.y, panel.x, panel.source_id))
        plans.append(_PagePlan(panels))
    return plans


def _maxrects_plan(
    ordered: Sequence[LockedSource], max_dimension: int
) -> list[_PagePlan]:
    capacity = max_dimension - _ATLAS_PADDING
    free_pages: list[list[_FreeRectangle]] = []
    packed_pages: list[list[_PackedRectangle]] = []
    page_modes: list[str] = []
    for source in ordered:
        width = source.width + _ATLAS_PADDING
        height = source.height + _ATLAS_PADDING
        candidate: tuple[tuple[int, ...], int, int] | None = None
        for page_index, free_rectangles in enumerate(free_pages):
            if page_modes[page_index] != source.mode:
                continue
            for free_index, free in enumerate(free_rectangles):
                if width > free.width or height > free.height:
                    continue
                score = (
                    min(free.width - width, free.height - height),
                    max(free.width - width, free.height - height),
                    free.width * free.height - width * height,
                    page_index,
                    free.y,
                    free.x,
                )
                if candidate is None or score < candidate[0]:
                    candidate = (score, page_index, free_index)
        if candidate is None:
            free_pages.append([_FreeRectangle(0, 0, capacity, capacity)])
            packed_pages.append([])
            page_modes.append(source.mode)
            page_index = len(free_pages) - 1
            free_index = 0
        else:
            _, page_index, free_index = candidate
        free = free_pages[page_index][free_index]
        used = _FreeRectangle(free.x, free.y, width, height)
        packed_pages[page_index].append(
            _PackedRectangle(source, used.x, used.y, used.width, used.height)
        )
        free_pages[page_index] = _split_free_rectangles(free_pages[page_index], used)
    return _plans_from_packed(packed_pages)


def _layout_signature(plans: Sequence[_PagePlan]) -> tuple[object, ...]:
    return tuple(
        (
            panel.page_number,
            panel.y,
            panel.x,
            panel.source_id,
            panel.width,
            panel.height,
            panel.mode,
        )
        for plan in plans
        for panel in plan.panels
    )


def _layout_cost(plans: Sequence[_PagePlan]) -> tuple[object, ...]:
    dimensions = [_page_dimensions(plan) for plan in plans]
    areas = [width * height for width, height in dimensions]
    return (
        len(plans),
        sum(areas),
        max(areas, default=0),
        _layout_signature(plans),
    )


def _exact_pack(
    sources: Sequence[LockedSource], max_dimension: int, max_pages: int
) -> list[_PagePlan] | None:
    capacity = max_dimension - _ATLAS_PADDING
    ordered = sorted(
        sources,
        key=lambda source: (
            -(source.width + _ATLAS_PADDING) * (source.height + _ATLAS_PADDING),
            -max(source.width, source.height),
            -source.height,
            -source.width,
            source.source_id,
        ),
    )
    pages: list[list[_PackedRectangle]] = []
    visited: set[tuple[object, ...]] = set()
    nodes = 0

    def search(index: int) -> list[list[_PackedRectangle]] | None:
        nonlocal nodes
        nodes += 1
        if nodes > _ATLAS_SEARCH_NODE_LIMIT:
            raise ValueError(
                "packing feasibility search limit reached; page overflow not proven"
            )
        if index == len(ordered):
            return [list(page) for page in pages]
        state = (
            index,
            tuple(
                sorted(
                    (
                        page[0].source.mode,
                        tuple(
                            sorted(
                                (
                                    placement.source.width,
                                    placement.source.height,
                                    placement.x,
                                    placement.y,
                                )
                                for placement in page
                            )
                        ),
                    )
                    for page in pages
                )
            ),
        )
        if state in visited:
            return None
        visited.add(state)
        source = ordered[index]
        width = source.width + _ATLAS_PADDING
        height = source.height + _ATLAS_PADDING
        page_limit = min(len(pages) + 1, max_pages)
        seen_page_shapes: set[tuple[str, tuple[tuple[int, int, int, int], ...]]] = set()
        for page_index in range(page_limit):
            is_new = page_index == len(pages)
            if is_new:
                pages.append([])
            page = pages[page_index]
            if page and page[0].source.mode != source.mode:
                continue
            page_shape = (
                source.mode,
                tuple(
                    sorted(
                        (
                            placement.x,
                            placement.y,
                            placement.width,
                            placement.height,
                        )
                        for placement in page
                    )
                ),
            )
            if page_shape in seen_page_shapes:
                if is_new:
                    pages.pop()
                continue
            seen_page_shapes.add(page_shape)
            x_positions = {0, *(placement.x + placement.width for placement in page)}
            y_positions = {0, *(placement.y + placement.height for placement in page)}
            for y in sorted(y_positions):
                for x in sorted(x_positions):
                    if x + width > capacity or y + height > capacity:
                        continue
                    candidate = _FreeRectangle(x, y, width, height)
                    if any(
                        _free_intersects(
                            candidate,
                            _FreeRectangle(
                                placement.x,
                                placement.y,
                                placement.width,
                                placement.height,
                            ),
                        )
                        for placement in page
                    ):
                        continue
                    page.append(_PackedRectangle(source, x, y, width, height))
                    result = search(index + 1)
                    if result is not None:
                        return result
                    page.pop()
            if is_new:
                pages.pop()
        return None

    packed = search(0)
    return None if packed is None else _plans_from_packed(packed)


def _plan_atlases(
    sources: Sequence[LockedSource], max_dimension: int, max_pages: int = 5
) -> list[_PagePlan]:
    orderings = [
        sorted(
            sources,
            key=lambda source: (
                -source.height,
                -source.width,
                -(source.width * source.height),
                source.source_id,
            ),
        ),
        sorted(
            sources,
            key=lambda source: (
                -max(source.width, source.height),
                -(source.width * source.height),
                -source.height,
                -source.width,
                source.source_id,
            ),
        ),
        sorted(
            sources,
            key=lambda source: (
                -(source.width * source.height),
                -source.height,
                -source.width,
                source.source_id,
            ),
        ),
        sorted(sources, key=lambda source: source.source_id),
    ]
    candidates = [_maxrects_plan(ordering, max_dimension) for ordering in orderings]
    best = min(candidates, key=_layout_cost)
    if len(best) <= max_pages:
        return best
    exact = _exact_pack(sources, max_dimension, max_pages)
    if exact is None:
        raise ValueError(
            f"source set requires more than {max_pages} atlas pages; "
            f"limit is {max_pages}"
        )
    return exact


def _page_dimensions(plan: _PagePlan) -> tuple[int, int]:
    return (
        max(panel.x + panel.width for panel in plan.panels) + _ATLAS_PADDING,
        max(panel.y + panel.height for panel in plan.panels) + _ATLAS_PADDING,
    )


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=9)
    return buffer.getvalue()


def _layout_payload(
    sources: Sequence[LockedSource],
    plans: Sequence[_PagePlan],
    output_root: Path,
    max_dimension: int,
) -> dict[str, object]:
    return {
        "digestVersion": _DIGEST_VERSION,
        "sourceLockSHA256": _source_lock_digest(sources),
        "outputRoot": str(output_root),
        "packingAlgorithm": _ATLAS_PACKING_ALGORITHM,
        "searchNodeLimit": _ATLAS_SEARCH_NODE_LIMIT,
        "baseMaxDimension": _ATLAS_BASE_DIMENSION,
        "maxDimension": max_dimension,
        "padding": _ATLAS_PADDING,
        "neutralRGBA": list(_ATLAS_NEUTRAL_RGBA),
        "pages": [
            {
                "number": number,
                "width": _page_dimensions(plan)[0],
                "height": _page_dimensions(plan)[1],
                "mode": plan.panels[0].mode,
            }
            for number, plan in enumerate(plans, start=1)
        ],
        "panels": [
            {
                "sourceID": panel.source_id,
                "pageNumber": panel.page_number,
                "x": panel.x,
                "y": panel.y,
                "width": panel.width,
                "height": panel.height,
                "mode": panel.mode,
                "decodedPixelSHA256": panel.decoded_pixel_sha256,
            }
            for plan in plans
            for panel in plan.panels
        ],
    }


def _atlas_index_digest(index: AtlasIndex) -> str:
    payload = index.to_json()
    payload.pop("atlasIndexSHA256")
    return _canonical_sha256(payload)


def _render_page(plan: _PagePlan, snapshots: dict[str, _ImageSnapshot]) -> Image.Image:
    width, height = _page_dimensions(plan)
    modes = {panel.mode for panel in plan.panels}
    if modes not in ({"RGB"}, {"RGBA"}):
        raise ValueError("atlas page must contain one supported native mode")
    mode = next(iter(modes))
    neutral = _ATLAS_NEUTRAL_RGBA if mode == "RGBA" else _ATLAS_NEUTRAL_RGBA[:3]
    canvas = Image.new(mode, (width, height), neutral)
    for panel in plan.panels:
        source = snapshots[panel.source_id].image
        if source.mode != mode:
            raise ValueError(f"atlas panel mode mismatch: {panel.source_id}")
        canvas.paste(source, (panel.x, panel.y))
    return canvas


def _directory_entries(path: Path) -> tuple[str, ...] | None:
    metadata = _existing_leaf_metadata(path)
    if metadata is None:
        return None
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"atlas output root is not a directory: {_absolute(path)}")
    anchor = _open_parent(path)
    descriptor = -1
    try:
        descriptor = os.open(anchor.leaf, _DIRECTORY_FLAGS, dir_fd=anchor.parent_fd)
        _revalidate_anchor(anchor, leaf_identity=_identity(metadata))
        return tuple(sorted(os.listdir(descriptor)))
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        anchor.close()


def _existing_atlas_pages(output_root: Path) -> tuple[Path, ...]:
    entries = _directory_entries(output_root)
    if entries is None:
        return ()
    unknown = [
        entry
        for entry in entries
        if entry != "index.json" and _ATLAS_PAGE_NAME.fullmatch(entry) is None
    ]
    if unknown:
        raise ValueError(f"unknown atlas output file: {unknown[0]}")
    page_names = tuple(entry for entry in entries if _ATLAS_PAGE_NAME.fullmatch(entry))
    for page_name in page_names:
        _existing_leaf_metadata(output_root / page_name)
    if not page_names and "index.json" not in entries:
        return ()
    if "index.json" not in entries:
        raise ValueError("unknown atlas output state: pages have no canonical index")
    try:
        payload = load_json_file(output_root / "index.json", "existing atlas index")
        if not isinstance(payload, dict) or not isinstance(payload.get("index"), dict):
            raise ValueError("existing atlas index is invalid")
        index_payload = payload["index"]
        if (
            index_payload.get("schemaVersion") != _SCHEMA_VERSION
            or index_payload.get("toolVersion") != _TOOL_VERSION
            or index_payload.get("digestVersion") != _DIGEST_VERSION
            or index_payload.get("packingAlgorithm") != _ATLAS_PACKING_ALGORITHM
            or index_payload.get("baseMaxDimension") != _ATLAS_BASE_DIMENSION
            or index_payload.get("padding") != _ATLAS_PADDING
            or index_payload.get("neutralRGBA") != list(_ATLAS_NEUTRAL_RGBA)
        ):
            raise ValueError("existing atlas index version or packing mismatch")
        if index_payload.get("outputRoot") != str(_absolute(output_root)):
            raise ValueError("existing atlas index output root mismatch")
        supplied_index_digest = index_payload.get("atlasIndexSHA256")
        if not isinstance(supplied_index_digest, str) or not _SHA256.fullmatch(
            supplied_index_digest
        ):
            raise ValueError("existing atlas index digest is invalid")
        unsigned_index = dict(index_payload)
        unsigned_index.pop("atlasIndexSHA256", None)
        if _canonical_sha256(unsigned_index) != supplied_index_digest:
            raise ValueError("existing atlas index digest mismatch")
        source_records = index_payload.get("sources")
        if not isinstance(source_records, list) or not source_records:
            raise ValueError("existing atlas source records are invalid")
        if index_payload.get("sourceLockSHA256") != _source_lock_digest_records(
            source_records
        ):
            raise ValueError("existing atlas source lock digest mismatch")
        page_records = index_payload.get("pages")
        if not isinstance(page_records, list):
            raise ValueError("existing atlas index pages are invalid")
        recorded_names: list[str] = []
        for record in page_records:
            if not isinstance(record, dict):
                raise ValueError("existing atlas page record is invalid")
            page_path = Path(str(record.get("path", "")))
            if page_path.parent != _absolute(output_root):
                raise ValueError("existing atlas page path mismatch")
            recorded_names.append(page_path.name)
            snapshot = _snapshot_image(page_path)
            if (
                snapshot.format != "PNG"
                or snapshot.image.mode != record.get("mode")
                or snapshot.image.width != record.get("width")
                or snapshot.image.height != record.get("height")
                or snapshot.byte_sha256 != record.get("byteSHA256")
                or snapshot.decoded_pixel_sha256 != record.get("decodedPixelSHA256")
            ):
                raise ValueError("existing atlas page hash mismatch")
        if tuple(sorted(recorded_names)) != page_names:
            raise ValueError("existing atlas page set mismatch")
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error).startswith("existing atlas"):
            raise
        raise ValueError("existing atlas index is invalid") from error
    return tuple(_absolute(output_root / name) for name in page_names)


def _prepare_atlas(
    sources: Sequence[LockedSource], output_dir: Path, max_pages: int
) -> tuple[AtlasIndex, list[tuple[Path, bytes]], tuple[Path, ...]]:
    if (
        isinstance(max_pages, bool)
        or not isinstance(max_pages, int)
        or not 1 <= max_pages <= 5
    ):
        raise ValueError("max_pages must be an integer from 1 through 5")
    if not sources:
        raise ValueError("at least one locked source is required")
    output_root = _absolute(output_dir)
    _owner_context(output_root)
    ordered = tuple(sorted(sources, key=lambda source: source.source_id))
    identifiers = [source.source_id for source in ordered]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate source ID")
    snapshots: dict[str, _ImageSnapshot] = {}
    for source in ordered:
        _, cache = _validate_locked_source(source)
        if source.mode not in _ATLAS_MODES:
            raise ValueError(
                "unsupported atlas source mode for exact native round-trip: "
                f"{source.source_id} ({source.mode}); supported modes are RGB and RGBA"
            )
        snapshots[source.source_id] = cache
    max_dimension = _atlas_dimension(ordered)
    plans = _plan_atlases(ordered, max_dimension, max_pages)
    pages: list[AtlasPage] = []
    panels: list[AtlasPanel] = []
    page_outputs: list[tuple[Path, bytes]] = []
    for page_number, plan in enumerate(plans, start=1):
        width, height = _page_dimensions(plan)
        canvas = _render_page(plan, snapshots)
        page_bytes = _png_bytes(canvas)
        page_path = output_root / f"page-{page_number:02d}.png"
        page_outputs.append((page_path, page_bytes))
        panels.extend(plan.panels)
        pages.append(
            AtlasPage(
                page_number,
                page_path,
                hashlib.sha256(page_bytes).hexdigest(),
                _decoded_hash_image(canvas),
                canvas.mode,
                width,
                height,
            )
        )
    source_lock_digest = _source_lock_digest(ordered)
    layout_digest = _canonical_sha256(
        _layout_payload(ordered, plans, output_root, max_dimension)
    )
    provisional = AtlasIndex(
        ordered,
        tuple(pages),
        tuple(panels),
        output_root,
        source_lock_digest,
        max_dimension,
        layout_digest,
        "0" * 64,
    )
    index = replace(provisional, atlas_index_sha256=_atlas_index_digest(provisional))
    existing_pages = _existing_atlas_pages(output_root)
    stale_pages = tuple(
        page
        for page in existing_pages
        if page not in {path for path, _ in page_outputs}
    )
    return index, page_outputs, stale_pages


def _atlas_report_payload(index: AtlasIndex) -> dict[str, object]:
    return {
        "index": index.to_json(),
        "verification": {"valid": True, "verified_panels": len(index.panels)},
    }


def _validated_atlas_report_path(
    output_root: Path, report_path: Path | None
) -> Path | None:
    if report_path is None:
        return None
    root = _absolute(output_root)
    report = _absolute(report_path)
    canonical = root / "index.json"
    if report == canonical:
        return report
    if report == root or root in report.parents or report in root.parents:
        raise ValueError(
            "custom atlas report must be outside the atlas output root; "
            "use the canonical output-root/index.json instead"
        )
    return report


def preflight_atlas_command_paths(
    manifest_path: Path,
    output_dir: Path,
    report_path: Path | None,
) -> None:
    """Validate all caller-provided atlas command paths before source loading."""

    output_root = _absolute(output_dir)
    report = _validated_atlas_report_path(output_root, report_path)
    roles = [
        PathRole("manifest", manifest_path, "input"),
        PathRole("output root", output_root, "directory"),
    ]
    if report is not None:
        roles.append(PathRole("report", report, "output"))
    preflight_path_roles(roles)


def _build_and_publish_atlases(
    sources: Sequence[LockedSource],
    output_dir: Path,
    *,
    max_pages: int,
    report_path: Path | None,
) -> AtlasIndex:
    output_root = _absolute(output_dir)
    report = _validated_atlas_report_path(output_root, report_path)
    canonical_report = output_root / "index.json"
    roles = [PathRole("output root", output_root, "directory")]
    for index, source in enumerate(sources):
        roles.extend(
            [
                PathRole(f"original[{index}]", source.original_path, "input"),
                PathRole(f"cache[{index}]", source.cache_path, "input"),
            ]
        )
    if report is not None and report != canonical_report:
        roles.append(PathRole("report", report, "output"))
    preflight_path_roles(roles)
    index, page_outputs, stale_pages = _prepare_atlas(sources, output_root, max_pages)
    payload = (
        json.dumps(
            _atlas_report_payload(index),
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")
    complete_roles = list(roles)
    complete_roles.extend(
        PathRole(f"page[{number}]", path, "output")
        for number, (path, _) in enumerate(page_outputs, start=1)
    )
    complete_roles.extend(
        PathRole(f"stale page[{number}]", path, "output")
        for number, path in enumerate(stale_pages, start=1)
    )
    complete_roles.append(PathRole("canonical index", canonical_report, "output"))
    preflight_path_roles(complete_roles)
    publications = [
        _Publication(path, page_bytes, f"page[{number}]")
        for number, (path, page_bytes) in enumerate(page_outputs, start=1)
    ]
    publications.extend(
        _Publication(path, None, f"stale page[{number}]")
        for number, path in enumerate(stale_pages, start=1)
    )
    if report is not None and report != canonical_report:
        publications.append(_Publication(report, payload, "report"))
    publications.append(_Publication(canonical_report, payload, "canonical index"))

    def validate_publication() -> None:
        verify_atlas_round_trip(index)

    _publish_artifacts(
        publications,
        validate_before_commit=validate_publication,
    )
    return index


def build_lossless_atlases(
    sources: Sequence[LockedSource], output_dir: Path, *, max_pages: int = 5
) -> AtlasIndex:
    return _build_and_publish_atlases(
        sources, output_dir, max_pages=max_pages, report_path=None
    )


def build_lossless_atlases_with_report(
    sources: Sequence[LockedSource],
    output_dir: Path,
    *,
    max_pages: int = 5,
    report_path: Path | None = None,
) -> AtlasIndex:
    return _build_and_publish_atlases(
        sources, output_dir, max_pages=max_pages, report_path=report_path
    )


def _rectangles_overlap(left: AtlasPanel, right: AtlasPanel) -> bool:
    return not (
        left.x + left.width <= right.x
        or right.x + right.width <= left.x
        or left.y + left.height <= right.y
        or right.y + right.height <= left.y
    )


def verify_atlas_round_trip(index: AtlasIndex) -> AtlasVerification:
    if (
        index.digest_version != _DIGEST_VERSION
        or index.base_max_dimension != _ATLAS_BASE_DIMENSION
        or index.padding != _ATLAS_PADDING
        or index.neutral_rgba != _ATLAS_NEUTRAL_RGBA
        or index.packing_algorithm != _ATLAS_PACKING_ALGORITHM
        or index.search_node_limit != _ATLAS_SEARCH_NODE_LIMIT
        or index.max_dimension != _atlas_dimension(index.sources)
    ):
        raise ValueError("atlas index packing constants were tampered")
    if not 1 <= len(index.pages) <= 5:
        raise ValueError("atlas index must contain one through five pages")
    source_ids = [source.source_id for source in index.sources]
    if source_ids != sorted(source_ids) or len(set(source_ids)) != len(source_ids):
        raise ValueError("atlas sources must be unique and sorted")
    sources = {source.source_id: source for source in index.sources}
    source_images: dict[str, Image.Image] = {}
    source_snapshots: dict[str, _ImageSnapshot] = {}
    for source in index.sources:
        _, cache = _validate_locked_source(source)
        if source.mode not in _ATLAS_MODES:
            raise ValueError(
                "unsupported atlas source mode for exact native round-trip: "
                f"{source.source_id} ({source.mode}); supported modes are RGB and RGBA"
            )
        source_images[source.source_id] = cache.image
        source_snapshots[source.source_id] = cache
    if index.source_lock_sha256 != _source_lock_digest(index.sources):
        raise ValueError("atlas source lock digest mismatch")
    page_numbers = [page.number for page in index.pages]
    if page_numbers != list(range(1, len(index.pages) + 1)):
        raise ValueError("atlas page numbers must be consecutive")
    if len({page.path for page in index.pages}) != len(index.pages):
        raise ValueError("duplicate atlas page paths")
    pages = {page.number: page for page in index.pages}
    used_pages = {panel.page_number for panel in index.panels}
    if used_pages != set(page_numbers):
        raise ValueError("unused atlas page or panel references a missing page")
    seen_panels: set[str] = set()
    page_panels: dict[int, list[AtlasPanel]] = {number: [] for number in page_numbers}
    for panel in index.panels:
        if panel.source_id in seen_panels or panel.source_id not in sources:
            raise ValueError("tampered atlas panel mapping")
        seen_panels.add(panel.source_id)
        if panel.page_number not in pages:
            raise ValueError("tampered atlas panel page mapping")
        source = sources[panel.source_id]
        if (
            panel.width,
            panel.height,
            panel.mode,
            panel.decoded_pixel_sha256,
        ) != (
            source.width,
            source.height,
            source.mode,
            source.decoded_pixel_sha256,
        ):
            raise ValueError(f"tampered atlas panel record: {panel.source_id}")
        if pages[panel.page_number].mode != panel.mode:
            raise ValueError(f"atlas page/panel mode mismatch: {panel.source_id}")
        if min(panel.x, panel.y, panel.width, panel.height) < 0:
            raise ValueError(f"invalid atlas panel rectangle: {panel.source_id}")
        page_panels[panel.page_number].append(panel)
    if seen_panels != set(source_ids):
        raise ValueError("atlas omits locked source")
    for number, panels in page_panels.items():
        for offset, panel in enumerate(panels):
            if any(_rectangles_overlap(panel, other) for other in panels[offset + 1 :]):
                raise ValueError(f"atlas panel overlap on page {number}")
    page_snapshots: dict[int, _ImageSnapshot] = {}
    output_root = _absolute(index.output_root)
    _owner_context(output_root)
    for page in index.pages:
        _owner_context(page.path)
        if _absolute(page.path) != output_root / f"page-{page.number:02d}.png":
            raise ValueError(f"atlas page path mismatch: {page.number}")
        snapshot = _snapshot_image(page.path)
        if (
            snapshot.format != "PNG"
            or page.mode not in _ATLAS_MODES
            or snapshot.image.mode != page.mode
        ):
            raise ValueError(f"atlas page format or mode mismatch: {page.number}")
        if (snapshot.image.width, snapshot.image.height) != (page.width, page.height):
            raise ValueError(f"atlas page dimensions mismatch: {page.number}")
        if snapshot.byte_sha256 != page.byte_sha256:
            raise ValueError(f"atlas page hash mismatch: {page.path}")
        if snapshot.decoded_pixel_sha256 != page.decoded_pixel_sha256:
            raise ValueError(f"atlas page pixel hash mismatch: {page.path}")
        page_snapshots[page.number] = snapshot
    expected_plans = _plan_atlases(index.sources, index.max_dimension, len(index.pages))
    expected_panels = tuple(panel for plan in expected_plans for panel in plan.panels)
    if len(expected_plans) != len(index.pages):
        raise ValueError("atlas page count does not match deterministic layout")
    if expected_panels != index.panels:
        raise ValueError("atlas panel records do not match deterministic layout")
    for page, plan in zip(index.pages, expected_plans):
        if (page.width, page.height) != _page_dimensions(plan):
            raise ValueError(f"atlas page dimensions mismatch: {page.number}")
    expected_layout = _canonical_sha256(
        _layout_payload(index.sources, expected_plans, output_root, index.max_dimension)
    )
    if index.layout_sha256 != expected_layout:
        raise ValueError("atlas canonical layout digest mismatch")
    if index.atlas_index_sha256 != _atlas_index_digest(index):
        raise ValueError("atlas index canonical digest mismatch")
    for page, plan in zip(index.pages, expected_plans):
        expected_image = _render_page(plan, source_snapshots)
        actual = page_snapshots[page.number]
        if actual.image.tobytes() != expected_image.tobytes():
            raise ValueError(f"atlas canonical page pixels mismatch: {page.number}")
        if actual.data != _png_bytes(expected_image):
            raise ValueError(f"atlas canonical page bytes mismatch: {page.number}")
    for panel in index.panels:
        page_image = page_snapshots[panel.page_number].image
        if (
            panel.x + panel.width > page_image.width
            or panel.y + panel.height > page_image.height
        ):
            raise ValueError(f"atlas panel outside page: {panel.source_id}")
        cropped = page_image.crop(
            (panel.x, panel.y, panel.x + panel.width, panel.y + panel.height)
        )
        source_image = source_images[panel.source_id]
        if (
            cropped.mode != source_image.mode
            or cropped.size != source_image.size
            or cropped.tobytes() != source_image.tobytes()
            or _decoded_hash_image(cropped) != panel.decoded_pixel_sha256
        ):
            raise ValueError(f"atlas round-trip pixels mismatch: {panel.source_id}")
    return AtlasVerification(True, len(index.panels))


@dataclass(frozen=True)
class ChromaConfig:
    key_rgb: tuple[int, int, int] = (0, 255, 0)
    distance_threshold: int = 36
    edge_distance_threshold: int = 72

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key_rgb, tuple)
            or len(self.key_rgb) != 3
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 255
                for value in self.key_rgb
            )
        ):
            raise ValueError("key_rgb must contain three integer bytes")
        if (
            isinstance(self.distance_threshold, bool)
            or isinstance(self.edge_distance_threshold, bool)
            or not isinstance(self.distance_threshold, int)
            or not isinstance(self.edge_distance_threshold, int)
            or not 0 <= self.distance_threshold < self.edge_distance_threshold <= 255
        ):
            raise ValueError("chroma thresholds must be increasing integer bytes")

    def to_json(self) -> dict[str, object]:
        return {
            "keyRGB": list(self.key_rgb),
            "distanceThreshold": self.distance_threshold,
            "edgeDistanceThreshold": self.edge_distance_threshold,
        }


_CHROMA_CONFIG_FIELDS = {
    "keyRGB",
    "distanceThreshold",
    "edgeDistanceThreshold",
}


def load_chroma_config(path: Path) -> ChromaConfig:
    payload = _exact_object(
        load_json_file(path, "chroma config"),
        label="chroma config",
        required=_CHROMA_CONFIG_FIELDS,
    )
    key = payload["keyRGB"]
    if not isinstance(key, list) or len(key) != 3:
        raise ValueError("chroma config keyRGB must contain three integer bytes")
    return ChromaConfig(
        tuple(
            _required_integer(value, f"chroma config keyRGB[{index}]")
            for index, value in enumerate(key)
        ),  # type: ignore[arg-type]
        _required_integer(
            payload["distanceThreshold"], "chroma config distanceThreshold"
        ),
        _required_integer(
            payload["edgeDistanceThreshold"],
            "chroma config edgeDistanceThreshold",
        ),
    )


@dataclass(frozen=True)
class TransparencyReport:
    config: ChromaConfig
    input_byte_sha256: str
    output_byte_sha256: str
    decoded_pixel_sha256: str
    width: int
    height: int
    mode: str
    minimum_alpha: int
    maximum_alpha: int
    corner_alpha: tuple[int, int, int, int]
    transparent_fraction: float
    boundary_connected_opaque_flood_count: int
    remaining_key_fringe_count: int

    def to_json(self) -> dict[str, object]:
        return {
            "schemaVersion": _SCHEMA_VERSION,
            "toolVersion": _TOOL_VERSION,
            "config": self.config.to_json(),
            "inputByteSHA256": self.input_byte_sha256,
            "outputByteSHA256": self.output_byte_sha256,
            "decodedPixelSHA256": self.decoded_pixel_sha256,
            "width": self.width,
            "height": self.height,
            "mode": self.mode,
            "minimumAlpha": self.minimum_alpha,
            "maximumAlpha": self.maximum_alpha,
            "cornerAlpha": list(self.corner_alpha),
            "transparentFraction": self.transparent_fraction,
            "boundaryConnectedOpaqueFloodCount": self.boundary_connected_opaque_flood_count,
            "remainingKeyFringeCount": self.remaining_key_fringe_count,
        }


def _distance(rgb: tuple[int, int, int], key: tuple[int, int, int]) -> float:
    return math.sqrt(
        sum((left - right) ** 2 for left, right in zip(rgb, key, strict=True))
    )


def _neighbors(x: int, y: int, width: int, height: int) -> tuple[tuple[int, int], ...]:
    return tuple(
        (nx, ny)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
        if 0 <= nx < width and 0 <= ny < height
    )


def _boundary_points(width: int, height: int) -> tuple[tuple[int, int], ...]:
    points = [(x, 0) for x in range(width)]
    if height > 1:
        points.extend((x, height - 1) for x in range(width))
    points.extend((0, y) for y in range(1, height - 1))
    if width > 1:
        points.extend((width - 1, y) for y in range(1, height - 1))
    return tuple(points)


def _boundary_connected(
    image: Image.Image, key: tuple[int, int, int], threshold: int
) -> set[tuple[int, int]]:
    width, height = image.size
    queue: deque[tuple[int, int]] = deque()
    queued: set[tuple[int, int]] = set()
    for point in _boundary_points(width, height):
        pixel = image.getpixel(point)
        if _distance(pixel[:3], key) <= threshold:
            queue.append(point)
            queued.add(point)
    connected: set[tuple[int, int]] = set()
    while queue:
        point = queue.popleft()
        connected.add(point)
        for neighbor in _neighbors(*point, width, height):
            if neighbor in queued:
                continue
            pixel = image.getpixel(neighbor)
            if _distance(pixel[:3], key) <= threshold:
                queued.add(neighbor)
                queue.append(neighbor)
    return connected


def _boundary_opaque_flood_count(image: Image.Image) -> int:
    """Count broad boundary floods and alpha-weighted inset mattes.

    Broad boundary contact remains a per-component decision. Inset matte
    classification instead uses the union of every nonzero-alpha pixel, so a
    one-pixel transparent seam cannot partition a baked background into safe
    sub-threshold components. The union records bbox area (B), alpha fill (F),
    dense-row/column fractions (R/C), and the mean opacity deficit (D) in the
    bbox core after excluding a three-pixel perimeter. Its continuous effective
    area is ``B + min(.10, 18 * D)``.

    Alpha-only inspection still cannot distinguish every giant rectangular
    product from a pixel-identical matte. The conservative 70% effective-area
    threshold deliberately leaves 50--65% product silhouettes to mandatory
    human review. The scan is O(width * height); union statistics add only
    O(width + height) counters, while the component traversal uses flat integer
    offsets rather than coordinate tuples.
    """

    width, height = image.size
    canvas_area = width * height
    minimum_size = max(
        _OPAQUE_FLOOD_MIN_PIXELS,
        math.ceil(canvas_area * _OPAQUE_FLOOD_MIN_AREA_FRACTION),
    )
    boundary_length = width * 2 + max(0, height - 2) * min(2, width)
    minimum_boundary_contact = max(
        4, math.ceil(boundary_length * _OPAQUE_FLOOD_MIN_BOUNDARY_FRACTION)
    )
    alpha = image.getchannel("A").tobytes()
    visited = bytearray(canvas_area)
    row_alpha_mass = [0] * height
    column_alpha_mass = [0] * width
    total_nonzero = 0
    total_alpha_mass = 0
    union_min_x = width
    union_max_x = -1
    union_min_y = height
    union_max_y = -1
    flood_count = 0
    for seed in range(canvas_area):
        if visited[seed] or alpha[seed] == 0:
            continue
        queue: deque[int] = deque([seed])
        visited[seed] = 1
        component_size = 0
        alpha_sum = 0
        boundary_alpha_sum = 0
        boundary_band_contact = 0
        while queue:
            offset = queue.popleft()
            y, x = divmod(offset, width)
            opacity = alpha[offset]
            component_size += 1
            alpha_sum += opacity
            total_nonzero += 1
            total_alpha_mass += opacity
            union_min_x = min(union_min_x, x)
            union_max_x = max(union_max_x, x)
            union_min_y = min(union_min_y, y)
            union_max_y = max(union_max_y, y)
            row_alpha_mass[y] += opacity
            column_alpha_mass[x] += opacity
            if x < 2 or y < 2 or x >= width - 2 or y >= height - 2:
                boundary_band_contact += 1
                boundary_alpha_sum += opacity
            if x > 0:
                neighbor = offset - 1
                if not visited[neighbor] and alpha[neighbor] > 0:
                    visited[neighbor] = 1
                    queue.append(neighbor)
            if x + 1 < width:
                neighbor = offset + 1
                if not visited[neighbor] and alpha[neighbor] > 0:
                    visited[neighbor] = 1
                    queue.append(neighbor)
            if y > 0:
                neighbor = offset - width
                if not visited[neighbor] and alpha[neighbor] > 0:
                    visited[neighbor] = 1
                    queue.append(neighbor)
            if y + 1 < height:
                neighbor = offset + width
                if not visited[neighbor] and alpha[neighbor] > 0:
                    visited[neighbor] = 1
                    queue.append(neighbor)

        mean_opacity = alpha_sum / (component_size * 255)
        effective_size = alpha_sum / 255
        boundary_flood = (
            mean_opacity >= _MATTE_MIN_MEAN_OPACITY
            and effective_size >= minimum_size
            and boundary_alpha_sum / 255 >= minimum_boundary_contact
            and boundary_band_contact >= minimum_boundary_contact
        )
        if boundary_flood:
            flood_count += component_size

    if total_nonzero:
        box_width = union_max_x - union_min_x + 1
        box_height = union_max_y - union_min_y + 1
        box_area = box_width * box_height
        canvas_fraction = box_area / canvas_area
        alpha_fill = total_alpha_mass / (255 * box_area)
        dense_rows = sum(
            row_alpha_mass[y] / (255 * box_width) >= _INSET_MATTE_DENSE_LINE_FRACTION
            for y in range(union_min_y, union_max_y + 1)
        )
        dense_columns = sum(
            column_alpha_mass[x] / (255 * box_height)
            >= _INSET_MATTE_DENSE_LINE_FRACTION
            for x in range(union_min_x, union_max_x + 1)
        )
        core_deficit_sum = 0.0
        core_nonzero = 0
        core_left = union_min_x + _INSET_MATTE_CORE_PERIMETER
        core_right = union_max_x - _INSET_MATTE_CORE_PERIMETER
        core_top = union_min_y + _INSET_MATTE_CORE_PERIMETER
        core_bottom = union_max_y - _INSET_MATTE_CORE_PERIMETER
        if core_left <= core_right and core_top <= core_bottom:
            for y in range(core_top, core_bottom + 1):
                row_offset = y * width
                for x in range(core_left, core_right + 1):
                    opacity = alpha[row_offset + x]
                    if opacity:
                        core_nonzero += 1
                        core_deficit_sum += (255 - opacity) / 255
        mean_core_deficit = core_deficit_sum / core_nonzero if core_nonzero else 0.0
        effective_area = canvas_fraction + min(
            _INSET_MATTE_MAX_DEFICIT_BOOST,
            _INSET_MATTE_DEFICIT_WEIGHT * mean_core_deficit,
        )
        inset_matte = (
            effective_area >= _INSET_MATTE_MIN_EFFECTIVE_AREA
            and alpha_fill >= _INSET_MATTE_MIN_ALPHA_FILL
            and dense_rows / box_height >= _INSET_MATTE_MIN_DENSE_AXIS_FRACTION
            and dense_columns / box_width >= _INSET_MATTE_MIN_DENSE_AXIS_FRACTION
        )
        if inset_matte:
            flood_count += total_nonzero
    return flood_count


def _transparency_report(
    snapshot: _ImageSnapshot,
    config: ChromaConfig,
    *,
    input_hash: str,
) -> TransparencyReport:
    if snapshot.format != "PNG":
        raise ValueError("transparency output must be PNG")
    image = snapshot.image
    if image.mode != "RGBA":
        raise ValueError("transparency output must be RGBA")
    alpha = image.getchannel("A").tobytes()
    corners = tuple(
        image.getpixel(point)[3]
        for point in (
            (0, 0),
            (image.width - 1, 0),
            (0, image.height - 1),
            (image.width - 1, image.height - 1),
        )
    )
    rgba = image.tobytes()
    fringe_threshold_squared = config.edge_distance_threshold**2
    fringe = 0
    key_red, key_green, key_blue = config.key_rgb
    for offset in range(0, len(rgba), 4):
        red, green, blue, opacity = rgba[offset : offset + 4]
        if opacity == 0:
            continue
        distance_squared = (
            (red - key_red) ** 2 + (green - key_green) ** 2 + (blue - key_blue) ** 2
        )
        if distance_squared < fringe_threshold_squared:
            fringe += 1
    return TransparencyReport(
        config,
        input_hash,
        snapshot.byte_sha256,
        snapshot.decoded_pixel_sha256,
        image.width,
        image.height,
        image.mode,
        min(alpha),
        max(alpha),
        corners,  # type: ignore[arg-type]
        alpha.count(0) / len(alpha),
        _boundary_opaque_flood_count(image),
        fringe,
    )


def _decontaminate_pixel(
    pixel: tuple[int, int, int, int], config: ChromaConfig
) -> tuple[int, int, int, int]:
    red, green, blue, alpha = pixel
    distance = _distance((red, green, blue), config.key_rgb)
    coverage = (distance - config.distance_threshold) / (
        config.edge_distance_threshold - config.distance_threshold
    )
    coverage = max(0.0, min(1.0, coverage))
    if coverage == 0:
        return red, green, blue, 0
    recovered = tuple(
        max(0, min(255, round((channel - (1.0 - coverage) * key) / coverage)))
        for channel, key in zip((red, green, blue), config.key_rgb, strict=True)
    )
    return recovered[0], recovered[1], recovered[2], min(alpha, round(alpha * coverage))


def _prepare_chroma(
    input_path: Path, output_path: Path, config: ChromaConfig
) -> tuple[bytes, TransparencyReport]:
    input_absolute = _absolute(input_path)
    output_absolute = _absolute(output_path)
    if input_absolute == output_absolute:
        raise ValueError("refusing to key in place")
    snapshot = _snapshot_image(input_path)
    image = snapshot.image.convert("RGBA")
    original = image.copy()
    connected = _boundary_connected(original, config.key_rgb, config.distance_threshold)
    frontier: set[tuple[int, int]] = set()
    edge_queue: deque[tuple[int, int]] = deque(connected)
    examined = set(connected)
    while edge_queue:
        point = edge_queue.popleft()
        for neighbor in _neighbors(*point, image.width, image.height):
            if neighbor in examined:
                continue
            examined.add(neighbor)
            pixel = original.getpixel(neighbor)
            distance = _distance(pixel[:3], config.key_rgb)
            if (
                config.distance_threshold < distance < config.edge_distance_threshold
                and pixel[3] > 0
            ):
                frontier.add(neighbor)
                edge_queue.append(neighbor)
    output_pixels = image.load()
    for x, y in connected:
        red, green, blue, _ = original.getpixel((x, y))
        output_pixels[x, y] = (red, green, blue, 0)
    for x, y in frontier:
        output_pixels[x, y] = _decontaminate_pixel(original.getpixel((x, y)), config)
    output_bytes = _png_bytes(image)
    output_snapshot = _snapshot_image_bytes(output_absolute, output_bytes)
    report = _transparency_report(
        output_snapshot, config, input_hash=snapshot.byte_sha256
    )
    return output_bytes, report


def remove_chroma(
    input_path: Path, output_path: Path, config: ChromaConfig
) -> TransparencyReport:
    if _absolute(input_path) == _absolute(output_path):
        raise ValueError("refusing to key in place")
    preflight_path_roles(
        [
            PathRole("input", input_path, "input"),
            PathRole("output", output_path, "output"),
        ]
    )
    output_bytes, report = _prepare_chroma(input_path, output_path, config)
    _publish_artifacts([_Publication(output_path, output_bytes, "output")])
    return report


def remove_chroma_with_report(
    input_path: Path,
    output_path: Path,
    config: ChromaConfig,
    report_path: Path,
    *,
    config_path: Path | None = None,
) -> TransparencyReport:
    roles = [
        PathRole("input", input_path, "input"),
        PathRole("output", output_path, "output"),
        PathRole("report", report_path, "output"),
    ]
    if config_path is not None:
        roles.append(PathRole("config", config_path, "input"))
    preflight_path_roles(roles)
    output_bytes, report = _prepare_chroma(input_path, output_path, config)
    report_bytes = (
        json.dumps(report.to_json(), indent=2, sort_keys=True, separators=(",", ": "))
        + "\n"
    ).encode("utf-8")
    _publish_artifacts(
        [
            _Publication(output_path, output_bytes, "output"),
            _Publication(report_path, report_bytes, "report"),
        ]
    )
    return report


def _inspect_with_config(
    path: Path, expected_width: int, expected_height: int, config: ChromaConfig
) -> TransparencyReport:
    if (
        isinstance(expected_width, bool)
        or isinstance(expected_height, bool)
        or not isinstance(expected_width, int)
        or not isinstance(expected_height, int)
        or expected_width <= 0
        or expected_height <= 0
    ):
        raise ValueError("expected transparency dimensions must be positive integers")
    snapshot = _snapshot_image(path)
    report = _transparency_report(snapshot, config, input_hash=snapshot.byte_sha256)
    if (report.width, report.height) != (expected_width, expected_height):
        raise ValueError("unexpected transparency dimensions")
    if report.minimum_alpha != 0 or report.maximum_alpha == 0:
        raise ValueError("output is all opaque or fully transparent")
    if report.corner_alpha != (0, 0, 0, 0):
        raise ValueError("transparent corners are required")
    if report.boundary_connected_opaque_flood_count:
        raise ValueError("boundary opaque flood remains")
    if report.remaining_key_fringe_count:
        raise ValueError("key fringe remains")
    return report


def inspect_transparency(
    path: Path,
    expected_width: int,
    expected_height: int,
    key_rgb: tuple[int, int, int],
) -> TransparencyReport:
    return _inspect_with_config(
        path,
        expected_width,
        expected_height,
        ChromaConfig(key_rgb=key_rgb),
    )


def inspect_transparency_with_config(
    path: Path,
    expected_width: int,
    expected_height: int,
    config: ChromaConfig,
) -> TransparencyReport:
    return _inspect_with_config(path, expected_width, expected_height, config)


def inspect_transparency_with_report(
    path: Path,
    expected_width: int,
    expected_height: int,
    config: ChromaConfig,
    report_path: Path,
    *,
    config_path: Path | None = None,
) -> TransparencyReport:
    roles = [
        PathRole("image", path, "input"),
        PathRole("report", report_path, "output"),
    ]
    if config_path is not None:
        roles.append(PathRole("config", config_path, "input"))
    preflight_path_roles(roles)
    report = _inspect_with_config(path, expected_width, expected_height, config)
    report_bytes = (
        json.dumps(report.to_json(), indent=2, sort_keys=True, separators=(",", ": "))
        + "\n"
    ).encode("utf-8")
    _publish_artifacts([_Publication(report_path, report_bytes, "report")])
    return report
