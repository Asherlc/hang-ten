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
import stat
import tempfile
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

import PIL
from PIL import Image, UnidentifiedImageError


_TOOL_VERSION = "cord-render-assets/1"
_SCHEMA_VERSION = 1
_OWNER_PREFIX = "joyful-donkey-"
_ATLAS_MAX_DIMENSION = 2048
_ATLAS_PADDING = 8
_ATLAS_MODES = frozenset({"1", "L", "LA", "P", "RGB", "RGBA"})
_SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlink_components(path: Path) -> None:
    absolute = _absolute(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"symlink path components are rejected: {current}")


def _owner_context(path: Path) -> Path:
    """Return the strict owner root containing *path* without following links."""

    absolute = _absolute(path)
    parts = absolute.parts
    for index, part in enumerate(parts[:-1]):
        if (
            part == ".context"
            and index + 1 < len(parts)
            and parts[index + 1].startswith(_OWNER_PREFIX)
            and len(parts[index + 1]) > len(_OWNER_PREFIX)
        ):
            _reject_symlink_components(absolute)
            root = Path(*parts[: index + 2])
            resolved = absolute.resolve(strict=False)
            resolved_root = root.resolve(strict=False)
            if resolved == resolved_root or resolved_root in resolved.parents:
                return resolved_root
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
        return root.resolve(strict=False)
    return Path(__file__).resolve().parents[4]


