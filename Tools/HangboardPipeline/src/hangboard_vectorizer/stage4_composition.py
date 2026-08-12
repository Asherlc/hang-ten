"""Pure, evidence-preserving Stage 4 selectable illustration composition."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from typing import Mapping
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

from .display_paths import DisplayPath, parse_display_path
from .vector_smoothing import rasterize_display_path


_TYPES = frozenset(("pocket", "jug", "sloper"))
_SCENARIOS = ("jugs", "slopers", "symmetric-pockets", "mixed", "all")


@dataclass(frozen=True, slots=True)
class Stage4Region:
    id: str
    piece_id: str
    piece_index: int
    grip_type: str
    display_path: DisplayPath


@dataclass(frozen=True, slots=True)
class HighlightScenario:
    id: str
    selected_ids: tuple[str, ...]
    mask_sha256: str
    changed_pixels: int


@dataclass(frozen=True, slots=True)
class Stage4Candidate:
    width: int
    height: int
    source_png: bytes
    svg: bytes
    manifest: bytes
    normal_png: bytes
    highlight_pngs: tuple[tuple[str, bytes], ...]
    highlight_manifest: bytes


def compose_stage4(
    source_png: bytes, stage3_document: Mapping[str, object]
) -> Stage4Candidate:
    """Create all deterministic Stage 4 candidate bytes from supplied evidence."""
    rgba = _decode_rgba_png(source_png)
    height, width = rgba.shape[:2]
    regions = _parse_stage3_regions(stage3_document, width, height)
    masks = _coverage_masks(regions, width, height)
    scenarios = select_highlight_scenarios(regions, masks, width, height)
    previews: list[tuple[str, bytes]] = []
    records: list[dict[str, object]] = []
    for name in _SCENARIOS:
        selected = scenarios[name]
        image = render_highlight(rgba, masks, selected)
        _validate_highlight(rgba, image, masks, selected, name)
        union = _selected_union(masks, selected, height, width)
        changed = np.any(image[..., :3] != rgba[..., :3], axis=2)
        previews.append((name, _encode_png(image)))
        records.append(
            {
                "changedPixels": int(changed.sum()),
                "id": name,
                "maskSha256": sha256(union.tobytes()).hexdigest(),
                "selectedIds": list(selected),
            }
        )
    manifest = {
        "canvas": {"height": height, "width": width},
        "regions": [
            {
                "displayPath": region.display_path.data,
                "id": region.id,
                "pieceId": region.piece_id,
                "pieceIndex": region.piece_index,
                "type": region.grip_type,
            }
            for region in regions
        ],
        "schemaVersion": 1,
        "stage": 4,
    }
    highlights = {"scenarios": records, "schemaVersion": 1, "stage": 4}
    return Stage4Candidate(
        width,
        height,
        source_png,
        _serialize_svg(source_png, width, height, regions),
        _json_bytes(manifest),
        _encode_png(rgba),
        tuple(previews),
        _json_bytes(highlights),
    )


def select_highlight_scenarios(
    regions: tuple[Stage4Region, ...],
    masks: Mapping[str, np.ndarray],
    width: int,
    height: int,
) -> Mapping[str, tuple[str, ...]]:
    """Select generic, stable examples without relying on product-specific IDs."""
    if width < 1 or height < 1 or {region.id for region in regions} != set(masks):
        raise ValueError("Stage 4 regions and masks do not agree")
    metrics = {region.id: _mask_metrics(masks[region.id]) for region in regions}
    jugs = tuple(region.id for region in regions if region.grip_type == "jug")
    slopers = tuple(region.id for region in regions if region.grip_type == "sloper")
    pockets = tuple(region for region in regions if region.grip_type == "pocket")
    symmetric = _symmetric_pockets(pockets, metrics, width, height)
    seeds: list[str] = []
    if jugs:
        seeds.append(
            min(jugs, key=lambda identifier: (metrics[identifier][0], identifier))
        )
    if slopers:
        seeds.append(
            max(slopers, key=lambda identifier: (metrics[identifier][3], identifier))
        )
    if pockets:
        seeds.append(
            min(
                (region.id for region in pockets),
                key=lambda identifier: (
                    (metrics[identifier][0] - width / 2) ** 2
                    + (metrics[identifier][1] - height / 2) ** 2,
                    identifier,
                ),
            )
        )
    # Preserve document order for seeds, then fill with deterministic farthest points.
    mixed = [region.id for region in regions if region.id in seeds]
    all_ids = tuple(region.id for region in regions)
    while len(mixed) < min(6, len(regions)):
        candidates = [region.id for region in regions if region.id not in mixed]
        if not candidates:
            break

        def distance(identifier: str) -> tuple[float, str]:
            x, y = metrics[identifier][:2]
            nearest = (
                min(
                    (x - metrics[chosen][0]) ** 2 + (y - metrics[chosen][1]) ** 2
                    for chosen in mixed
                )
                if mixed
                else float("inf")
            )
            return nearest, identifier

        mixed.append(max(candidates, key=distance))
    return {
        "jugs": jugs,
        "slopers": slopers,
        "symmetric-pockets": symmetric,
        "mixed": tuple(mixed),
        "all": all_ids,
    }


def render_highlight(
    rgba: np.ndarray,
    masks: Mapping[str, np.ndarray],
    selected_ids: tuple[str, ...],
    *,
    color: tuple[int, int, int] = (255, 90, 31),
    opacity: float = 0.48,
) -> np.ndarray:
    """Apply a straight-alpha RGB source-over highlight, keeping source alpha."""
    source = np.asarray(rgba)
    if source.dtype != np.uint8 or source.ndim != 3 or source.shape[2] != 4:
        raise ValueError("highlight source must be an RGBA uint8 raster")
    if (
        not 0 <= opacity <= 1
        or len(color) != 3
        or any(type(value) is not int or not 0 <= value <= 255 for value in color)
    ):
        raise ValueError("highlight color or opacity is invalid")
    if len(set(selected_ids)) != len(selected_ids) or any(
        identifier not in masks for identifier in selected_ids
    ):
        raise ValueError("highlight selection references unknown regions")
    coverage = _selected_union(
        masks, selected_ids, source.shape[0], source.shape[1]
    ).astype(np.float32)
    alpha = coverage * opacity
    result = source.copy()
    rgb = source[..., :3].astype(np.float32)
    overlay = np.asarray(color, dtype=np.float32)
    result[..., :3] = np.clip(
        np.rint(rgb * (1.0 - alpha[..., None]) + overlay * alpha[..., None]), 0, 255
    ).astype(np.uint8)
    return result


def _parse_stage3_regions(
    document: Mapping[str, object], width: int, height: int
) -> tuple[Stage4Region, ...]:
    expected = {
        "canonicalSeams",
        "height",
        "pieces",
        "profile",
        "regions",
        "schemaVersion",
        "stage",
        "stage2AcceptanceRawSha256",
        "width",
    }
    if (
        not isinstance(document, Mapping)
        or set(document) != expected
        or document.get("schemaVersion") != 1
        or document.get("stage") != 3
        or document.get("width") != width
        or document.get("height") != height
    ):
        raise ValueError("invalid Stage 3 document")
    pieces = document.get("pieces")
    values = document.get("regions")
    if not isinstance(pieces, list) or not isinstance(values, list) or not values:
        raise ValueError("Stage 3 document has no regions")
    owners: dict[int, str] = {}
    for index, piece in enumerate(pieces):
        if (
            not isinstance(piece, Mapping)
            or piece.get("pieceIndex") != index
            or piece.get("id") != f"piece-{index + 1:02d}-silhouette"
        ):
            raise ValueError("Stage 3 piece ownership is invalid")
        owners[index] = piece["id"]
    result: list[Stage4Region] = []
    seen: set[str] = set()
    for ordinal, value in enumerate(values, start=1):
        if not isinstance(value, Mapping):
            raise ValueError("Stage 3 region is invalid")
        identifier, piece_index, grip_type = (
            value.get("id"),
            value.get("pieceIndex"),
            value.get("type"),
        )
        if (
            not isinstance(identifier, str)
            or identifier in seen
            or type(piece_index) is not int
            or piece_index not in owners
            or grip_type not in _TYPES
            or identifier != f"piece-{piece_index + 1:02d}-hold-{ordinal:02d}"
        ):
            raise ValueError("Stage 3 region identity is invalid")
        raw_path = value.get("displayPath")
        parsed_path = parse_display_path(
            raw_path, identifier, width, height, allow_linear_segments=True
        )
        if parsed_path is None or not isinstance(raw_path, str):
            raise ValueError("Stage 3 region path is missing")
        seen.add(identifier)
        # Keep the accepted Stage 3 string exactly for the interactive contract;
        # use the parser's canonical tokens only when rasterizing below.
        result.append(
            Stage4Region(
                identifier,
                owners[piece_index],
                piece_index,
                grip_type,
                DisplayPath(raw_path, parsed_path.commands, parsed_path.coordinates),
            )
        )
    return tuple(result)


def _coverage_masks(
    regions: tuple[Stage4Region, ...], width: int, height: int
) -> dict[str, np.ndarray]:
    masks: dict[str, np.ndarray] = {}
    for region in regions:
        parsed = parse_display_path(
            region.display_path.data,
            region.id,
            width,
            height,
            allow_linear_segments=True,
        )
        assert parsed is not None
        high = rasterize_display_path(parsed, width, height, scale=4)
        masks[region.id] = (
            high.reshape(height, 4, width, 4)
            .mean(axis=(1, 3), dtype=np.float64)
            .astype(np.float32)
        )
    return masks


def _mask_metrics(mask: np.ndarray) -> tuple[float, float, float, float, float]:
    value = np.asarray(mask, dtype=np.float64)
    if value.ndim != 2 or not np.any(value > 0):
        raise ValueError("Stage 3 path has an empty raster mask")
    y, x = np.indices(value.shape)
    area = float(value.sum())
    cx, cy = float((x * value).sum() / area), float((y * value).sum() / area)
    ys, xs = np.nonzero(value > 0)
    return cx, cy, float(ys.max() - ys.min() + 1), float(xs.max() - xs.min() + 1), area


def _symmetric_pockets(
    pockets: tuple[Stage4Region, ...],
    metrics: Mapping[str, tuple[float, float, float, float, float]],
    width: int,
    height: int,
) -> tuple[str, ...]:
    if len(pockets) < 2:
        return ()
    median_height = float(np.median([metrics[region.id][2] for region in pockets]))
    ordered = sorted(pockets, key=lambda region: (metrics[region.id][1], region.id))
    rows: list[list[Stage4Region]] = []
    for region in ordered:
        if (
            not rows
            or metrics[region.id][1] - metrics[rows[-1][-1].id][1]
            > 0.35 * median_height
        ):
            rows.append([region])
        else:
            rows[-1].append(region)
    row = min(
        rows,
        key=lambda values: (
            abs(np.mean([metrics[item.id][1] for item in values]) - height / 2),
            tuple(item.id for item in values),
        ),
    )
    midpoint = width / 2
    pairs: list[
        tuple[tuple[float, float, float, tuple[str, str]], tuple[str, str]]
    ] = []
    for left in row:
        for right in row:
            if metrics[left.id][0] >= midpoint or metrics[right.id][0] <= midpoint:
                continue
            lx, ly, _, _, la = metrics[left.id]
            rx, ry, _, _, ra = metrics[right.id]
            score = (
                abs(ly - ry) / max(median_height, 1),
                abs((lx + rx) - width) / max(width, 1),
                abs(la - ra) / max(la, ra, 1),
                tuple(sorted((left.id, right.id))),
            )
            pairs.append((score, (left.id, right.id)))
    if not pairs:
        return ()
    chosen = min(pairs, key=lambda value: value[0])[1]
    order = {region.id: index for index, region in enumerate(pockets)}
    return tuple(sorted(chosen, key=order.__getitem__))


def _selected_union(
    masks: Mapping[str, np.ndarray],
    selected_ids: tuple[str, ...],
    height: int,
    width: int,
) -> np.ndarray:
    result = np.zeros((height, width), dtype=np.float32)
    for identifier in selected_ids:
        value = np.asarray(masks[identifier], dtype=np.float32)
        if value.shape != (height, width) or np.any(value < 0) or np.any(value > 1):
            raise ValueError("highlight mask is invalid")
        result = np.maximum(result, value)
    return result


def _validate_highlight(
    source: np.ndarray,
    highlighted: np.ndarray,
    masks: Mapping[str, np.ndarray],
    selected: tuple[str, ...],
    name: str,
) -> None:
    changed = np.any(source[..., :3] != highlighted[..., :3], axis=2)
    union = _selected_union(masks, selected, source.shape[0], source.shape[1]) > 0
    unrelated = (
        _selected_union(
            masks,
            tuple(identifier for identifier in masks if identifier not in selected),
            source.shape[0],
            source.shape[1],
        )
        > 0
    ) & ~union
    if np.any(changed & ~union) or np.any(changed & unrelated):
        raise ValueError(f"highlight leaks outside selected masks: {name}")
    if selected:
        denominator = int(np.count_nonzero(changed | union))
        if denominator == 0 or np.count_nonzero(changed & union) / denominator < 0.995:
            raise ValueError(f"highlight coverage is incomplete: {name}")
    elif np.any(changed):
        raise ValueError(f"empty highlight changed pixels: {name}")
    if name == "all":
        for identifier, mask in masks.items():
            if np.any(mask > 0) and not np.any(changed & (mask > 0)):
                raise ValueError(f"all highlight omitted {identifier}")


def _decode_rgba_png(data: bytes) -> np.ndarray:
    try:
        with Image.open(BytesIO(data)) as image:
            if (
                image.format != "PNG"
                or image.mode != "RGBA"
                or getattr(image, "n_frames", 1) != 1
            ):
                raise ValueError("Stage 4 source must be one RGBA PNG")
            image.seek(0)
            return np.asarray(image).copy()
    except (OSError, ValueError) as error:
        raise ValueError("Stage 4 source must be one RGBA PNG") from error


def _encode_png(rgba: np.ndarray) -> bytes:
    output = BytesIO()
    Image.fromarray(np.asarray(rgba, dtype=np.uint8), mode="RGBA").save(
        output, format="PNG", optimize=False, compress_level=9
    )
    return output.getvalue()


def _serialize_svg(
    source_png: bytes, width: int, height: int, regions: tuple[Stage4Region, ...]
) -> bytes:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.Element(
        "{http://www.w3.org/2000/svg}svg",
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
        },
    )
    style = ET.SubElement(root, "{http://www.w3.org/2000/svg}style")
    style.text = ".product-render { pointer-events: none; }\n.grip-region { fill: transparent; stroke: none; pointer-events: all; }\n.grip-region:hover { fill: #ff5a1f; fill-opacity: .24; }\n.grip-region.active { fill: #ff5a1f; fill-opacity: .48; }"
    ET.SubElement(
        root,
        "{http://www.w3.org/2000/svg}image",
        {
            "class": "product-render",
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "preserveAspectRatio": "none",
            "href": "data:image/png;base64,"
            + base64.b64encode(source_png).decode("ascii"),
        },
    )
    for region in regions:
        ET.SubElement(
            root,
            "{http://www.w3.org/2000/svg}path",
            {
                "id": region.id,
                "class": "grip-region",
                "data-piece": region.piece_id,
                "data-type": region.grip_type,
                "d": region.display_path.data,
            },
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=False) + b"\n"


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
