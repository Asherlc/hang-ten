"""Deterministic 2.5D rendering for smooth product templates."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from io import BytesIO
from types import MappingProxyType

import cv2
import numpy as np
from PIL import Image

from .display_paths import DisplayPath, flatten_display_path
from .models import ConversionError
from .templates import (
    _SAFE_RENDER_ASSET,
    ProductRenderProfile,
    ProductTemplate,
    TemplateRegion,
)


_LIGHT_WOOD = np.array([244.0, 224.0, 188.0], dtype=np.float32)
_MID_WOOD = np.array([226.0, 193.0, 140.0], dtype=np.float32)
_CAVITY_WOOD = np.array([104.0, 73.0, 37.0], dtype=np.float32)


@dataclass(frozen=True, slots=True)
class ProductRender:
    """Canonical product render and its exact semantic geometry."""

    rgba: np.ndarray
    height: np.ndarray
    masks: Mapping[str, np.ndarray]


def render_product(template: ProductTemplate) -> ProductRender:
    """Render one product template as a deterministic pale-wood height field."""
    profile = template.render_profile
    if profile is None:
        raise ConversionError("product rendering requires a renderProfile")
    if profile.style != "pale-wood-heightfield-v1":
        raise ConversionError(f"unsupported product render style {profile.style!r}")
    if template.display_outline_path is None:
        raise ConversionError("product rendering requires displayOutlinePath")
    if template.display_front_path is None:
        raise ConversionError("product rendering requires displayFrontPath")

    _validate_center_topology(template)

    width = template.canonical_width
    height_px = template.canonical_height
    ss = profile.supersample
    body_mask = _path_mask(template.display_outline_path, width, height_px, ss)
    body_mask &= _template_outline_mask(template.outline, width, height_px, ss)
    front_mask = _path_mask(template.display_front_path, width, height_px, ss)
    front_mask &= body_mask

    region_masks: dict[str, np.ndarray] = {}
    for region in template.regions:
        if region.display_path is None:
            raise ConversionError(f"enabled region {region.id!r} requires displayPath")
        if region.id in region_masks:
            raise ConversionError(f"duplicate product render mask {region.id!r}")
        mask = _path_mask(region.display_path, width, height_px, ss)
        inside_mask = mask & body_mask
        if not np.any(inside_mask):
            raise ConversionError(
                f"region mask {region.id!r} is outside the board silhouette"
            )
        outside_mask = mask & (body_mask == 0)
        if np.any(outside_mask) and region.type not in ("jug", "sloper"):
            raise ConversionError(
                f"{region.type} mask {region.id!r} extends outside the board silhouette"
            )
        region_masks[region.id] = inside_mask

    high_height, cavity = _compose_height(
        body_mask, front_mask, template.regions, region_masks, profile
    )
    high_rgb = _shade_height(high_height, body_mask, cavity, profile)

    rgba = _downsample_rgba(high_rgb, body_mask, width, height_px)
    canonical_height = cv2.resize(
        high_height, (width, height_px), interpolation=cv2.INTER_LANCZOS4
    ).astype(np.float32)
    canonical_height[rgba[..., 3] == 0] = 0.0

    canonical_masks: dict[str, np.ndarray] = {}
    for key, mask in region_masks.items():
        coverage = cv2.resize(
            mask.astype(np.float32),
            (width, height_px),
            interpolation=cv2.INTER_AREA,
        )
        semantic_mask = coverage >= 0.5
        semantic_mask.setflags(write=False)
        canonical_masks[key] = semantic_mask

    rgba.setflags(write=False)
    canonical_height.setflags(write=False)
    return ProductRender(
        rgba=rgba,
        height=canonical_height,
        masks=MappingProxyType(canonical_masks),
    )


def encode_png_data_url(rgba: np.ndarray) -> str:
    """Encode a canonical RGBA array as a metadata-free PNG data URL."""
    if rgba.dtype != np.uint8 or rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("PNG encoding requires an H x W x 4 uint8 RGBA array")
    buffer = BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(
        buffer, format="PNG", optimize=False, compress_level=9
    )
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def load_render_asset(template: ProductTemplate) -> bytes:
    """Load and validate a template's canonical packaged PNG without rewriting it."""
    if template.render_asset is None:
        raise ConversionError("product template does not declare a renderAsset")
    _validate_render_asset_name(template.render_asset)
    try:
        png_bytes = (
            resources.files("hangboard_vectorizer.products")
            .joinpath(template.render_asset)
            .read_bytes()
        )
        with Image.open(BytesIO(png_bytes)) as image:
            image.load()
            if image.format != "PNG":
                raise ConversionError("renderAsset must decode as PNG")
            if image.mode != "RGBA":
                raise ConversionError("renderAsset must decode as RGBA")
            if image.size != (template.canonical_width, template.canonical_height):
                raise ConversionError(
                    "renderAsset dimensions must match canonicalViewBox"
                )
    except ConversionError:
        raise
    except (OSError, ValueError) as error:
        raise ConversionError(
            f"could not load renderAsset {template.render_asset!r}"
        ) from error
    return png_bytes


