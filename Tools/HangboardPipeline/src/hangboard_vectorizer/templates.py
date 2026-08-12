"""Immutable product-template models and built-in template discovery."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
import json
import math
import re
from typing import Literal, NoReturn, TypeAlias

import cv2
import numpy as np

from .display_paths import DisplayPath, parse_display_path
from .geometry import RectifiedBoard
from .models import ConversionError
from .regions import GripRegion, RegionLayout


TemplateRegionType: TypeAlias = Literal["pocket", "edge", "rail", "jug", "sloper"]
MetadataValue: TypeAlias = str | int | float | bool

_SUPPORTED_REGION_TYPES = frozenset({"pocket", "edge", "rail", "jug", "sloper"})
_SAFE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SAFE_RENDER_ASSET = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.png\Z")
_HARD_EDGE_DISPLAY_PATH_IDS = frozenset(
    {
        "jug-left",
        "jug-right",
        "sloper-35-left",
        "sloper-35-right",
    }
)


@dataclass(frozen=True, slots=True)
class TemplateRegion:
    id: str
    type: TemplateRegionType
    label: str
    side: Literal["left", "right"] | None
    polygons: tuple[np.ndarray, ...]
    metadata: tuple[tuple[str, MetadataValue], ...]
    display_path: DisplayPath | None = None


@dataclass(frozen=True, slots=True)
class ProductRenderProfile:
    style: str
    seed: int
    supersample: int
    bevel_radius: float
    pocket_depth: float
    surface_relief: float
    front_drop: float
    grain_strength: float
    light_direction: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ProductTemplate:
    schema_version: int
    product_id: str
    display_name: str
    canonical_width: int
    canonical_height: int
    outline: tuple[np.ndarray, ...]
    regions: tuple[TemplateRegion, ...]
    display_outline_path: DisplayPath | None = None
    display_front_path: DisplayPath | None = None
    render_profile: ProductRenderProfile | None = None
    render_asset: str | None = None


_TEMPLATE_REGISTRY: tuple[ProductTemplate, ...] | None = None


def load_template_document(document: object) -> ProductTemplate:
    """Validate one parsed product-template JSON document."""
    root = _mapping(document, "document")
    schema_version = _integer(root.get("schemaVersion"), "schemaVersion")
    if schema_version != 1:
        _invalid("schemaVersion must be 1")

    product_id = _identifier(root.get("productId"), "productId")
    display_name = _nonempty_string(root.get("displayName"), "displayName")
    canonical_width, canonical_height = _view_box(root.get("canonicalViewBox"))
    outline = _polygons(root.get("outline"), "outline")
    if not outline:
        _invalid("outline must not be empty")
    display_outline_path = parse_display_path(
        root.get("displayOutlinePath"),
        "displayOutlinePath",
        canonical_width,
        canonical_height,
    )
    display_front_path = parse_display_path(
        root.get("displayFrontPath"),
        "displayFrontPath",
        canonical_width,
        canonical_height,
    )
    render_profile = (
        _parse_render_profile(root["renderProfile"])
        if "renderProfile" in root
        else None
    )
    render_asset = _render_asset(root["renderAsset"]) if "renderAsset" in root else None
    raw_regions = _sequence(root.get("regions"), "regions")
    region_ids: set[str] = set()
    regions: list[TemplateRegion] = []
    for index, raw_region in enumerate(raw_regions):
        field = f"regions[{index}]"
        region = _parse_region(raw_region, field, canonical_width, canonical_height)
        if region.id in region_ids:
            _invalid(f"{field}.id duplicates {region.id!r}")
        region_ids.add(region.id)
        regions.append(region)

    return ProductTemplate(
        schema_version=schema_version,
        product_id=product_id,
        display_name=display_name,
        canonical_width=canonical_width,
        canonical_height=canonical_height,
        outline=outline,
        regions=tuple(regions),
        display_outline_path=display_outline_path,
        display_front_path=display_front_path,
        render_profile=render_profile,
        render_asset=render_asset,
    )


def get_product_template(product_id: str) -> ProductTemplate:
    """Return the built-in template with an exact product ID match."""
    registry = _product_templates()
    for template in registry:
        if template.product_id == product_id:
            return template
    supported = ", ".join(template.product_id for template in registry) or "(none)"
    raise ConversionError(
        f"unknown product template {product_id!r}; supported IDs: {supported}"
    )


def list_product_templates() -> tuple[tuple[str, str], ...]:
    """List built-in templates as deterministically ordered ID/name pairs."""
    return tuple(
        (template.product_id, template.display_name)
        for template in _product_templates()
    )


def layout_from_template(
    template: ProductTemplate, board: RectifiedBoard
) -> RegionLayout:
    """Convert normalized template polygons into canonical board-pixel regions."""
    if (board.width, board.height) != (
        template.canonical_width,
        template.canonical_height,
    ):
        raise ConversionError("template layout requires canonical dimensions")
    regions: list[GripRegion] = []
    scale = np.array([board.width, board.height], dtype=np.float64)
    for template_region in template.regions:
        contours = tuple(polygon * scale for polygon in template_region.polygons)
        if any(not np.isfinite(contour).all() for contour in contours):
            raise ConversionError("template region contains non-finite coordinates")
        areas = tuple(
            abs(float(cv2.contourArea(contour.astype(np.float32))))
            for contour in contours
        )
        primary_index = max(range(len(contours)), key=areas.__getitem__)
        center, bbox = _combined_geometry(contours, board.width, board.height)
        regions.append(
            GripRegion(
                id=template_region.id,
                opening_id="",
                type=template_region.type,
                side=template_region.side,
                contour=contours[primary_index],
                center=center,
                bbox=bbox,
                source="template",
                contours=contours,
                label=template_region.label,
                metadata=template_region.metadata,
                template_region_id=template_region.id,
                display_path=template_region.display_path,
            )
        )
    return RegionLayout(openings=(), regions=tuple(regions))


def _product_templates() -> tuple[ProductTemplate, ...]:
    global _TEMPLATE_REGISTRY
    if _TEMPLATE_REGISTRY is not None:
        return _TEMPLATE_REGISTRY

    discovered = tuple(
        load_template_document(document) for document in _iter_template_documents()
    )
    by_id: dict[str, ProductTemplate] = {}
    for template in discovered:
        if template.product_id in by_id:
            _invalid(f"productId duplicates {template.product_id!r}")
        by_id[template.product_id] = template
    registry = tuple(by_id[product_id] for product_id in sorted(by_id))
    _TEMPLATE_REGISTRY = registry
    return registry


def _combined_geometry(
    contours: tuple[np.ndarray, ...], board_width: int, board_height: int
) -> tuple[tuple[float, float], tuple[int, int, int, int]]:
    raster = np.zeros((board_height, board_width), dtype=np.uint8)
    raster_contours = [np.rint(contour).astype(np.int32) for contour in contours]
    cv2.fillPoly(raster, raster_contours, 1)
    points = cv2.findNonZero(raster)
    if points is None:
        raise ConversionError("template region has no rasterized geometry")
    x, y, width, height = cv2.boundingRect(points)
    moments = cv2.moments(raster, binaryImage=True)
    return (
        (
            float(moments["m10"] / moments["m00"]),
            float(moments["m01"] / moments["m00"]),
        ),
        (x, y, width, height),
    )


def _iter_template_documents() -> Iterable[object]:
    """Read every package JSON resource without making package paths observable."""
    package_files = resources.files("hangboard_vectorizer.products")
    for resource in sorted(package_files.iterdir(), key=lambda item: item.name):
        if resource.name.endswith(".json"):
            yield json.loads(resource.read_text(encoding="utf-8"))


def _parse_region(
    raw_region: object, field: str, canonical_width: int, canonical_height: int
) -> TemplateRegion:
    region = _mapping(raw_region, field)
    region_id = _identifier(region.get("id"), f"{field}.id")
    region_type = _nonempty_string(region.get("type"), f"{field}.type")
    if region_type not in _SUPPORTED_REGION_TYPES:
        _invalid(f"{field}.type is unsupported")
    label = _nonempty_string(region.get("label"), f"{field}.label")
    raw_side = region.get("side")
    if raw_side is not None and raw_side not in ("left", "right"):
        _invalid(f"{field}.side must be left or right")
    polygons = _polygons(region.get("polygons"), f"{field}.polygons")
    if not polygons:
        _invalid(f"{field}.polygons must not be empty")
    return TemplateRegion(
        id=region_id,
        type=region_type,  # type: ignore[arg-type]
        label=label,
        side=raw_side,
        polygons=polygons,
        metadata=_metadata(region.get("metadata", {}), f"{field}.metadata"),
        display_path=parse_display_path(
            region.get("displayPath"),
            f"{field}.displayPath",
            canonical_width,
            canonical_height,
            allow_linear_segments=region_id in _HARD_EDGE_DISPLAY_PATH_IDS,
        ),
    )


def _parse_render_profile(value: object) -> ProductRenderProfile:
    profile = _mapping(value, "renderProfile")
    style = _nonempty_string(profile.get("style"), "renderProfile.style")
    if style != "pale-wood-heightfield-v1":
        _invalid("renderProfile.style is unsupported")
    seed = _integer(profile.get("seed"), "renderProfile.seed")
    if seed < 0:
        _invalid("renderProfile.seed must be nonnegative")
    supersample = _integer(profile.get("supersample"), "renderProfile.supersample")
    if not 2 <= supersample <= 4:
        _invalid("renderProfile.supersample must be within 2..4")

    light_direction_values = _sequence(
        profile.get("lightDirection"), "renderProfile.lightDirection"
    )
    if len(light_direction_values) != 3:
        _invalid("renderProfile.lightDirection must contain three values")
    light_direction = tuple(
        _finite_number(item, f"renderProfile.lightDirection[{index}]")
        for index, item in enumerate(light_direction_values)
    )
    maximum_component = max(abs(component) for component in light_direction)
    if maximum_component == 0.0:
        _invalid("renderProfile.lightDirection must be nonzero")
    normalized_components = tuple(
        component / maximum_component for component in light_direction
    )
    normalized_length = math.sqrt(
        sum(component * component for component in normalized_components)
    )
    normalized_light_direction = tuple(
        component / normalized_length for component in normalized_components
    )

    grain_strength = _finite_number(
        profile.get("grainStrength"), "renderProfile.grainStrength"
    )
    if not 0.0 <= grain_strength <= 0.25:
        _invalid("renderProfile.grainStrength must be within 0..0.25")

    return ProductRenderProfile(
        style=style,
        seed=seed,
        supersample=supersample,
        bevel_radius=_positive_number(
            profile.get("bevelRadius"), "renderProfile.bevelRadius"
        ),
        pocket_depth=_positive_number(
            profile.get("pocketDepth"), "renderProfile.pocketDepth"
        ),
        surface_relief=_positive_number(
            profile.get("surfaceRelief"), "renderProfile.surfaceRelief"
        ),
        front_drop=_nonnegative_number(
            profile.get("frontDrop"), "renderProfile.frontDrop"
        ),
        grain_strength=grain_strength,
        light_direction=normalized_light_direction,  # type: ignore[arg-type]
    )


def _render_asset(value: object) -> str:
    asset = _nonempty_string(value, "renderAsset")
    if not is_safe_render_asset(asset):
        _invalid("renderAsset must be a safe PNG filename")
    return asset


def _view_box(value: object) -> tuple[int, int]:
    values = _sequence(value, "canonicalViewBox")
    if len(values) != 4:
        _invalid("canonicalViewBox must contain four values")
    if (
        _integer(values[0], "canonicalViewBox") != 0
        or _integer(values[1], "canonicalViewBox") != 0
    ):
        _invalid("canonicalViewBox origin must be 0 0")
    width = _integer(values[2], "canonicalViewBox")
    height = _integer(values[3], "canonicalViewBox")
    if width <= 0 or height <= 0:
        _invalid("canonicalViewBox width and height must be positive")
    return width, height


def _polygons(value: object, field: str) -> tuple[np.ndarray, ...]:
    values = _sequence(value, field)
    polygons = tuple(
        _polygon(polygon, f"{field}[{index}]") for index, polygon in enumerate(values)
    )
    return polygons


def _polygon(value: object, field: str) -> np.ndarray:
    points = _sequence(value, field)
    parsed: list[tuple[float, float]] = []
    for index, point in enumerate(points):
        coordinates = _sequence(point, f"{field}[{index}]")
        if len(coordinates) != 2:
            _invalid(f"{field}[{index}] must contain an x and y coordinate")
        x = _coordinate(coordinates[0], f"{field}[{index}][0]")
        y = _coordinate(coordinates[1], f"{field}[{index}][1]")
        parsed.append((x, y))
    if len(parsed) < 3:
        _invalid(f"{field} must have at least three distinct points")
    if len(set(parsed)) != len(parsed):
        _invalid(f"{field} must not repeat vertices")
    twice_area = sum(
        x * next_y - next_x * y
        for (x, y), (next_x, next_y) in zip(
            parsed, parsed[1:] + parsed[:1], strict=True
        )
    )
    if math.isclose(twice_area, 0.0, abs_tol=1e-12):
        _invalid(f"{field} must have non-zero area")
    polygon = np.asarray(parsed, dtype=np.float64)
    polygon.setflags(write=False)
    return polygon


def _metadata(value: object, field: str) -> tuple[tuple[str, MetadataValue], ...]:
    mapping = _mapping(value, field)
    entries: list[tuple[str, MetadataValue]] = []
    for key, item in mapping.items():
        if not isinstance(key, str):
            _invalid(f"{field} keys must be strings")
        if isinstance(item, bool) or isinstance(item, str) or isinstance(item, int):
            entries.append((key, item))
        elif isinstance(item, float) and math.isfinite(item):
            entries.append((key, item))
        else:
            _invalid(f"{field}.{key} must be a JSON scalar")
    return tuple(sorted(entries))


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _invalid(f"{field} must be an object")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _invalid(f"{field} must be an array")
    return value


def _identifier(value: object, field: str) -> str:
    identifier = _nonempty_string(value, field)
    if not _SAFE_ID.fullmatch(identifier):
        _invalid(f"{field} must be a safe ID")
    return identifier


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        _invalid(f"{field} must be a non-empty string")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid(f"{field} must be an integer")
    return value


def _coordinate(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid(f"{field} must be numeric")
    coordinate = float(value)
    if not math.isfinite(coordinate):
        _invalid(f"{field} must be finite")
    if not 0.0 <= coordinate <= 1.0:
        _invalid(f"{field} must be within 0..1")
    return coordinate


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        _invalid(f"{field} must be finite")
    return number


def _positive_number(value: object, field: str) -> float:
    number = _finite_number(value, field)
    if number <= 0.0:
        _invalid(f"{field} must be positive")
    return number


def _nonnegative_number(value: object, field: str) -> float:
    number = _finite_number(value, field)
    if number < 0.0:
        _invalid(f"{field} must be nonnegative")
    return number


def _invalid(message: str) -> NoReturn:
    raise ConversionError(f"invalid product template: {message}")


def is_safe_render_asset(name: str) -> bool:
    """Return whether *name* is a safe packaged PNG filename."""
    return _SAFE_RENDER_ASSET.fullmatch(name) is not None
