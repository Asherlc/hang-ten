"""Generic Stage 4 clean, selectable product illustration.

This renderer intentionally consumes only approved vector geometry plus robust
colour/noise scalars from the approved Stage 1 raster.  No photographed pixels
are copied into the illustration.
"""

from __future__ import annotations

import base64
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile
from types import MappingProxyType
from typing import Protocol
from xml.sax.saxutils import escape

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .display_paths import DisplayPath, flatten_display_path, parse_display_path
from .generic_stage0 import StageCheckpoint
from .models import ConversionError


_GRIP_TYPES = ("jug", "sloper", "edge", "pocket")
_HIGHLIGHT = np.asarray((255.0, 91.0, 36.0), np.float32)
_WARM_WHITE = (248, 247, 244)
_CANDIDATE_FILES = (
    "stage-4-candidate.json",
    "stage-4-normal.png",
    "stage-4-product.svg",
    "stage-4-manifest.json",
    "stage-4-highlight-all.png",
    "stage-4-highlight-jugs.png",
    "stage-4-highlight-slopers.png",
    "stage-4-highlight-edges.png",
    "stage-4-highlight-pockets.png",
    "stage-4-highlight-symmetric-pair.png",
    "stage-4-highlight-mixed.png",
    "stage-4-highlights.json",
    "stage-4-review.png",
)


@dataclass(frozen=True, slots=True)
class GenericStage4Profile:
    profile_id: str = "generic-pale-wood-heightfield-v1"
    supersample: int = 4
    body_bevel: float = 5.0
    pocket_depth: float = 13.0
    edge_depth: float = 4.0
    surface_relief: float = 5.0
    grain_strength_cap: float = 0.045
    light_direction: tuple[float, float, float] = (-0.35, -0.45, 0.82)


class Stage4RunContext(Protocol):
    root: Path
    manifest: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class GenericStage4Runner:
    profile: GenericStage4Profile = GenericStage4Profile()
    stage: int = 4

    def run(self, context: Stage4RunContext, artifact_root: Path) -> StageCheckpoint:
        return run_generic_stage4(context, artifact_root, profile=self.profile)


@dataclass(frozen=True, slots=True)
class _Region:
    id: int
    key: str
    grip_type: str
    piece_index: int
    display_path: DisplayPath
    symmetry_pair: str | None