def _validate_render_asset_name(render_asset: object) -> None:
    """Reject unsafe resource names at the resource-loading boundary."""
    if (
        not isinstance(render_asset, str)
        or _SAFE_RENDER_ASSET.fullmatch(render_asset) is None
    ):
        raise ConversionError("renderAsset must be a safe PNG filename")


def encode_png_bytes_data_url(png_bytes: bytes) -> str:
    """Encode already-validated PNG bytes without changing the PNG payload."""
    payload = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{payload}"


def _validate_center_topology(template: ProductTemplate) -> None:
    legacy_ids = {"sloper-20-left", "sloper-20-right"}
    if any(region.id in legacy_ids for region in template.regions):
        raise ConversionError("legacy split-center sloper masks are not supported")

    slopers = tuple(region for region in template.regions if region.type == "sloper")
    if template.product_id == "beastmaker-1000":
        if tuple(region.id for region in slopers) != (
            "sloper-35-left",
            "sloper-35-right",
            "sloper-center",
        ):
            raise ConversionError("beastmaker-1000 requires three canonical sloper masks")


def _path_mask(
    path: DisplayPath, width: int, height: int, supersample: int
) -> np.ndarray:
    contour = flatten_display_path(path, scale=float(supersample))
    raster = np.zeros((height * supersample, width * supersample), dtype=np.uint8)
    cv2.fillPoly(raster, [np.rint(contour).astype(np.int32)], 1)
    return raster


def _template_outline_mask(
    outline: tuple[np.ndarray, ...], width: int, height: int, supersample: int
) -> np.ndarray:
    """Rasterize the physical normalized outline independently of display art."""
    raster = np.zeros((height * supersample, width * supersample), dtype=np.uint8)
    contours = []
    for polygon in outline:
        contour = polygon.copy()
        contour[:, 0] *= width * supersample
        contour[:, 1] *= height * supersample
        contours.append(np.rint(contour).astype(np.int32))
    cv2.fillPoly(raster, contours, 1)
    return raster.astype(bool)


def _compose_height(
    body_mask: np.ndarray,
    front_mask: np.ndarray,
    regions: tuple[TemplateRegion, ...],
    region_masks: Mapping[str, np.ndarray],
    profile: ProductRenderProfile,
) -> tuple[np.ndarray, np.ndarray]:
    ss = profile.supersample
    bevel = profile.bevel_radius * ss

    inside = cv2.distanceTransform(body_mask.astype(np.uint8), cv2.DIST_L2, 5)
    body_bevel = np.clip(inside / bevel, 0.0, 1.0)
    height = 12.0 * _smoothstep(body_bevel)

    front_distance = cv2.distanceTransform(
        front_mask.astype(np.uint8), cv2.DIST_L2, 5
    )
    front_weight = _smoothstep(np.clip(front_distance / bevel, 0.0, 1.0))
    height -= profile.front_drop * front_weight

    cavity = np.zeros(body_mask.shape, dtype=np.float32)
    for region in regions:
        mask = region_masks[region.id]
        if region.type not in ("jug", "sloper", "pocket"):
            continue
        distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
        weight = _smoothstep(np.clip(distance / bevel, 0.0, 1.0))
        if region.type == "pocket":
            height -= profile.pocket_depth * weight
            cavity = np.maximum(cavity, weight)
        else:
            height += profile.surface_relief * weight

    height *= body_mask
    return height.astype(np.float32), cavity


