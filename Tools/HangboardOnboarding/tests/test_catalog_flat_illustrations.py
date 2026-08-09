from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import tarfile

import numpy as np
from PIL import Image
import pytest

from hangboard_vectorizer.catalog_flat_illustrations import (
    BOARD_COLOR,
    CAVITY_COLOR,
    CONTOUR_COLOR,
    PARCHMENT_COLOR,
    render_flat_catalog,
    render_flat_illustration,
)
from hangboard_vectorizer.catalog_outlines import (
    CatalogOutlineDocument,
    HoldOutline,
    OutlineCommand,
    OutlinePath,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "docs" / "hangboard-generative-catalog"
OUTLINE_TREE = "docs/hangboard-generative-catalog/outlines"


def _write_source(path: Path, *, split: bool) -> None:
    image = Image.new("RGB", (200, 80), (246, 246, 244))
    pixels = image.load()
    if split:
        spans = ((20, 80), (120, 180))
    else:
        spans = ((20, 180),)
    for left, right in spans:
        for x in range(left, right):
            for y in range(20, 60):
                pixels[x, y] = (34, 34, 34)
    image.save(path, format="PNG")


def _document(source_name: str, *, hold_left: float, hold_right: float) -> CatalogOutlineDocument:
    return CatalogOutlineDocument(
        schema_version=1,
        source_image=f"../{source_name}",
        canvas_width=200,
        canvas_height=80,
        coordinate_space="normalized",
        references=({"title": "Fixture", "url": "https://example.com", "hints": ()},),
        outlines=(
            HoldOutline(
                id="hold-1",
                label="Hold 1",
                kind="edge",
                confidence=1.0,
                bounds=(hold_left, 0.375, hold_right - hold_left, 0.25),
                path=OutlinePath(
                    commands=(
                        OutlineCommand("M", (hold_left, 0.375)),
                        OutlineCommand("L", (hold_right, 0.375)),
                        OutlineCommand("L", (hold_right, 0.625)),
                        OutlineCommand("L", (hold_left, 0.625)),
                        OutlineCommand("L", (hold_left, 0.375)),
                    ),
                    closed=True,
                ),
                notes="Synthetic hold",
            ),
        ),
    )


def _extract_head_outlines(destination: Path) -> Path:
    archive = subprocess.check_output(
        ["git", "archive", "--format=tar", "HEAD", OUTLINE_TREE],
        cwd=REPO_ROOT,
    )
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        tar.extractall(destination, filter="data")
    return destination / OUTLINE_TREE


def _load_document(path: Path) -> CatalogOutlineDocument:
    return CatalogOutlineDocument.from_json(json.loads(path.read_text(encoding="utf-8")))


def _outline_mask(path: OutlinePath, width: int, height: int) -> np.ndarray:
    from hangboard_vectorizer.catalog_flat_illustrations import _outline_mask as render_outline_mask

    return render_outline_mask(path, width, height)


def test_render_flat_illustration_preserves_split_board_gap_and_canvas_size(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "split-board.png"
    output_path = tmp_path / "split-board-flat.png"
    _write_source(source_path, split=True)
    document = _document(source_path.name, hold_left=0.20, hold_right=0.25)

    render_flat_illustration(source_path, document, output_path)

    with Image.open(output_path) as rendered_image:
        assert rendered_image.size == (200, 80)
        rendered = np.array(rendered_image.convert("RGB"))

    assert tuple(rendered[40, 35]) == BOARD_COLOR
    assert tuple(rendered[40, 165]) == BOARD_COLOR
    assert tuple(rendered[40, 100]) == PARCHMENT_COLOR
    assert tuple(rendered[40, 45]) == CAVITY_COLOR


def test_render_flat_illustration_uses_one_pixel_inner_contour(tmp_path: Path) -> None:
    source_path = tmp_path / "solid-board.png"
    output_path = tmp_path / "solid-board-flat.png"
    _write_source(source_path, split=False)
    document = _document(source_path.name, hold_left=0.30, hold_right=0.35)

    render_flat_illustration(source_path, document, output_path)

    rendered = np.array(Image.open(output_path).convert("RGB"))

    assert tuple(rendered[19, 40]) == PARCHMENT_COLOR
    assert tuple(rendered[20, 40]) == CONTOUR_COLOR
    assert tuple(rendered[21, 40]) == BOARD_COLOR
    assert tuple(rendered[40, 19]) == PARCHMENT_COLOR
    assert tuple(rendered[40, 20]) == CONTOUR_COLOR
    assert tuple(rendered[40, 21]) == BOARD_COLOR


def test_render_flat_catalog_is_byte_identical_across_runs_and_uses_flat_names(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    outline_dir = tmp_path / "outlines"
    output_dir = tmp_path / "flat-illustrations"
    source_dir.mkdir()
    outline_dir.mkdir()

    alpha_source = source_dir / "alpha-board.png"
    beta_source = source_dir / "beta-board.png"
    _write_source(alpha_source, split=True)
    _write_source(beta_source, split=False)

    alpha_document = _document(alpha_source.name, hold_left=0.20, hold_right=0.25)
    beta_document = _document(beta_source.name, hold_left=0.60, hold_right=0.66)

    (outline_dir / "alpha-board.json").write_text(
        json.dumps(alpha_document.to_json(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (outline_dir / "beta-board.json").write_text(
        json.dumps(beta_document.to_json(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    first_contact_sheet = tmp_path / "contact-sheet-first.png"
    outputs = render_flat_catalog(source_dir, outline_dir, output_dir, first_contact_sheet)
    first_bytes = {path.name: path.read_bytes() for path in outputs}
    first_contact_bytes = first_contact_sheet.read_bytes()

    second_contact_sheet = tmp_path / "contact-sheet-second.png"
    repeated_outputs = render_flat_catalog(
        source_dir, outline_dir, output_dir, second_contact_sheet
    )
    second_bytes = {path.name: path.read_bytes() for path in repeated_outputs}
    second_contact_bytes = second_contact_sheet.read_bytes()

    assert tuple(path.name for path in outputs) == (
        "alpha-board-flat.png",
        "beta-board-flat.png",
    )
    assert tuple(path.name for path in repeated_outputs) == (
        "alpha-board-flat.png",
        "beta-board-flat.png",
    )
    assert second_bytes == first_bytes
    assert second_contact_bytes == first_contact_bytes


@pytest.mark.parametrize(
    ("stem", "x", "y"),
    (
        ("beastmaker-2000", 1605, 225),
        ("beastmaker-2000", 165, 406),
        ("dewoodstok-woodbord", 72, 447),
        ("dewoodstok-woodbord", 231, 609),
    ),
)
def test_render_flat_illustration_preserves_representative_low_contrast_board_planes(
    tmp_path: Path, stem: str, x: int, y: int
) -> None:
    outline_dir = _extract_head_outlines(tmp_path)
    source_path = SOURCE_DIR / f"{stem}.png"
    document = _load_document(outline_dir / f"{stem}.json")
    output_path = tmp_path / f"{stem}-flat.png"

    render_flat_illustration(source_path, document, output_path)

    rendered = np.array(Image.open(output_path).convert("RGB"))
    assert tuple(rendered[y, x]) == BOARD_COLOR


def test_render_flat_catalog_gives_every_committed_outline_visible_cavity_pixels(
    tmp_path: Path,
) -> None:
    outline_dir = _extract_head_outlines(tmp_path / "snapshot")
    output_dir = tmp_path / "flat-illustrations"
    contact_sheet_path = tmp_path / "flat-illustrations-contact-sheet.png"

    outputs = render_flat_catalog(SOURCE_DIR, outline_dir, output_dir, contact_sheet_path)
    rendered_by_stem = {
        path.stem.removesuffix("-flat"): np.array(Image.open(path).convert("RGB"))
        for path in outputs
    }

    missing: list[tuple[str, str]] = []
    for outline_path in sorted(outline_dir.glob("*.json")):
        document = _load_document(outline_path)
        rendered = rendered_by_stem[outline_path.stem]
        for outline in document.outlines:
            mask = _outline_mask(outline.path, document.canvas_width, document.canvas_height)
            cavity_pixels = np.all(rendered == np.array(CAVITY_COLOR), axis=2) & mask
            if not np.any(cavity_pixels):
                missing.append((outline_path.name, outline.id))

    assert missing == []
