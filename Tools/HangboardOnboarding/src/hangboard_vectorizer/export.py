from __future__ import annotations

import xml.etree.ElementTree as ET

import cv2
import numpy as np

from .alignment import AlignmentInfo
from .geometry import Opening, RectifiedBoard
from .product_render import (
    encode_png_bytes_data_url,
    load_render_asset,
)
from .product_validation import validate_product_output
from .regions import GripRegion
from .templates import ProductTemplate, TemplateRegion


_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NAMESPACE)


def build_manifest(
    source: str,
    board: RectifiedBoard,
    openings: tuple[Opening, ...],
    regions: tuple[GripRegion, ...],
    *,
    product: ProductTemplate | None = None,
    alignment: AlignmentInfo | None = None,
) -> dict[str, object]:
    """Build a JSON-serializable manifest with normalized feature geometry."""
    if board.width <= 0 or board.height <= 0:
        raise ValueError("board dimensions must be positive")
    if product is not None:
        validate_product_output(product, regions)
    opening_ids = {opening.id for opening in openings}
    for region in regions:
        if region.source == "automatic" and region.opening_id not in opening_ids:
            raise ValueError(
                f"automatic region {region.id!r} must reference an existing opening"
            )
    manifest: dict[str, object] = {
        "schemaVersion": 1,
        "source": source,
        "canvas": {"width": int(board.width), "height": int(board.height)},
        "warnings": list(board.warnings),
        "openings": [
            {
                "id": opening.id,
                "center": _normalized_point(opening.center, board),
                "bbox": _normalized_bbox(opening.bbox, board),
                "contour": _normalized_contour(opening.contour, board),
                "area": float(opening.area) / (board.width * board.height),
                "aspectRatio": float(opening.aspect_ratio),
            }
            for opening in openings
        ],
        "regions": [_region_manifest(region, board) for region in regions],
    }
    if product is not None:
        manifest["product"] = {
            "id": product.product_id,
            "displayName": product.display_name,
            "templateSchemaVersion": product.schema_version,
        }
    if alignment is not None:
        manifest["alignment"] = {
            "method": alignment.method,
            "aspectRatioError": float(alignment.aspect_ratio_error),
            "confidence": alignment.confidence,
        }
    return manifest