def _shade_height(
    height: np.ndarray,
    body_mask: np.ndarray,
    cavity: np.ndarray,
    profile: ProductRenderProfile,
) -> np.ndarray:
    dy, dx = np.gradient(height)
    normal_length = np.sqrt(dx * dx + dy * dy + 1.0)
    nx = -dx / normal_length
    ny = -dy / normal_length
    nz = 1.0 / normal_length
    lx, ly, lz = profile.light_direction
    diffuse = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)

    blurred_height = cv2.GaussianBlur(height, (0, 0), sigmaX=8.0, sigmaY=8.0)
    concavity = np.clip(
        (blurred_height - height) / max(profile.pocket_depth, 1.0), 0.0, 1.0
    )
    lighting = np.clip(0.50 + 0.62 * diffuse - 0.16 * concavity, 0.38, 1.08)

    inside = cv2.distanceTransform(body_mask.astype(np.uint8), cv2.DIST_L2, 5)
    body_bevel = _smoothstep(
        np.clip(inside / (profile.bevel_radius * profile.supersample), 0.0, 1.0)
    )
    surface = (
        _MID_WOOD[None, None, :] * (1.0 - body_bevel[..., None])
        + _LIGHT_WOOD[None, None, :] * body_bevel[..., None]
    )
    color = (
        surface * (1.0 - cavity[..., None])
        + _CAVITY_WOOD[None, None, :] * cavity[..., None]
    )

    grain = _wood_grain(height.shape, profile)
    color *= lighting[..., None]
    color *= 1.0 + profile.grain_strength * grain[..., None]
    color = np.clip(color, 0.0, 255.0)
    color *= body_mask[..., None]
    return color.astype(np.float32)


def _wood_grain(
    shape: tuple[int, int], profile: ProductRenderProfile
) -> np.ndarray:
    rng = np.random.default_rng(profile.seed)
    first = rng.standard_normal(shape, dtype=np.float32)
    second = rng.standard_normal(shape, dtype=np.float32)
    ss = profile.supersample
    first = cv2.GaussianBlur(first, (0, 0), sigmaX=36.0 * ss, sigmaY=1.8 * ss)
    second = cv2.GaussianBlur(second, (0, 0), sigmaX=12.0 * ss, sigmaY=0.7 * ss)
    first = _standardize(first)
    second = _standardize(second)
    grain = 0.68 * first + 0.32 * second
    grain -= float(np.mean(grain, dtype=np.float64))
    maximum = float(np.max(np.abs(grain)))
    if maximum > 0.0:
        grain /= maximum
    return grain.astype(np.float32)


def _standardize(values: np.ndarray) -> np.ndarray:
    mean = float(np.mean(values, dtype=np.float64))
    standard_deviation = float(np.std(values, dtype=np.float64))
    if standard_deviation == 0.0:
        return np.zeros_like(values)
    return ((values - mean) / standard_deviation).astype(np.float32)


def _downsample_rgba(
    high_rgb: np.ndarray,
    body_mask: np.ndarray,
    width: int,
    height: int,
) -> np.ndarray:
    rgb = cv2.resize(high_rgb, (width, height), interpolation=cv2.INTER_LANCZOS4)
    alpha = cv2.resize(
        body_mask.astype(np.float32),
        (width, height),
        interpolation=cv2.INTER_LANCZOS4,
    )
    alpha = np.clip(alpha, 0.0, 1.0)
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = np.rint(np.clip(rgb, 0.0, 255.0)).astype(np.uint8)
    rgba[..., 3] = np.rint(alpha * 255.0).astype(np.uint8)
    rgba[rgba[..., 3] == 0, :3] = 0
    return rgba


def _smoothstep(value: np.ndarray) -> np.ndarray:
    return value * value * (3.0 - 2.0 * value)