def _prepare_owner_path(path: Path) -> tuple[Path, Path]:
    owner = _owner_context(path)
    target = _absolute(path).resolve(strict=False)
    if target == owner or owner not in target.parents:
        raise ValueError("output path escapes its owner context")
    _reject_symlink_components(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(target)
    resolved_parent = target.parent.resolve(strict=True)
    if resolved_parent != owner and owner not in resolved_parent.parents:
        raise ValueError("output path escapes its owner context")
    return owner, target


def _atomic_write_bytes(path: Path, payload: bytes) -> Path:
    _, target = _prepare_owner_path(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.tmp-", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if target.exists() and target.is_symlink():
            raise ValueError(f"symlink outputs are rejected: {target}")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target.resolve(strict=True)


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
    source = _absolute(path)
    _reject_symlink_components(source)
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(source, flags)
    except (FileNotFoundError, OSError) as error:
        raise ValueError(f"expected a readable regular image: {source}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"expected a readable regular image: {source}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    data = b"".join(chunks)
    if identity_before != identity_after or len(data) != before.st_size:
        raise ValueError(f"source changed while it was being locked: {source}")
    try:
        current = source.lstat()
    except OSError as error:
        raise ValueError(f"source changed while it was being locked: {source}") from error
    path_identity = (
        current.st_dev,
        current.st_ino,
        current.st_size,
        current.st_mtime_ns,
    )
    if stat.S_ISLNK(current.st_mode) or path_identity != identity_before:
        raise ValueError(f"source changed while it was being locked: {source}")
    image, image_format = _decode_image(data, source)
    return _ImageSnapshot(
        source,
        data,
        hashlib.sha256(data).hexdigest(),
        image,
        image_format,
        _decoded_hash_image(image),
    )


def _image(path: Path) -> Image.Image:
    return _snapshot_image(path).image


def _sha256(path: Path) -> str:
    return _snapshot_image(path).byte_sha256


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
        }


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
    if not isinstance(reviewed_at, date):
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
    suffix = snapshot.path.suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ".image"
    cache_path = owner / "sources" / "locked" / (
        f"{source_id}-{snapshot.byte_sha256}{suffix}"
    )
    resolved_cache = _atomic_write_bytes(cache_path, snapshot.data)
    return LockedSource(
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
        resolved_cache,
    )


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


def _load_json(path: Path, label: str) -> object:
    absolute = _absolute(path)
    _reject_symlink_components(absolute)
    try:
        text = absolute.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"unable to read {label}: {absolute}") from error
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


def freeze_source_manifest(manifest: Path) -> tuple[LockedSource, ...]:
    """Atomically replace a source manifest with its frozen lock artifact."""

    owner = _owner_context(manifest)
    payload = _exact_object(
        _load_json(manifest, "manifest"), label="manifest", required={"sources"}
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
    locked: list[LockedSource] = []
    for source_path, source_id, url, publisher, role, revision, reviewed_at in parsed:
        snapshot = _snapshot_image(source_path)
        locked.append(
            _lock_snapshot(
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
    artifact = {
        "schemaVersion": _SCHEMA_VERSION,
        "toolVersion": _TOOL_VERSION,
        "kind": "cordSourceLock",
        "sources": [source.to_json() for source in ordered],
    }
    write_owner_json(manifest, artifact)
    return ordered


def source_lock_artifact(sources: Sequence[LockedSource]) -> dict[str, object]:
    return {
        "schemaVersion": _SCHEMA_VERSION,
        "toolVersion": _TOOL_VERSION,
        "kind": "cordSourceLock",
        "sources": [source.to_json() for source in sources],
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
    cache_resolved = _absolute(cache_path).resolve(strict=False)
    expected_cache_root = (manifest_owner / "sources" / "locked").resolve(strict=False)
    if expected_cache_root not in cache_resolved.parents:
        raise ValueError(f"{label}.cachePath escapes the manifest owner cache")
    source = LockedSource(
        source_id,
        _required_string(record["url"], f"{label}.url"),
        _required_string(record["publisher"], f"{label}.publisher"),
        _required_string(record["role"], f"{label}.role"),
        _required_string(record["revision"], f"{label}.revision"),
        reviewed.isoformat(),
        _required_sha256(record["byteSHA256"], f"{label}.byteSHA256"),
        _required_sha256(
            record["decodedPixelSHA256"], f"{label}.decodedPixelSHA256"
        ),
        _required_string(record["mode"], f"{label}.mode"),
        _required_integer(record["width"], f"{label}.width", positive=True),
        _required_integer(record["height"], f"{label}.height", positive=True),
        _absolute(original_path).resolve(strict=False),
        cache_resolved,
    )
    _validate_locked_source(source)
    return source


def load_locked_sources(manifest: Path) -> list[LockedSource]:
    owner = _owner_context(manifest)
    payload = _exact_object(
        _load_json(manifest, "locked source manifest"),
        label="locked source manifest",
        required={"schemaVersion", "toolVersion", "kind", "sources"},
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
    records = payload["sources"]
    if not isinstance(records, list) or not records:
        raise ValueError("locked source manifest.sources must be a non-empty array")
    sources = [
        _locked_source_from_json(record, label=f"sources[{index}]", manifest_owner=owner)
        for index, record in enumerate(records)
    ]
    identifiers = [source.source_id for source in sources]
    if len(set(identifiers)) != len(identifiers):
        duplicate = next(identifier for identifier in identifiers if identifiers.count(identifier) > 1)
        raise ValueError(f"duplicate source ID: {duplicate}")
    if identifiers != sorted(identifiers):
        raise ValueError("locked source manifest sources must be sorted by sourceID")
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


def _validate_locked_source(source: LockedSource) -> tuple[_ImageSnapshot, _ImageSnapshot]:
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
    _required_integer(source.width, "width", positive=True)
    _required_integer(source.height, "height", positive=True)
    if not isinstance(source.original_path, Path) or not isinstance(source.cache_path, Path):
        raise ValueError("locked source paths must be Path values")
    original = _snapshot_image(source.original_path)
    _validate_snapshot_against_source(original, source, "original")
    cache_owner = _owner_context(source.cache_path)
    expected_cache_root = (cache_owner / "sources" / "locked").resolve(strict=False)
    cache_resolved = _absolute(source.cache_path).resolve(strict=False)
    if expected_cache_root not in cache_resolved.parents:
        raise ValueError(f"locked source cache path mismatch: {source.source_id}")
    cache = _snapshot_image(source.cache_path)
    _validate_snapshot_against_source(cache, source, "locked")
    if original.data != cache.data:
        raise ValueError(f"locked source bytes differ from original: {source.source_id}")
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
    max_dimension: int = _ATLAS_MAX_DIMENSION
    padding: int = _ATLAS_PADDING

    def to_json(self) -> dict[str, object]:
        return {
            "schemaVersion": _SCHEMA_VERSION,
            "toolVersion": _TOOL_VERSION,
            "pillowVersion": PIL.__version__,
            "maxDimension": self.max_dimension,
            "padding": self.padding,
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
class _Shelf:
    y: int
    height: int
    next_x: int


@dataclass
class _PagePlan:
    shelves: list[_Shelf]
    panels: list[AtlasPanel]


def _plan_atlases(sources: Sequence[LockedSource]) -> list[_PagePlan]:
    pages: list[_PagePlan] = []
    for source in sources:
        if (
            source.width + _ATLAS_PADDING * 2 > _ATLAS_MAX_DIMENSION
            or source.height + _ATLAS_PADDING * 2 > _ATLAS_MAX_DIMENSION
        ):
            raise ValueError(f"source cannot fit a lossless atlas page: {source.source_id}")
        placement: tuple[_PagePlan, int, int] | None = None
        for page in pages:
            for shelf in page.shelves:
                if (
                    source.height <= shelf.height
                    and shelf.next_x + source.width + _ATLAS_PADDING
                    <= _ATLAS_MAX_DIMENSION
                ):
                    placement = (page, shelf.next_x, shelf.y)
                    shelf.next_x += source.width + _ATLAS_PADDING
                    break
            if placement is not None:
                break
            new_y = (
                _ATLAS_PADDING
                if not page.shelves
                else page.shelves[-1].y + page.shelves[-1].height + _ATLAS_PADDING
            )
            if new_y + source.height + _ATLAS_PADDING <= _ATLAS_MAX_DIMENSION:
                shelf = _Shelf(
                    new_y,
                    source.height,
                    _ATLAS_PADDING + source.width + _ATLAS_PADDING,
                )
                page.shelves.append(shelf)
                placement = (page, _ATLAS_PADDING, new_y)
                break
        if placement is None:
            page = _PagePlan(
                [
                    _Shelf(
                        _ATLAS_PADDING,
                        source.height,
                        _ATLAS_PADDING + source.width + _ATLAS_PADDING,
                    )
                ],
                [],
            )
            pages.append(page)
            placement = (page, _ATLAS_PADDING, _ATLAS_PADDING)
        page, x, y = placement
        page.panels.append(
            AtlasPanel(
                source.source_id,
                pages.index(page) + 1,
                x,
                y,
                source.width,
                source.height,
                source.mode,
                source.decoded_pixel_sha256,
            )
        )
    return pages


def _page_dimensions(plan: _PagePlan) -> tuple[int, int]:
    return (
        max(panel.x + panel.width for panel in plan.panels) + _ATLAS_PADDING,
        max(panel.y + panel.height for panel in plan.panels) + _ATLAS_PADDING,
    )


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=9)
    return buffer.getvalue()


def build_lossless_atlases(
    sources: Sequence[LockedSource], output_dir: Path, *, max_pages: int = 5
) -> AtlasIndex:
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 5:
        raise ValueError("max_pages must be an integer from 1 through 5")
    if not sources:
        raise ValueError("at least one locked source is required")
    _owner_context(output_dir)
    ordered = tuple(sorted(sources, key=lambda source: source.source_id))
    identifiers = [source.source_id for source in ordered]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate source ID")
    snapshots: dict[str, _ImageSnapshot] = {}
    for source in ordered:
        _, cache = _validate_locked_source(source)
        if source.mode not in _ATLAS_MODES:
            raise ValueError(
                f"source mode cannot round-trip through an RGBA atlas: {source.source_id} ({source.mode})"
            )
        snapshots[source.source_id] = cache
    plans = _plan_atlases(ordered)
    if len(plans) > max_pages:
        raise ValueError(
            f"source set requires {len(plans)} atlas pages; limit is {max_pages}"
        )
    pages: list[AtlasPage] = []
    panels: list[AtlasPanel] = []
    for page_number, plan in enumerate(plans, start=1):
        width, height = _page_dimensions(plan)
        canvas = Image.new("RGBA", (width, height), (128, 128, 128, 255))
        for panel in plan.panels:
            source_image = snapshots[panel.source_id].image
            canvas.paste(source_image.convert("RGBA"), (panel.x, panel.y))
            panels.append(panel)
        page_path = _atomic_write_bytes(
            output_dir / f"page-{page_number:02d}.png", _png_bytes(canvas)
        )
        page_snapshot = _snapshot_image(page_path)
        pages.append(
            AtlasPage(
                page_number,
                page_path,
                page_snapshot.byte_sha256,
                page_snapshot.decoded_pixel_sha256,
                page_snapshot.image.mode,
                width,
                height,
            )
        )
    return AtlasIndex(ordered, tuple(pages), tuple(panels))


def _rectangles_overlap(left: AtlasPanel, right: AtlasPanel) -> bool:
    return not (
        left.x + left.width <= right.x
        or right.x + right.width <= left.x
        or left.y + left.height <= right.y
        or right.y + right.height <= left.y
    )


def verify_atlas_round_trip(index: AtlasIndex) -> AtlasVerification:
    if index.max_dimension != _ATLAS_MAX_DIMENSION or index.padding != _ATLAS_PADDING:
        raise ValueError("atlas index packing constants were tampered")
    if not 1 <= len(index.pages) <= 5:
        raise ValueError("atlas index must contain one through five pages")
    source_ids = [source.source_id for source in index.sources]
    if source_ids != sorted(source_ids) or len(set(source_ids)) != len(source_ids):
        raise ValueError("atlas sources must be unique and sorted")
    sources = {source.source_id: source for source in index.sources}
    source_images: dict[str, Image.Image] = {}
    for source in index.sources:
        _, cache = _validate_locked_source(source)
        source_images[source.source_id] = cache.image.convert("RGBA")
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
    common_parent: Path | None = None
    for page in index.pages:
        _owner_context(page.path)
        if page.path.name != f"page-{page.number:02d}.png":
            raise ValueError(f"atlas page path mismatch: {page.number}")
        parent = page.path.parent.resolve(strict=False)
        if common_parent is None:
            common_parent = parent
        elif parent != common_parent:
            raise ValueError("atlas pages must share one output directory")
        snapshot = _snapshot_image(page.path)
        if snapshot.format != "PNG" or snapshot.image.mode != "RGBA":
            raise ValueError(f"atlas page format or mode mismatch: {page.number}")
        if (snapshot.image.width, snapshot.image.height) != (page.width, page.height):
            raise ValueError(f"atlas page dimensions mismatch: {page.number}")
        if snapshot.byte_sha256 != page.byte_sha256:
            raise ValueError(f"atlas page hash mismatch: {page.path}")
        if snapshot.decoded_pixel_sha256 != page.decoded_pixel_sha256:
            raise ValueError(f"atlas page pixel hash mismatch: {page.path}")
        if page.mode != "RGBA":
            raise ValueError(f"atlas page mode record mismatch: {page.number}")
        page_snapshots[page.number] = snapshot
    expected_plans = _plan_atlases(index.sources)
    expected_panels = tuple(
        panel for plan in expected_plans for panel in plan.panels
    )
    if len(expected_plans) != len(index.pages):
        raise ValueError("atlas page count does not match deterministic layout")
    if expected_panels != index.panels:
        raise ValueError("atlas panel records do not match deterministic layout")
    for page, plan in zip(index.pages, expected_plans):
        if (page.width, page.height) != _page_dimensions(plan):
            raise ValueError(f"atlas page dimensions mismatch: {page.number}")
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
        if cropped.tobytes() != source_images[panel.source_id].tobytes():
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
            or not 0
            <= self.distance_threshold
            < self.edge_distance_threshold
            <= 255
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
        _load_json(path, "chroma config"),
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
    width, height = image.size
    minimum_size = max(16, math.ceil(width * height * 0.05))
    boundary = frozenset(_boundary_points(width, height))
    minimum_boundary_contact = max(4, math.ceil(len(boundary) * 0.10))
    visited: set[tuple[int, int]] = set()
    flood_count = 0
    for seed in boundary:
        if seed in visited:
            continue
        seed_pixel = image.getpixel(seed)
        if seed_pixel[3] != 255:
            continue
        queue: deque[tuple[int, int]] = deque([seed])
        component: set[tuple[int, int]] = {seed}
        visited.add(seed)
        while queue:
            point = queue.popleft()
            for neighbor in _neighbors(*point, width, height):
                if neighbor in visited:
                    continue
                pixel = image.getpixel(neighbor)
                if pixel[3] == 255:
                    component.add(neighbor)
                    visited.add(neighbor)
                    queue.append(neighbor)
        if (
            len(component) >= minimum_size
            and len(component.intersection(boundary)) >= minimum_boundary_contact
        ):
            flood_count += len(component)
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
    pixels = list(image.get_flattened_data())
    alpha = [pixel[3] for pixel in pixels]
    corners = tuple(
        image.getpixel(point)[3]
        for point in (
            (0, 0),
            (image.width - 1, 0),
            (0, image.height - 1),
            (image.width - 1, image.height - 1),
        )
    )
    fringe = sum(
        1
        for pixel in pixels
        if pixel[3] > 0
        and _distance(pixel[:3], config.key_rgb) < config.edge_distance_threshold
    )
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


def remove_chroma(
    input_path: Path, output_path: Path, config: ChromaConfig
) -> TransparencyReport:
    input_absolute = _absolute(input_path)
    output_absolute = _absolute(output_path)
    if input_absolute.resolve(strict=False) == output_absolute.resolve(strict=False):
        raise ValueError("refusing to key in place")
    _owner_context(output_path)
    snapshot = _snapshot_image(input_path)
    image = snapshot.image.convert("RGBA")
    original = image.copy()
    connected = _boundary_connected(
        original, config.key_rgb, config.distance_threshold
    )
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
                config.distance_threshold
                < distance
                < config.edge_distance_threshold
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
    output = _atomic_write_bytes(output_path, _png_bytes(image))
    output_snapshot = _snapshot_image(output)
    return _transparency_report(
        output_snapshot, config, input_hash=snapshot.byte_sha256
    )


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
    report = _transparency_report(
        snapshot, config, input_hash=snapshot.byte_sha256
    )
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