def render_svg(
    board: RectifiedBoard,
    openings: tuple[Opening, ...],
    regions: tuple[GripRegion, ...],
    *,
    normalized_width: int | float = 1000,
    board_color: str = "#d7a86e",
    opening_color: str = "#242424",
    highlight_color: str = "#ff5a1f",
    product: ProductTemplate | None = None,
) -> str:
    """Render the board, visible openings, and interactive grip overlays as SVG."""
    if board.width <= 0 or board.height <= 0 or normalized_width <= 0:
        raise ValueError("board and normalized SVG dimensions must be positive")
    if product is not None:
        validate_product_output(product, regions)
    scale = float(normalized_width) / board.width
    normalized_height = board.height * scale
    root = ET.Element(
        _svg_tag("svg"),
        {"viewBox": f"0 0 {_number(normalized_width)} {_number(normalized_height)}"},
    )
    template_regions = (
        {region.id: region for region in product.regions} if product is not None else {}
    )
    uses_curated_display_geometry = (
        product is not None
        and product.render_asset is None
        and (
            product.display_outline_path is not None
            or any(
                not region.disabled and region.display_path is not None
                for region in regions
            )
        )
    )
    uses_product_render_asset = product is not None and product.render_asset is not None
    style = ET.SubElement(root, _svg_tag("style"))
    if uses_product_render_asset:
        style.text = (
            ".product-render { pointer-events: none; }\n"
            ".grip-region { fill: transparent; stroke: none; pointer-events: all; }\n"
            f".grip-region:hover {{ fill: {highlight_color}; fill-opacity: .24; }}\n"
            f".grip-region.active {{ fill: {highlight_color}; fill-opacity: .48; }}"
        )
    elif uses_curated_display_geometry:
        _add_curated_defs(root)
        style.text = (
            ".board-silhouette { fill: url(#board-wood); filter: drop-shadow(0 5px 5px rgba(36, 24, 14, .18)); }\n"
            ".board-front-face { fill: url(#board-front); pointer-events: none; }\n"
            ".grip-decoration { pointer-events: none; }\n"
            ".grip-pocket-rim { fill: #d8aa70; stroke: #f0d39f; stroke-width: 11; stroke-linejoin: round; }\n"
            ".grip-pocket-wall { fill: #6f4829; stroke: #9e683a; stroke-width: 6; stroke-linejoin: round; }\n"
            ".grip-pocket-cavity { fill: url(#pocket-cavity); filter: drop-shadow(0 3px 2px rgba(67, 38, 15, .42)); }\n"
            ".grip-surface-shadow { fill: #82512b; fill-opacity: .42; }\n"
            ".grip-surface { stroke-linejoin: round; }\n"
            ".grip-surface[data-type='jug'] { fill: url(#surface-jug); stroke: #c18b52; stroke-width: 1.25; }\n"
            ".grip-surface[data-angle='35'] { fill: url(#surface-35); stroke: #9b6738; stroke-width: 1.25; }\n"
            ".grip-surface[data-angle='20'] { fill: url(#surface-20); stroke: #aa7440; stroke-width: 1.25; }\n"
            ".grip-region { fill: transparent; stroke: none; pointer-events: all; }\n"
            f".grip-region:hover {{ fill: {highlight_color}; fill-opacity: .32; }}\n"
            f".grip-region.active {{ fill: {highlight_color}; fill-opacity: .62; }}"
        )
    else:
        style.text = (
            ".grip-region { fill: transparent; pointer-events: all; }\n"
            f".grip-region:hover {{ fill: {highlight_color}; fill-opacity: .25; }}\n"
            f".grip-region.active {{ fill: {highlight_color}; fill-opacity: .55; }}"
        )

    if uses_product_render_asset:
        assert product is not None
        ET.SubElement(
            root,
            _svg_tag("image"),
            {
                "class": "product-render",
                "x": "0",
                "y": "0",
                "width": _number(normalized_width),
                "height": _number(normalized_height),
                "preserveAspectRatio": "none",
                "href": encode_png_bytes_data_url(load_render_asset(product)),
            },
        )
    else:
        if product is not None and product.display_outline_path is not None:
            board_path = product.display_outline_path.scaled(scale)
        else:
            board_path = _path_data(_board_contour(board.mask), scale)
        ET.SubElement(
            root,
            _svg_tag("path"),
            {
                "class": "board-silhouette",
                "fill": board_color,
                "d": board_path,
            },
        )
        if product is not None and product.display_front_path is not None:
            ET.SubElement(
                root,
                _svg_tag("path"),
                {
                    "class": "board-front-face",
                    "d": product.display_front_path.scaled(scale),
                },
            )
        for opening in openings:
            ET.SubElement(
                root,
                _svg_tag("path"),
                {
                    "class": "opening",
                    "fill": opening_color,
                    "d": _path_data(opening.contour, scale),
                },
            )
    for region in regions:
        if region.disabled:
            continue
        attributes = {
            "id": region.id,
            "class": "grip-region",
            "data-opening": region.opening_id,
            "data-type": region.type,
            "data-source": region.source,
        }
        if region.side is not None:
            attributes["data-side"] = region.side
        if region.label is not None:
            attributes["data-label"] = region.label
        template_region = template_regions.get(region.template_region_id or "")
        if product is not None and region.display_path is not None:
            path_data = region.display_path.scaled(scale)
        else:
            path_data = " ".join(
                _path_data(contour, scale) for contour in _region_contours(region)
            )
        attributes["d"] = path_data
        if uses_curated_display_geometry and template_region is not None:
            if region.type == "pocket":
                ET.SubElement(
                    root,
                    _svg_tag("path"),
                    {"class": "grip-decoration grip-pocket-rim", "d": path_data},
                )
                ET.SubElement(
                    root,
                    _svg_tag("path"),
                    {"class": "grip-decoration grip-pocket-wall", "d": path_data},
                )
                ET.SubElement(
                    root,
                    _svg_tag("path"),
                    {
                        "class": "grip-decoration grip-pocket-cavity",
                        "transform": f"translate(0 {_number(2 * scale)})",
                        "d": path_data,
                    },
                )
            elif region.type in ("sloper", "jug"):
                surface_attributes = _surface_attributes(region, template_region)
                ET.SubElement(
                    root,
                    _svg_tag("path"),
                    {
                        **surface_attributes,
                        "class": "grip-decoration grip-surface-shadow",
                        "transform": f"translate(0 {_number(4 * scale)})",
                        "d": path_data,
                    },
                )
                ET.SubElement(
                    root,
                    _svg_tag("path"),
                    {
                        **surface_attributes,
                        "class": "grip-decoration grip-surface",
                        "d": path_data,
                    },
                )
        ET.SubElement(root, _svg_tag("path"), attributes)
    return ET.tostring(root, encoding="unicode")


