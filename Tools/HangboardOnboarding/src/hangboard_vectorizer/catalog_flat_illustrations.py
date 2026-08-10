"""Deterministic flat preview rendering for the hangboard catalog."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .catalog_outlines import CatalogOutlineDocument, OutlinePath, validate_catalog_document
from .display_paths import DisplayPath, flatten_display_path


PARCHMENT_COLOR = (242, 231, 214)
BOARD_COLOR = (204, 176, 140)
CONTOUR_COLOR = (160, 129, 97)
CAVITY_COLOR = (121, 92, 63)

_CONTACT_COLUMNS = 4
_CONTACT_PADDING = 20
_CONTACT_LABEL_GAP = 8
_CONTACT_LABEL_HEIGHT = 14
_CONTACT_TILE_WIDTH = 320
_CONTACT_TILE_HEIGHT = 220
_CONTACT_SHEET_SKIP_NAMES = frozenset(
    {"contact-sheet-primary.png", "flat-illustrations-contact-sheet.png"}
)


def render_flat_illustration(
    source_path: Path, document: CatalogOutlineDocument, output_path: Path
) -> None:
    validate_catalog_document(document, source_path=source_path)
    with Image.open(source_path) as source_image:
        rgb = np.array(source_image.convert("RGB"), dtype=np.uint8)
    outline_masks = tuple(
        _outline_mask(outline.path, document.canvas_width, document.canvas_height)
        for outline in document.outlines
    )
    board_mask = _detect_board_components(rgb)
    board_mask = _merge_outline_support(board_mask, outline_masks)

    rendered = np.full(rgb.shape, PARCHMENT_COLOR, dtype=np.uint8)
    rendered[board_mask] = BOARD_COLOR

    contour = _mask_boundary(board_mask)
    rendered[contour] = CONTOUR_COLOR

    for hold_mask in outline_masks:
        hold_mask = hold_mask & board_mask
        rendered[hold_mask] = CAVITY_COLOR

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _save_rgb_png(rendered, output_path)


def render_flat_catalog(
    source_dir: Path, outline_dir: Path, output_dir: Path, contact_sheet_path: Path
) -> tuple[Path, ...]:
    sources = _catalog_sources(source_dir)
    outlines = {path.stem: path for path in sorted(outline_dir.glob("*.json")) if path.is_file()}
    source_stems = {path.stem for path in sources}
    if set(outlines) != source_stems:
        missing = sorted(source_stems - set(outlines))
        unexpected = sorted(set(outlines) - source_stems)
        problems: list[str] = []
        if missing:
            problems.append(f"missing outlines: {', '.join(missing)}")
        if unexpected:
            problems.append(f"unexpected outlines: {', '.join(unexpected)}")
        raise ValueError("; ".join(problems))

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths: list[Path] = []
    for source_path in sources:
        payload = json.loads(outlines[source_path.stem].read_text(encoding="utf-8"))
        document = CatalogOutlineDocument.from_json(payload)
        output_path = output_dir / f"{source_path.stem}-flat.png"
        render_flat_illustration(source_path, document, output_path)
        rendered_paths.append(output_path)

    _render_contact_sheet(tuple(rendered_paths), contact_sheet_path)
    return tuple(rendered_paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hangboard-catalog-flat")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--outline-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    args = parser.parse_args(argv)

    outputs = render_flat_catalog(
        args.source_dir, args.outline_dir, args.output_dir, args.contact_sheet
    )
    print(f"Rendered {len(outputs)} flat illustration(s)")
    return 0


def _catalog_sources(source_dir: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in source_dir.glob("*.png")
            if path.is_file()
            and path.name not in _CONTACT_SHEET_SKIP_NAMES
            and not path.name.endswith("-flat.png")
        )
    )


def _detect_board_components(rgb: np.ndarray) -> np.ndarray:
    border = np.concatenate(
        (rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]),
        axis=0,
    )
    border_float = border.astype(np.float32)
    background = np.median(border_float, axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32) - background, axis=2)
    border_distance = np.linalg.norm(border_float - background, axis=1)
    threshold = _border_noise_threshold(border_distance)
    candidate = np.where(distance >= threshold, 255, 0).astype(np.uint8)
    if not np.any(candidate):
        grayscale = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        candidate = cv2.adaptiveThreshold(
            grayscale,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            6,
        )

    kernel = np.ones((5, 5), dtype=np.uint8)
    cleaned = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
    if count <= 1:
        raise ValueError("board mask could not be determined")
    largest = int(stats[1:, cv2.CC_STAT_AREA].max())
    minimum_area = max(int(math.ceil(largest * 0.05)), 64)
    mask = np.zeros(cleaned.shape, dtype=bool)
    for label in range(1, count):
        if int(stats[label, cv2.CC_STAT_AREA]) >= minimum_area:
            mask |= labels == label
    if not np.any(mask):
        raise ValueError("board mask could not be determined")

    normalized = np.where(mask, 255, 0).astype(np.uint8)
    normalized = cv2.morphologyEx(normalized, cv2.MORPH_CLOSE, kernel, iterations=1)
    return normalized > 0


def _border_noise_threshold(border_distance: np.ndarray) -> float:
    median = float(np.median(border_distance))
    mad_sigma = float(np.median(np.abs(border_distance - median))) * 1.4826
    std_sigma = float(border_distance.std())
    noise_sigma = max(mad_sigma, std_sigma, 0.5)
    return max(6.0, median + 10.0 * noise_sigma)


def _merge_outline_support(
    board_mask: np.ndarray, outline_masks: tuple[np.ndarray, ...]
) -> np.ndarray:
    supported = board_mask.copy()
    for outline_mask in outline_masks:
        supported |= outline_mask
    supported = cv2.morphologyEx(
        np.where(supported, 255, 0).astype(np.uint8),
        cv2.MORPH_CLOSE,
        np.ones((3, 3), dtype=np.uint8),
        iterations=1,
    )
    return supported > 0


def _mask_boundary(mask: np.ndarray) -> np.ndarray:
    raster = np.where(mask, 255, 0).astype(np.uint8)
    eroded = cv2.erode(raster, np.ones((3, 3), dtype=np.uint8), iterations=1)
    return (raster > 0) & ~(eroded > 0)


def _outline_mask(path: OutlinePath, width: int, height: int) -> np.ndarray:
    display_path = _display_path_for_outline(path, width, height)
    contour = flatten_display_path(display_path)
    raster = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(raster, [np.rint(contour).astype(np.int32)], 1)
    return raster.astype(bool)


def _display_path_for_outline(path: OutlinePath, width: int, height: int) -> DisplayPath:
    tokens: list[str] = []
    commands: list[str] = []
    coordinates: list[tuple[float, float]] = []
    for command in path.commands:
        commands.append(command.command)
        tokens.append(command.command)
        if command.controls is not None:
            for control in command.controls:
                pixel = (control[0] * width, control[1] * height)
                coordinates.append(pixel)
                tokens.extend(_point_tokens(pixel))
        pixel_to = (command.to[0] * width, command.to[1] * height)
        coordinates.append(pixel_to)
        tokens.extend(_point_tokens(pixel_to))
    commands.append("Z")
    tokens.append("Z")
    return DisplayPath(
        " ".join(tokens),
        tuple(commands),
        tuple(coordinates),
    )


def _point_tokens(point: tuple[float, float]) -> tuple[str, str]:
    return (f"{point[0]:.12g}", f"{point[1]:.12g}")


def _render_contact_sheet(image_paths: tuple[Path, ...], contact_sheet_path: Path) -> None:
    font = ImageFont.load_default()
    rows = math.ceil(len(image_paths) / _CONTACT_COLUMNS)
    cell_width = _CONTACT_TILE_WIDTH + _CONTACT_PADDING * 2
    cell_height = (
        _CONTACT_TILE_HEIGHT
        + _CONTACT_PADDING * 2
        + _CONTACT_LABEL_GAP
        + _CONTACT_LABEL_HEIGHT
    )
    sheet = Image.new(
        "RGB",
        (_CONTACT_COLUMNS * cell_width, rows * cell_height),
        PARCHMENT_COLOR,
    )
    draw = ImageDraw.Draw(sheet)

    for index, image_path in enumerate(image_paths):
        row, column = divmod(index, _CONTACT_COLUMNS)
        origin_x = column * cell_width
        origin_y = row * cell_height
        with Image.open(image_path) as image:
            tile = image.convert("RGB")
            tile.thumbnail(
                (_CONTACT_TILE_WIDTH, _CONTACT_TILE_HEIGHT),
                Image.Resampling.LANCZOS,
            )
            image_x = origin_x + _CONTACT_PADDING + (_CONTACT_TILE_WIDTH - tile.width) // 2
            image_y = origin_y + _CONTACT_PADDING + (_CONTACT_TILE_HEIGHT - tile.height) // 2
            sheet.paste(tile, (image_x, image_y))

        label = image_path.stem.removesuffix("-flat")
        bbox = draw.textbbox((0, 0), label, font=font)
        label_width = bbox[2] - bbox[0]
        label_x = origin_x + (cell_width - label_width) // 2
        label_y = origin_y + _CONTACT_PADDING + _CONTACT_TILE_HEIGHT + _CONTACT_LABEL_GAP
        draw.text((label_x, label_y), label, fill=CONTOUR_COLOR, font=font)

    contact_sheet_path.parent.mkdir(parents=True, exist_ok=True)
    _save_rgb_png(np.array(sheet, dtype=np.uint8), contact_sheet_path)


def _save_rgb_png(rgb: np.ndarray, output_path: Path) -> None:
    Image.fromarray(rgb, mode="RGB").save(
        output_path,
        format="PNG",
        optimize=False,
        compress_level=9,
    )


if __name__ == "__main__":
    raise SystemExit(main())
