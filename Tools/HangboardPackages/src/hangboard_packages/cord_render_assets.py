"""Deterministic evidence and transparency gates for cord-render candidates.

These utilities intentionally operate only in owner-named ``.context`` trees.
Atlases are immutable input preparation; chroma removal is the sole output
conversion supported here.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

from PIL import Image, UnidentifiedImageError


_OWNER_TOKEN = ".context/joyful-donkey-"
_ATLAS_MAX_DIMENSION = 2048
_seen_source_ids: set[str] = set()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _owner_context(path: Path) -> Path:
    resolved = path.resolve()
    marker = _OWNER_TOKEN
    value = str(resolved)
    start = value.find(marker)
    if start < 0:
        raise ValueError("path must be inside an owner-named .context/joyful-donkey-* directory")
    end = value.find("/", start + len(marker))
    return Path(value if end < 0 else value[:end])


def _image(path: Path) -> Image.Image:
    if path.is_symlink():
        raise ValueError(f"symlink sources are rejected: {path}")
    try:
        with Image.open(path) as opened:
            opened.load()
            return opened.copy()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError(f"expected a readable image: {path}") from error


def decoded_pixel_sha256(path: Path) -> str:
    image = _image(path)
    digest = hashlib.sha256()
    digest.update(image.mode.encode("ascii"))
    digest.update(b"\0")
    digest.update(f"{image.width}x{image.height}".encode("ascii"))
    digest.update(b"\0")
    digest.update(image.tobytes())
    return digest.hexdigest()


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
    cache_path: Path

    def to_json(self) -> dict[str, object]:
        result = asdict(self)
        result["sourceID"] = result.pop("source_id")
        result["reviewedAt"] = result.pop("reviewed_at")
        result["decodedPixelSHA256"] = result.pop("decoded_pixel_sha256")
        result["byteSHA256"] = result.pop("byte_sha256")
        result["cachePath"] = str(result.pop("cache_path"))
        return result


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
    if not isinstance(reviewed_at, date):
        raise ValueError("reviewed_at must be an immutable date")
    for label, value in (("source_id", source_id), ("url", url), ("publisher", publisher), ("role", role), ("revision", revision)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be non-empty immutable source metadata")
    if source_id in _seen_source_ids:
        raise ValueError(f"duplicate source ID: {source_id}")
    image = _image(path)
    source = path.resolve()
    cache_dir = _owner_context(source) / "sources" / "locked"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = (cache_dir / f"{source_id}-{_sha256(source)}{source.suffix.lower()}").resolve()
    cache_path.write_bytes(source.read_bytes())
    _seen_source_ids.add(source_id)
    return LockedSource(source_id, url, publisher, role, revision, reviewed_at.isoformat(), _sha256(source), decoded_pixel_sha256(source), image.mode, image.width, image.height, cache_path)


@dataclass(frozen=True)
class AtlasPage:
    number: int
    path: Path
    byte_sha256: str
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

    def to_json(self) -> dict[str, object]:
        return {
            "sources": [source.to_json() for source in self.sources],
            "pages": [{**asdict(page), "path": str(page.path)} for page in self.pages],
            "panels": [asdict(panel) for panel in self.panels],
        }


@dataclass(frozen=True)
class AtlasVerification:
    valid: bool
    verified_panels: int


def build_lossless_atlases(sources: Sequence[LockedSource], output_dir: Path, *, max_pages: int = 5) -> AtlasIndex:
    if not 1 <= max_pages <= 5:
        raise ValueError("at most five atlas pages are permitted")
    if not sources:
        raise ValueError("at least one locked source is required")
    output_root = _owner_context(output_dir)
    if output_dir.resolve() != output_root and output_root not in output_dir.resolve().parents:
        raise ValueError("atlas output must stay in owner context")
    ordered = tuple(sorted(sources, key=lambda source: source.source_id))
    if len({source.source_id for source in ordered}) != len(ordered):
        raise ValueError("duplicate source ID")
    padding = 8
    if any(source.width + padding * 2 > _ATLAS_MAX_DIMENSION or source.height + padding * 2 > _ATLAS_MAX_DIMENSION for source in ordered):
        raise ValueError("source cannot fit a lossless atlas page")
    page_sources: list[list[LockedSource]] = [[]]
    page_height = padding
    for source in ordered:
        required_height = source.height + padding
        if page_sources[-1] and page_height + required_height > _ATLAS_MAX_DIMENSION:
            page_sources.append([])
            page_height = padding
        page_sources[-1].append(source)
        page_height += required_height
    if len(page_sources) > max_pages:
        raise ValueError("source set requires more than five atlas pages")
    output_dir.mkdir(parents=True, exist_ok=True)
    panels: list[AtlasPanel] = []
    pages: list[AtlasPage] = []
    for page_number, sources_for_page in enumerate(page_sources, start=1):
        width = max(source.width for source in sources_for_page) + padding * 2
        height = sum(source.height + padding for source in sources_for_page) + padding
        canvas = Image.new("RGBA", (width, height), (128, 128, 128, 255))
        y = padding
        for source in sources_for_page:
            if _sha256(source.cache_path) != source.byte_sha256 or decoded_pixel_sha256(source.cache_path) != source.decoded_pixel_sha256:
                raise ValueError(f"locked source hash mismatch: {source.source_id}")
            image = _image(source.cache_path)
            # paste preserves the decoded panel exactly; no EXIF transpose or transform occurs.
            canvas.paste(image.convert("RGBA"), (padding, y))
            panels.append(AtlasPanel(source.source_id, page_number, padding, y, source.width, source.height, source.mode, source.decoded_pixel_sha256))
            y += source.height + padding
        page_path = output_dir / f"page-{page_number:02d}.png"
        canvas.save(page_path, format="PNG", optimize=False, compress_level=9)
        pages.append(AtlasPage(page_number, page_path.resolve(), _sha256(page_path), width, height))
    return AtlasIndex(ordered, tuple(pages), tuple(panels))


def verify_atlas_round_trip(index: AtlasIndex) -> AtlasVerification:
    sources = {source.source_id: source for source in index.sources}
    pages = {page.number: page for page in index.pages}
    if len(sources) != len(index.sources) or len(pages) != len(index.pages):
        raise ValueError("duplicate atlas source or page records")
    for page in index.pages:
        if _sha256(page.path) != page.byte_sha256:
            raise ValueError(f"atlas page hash mismatch: {page.path}")
    seen: set[str] = set()
    for panel in index.panels:
        if panel.source_id in seen or panel.source_id not in sources or panel.page_number not in pages:
            raise ValueError("tampered atlas panel mapping")
        seen.add(panel.source_id)
        source = sources[panel.source_id]
        page = pages[panel.page_number]
        if (panel.width, panel.height, panel.mode, panel.decoded_pixel_sha256) != (source.width, source.height, source.mode, source.decoded_pixel_sha256):
            raise ValueError(f"tampered atlas panel record: {panel.source_id}")
        image = _image(page.path)
        if panel.x < 0 or panel.y < 0 or panel.x + panel.width > image.width or panel.y + panel.height > image.height:
            raise ValueError(f"atlas panel outside page: {panel.source_id}")
        crop = image.crop((panel.x, panel.y, panel.x + panel.width, panel.y + panel.height)).convert(source.mode)
        digest = hashlib.sha256()
        digest.update(source.mode.encode("ascii")); digest.update(b"\0"); digest.update(f"{source.width}x{source.height}".encode("ascii")); digest.update(b"\0"); digest.update(crop.tobytes())
        if digest.hexdigest() != source.decoded_pixel_sha256:
            raise ValueError(f"atlas round-trip pixels mismatch: {panel.source_id}")
    if seen != set(sources):
        raise ValueError("atlas omits locked source")
    return AtlasVerification(True, len(seen))


@dataclass(frozen=True)
class ChromaConfig:
    key_rgb: tuple[int, int, int] = (0, 255, 0)
    distance_threshold: int = 36
    edge_distance_threshold: int = 72

    def __post_init__(self) -> None:
        if len(self.key_rgb) != 3 or any(not isinstance(value, int) or not 0 <= value <= 255 for value in self.key_rgb):
            raise ValueError("key_rgb must contain three bytes")
        if not 0 <= self.distance_threshold <= self.edge_distance_threshold <= 255:
            raise ValueError("chroma thresholds must be bounded bytes")


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
            "config": {"keyRGB": self.config.key_rgb, "distanceThreshold": self.config.distance_threshold, "edgeDistanceThreshold": self.config.edge_distance_threshold},
            "inputByteSHA256": self.input_byte_sha256, "outputByteSHA256": self.output_byte_sha256,
            "decodedPixelSHA256": self.decoded_pixel_sha256, "width": self.width, "height": self.height, "mode": self.mode,
            "minimumAlpha": self.minimum_alpha, "maximumAlpha": self.maximum_alpha, "cornerAlpha": self.corner_alpha,
            "transparentFraction": self.transparent_fraction, "boundaryConnectedOpaqueFloodCount": self.boundary_connected_opaque_flood_count,
            "remainingKeyFringeCount": self.remaining_key_fringe_count,
        }


def _distance(rgb: tuple[int, int, int], key: tuple[int, int, int]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(rgb, key)))


def _boundary_connected(image: Image.Image, threshold: int) -> set[tuple[int, int]]:
    width, height = image.size
    queue: deque[tuple[int, int]] = deque()
    visited: set[tuple[int, int]] = set()
    for x in range(width): queue.extend(((x, 0), (x, height - 1)))
    for y in range(1, height - 1): queue.extend(((0, y), (width - 1, y)))
    key = image.info.get("_chroma_key", (0, 255, 0))
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited or _distance(image.getpixel((x, y))[:3], key) > threshold:
            continue
        visited.add((x, y))
        queue.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
        queue = deque((nx, ny) for nx, ny in queue if 0 <= nx < width and 0 <= ny < height)
    return visited


def _boundary_offwhite_flood(image: Image.Image) -> set[tuple[int, int]]:
    width, height = image.size
    queue: deque[tuple[int, int]] = deque()
    visited: set[tuple[int, int]] = set()
    for x in range(width): queue.extend(((x, 0), (x, height - 1)))
    for y in range(1, height - 1): queue.extend(((0, y), (width - 1, y)))
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        red, green, blue, alpha = image.getpixel((x, y))
        if alpha != 255 or _distance((red, green, blue), (250, 250, 245)) >= 18:
            continue
        visited.add((x, y))
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                queue.append((nx, ny))
    return visited


def _report(path: Path, config: ChromaConfig, input_hash: str = "") -> TransparencyReport:
    try:
        with Image.open(path) as original:
            if original.format != "PNG":
                raise ValueError("transparency output must be PNG")
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError(f"expected a readable image: {path}") from error
    image = _image(path)
    if image.mode != "RGBA":
        raise ValueError("transparency output must be RGBA")
    image.info["_chroma_key"] = config.key_rgb
    pixels = list(image.get_flattened_data())
    alpha = [pixel[3] for pixel in pixels]
    corners = tuple(image.getpixel(point)[3] for point in ((0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1)))
    flood = len(_boundary_offwhite_flood(image))
    fringe = sum(1 for pixel in pixels if pixel[3] > 0 and _distance(pixel[:3], config.key_rgb) <= config.edge_distance_threshold)
    return TransparencyReport(config, input_hash, _sha256(path), decoded_pixel_sha256(path), image.width, image.height, image.mode, min(alpha), max(alpha), corners, alpha.count(0) / len(alpha), flood, fringe)


def remove_chroma(input_path: Path, output_path: Path, config: ChromaConfig = ChromaConfig()) -> TransparencyReport:
    if input_path.resolve() == output_path.resolve():
        raise ValueError("refusing to key in place")
    _owner_context(output_path)
    image = _image(input_path).convert("RGBA")
    image.info["_chroma_key"] = config.key_rgb
    connected = _boundary_connected(image, config.distance_threshold)
    pixels = image.load()
    for x, y in connected:
        red, green, blue, alpha = pixels[x, y]
        distance = _distance((red, green, blue), config.key_rgb)
        if distance <= config.distance_threshold:
            pixels[x, y] = (red, green, blue, 0)
    # Only partially keyed pixels that neighbor the boundary-connected matte are decontaminated.
    for x, y in connected:
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if not (0 <= nx < image.width and 0 <= ny < image.height) or (nx, ny) in connected:
                continue
            red, green, blue, alpha = pixels[nx, ny]
            distance = _distance((red, green, blue), config.key_rgb)
            if config.distance_threshold < distance <= config.edge_distance_threshold and alpha > 0:
                pixels[nx, ny] = (red, green, blue, round(alpha * (distance - config.distance_threshold) / (config.edge_distance_threshold - config.distance_threshold)))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=False, compress_level=9)
    return _report(output_path, config, _sha256(input_path))


def inspect_transparency(path: Path, expected_width: int, expected_height: int, key_rgb: tuple[int, int, int]) -> TransparencyReport:
    report = _report(path, ChromaConfig(key_rgb=key_rgb))
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


def load_locked_sources(manifest: Path) -> list[LockedSource]:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ValueError("source manifest requires sources array")
    result = []
    for record in payload["sources"]:
        result.append(lock_source(Path(record["path"]), source_id=record["sourceID"], url=record["url"], publisher=record["publisher"], role=record["role"], revision=record["revision"], reviewed_at=date.fromisoformat(record["reviewedAt"])))
    return result