def run_generic_stage4(
    context: Stage4RunContext,
    artifact_root: Path,
    *,
    profile: GenericStage4Profile = GenericStage4Profile(),
) -> StageCheckpoint:
    """Render an accepted Stage 3 document as a clean selectable illustration."""
    if artifact_root.exists():
        raise FileExistsError(f"Stage 4 artifact root already exists: {artifact_root}")
    rgba, document, evidence, pixel_sha = _approved_inputs(context)
    canvas = document.get("canvas")
    if not isinstance(canvas, Mapping):
        raise ConversionError("Stage 3 canvas is missing")
    width, height = int(canvas.get("width", 0)), int(canvas.get("height", 0))
    if (width, height) != (rgba.shape[1], rgba.shape[0]):
        raise ConversionError("Stage 3 canvas does not match Stage 1 raster")
    silhouettes, regions = _geometry(document, width, height)

    normal, coverages = _render(rgba, silhouettes, regions, pixel_sha, profile)
    normal_again, coverages_again = _render(
        rgba, silhouettes, regions, pixel_sha, profile
    )
    if not np.array_equal(normal, normal_again) or any(
        not np.array_equal(coverages[key], coverages_again[key]) for key in coverages
    ):
        raise ConversionError("generic Stage 4 rendering is not deterministic")

    scenarios = _scenarios(regions, coverages)
    highlighted = {
        name: _highlight(normal, coverages, selected)
        for name, selected in scenarios.items()
    }
    manifest = _manifest(width, height, document, regions, profile)
    highlights = _highlight_document(scenarios, coverages)

    temporary_root: Path | None = None
    try:
        artifact_root.parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(
                prefix=f".{artifact_root.name}.tmp-", dir=artifact_root.parent
            )
        )
        normal_path = temporary_root / "stage-4-normal.png"
        _write_png(normal_path, normal)
        for name, image in highlighted.items():
            _write_png(temporary_root / f"stage-4-highlight-{name}.png", image)
        _write_json(temporary_root / "stage-4-manifest.json", manifest)
        _write_json(temporary_root / "stage-4-highlights.json", highlights)
        (temporary_root / "stage-4-product.svg").write_text(
            _selectable_svg(_encode_png(normal), width, height, regions),
            encoding="utf-8",
        )
        _write_png(
            temporary_root / "stage-4-review.png",
            _review(normal, highlighted),
        )

        candidate = {
            "highlights": {
                "fileSha256": _hash_file(temporary_root / "stage-4-highlights.json"),
                "path": "stage-4-highlights.json",
            },
            "inputAcceptance": evidence["stage3Acceptance"],
            "inputRaster": evidence["stage1Rgba"],
            "inputVectorRegions": evidence["stage3Regions"],
            "manifest": {
                "fileSha256": _hash_file(temporary_root / "stage-4-manifest.json"),
                "path": "stage-4-manifest.json",
            },
            "normal": {
                "fileSha256": _hash_file(normal_path),
                "height": height,
                "path": "stage-4-normal.png",
                "width": width,
            },
            "profile": asdict(profile),
            "productSvg": {
                "fileSha256": _hash_file(temporary_root / "stage-4-product.svg"),
                "path": "stage-4-product.svg",
            },
            "regionCount": len(regions),
            "stage": 4,
            "typeCounts": dict(
                sorted(Counter(region.grip_type for region in regions).items())
            ),
        }
        _write_json(temporary_root / "stage-4-candidate.json", candidate)
        hashes = {name: _hash_file(temporary_root / name) for name in _CANDIDATE_FILES}
        _write_json(temporary_root / "candidate-hashes.json", hashes)
        temporary_root.replace(artifact_root)
        return StageCheckpoint(
            stage=4,
            artifact_root=artifact_root,
            candidate_hashes=MappingProxyType(hashes),
            review_path=artifact_root / "stage-4-review.png",
            machine_passed=True,
        )
    except Exception:
        if temporary_root is not None:
            shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def _approved_inputs(
    context: Stage4RunContext,
) -> tuple[np.ndarray, dict[str, object], dict[str, object], str]:
    stages = context.manifest.get("stages")
    if not isinstance(stages, list) or len(stages) < 4:
        raise ConversionError(
            "Stage 4 requires approved Stage 1 and Stage 3 checkpoints"
        )
    stage1, stage3 = stages[1], stages[3]
    if not isinstance(stage1, Mapping) or not isinstance(stage3, Mapping):
        raise ConversionError("Stage 4 input records are invalid")
    if stage1.get("status") != "approved" or stage3.get("status") != "approved":
        raise ConversionError("Stage 1 and Stage 3 must be approved")
    stage1_acceptance_path = _inside_root(context.root, stage1.get("acceptancePath"))
    stage3_acceptance_path = _inside_root(context.root, stage3.get("acceptancePath"))
    if _hash_file(stage1_acceptance_path) != stage1.get("acceptanceSha256"):
        raise ConversionError("Stage 1 acceptance hash changed")
    if _hash_file(stage3_acceptance_path) != stage3.get("acceptanceSha256"):
        raise ConversionError("Stage 3 acceptance hash changed")
    stage1_acceptance = _read_json(stage1_acceptance_path)
    stage3_acceptance = _read_json(stage3_acceptance_path)
    run_identity = context.manifest.get("runIdentitySha256")
    if (
        stage1_acceptance.get("runIdentitySha256") != run_identity
        or stage3_acceptance.get("runIdentitySha256") != run_identity
    ):
        raise ConversionError("Stage 4 evidence belongs to another run")

    raster_record = stage1_acceptance.get("registered")
    vector_record = stage3_acceptance.get("vectorRegions")
    if not isinstance(raster_record, Mapping) or not isinstance(vector_record, Mapping):
        raise ConversionError("Stage 4 accepted evidence is incomplete")
    rgba_path = _inside_root(context.root, raster_record.get("path"))
    vector_path = _inside_root(context.root, vector_record.get("path"))
    if _hash_file(rgba_path) != raster_record.get("fileSha256"):
        raise ConversionError("accepted Stage 1 raster changed")
    if _hash_file(vector_path) != vector_record.get("fileSha256"):
        raise ConversionError("accepted Stage 3 vector document changed")
    with Image.open(rgba_path) as image:
        if image.mode != "RGBA":
            raise ConversionError("Stage 1 raster must be RGBA")
        rgba = np.asarray(image, dtype=np.uint8).copy()
    document = _read_json(vector_path)
    if document.get("stage") != 3 or document.get("schemaVersion") != 1:
        raise ConversionError("Stage 3 vector document is invalid")
    pixel_sha = raster_record.get("pixelSha256")
    if not isinstance(pixel_sha, str) or len(pixel_sha) != 64:
        raise ConversionError("Stage 1 pixel hash is invalid")
    evidence = {
        "stage1Rgba": {"path": raster_record["path"], "sha256": _hash_file(rgba_path)},
        "stage3Acceptance": {
            "path": stage3["acceptancePath"],
            "sha256": stage3["acceptanceSha256"],
        },
        "stage3Regions": {
            "path": vector_record["path"],
            "sha256": _hash_file(vector_path),
        },
    }
    return rgba, document, evidence, pixel_sha