def _add_curated_defs(root: ET.Element) -> None:
    defs = ET.SubElement(root, _svg_tag("defs"))
    wood = ET.SubElement(
        defs,
        _svg_tag("linearGradient"),
        {"id": "board-wood", "x1": "0%", "y1": "0%", "x2": "0%", "y2": "100%"},
    )
    ET.SubElement(wood, _svg_tag("stop"), {"offset": "0", "stop-color": "#eccb98"})
    ET.SubElement(wood, _svg_tag("stop"), {"offset": ".58", "stop-color": "#d8ad74"})
    ET.SubElement(wood, _svg_tag("stop"), {"offset": "1", "stop-color": "#c58d52"})
    front = ET.SubElement(
        defs,
        _svg_tag("linearGradient"),
        {"id": "board-front", "x1": "0%", "y1": "0%", "x2": "0%", "y2": "100%"},
    )
    ET.SubElement(front, _svg_tag("stop"), {"offset": "0", "stop-color": "#c99459"})
    ET.SubElement(front, _svg_tag("stop"), {"offset": "1", "stop-color": "#ad713e"})
    _add_gradient(defs, "surface-jug", "#e2bd87", "#c78f54")
    _add_gradient(defs, "surface-35", "#d2a069", "#ad713d")
    _add_gradient(defs, "surface-20", "#dfb681", "#c38c53")
    _add_gradient(defs, "pocket-cavity", "#755033", "#2d1c12")


def _add_gradient(defs: ET.Element, gradient_id: str, top: str, bottom: str) -> None:
    gradient = ET.SubElement(
        defs,
        _svg_tag("linearGradient"),
        {
            "id": gradient_id,
            "x1": "0%",
            "y1": "0%",
            "x2": "0%",
            "y2": "100%",
        },
    )
    ET.SubElement(gradient, _svg_tag("stop"), {"offset": "0", "stop-color": top})
    ET.SubElement(
        gradient,
        _svg_tag("stop"),
        {"offset": "1", "stop-color": bottom},
    )


def _surface_attributes(
    region: GripRegion, template_region: TemplateRegion
) -> dict[str, str]:
    metadata = dict(template_region.metadata)
    attributes = {"data-type": region.type}
    angle = metadata.get("angleDeg")
    if angle is not None:
        attributes["data-angle"] = _number(float(angle))
    return attributes


def render_preview(
    board: RectifiedBoard,
    openings: tuple[Opening, ...],
    regions: tuple[GripRegion, ...],
) -> np.ndarray:
    """Render a diagnostic RGB image over the perspective-corrected board."""
    if (
        board.rgb.ndim != 3
        or board.rgb.shape[2] != 3
        or board.rgb.shape[:2] != (board.height, board.width)
    ):
        raise ValueError("board image dimensions do not match its canvas")

    preview = np.ascontiguousarray(board.rgb.astype(np.uint8, copy=True))
    line_width = max(1, round(board.width / 500))
    font_scale = max(0.35, board.width / 1_200)
    font_thickness = max(1, round(board.width / 700))

    for opening in openings:
        cv2.drawContours(
            preview,
            [_integer_contour(opening.contour)],
            -1,
            (0, 255, 255),
            line_width + 2,
            lineType=cv2.LINE_AA,
        )

    colors = _region_colors(len(regions))
    for region, color in zip(regions, colors, strict=True):
        contours = [_integer_contour(contour) for contour in _region_contours(region)]
        cv2.drawContours(
            preview,
            contours,
            -1,
            color,
            line_width,
            lineType=cv2.LINE_AA,
        )
        center = tuple(round(coordinate) for coordinate in region.center)
        cv2.circle(preview, center, max(2, line_width + 1), color, thickness=-1)
        cv2.putText(
            preview,
            region.id,
            (center[0] + 3, center[1] - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            font_thickness,
            lineType=cv2.LINE_AA,
        )

    if board.warnings:
        lines = [f"Warning: {warning}" for warning in board.warnings]
        line_height = max(14, round(24 * font_scale))
        banner_height = min(board.height, 6 + line_height * len(lines))
        overlay = preview.copy()
        cv2.rectangle(
            overlay,
            (0, 0),
            (board.width - 1, banner_height - 1),
            (0, 0, 0),
            -1,
        )
        cv2.addWeighted(overlay, 0.65, preview, 0.35, 0, dst=preview)
        for index, line in enumerate(lines, start=1):
            cv2.putText(
                preview,
                line,
                (5, min(board.height - 3, index * line_height)),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                font_thickness,
                lineType=cv2.LINE_AA,
            )
    return preview


def _integer_contour(contour: np.ndarray) -> np.ndarray:
    return np.rint(contour).astype(np.int32).reshape(-1, 1, 2)


def _region_colors(count: int) -> tuple[tuple[int, int, int], ...]:
    colors: list[tuple[int, int, int]] = []
    for index in range(count):
        hue = round(179 * index / max(1, count))
        hsv = np.array([[[hue, 220, 255]]], dtype=np.uint8)
        rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)[0, 0]
        colors.append(tuple(int(channel) for channel in rgb))
    return tuple(colors)


