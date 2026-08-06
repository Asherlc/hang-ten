"""Product-neutral Stage 0 source registration for commercial photographs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
from types import MappingProxyType
from typing import Literal, Mapping
import unicodedata

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .geometry import RectifiedBoard
from .models import ConversionError
from .source_cache import CachedSource


@dataclass(frozen=True, slots=True)
class CommercialIdentityAssertion:
    asserted_name: str
    normalized_name: str
    product_key: str
    assertion_source: Literal["caller"] = "caller"


@dataclass(frozen=True, slots=True)
class GenericStage0Profile:
    profile_id: str = "generic-commercial-source-v1"
    canonical_width: int = 1000
    background_tolerance: float = 18.0
    minimum_component_area_ratio: float = 0.005
    minimum_relative_component_area: float = 0.05
    maximum_piece_count: int = 4


@dataclass(frozen=True, slots=True)
class StageCheckpoint:
    stage: int
    artifact_root: Path
    candidate_hashes: Mapping[str, str]
    review_path: Path
    machine_passed: bool


_CANDIDATE_FILES = (
    "stage-0-candidate.json",
    "stage-0-source-preview.png",
    "stage-0-isolation.png",
    "stage-0-registered-rgba.png",
    "stage-0-review.png",
)
_COMPONENT_COLORS = ((220, 68, 55), (54, 122, 210), (55, 156, 99), (187, 101, 30))
# A single slash between name words is punctuation; roots and multi-segment tokens are paths.
_ABSOLUTE_PATH = re.compile(
    r"(?:^[/\\]\S*|(?<!\w)[/\\]\S+|"
    r"[/\\][^\s/\\]+[/\\][^\s/\\]+|[a-z]:[/\\]+|file:)",
    re.IGNORECASE,
)
_CALENDAR_DATE = re.compile(
    r"(?:^|\D)(?:19|20)\d{2}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01])(?:$|\D)"
)
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_TEMPORARY_IDENTIFIER = re.compile(
    r"\b(?:tmp|temp|upload|image|photo|file|untitled)[_-][a-z0-9]{6,}\b",
    re.IGNORECASE,
)


def commercial_identity(asserted_name: str) -> CommercialIdentityAssertion:
    """Record a caller assertion without turning it into a verification claim."""
    if not isinstance(asserted_name, str) or not asserted_name or not all(
        character.isprintable() for character in asserted_name
    ):
        raise ValueError("commercial identity must be printable nonempty text")
    normalized_name = " ".join(asserted_name.split())
    if not normalized_name:
        raise ValueError("commercial identity must be printable nonempty text")
    if (
        _ABSOLUTE_PATH.search(normalized_name)
        or _CALENDAR_DATE.search(normalized_name)
        or _UUID.search(normalized_name)
        or _TEMPORARY_IDENTIFIER.search(normalized_name)
    ):
        raise ValueError("commercial identity must be a stable commercial name")
    ascii_name = unicodedata.normalize("NFKD", normalized_name).encode("ascii", "ignore").decode("ascii")
    product_key = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:80]
    if not product_key:
        raise ValueError("commercial identity must have an ASCII product key")
    return CommercialIdentityAssertion(
        asserted_name=asserted_name,
        normalized_name=normalized_name,
        product_key=product_key,
    )


def run_generic_stage0(
    source: CachedSource,
    identity: CommercialIdentityAssertion,
    artifact_root: Path,
    *,
    profile: GenericStage0Profile = GenericStage0Profile(),
) -> StageCheckpoint:
    """Register an immutable source into generic, reviewable Stage 0 artifacts."""
    if identity != commercial_identity(identity.asserted_name):
        raise ValueError("commercial identity assertion is inconsistent")
    if artifact_root.exists():
        raise FileExistsError(f"Stage 0 artifact root already exists: {artifact_root}")
    if profile.canonical_width <= 0 or profile.maximum_piece_count < 1:
        raise ValueError("generic Stage 0 profile has invalid limits")
    raw = source.cached_path.read_bytes()
    if sha256(raw).hexdigest() != source.raw_sha256:
        raise ConversionError("cached source raw hash does not match its evidence")
    rgb = _decode_cached_rgb(raw, source)
    first = _register(rgb, profile)
    second = _register(rgb, profile)
    if first.rgba.tobytes() != second.rgba.tobytes() or first.metadata != second.metadata:
        raise ConversionError("generic Stage 0 registration is not deterministic")

    temporary_root: Path | None = None
    try:
        temporary_root = Path(
            tempfile.mkdtemp(prefix=f".{artifact_root.name}.tmp-", dir=artifact_root.parent)
        )
        _write_png(temporary_root / "stage-0-source-preview.png", rgb)
        _write_png(temporary_root / "stage-0-isolation.png", _isolation_overlay(rgb, first.labels, first.quadrilateral))
        registered_path = temporary_root / "stage-0-registered-rgba.png"
        _write_png(registered_path, first.rgba)
        registered_file_sha = _hash_file(registered_path)
        candidate = {
            "cachedSource": {
                "decodedRgbSha256": source.decoded_rgb_sha256,
                "height": source.height,
                "imageFormat": source.image_format,
                "kind": source.kind,
                "locatorSha256": source.locator_sha256,
                "rawSha256": source.raw_sha256,
                "sanitizedLocator": source.sanitized_locator,
                "width": source.width,
            },
            "foregroundFraction": first.metadata["foregroundFraction"],
            "identity": {
                "assertionSource": identity.assertion_source,
                "assertedName": identity.asserted_name,
                "normalizedName": identity.normalized_name,
                "productKey": identity.product_key,
            },
            "pieceCount": first.metadata["pieceCount"],
            "profile": asdict(profile),
            "quadrilateral": first.metadata["quadrilateral"],
            "registered": {
                "fileSha256": registered_file_sha,
                "height": first.rgba.shape[0],
                "pixelSha256": sha256(first.rgba.tobytes()).hexdigest(),
                "width": first.rgba.shape[1],
            },
            "sourceDimensions": {"height": source.height, "width": source.width},
            "stage": 0,
        }
        _write_json(temporary_root / "stage-0-candidate.json", candidate)
        review = _review_image(rgb, first.overlay, first.rgba, identity, source.sanitized_locator)
        _write_png(temporary_root / "stage-0-review.png", review)
        hashes = {name: _hash_file(temporary_root / name) for name in _CANDIDATE_FILES}
        _write_json(temporary_root / "candidate-hashes.json", hashes)
        temporary_root.replace(artifact_root)
        return StageCheckpoint(
            stage=0,
            artifact_root=artifact_root,
            candidate_hashes=MappingProxyType(hashes),
            review_path=artifact_root / "stage-0-review.png",
            machine_passed=True,
        )
    except Exception:
        if temporary_root is not None:
            shutil.rmtree(temporary_root, ignore_errors=True)
        raise


@dataclass(frozen=True, slots=True)
class _Registration:
    rgba: np.ndarray
    labels: np.ndarray
    quadrilateral: np.ndarray
    metadata: dict[str, object]
    overlay: np.ndarray


def _decode_cached_rgb(raw: bytes, source: CachedSource) -> np.ndarray:
    from io import BytesIO

    try:
        with Image.open(BytesIO(raw)) as image:
            if getattr(image, "is_animated", False) or getattr(image, "n_frames", 1) != 1:
                raise ConversionError("cached source must not be animated")
            rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB"), dtype=np.uint8)
    except Exception as error:
        if isinstance(error, ConversionError):
            raise
        raise ConversionError("cached source is no longer decodable") from error
    if rgb.shape[:2] != (source.height, source.width) or sha256(rgb.tobytes()).hexdigest() != source.decoded_rgb_sha256:
        raise ConversionError("cached source pixels do not match its evidence")
    return rgb


def _register(rgb: np.ndarray, profile: GenericStage0Profile) -> _Registration:
    height, width = rgb.shape[:2]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    thickness = max(8, min(64, round(min(height, width) * 0.03)))
    border = np.concatenate((lab[:thickness].reshape(-1, 3), lab[-thickness:].reshape(-1, 3), lab[:, :thickness].reshape(-1, 3), lab[:, -thickness:].reshape(-1, 3)))
    background = np.median(border, axis=0)
    mask = (np.linalg.norm(lab - background, axis=2) > profile.background_tolerance).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if component_count <= 1:
        raise ConversionError("could not isolate a commercial product")
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest_area = int(areas.max())
    minimum_area = max(profile.minimum_component_area_ratio * height * width, profile.minimum_relative_component_area * largest_area)
    retained = [label for label in range(1, component_count) if stats[label, cv2.CC_STAT_AREA] >= minimum_area]
    if not 1 <= len(retained) <= min(4, profile.maximum_piece_count):
        raise ConversionError("commercial product has an unsupported piece count")
    union_mask = np.isin(labels, retained)
    foreground_fraction = float(union_mask.mean())
    if not 0.02 <= foreground_fraction <= 0.90:
        raise ConversionError("commercial product coverage is outside Stage 0 limits")
    quadrilateral = _quadrilateral(union_mask)
    rectified = _orient_board(rgb, union_mask, quadrilateral)
    rectified_mask = rectified.mask
    ratio = rectified.width / rectified.height
    if not 1.5 <= ratio <= 12.0:
        raise ConversionError("commercial product aspect ratio is outside Stage 0 limits")
    output_height = round(profile.canonical_width * rectified.height / rectified.width)
    resized_rgb = cv2.resize(rectified.rgb, (profile.canonical_width, output_height), interpolation=cv2.INTER_LANCZOS4)
    resized_mask = cv2.resize(rectified_mask.astype(np.uint8), (profile.canonical_width, output_height), interpolation=cv2.INTER_NEAREST).astype(bool)
    rgba = np.empty((output_height, profile.canonical_width, 4), dtype=np.uint8)
    rgba[..., :3] = resized_rgb
    rgba[..., 3] = resized_mask.astype(np.uint8) * 255
    rgba[~resized_mask, :3] = 0
    rgba.setflags(write=False)
    display_labels = np.zeros_like(labels)
    for index, label in enumerate(retained, start=1):
        display_labels[labels == label] = index
    overlay = _isolation_overlay(rgb, display_labels, quadrilateral)
    return _Registration(
        rgba=rgba,
        labels=display_labels,
        quadrilateral=quadrilateral,
        metadata={
            "foregroundFraction": foreground_fraction,
            "pieceCount": len(retained),
            "quadrilateral": [[round(float(value), 6) for value in point] for point in quadrilateral],
        },
        overlay=overlay,
    )


def _quadrilateral(mask: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    corners = cv2.boxPoints(cv2.minAreaRect(np.vstack(contours))).astype(np.float32)
    return _order_corners(corners)


def _orient_board(
    rgb: np.ndarray, mask: np.ndarray, frame: np.ndarray
) -> RectifiedBoard:
    """Derotate and tightly crop a product without changing its perspective."""
    long_axis = (frame[1] - frame[0]) + (frame[2] - frame[3])
    long_axis /= np.linalg.norm(long_axis)
    short_axis = np.array((-long_axis[1], long_axis[0]), dtype=np.float32)
    transform = np.array(
        (
            (long_axis[0], long_axis[1], 0.0),
            (short_axis[0], short_axis[1], 0.0),
        ),
        dtype=np.float64,
    )
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    transformed = cv2.transform(np.vstack(contours).astype(np.float32), transform).reshape(-1, 2)
    left = int(np.floor(transformed[:, 0].min()))
    top = int(np.floor(transformed[:, 1].min()))
    right = int(np.ceil(transformed[:, 0].max()))
    bottom = int(np.ceil(transformed[:, 1].max()))
    transform[:, 2] = (-left, -top)
    width = right - left + 1
    height = bottom - top + 1
    oriented_rgb = cv2.warpAffine(rgb, transform, (width, height))
    oriented_mask = cv2.warpAffine(
        mask.astype(np.uint8),
        transform,
        (width, height),
        flags=cv2.INTER_NEAREST,
    ).astype(bool)
    return RectifiedBoard(
        rgb=oriented_rgb,
        mask=oriented_mask,
        width=width,
        height=height,
        warnings=("orientation-only registration",),
    )


def _order_corners(points: np.ndarray) -> np.ndarray:
    center = points.mean(axis=0)
    cyclic = points[np.argsort(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))]
    edges = np.roll(cyclic, -1, axis=0) - cyclic
    if np.linalg.norm(edges[1]) + np.linalg.norm(edges[3]) > np.linalg.norm(edges[0]) + np.linalg.norm(edges[2]):
        cyclic = np.roll(cyclic, -1, axis=0)
    axis = (cyclic[1] - cyclic[0]) + (cyclic[2] - cyclic[3])
    axis /= np.linalg.norm(axis)
    if axis[0] < 0 or (axis[0] == 0 and axis[1] < 0):
        axis *= -1
    short_axis = np.array([-axis[1], axis[0]], dtype=np.float32)
    top, bottom = sorted(((cyclic[0], cyclic[1]), (cyclic[2], cyclic[3])), key=lambda edge: float(((edge[0] + edge[1]) / 2) @ short_axis))
    top_left, top_right = sorted(top, key=lambda point: float(point @ axis))
    bottom_left, bottom_right = sorted(bottom, key=lambda point: float(point @ axis))
    return np.float32((top_left, top_right, bottom_right, bottom_left))


def _isolation_overlay(rgb: np.ndarray, labels: np.ndarray, quadrilateral: np.ndarray) -> np.ndarray:
    overlay = rgb.copy()
    for index, color in enumerate(_COMPONENT_COLORS, start=1):
        selected = labels == index
        overlay[selected] = np.rint(0.55 * overlay[selected] + 0.45 * np.asarray(color)).astype(np.uint8)
    cv2.polylines(overlay, [np.rint(quadrilateral).astype(np.int32)], True, (24, 24, 24), 2, cv2.LINE_AA)
    return overlay


def _review_image(source: np.ndarray, isolation: np.ndarray, rgba: np.ndarray, identity: CommercialIdentityAssertion, locator: str) -> np.ndarray:
    canvas = Image.new("RGB", (2200, 1600), "#eeeeec")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((50, 35), f"Stage 0 review: {identity.asserted_name}", fill=(30, 30, 30), font=font)
    draw.text((50, 60), f"Source: {locator}", fill=(70, 70, 70), font=font)
    _paste_scaled(canvas, source, (50, 115), (1000, 600))
    _paste_scaled(canvas, isolation, (1150, 115), (1000, 600))
    draw.text((50, 95), "Original source", fill=(30, 30, 30), font=font)
    draw.text((1150, 95), "Isolation and registration quadrilateral", fill=(30, 30, 30), font=font)
    registered = Image.fromarray(rgba, "RGBA")
    canvas.paste(registered, (600, 850), registered)
    draw.text((600, 825), f"Registered RGBA ({rgba.shape[1]} px wide)", fill=(30, 30, 30), font=font)
    return np.asarray(canvas, dtype=np.uint8)


def _paste_scaled(canvas: Image.Image, pixels: np.ndarray, origin: tuple[int, int], maximum: tuple[int, int]) -> None:
    image = Image.fromarray(pixels)
    scale = min(maximum[0] / image.width, maximum[1] / image.height, 1.0)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    image = image.resize(size, Image.Resampling.LANCZOS)
    canvas.paste(image, origin)


def _write_png(path: Path, pixels: np.ndarray) -> None:
    Image.fromarray(pixels).save(path, format="PNG", optimize=False, compress_level=9)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