def _geometry(
    document: Mapping[str, object], width: int, height: int
) -> tuple[tuple[DisplayPath, ...], tuple[_Region, ...]]:
    silhouette_values = document.get("silhouettePaths")
    region_values = document.get("regions")
    if not isinstance(silhouette_values, list) or not silhouette_values:
        raise ConversionError("Stage 3 has no silhouette paths")
    if not isinstance(region_values, list) or not region_values:
        raise ConversionError("Stage 3 has no grip regions")
    silhouettes: list[DisplayPath] = []
    for expected_index, value in enumerate(silhouette_values):
        if not isinstance(value, Mapping) or value.get("pieceIndex") != expected_index:
            raise ConversionError("Stage 3 silhouette order is invalid")
        path = parse_display_path(
            value.get("displayPath"),
            "Stage 3 silhouette",
            width,
            height,
            allow_linear_segments=True,
        )
        if path is None:
            raise ConversionError("Stage 3 silhouette path is missing")
        silhouettes.append(path)

    regions: list[_Region] = []
    seen_keys: set[str] = set()
    for ordinal, value in enumerate(region_values, start=1):
        if not isinstance(value, Mapping) or value.get("id") != ordinal:
            raise ConversionError("Stage 3 region order is invalid")
        key, kind, piece_index = (
            value.get("key"),
            value.get("type"),
            value.get("pieceIndex"),
        )
        if (
            not isinstance(key, str)
            or not key
            or key in seen_keys
            or kind not in _GRIP_TYPES
            or type(piece_index) is not int
            or piece_index not in range(len(silhouettes))
        ):
            raise ConversionError("Stage 3 region identity is invalid")
        path = parse_display_path(
            value.get("displayPath"),
            f"Stage 3 region {ordinal}",
            width,
            height,
            allow_linear_segments=True,
        )
        if path is None or not isinstance(value.get("displayPath"), str):
            raise ConversionError("Stage 3 region path is missing")
        symmetry = value.get("symmetry")
        symmetry_pair = symmetry.get("pair") if isinstance(symmetry, Mapping) else None
        if symmetry_pair is not None and not isinstance(symmetry_pair, str):
            raise ConversionError("Stage 3 symmetry metadata is invalid")
        seen_keys.add(key)
        # Preserve the accepted string rather than serializing parsed tokens.
        immutable = DisplayPath(value["displayPath"], path.commands, path.coordinates)
        regions.append(
            _Region(ordinal, key, kind, piece_index, immutable, symmetry_pair)
        )
    return tuple(silhouettes), tuple(regions)