def _board_contour(mask: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        raise ValueError("board mask has no silhouette")
    return max(contours, key=cv2.contourArea).reshape(-1, 2)


def _path_data(contour: np.ndarray, scale: float) -> str:
    points = np.asarray(contour, dtype=np.float32).reshape(-1, 1, 2)
    if len(points) == 0:
        raise ValueError("cannot render an empty contour")
    perimeter = cv2.arcLength(points, True)
    simplified = cv2.approxPolyDP(points, 0.005 * perimeter, True).reshape(-1, 2)
    scaled = simplified.astype(float) * scale
    commands = [f"M {_number(scaled[0, 0])} {_number(scaled[0, 1])}"]
    commands.extend(
        f"L {_number(point[0])} {_number(point[1])}" for point in scaled[1:]
    )
    commands.append("Z")
    return " ".join(commands)


def _svg_tag(name: str) -> str:
    return f"{{{_SVG_NAMESPACE}}}{name}"


def _number(value: int | float | np.integer | np.floating) -> str:
    return f"{float(value):.12g}"


def _region_manifest(region: GripRegion, board: RectifiedBoard) -> dict[str, object]:
    manifest: dict[str, object] = {
        "id": region.id,
        "openingId": (
            None
            if region.source == "template" and not region.opening_id
            else region.opening_id
        ),
        "type": region.type,
        "side": region.side,
        "disabled": bool(region.disabled),
        "source": region.source,
        "center": _normalized_point(region.center, board),
        "bbox": _normalized_bbox(region.bbox, board),
        "contour": _normalized_contour(region.contour, board),
    }
    if region.label is not None:
        manifest["label"] = region.label
    if region.metadata:
        manifest["metadata"] = dict(region.metadata)
    if region.contours:
        manifest["contours"] = [
            _normalized_contour(contour, board) for contour in region.contours
        ]
    return manifest


def _region_contours(region: GripRegion) -> tuple[np.ndarray, ...]:
    return region.contours or (region.contour,)


def _normalized_point(point: tuple[float, float], board: RectifiedBoard) -> list[float]:
    return [
        _normalized_number(point[0], board.width),
        _normalized_number(point[1], board.height),
    ]


def _normalized_bbox(
    bbox: tuple[int, int, int, int], board: RectifiedBoard
) -> list[float]:
    x, y, width, height = bbox
    return [
        _normalized_number(x, board.width),
        _normalized_number(y, board.height),
        _normalized_number(width, board.width),
        _normalized_number(height, board.height),
    ]


def _normalized_contour(
    contour: np.ndarray, board: RectifiedBoard
) -> list[list[float]]:
    return [
        [
            _normalized_number(point[0], board.width),
            _normalized_number(point[1], board.height),
        ]
        for point in np.asarray(contour).reshape(-1, 2)
    ]


def _normalized_number(
    value: int | float | np.integer | np.floating, dimension: int
) -> float:
    return float(min(1.0, max(0.0, float(value) / dimension)))