def _render(
    source_rgba: np.ndarray,
    silhouettes: tuple[DisplayPath, ...],
    regions: tuple[_Region, ...],
    pixel_sha: str,
    profile: GenericStage4Profile,
) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    height, width = source_rgba.shape[:2]
    ss = profile.supersample
    if ss != 4:
        raise ConversionError("generic Stage 4 requires four-times supersampling")
    body = np.zeros((height * ss, width * ss), np.uint8)
    for path in silhouettes:
        body |= _path_mask(path, width, height, ss)
    body_bool = body > 0
    high_masks = {
        region.id: (_path_mask(region.display_path, width, height, ss) > 0) & body_bool
        for region in regions
    }
    if not np.any(body_bool) or any(not np.any(mask) for mask in high_masks.values()):
        raise ConversionError("Stage 4 geometry contains an empty mask")

    inside = cv2.distanceTransform(body_bool.astype(np.uint8), cv2.DIST_L2, 5)
    body_weight = _smoothstep(np.clip(inside / (profile.body_bevel * ss), 0.0, 1.0))
    height_field = 11.0 * body_weight
    cavity_weight = np.zeros_like(height_field, np.float32)
    edge_weight = np.zeros_like(height_field, np.float32)
    surface_weight = np.zeros_like(height_field, np.float32)
    for region in regions:
        mask = high_masks[region.id]
        distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
        if region.grip_type == "pocket":
            weight = _smoothstep(np.clip(distance / (4.6 * ss), 0.0, 1.0))
            height_field -= profile.pocket_depth * weight
            cavity_weight = np.maximum(cavity_weight, weight)
        elif region.grip_type == "edge":
            weight = _smoothstep(np.clip(distance / (3.4 * ss), 0.0, 1.0))
            height_field -= profile.edge_depth * weight
            edge_weight = np.maximum(edge_weight, weight)
        else:
            distance_weight = _smoothstep(np.clip(distance / (5.0 * ss), 0.0, 1.0))
            directional = _surface_taper(mask, region, width, ss)
            weight = distance_weight * directional
            height_field += profile.surface_relief * weight
            surface_weight = np.maximum(surface_weight, weight)
    height_field *= body_bool

    base_color, grain_strength = _source_cues(
        source_rgba, body_bool, high_masks, profile.grain_strength_cap, ss
    )
    high_rgb = _shade(
        height_field,
        body_bool,
        body_weight,
        cavity_weight,
        edge_weight,
        surface_weight,
        base_color,
        grain_strength,
        pixel_sha,
        profile,
    )
    normal = _downsample_rgba(high_rgb, body_bool, width, height)
    coverages = {
        identifier: np.clip(
            cv2.resize(
                mask.astype(np.float32), (width, height), interpolation=cv2.INTER_AREA
            ),
            0.0,
            1.0,
        )
        for identifier, mask in high_masks.items()
    }
    return normal, coverages


def _surface_taper(
    mask: np.ndarray, region: _Region, width: int, ss: int
) -> np.ndarray:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return np.zeros(mask.shape, np.float32)
    x0, x1 = float(xs.min()), float(xs.max())
    y0, y1 = float(ys.min()), float(ys.max())
    yy, xx = np.indices(mask.shape, dtype=np.float32)
    if region.grip_type == "sloper":
        # Slopers rise toward their outer/top shoulder and fade toward the
        # product-facing inner edge.  The accepted boundary remains untouched.
        if (x0 + x1) * 0.5 < width * ss * 0.33:
            axis = 1.0 - (xx - x0) / max(x1 - x0, 1.0)
        elif (x0 + x1) * 0.5 > width * ss * 0.67:
            axis = (xx - x0) / max(x1 - x0, 1.0)
        else:
            axis = 1.0 - (yy - y0) / max(y1 - y0, 1.0)
        taper = 0.58 + 0.42 * np.clip(axis, 0.0, 1.0)
    else:
        taper = np.ones(mask.shape, np.float32)
    taper *= mask
    return taper.astype(np.float32)


def _source_cues(
    rgba: np.ndarray,
    high_body: np.ndarray,
    high_masks: Mapping[int, np.ndarray],
    grain_cap: float,
    _ss: int,
) -> tuple[np.ndarray, float]:
    body = (
        cv2.resize(
            high_body.astype(np.uint8),
            (rgba.shape[1], rgba.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
        > 0
    )
    grips = np.zeros(body.shape, np.uint8)
    for mask in high_masks.values():
        grips |= cv2.resize(
            mask.astype(np.uint8),
            (rgba.shape[1], rgba.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
    grips = (
        cv2.dilate(grips, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19))) > 0
    )
    interior = cv2.distanceTransform(body.astype(np.uint8), cv2.DIST_L2, 5) > 10
    safe = body & interior & ~grips & (rgba[..., 3] > 0)
    if int(safe.sum()) < 100:
        safe = body & interior & (rgba[..., 3] > 0)
    pixels = rgba[..., :3][safe].astype(np.float32)
    if len(pixels) < 10:
        cue = np.asarray((235.0, 211.0, 174.0), np.float32)
    else:
        cue = np.median(pixels, axis=0).astype(np.float32)
    target = np.asarray((242.0, 220.0, 184.0), np.float32)
    base = np.clip(target * 0.72 + cue * 0.28, 175.0, 248.0)

    gray = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    horizontal_base = cv2.GaussianBlur(gray, (0, 0), sigmaX=18.0, sigmaY=1.2)
    residual = np.abs(gray - horizontal_base)[safe]
    cue_strength = float(np.median(residual)) if len(residual) else 0.015
    strength = min(grain_cap, max(0.018, 0.018 + cue_strength * 0.8))
    return base, strength


def _shade(
    height_field: np.ndarray,
    body: np.ndarray,
    body_weight: np.ndarray,
    cavity: np.ndarray,
    edge: np.ndarray,
    surface: np.ndarray,
    base_color: np.ndarray,
    grain_strength: float,
    pixel_sha: str,
    profile: GenericStage4Profile,
) -> np.ndarray:
    dy, dx = np.gradient(height_field)
    length = np.sqrt(dx * dx + dy * dy + 1.0)
    nx, ny, nz = -dx / length, -dy / length, 1.0 / length
    light = np.asarray(profile.light_direction, np.float32)
    light /= float(np.linalg.norm(light))
    diffuse = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0.0, 1.0)
    blurred = cv2.GaussianBlur(
        height_field,
        (0, 0),
        sigmaX=7.0 * profile.supersample,
        sigmaY=5.0 * profile.supersample,
    )
    concavity = np.clip(
        (blurred - height_field) / max(profile.pocket_depth, 1.0), 0.0, 1.0
    )
    lighting = np.clip(
        0.62 + 0.43 * diffuse - 0.20 * concavity + 0.035 * surface, 0.38, 1.08
    )

    routed = np.clip(body_weight, 0.0, 1.0)[..., None]
    edge_tone = np.clip(base_color * np.asarray((0.84, 0.80, 0.74), np.float32), 0, 255)
    surface_color = (
        edge_tone[None, None, :] * (1.0 - routed) + base_color[None, None, :] * routed
    )
    pocket_color = np.clip(
        base_color * np.asarray((0.43, 0.36, 0.28), np.float32), 0, 255
    )
    edge_color = np.clip(
        base_color * np.asarray((0.73, 0.66, 0.55), np.float32), 0, 255
    )
    color = surface_color * (1.0 - 0.82 * cavity[..., None]) + pocket_color[
        None, None, :
    ] * (0.82 * cavity[..., None])
    color = color * (1.0 - 0.34 * edge[..., None]) + edge_color[None, None, :] * (
        0.34 * edge[..., None]
    )

    grain = _wood_grain(
        height_field.shape, int(pixel_sha[:16], 16), profile.supersample
    )
    color *= 1.0 + grain_strength * grain[..., None]
    color *= lighting[..., None]
    color = np.clip(color, 0.0, 255.0)
    color *= body[..., None]
    return color.astype(np.float32)


def _wood_grain(shape: tuple[int, int], seed: int, ss: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    fields = []
    for sigma_x, sigma_y in ((42.0, 1.9), (17.0, 0.85), (7.0, 0.45)):
        noise = rng.standard_normal(shape, dtype=np.float32)
        fields.append(
            cv2.GaussianBlur(noise, (0, 0), sigmaX=sigma_x * ss, sigmaY=sigma_y * ss)
        )
    fields = [_standardize(field) for field in fields]
    grain = 0.58 * fields[0] + 0.29 * fields[1] + 0.13 * fields[2]
    grain = cv2.GaussianBlur(grain, (0, 0), sigmaX=0.35 * ss, sigmaY=0.18 * ss)
    grain -= float(np.mean(grain, dtype=np.float64))
    maximum = float(np.max(np.abs(grain)))
    if maximum:
        grain /= maximum
    return grain.astype(np.float32)


def _standardize(values: np.ndarray) -> np.ndarray:
    deviation = float(np.std(values, dtype=np.float64))
    if deviation == 0:
        return np.zeros_like(values)
    return ((values - float(np.mean(values, dtype=np.float64))) / deviation).astype(
        np.float32
    )


def _downsample_rgba(
    high_rgb: np.ndarray, body: np.ndarray, width: int, height: int
) -> np.ndarray:
    rgb = cv2.resize(high_rgb, (width, height), interpolation=cv2.INTER_LANCZOS4)
    alpha = np.clip(
        cv2.resize(
            body.astype(np.float32), (width, height), interpolation=cv2.INTER_LANCZOS4
        ),
        0.0,
        1.0,
    )
    result = np.zeros((height, width, 4), np.uint8)
    result[..., :3] = np.rint(np.clip(rgb, 0, 255)).astype(np.uint8)
    result[..., 3] = np.rint(alpha * 255).astype(np.uint8)
    result[result[..., 3] == 0, :3] = 0
    return result


def _scenarios(
    regions: tuple[_Region, ...], masks: Mapping[int, np.ndarray]
) -> dict[str, tuple[int, ...]]:
    by_type = {
        kind: tuple(region.id for region in regions if region.grip_type == kind)
        for kind in _GRIP_TYPES
    }
    pairs: dict[str, list[int]] = {}
    for region in regions:
        if region.symmetry_pair:
            pairs.setdefault(region.symmetry_pair, []).append(region.id)
    symmetric = tuple(next(iter(pairs.values()))) if pairs else ()
    mixed: list[int] = []
    for kind in _GRIP_TYPES:
        values = by_type[kind]
        if values:
            mixed.append(values[len(values) // 2])
    all_ids = tuple(region.id for region in regions)
    scenarios = {
        "all": all_ids,
        "jugs": by_type["jug"],
        "slopers": by_type["sloper"],
        "edges": by_type["edge"],
        "pockets": by_type["pocket"],
        "symmetric-pair": symmetric,
        "mixed": tuple(mixed),
    }
    if set(masks) != set(all_ids):
        raise ConversionError("Stage 4 masks do not match regions")
    return scenarios


def _highlight(
    normal: np.ndarray, masks: Mapping[int, np.ndarray], selected: tuple[int, ...]
) -> np.ndarray:
    coverage = np.zeros(normal.shape[:2], np.float32)
    for identifier in selected:
        coverage = np.maximum(coverage, masks[identifier])
    amount = 0.48 * coverage[..., None]
    result = normal.copy()
    rgb = normal[..., :3].astype(np.float32)
    result[..., :3] = np.rint(
        np.clip(rgb * (1.0 - amount) + _HIGHLIGHT * amount, 0, 255)
    ).astype(np.uint8)
    result[result[..., 3] == 0, :3] = 0
    return result


def _manifest(
    width: int,
    height: int,
    document: Mapping[str, object],
    regions: tuple[_Region, ...],
    profile: GenericStage4Profile,
) -> dict[str, object]:
    return {
        "canvas": {"height": height, "width": width},
        "profile": asdict(profile),
        "regions": [
            {
                "displayPath": region.display_path.data,
                "id": region.id,
                "interactionId": f"region-{region.id:02d}",
                "key": region.key,
                "pieceIndex": region.piece_index,
                "type": region.grip_type,
            }
            for region in regions
        ],
        "schemaVersion": 1,
        "silhouettePaths": document["silhouettePaths"],
        "stage": 4,
    }


def _highlight_document(
    scenarios: Mapping[str, tuple[int, ...]], masks: Mapping[int, np.ndarray]
) -> dict[str, object]:
    records = []
    for name, selected in scenarios.items():
        union = np.zeros(next(iter(masks.values())).shape, np.float32)
        for identifier in selected:
            union = np.maximum(union, masks[identifier])
        records.append(
            {
                "id": name,
                "maskSha256": sha256(union.tobytes()).hexdigest(),
                "selectedIds": list(selected),
            }
        )
    return {"scenarios": records, "schemaVersion": 1, "stage": 4}


def _selectable_svg(
    normal_png: bytes, width: int, height: int, regions: tuple[_Region, ...]
) -> str:
    encoded = base64.b64encode(normal_png).decode("ascii")
    paths = []
    for region in regions:
        paths.append(
            f'  <path id="region-{region.id:02d}" data-region-id="{region.id}" '
            f'data-key="{escape(region.key)}" data-type="{region.grip_type}" '
            f'data-piece-index="{region.piece_index}" d="{region.display_path.data}" />'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        "  <style>\n"
        "    .interaction path { fill: #ff5b24; fill-opacity: 0; cursor: pointer; pointer-events: all; transition: fill-opacity 120ms ease; }\n"
        '    .interaction path:hover, .interaction path.active, .interaction path[data-active="true"] { fill-opacity: .48; }\n'
        "  </style>\n"
        f'  <image width="{width}" height="{height}" href="data:image/png;base64,{encoded}" />\n'
        '  <g class="interaction">\n' + "\n".join(paths) + "\n  </g>\n</svg>\n"
    )


def _review(normal: np.ndarray, highlighted: Mapping[str, np.ndarray]) -> np.ndarray:
    pairs = (
        ("Clean normal", normal, "All holds", highlighted["all"]),
        ("Jugs", highlighted["jugs"], "Slopers", highlighted["slopers"]),
        ("Edges", highlighted["edges"], "Pockets", highlighted["pockets"]),
        (
            "Symmetric pair",
            highlighted["symmetric-pair"],
            "Mixed selection",
            highlighted["mixed"],
        ),
    )
    height, width = normal.shape[:2]
    gutter, outer, title_height = 18, 18, 36
    canvas = Image.new(
        "RGB",
        (
            width * 2 + gutter + outer * 2,
            (height + title_height) * 4 + gutter * 3 + outer * 2,
        ),
        _WARM_WHITE,
    )
    draw = ImageDraw.Draw(canvas)
    font = _font(16, bold=True)
    for row, (left_title, left, right_title, right) in enumerate(pairs):
        y = outer + row * (height + title_height + gutter)
        for column, (title, rgba) in enumerate(
            ((left_title, left), (right_title, right))
        ):
            x = outer + column * (width + gutter)
            draw.text((x + 4, y + 6), title, font=font, fill=(48, 45, 41))
            product = Image.fromarray(rgba, "RGBA")
            panel = Image.new("RGBA", (width, height), _WARM_WHITE + (255,))
            panel.alpha_composite(product)
            canvas.paste(panel.convert("RGB"), (x, y + title_height))
    return np.asarray(canvas, np.uint8)


def _path_mask(path: DisplayPath, width: int, height: int, ss: int) -> np.ndarray:
    contour = flatten_display_path(path, scale=float(ss), curve_steps=64)
    mask = np.zeros((height * ss, width * ss), np.uint8)
    cv2.fillPoly(mask, [np.rint(contour).astype(np.int32)], 1, lineType=cv2.LINE_8)
    return mask


def _smoothstep(value: np.ndarray) -> np.ndarray:
    return value * value * (3.0 - 2.0 * value)


def _inside_root(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ConversionError("artifact path must be relative")
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ConversionError("artifact path leaves the run root") from error
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConversionError(f"invalid JSON evidence: {path.name}") from error
    if not isinstance(value, dict):
        raise ConversionError(f"JSON evidence must be an object: {path.name}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _encode_png(array: np.ndarray) -> bytes:
    buffer = BytesIO()
    Image.fromarray(array, "RGBA" if array.shape[2] == 4 else "RGB").save(
        buffer, format="PNG", optimize=False, compress_level=9
    )
    return buffer.getvalue()


def _write_png(path: Path, array: np.ndarray) -> None:
    path.write_bytes(_encode_png(array))


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()
