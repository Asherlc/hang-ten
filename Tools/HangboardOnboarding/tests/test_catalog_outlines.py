from __future__ import annotations

from dataclasses import replace
import importlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import pytest

from hangboard_vectorizer.catalog_outlines import (
    CatalogOutlineDocument,
    HoldOutline,
    OutlineCommand,
    OutlinePath,
    normalize_contour,
    path_bounds,
    detect_hold_candidates,
    validate_catalog_document,
    write_catalog_document,
)


def write_synthetic_board(path: Path) -> Path:
    image = Image.new("RGBA", (240, 180), (246, 246, 246, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 20, 220, 160), radius=18, fill=(154, 112, 72, 255))
    draw.rounded_rectangle((50, 50, 105, 80), radius=10, fill=(110, 78, 48, 255))
    draw.rounded_rectangle((130, 92, 195, 125), radius=12, fill=(96, 70, 44, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def synthetic_low_contrast_white_rail_board() -> tuple[np.ndarray, np.ndarray]:
    height, width = 180, 320
    image = np.full((height, width, 4), (250, 250, 250, 255), dtype=np.uint8)
    board_mask = np.zeros((height, width), dtype=np.uint8)
    board_mask[24:156, 24:296] = 255
    image[board_mask > 0, :3] = (246, 246, 246)
    for y in (68, 94, 120):
        image[y : y + 9, 32:288, :3] = (242, 242, 242)
    return image, board_mask


def sample_document() -> CatalogOutlineDocument:
    return CatalogOutlineDocument(
        schema_version=1,
        source_image="board.png",
        canvas_width=100,
        canvas_height=100,
        coordinate_space="normalized",
        references=(
            {
                "title": "Manufacturer photo",
                "url": "https://example.com/board",
                "hints": ("front-lit", "square-on"),
            },
        ),
        outlines=(
            HoldOutline(
                id="hold-01",
                label="Main edge",
                kind="edge",
                confidence=0.91,
                bounds=(0.1, 0.1, 0.9, 0.8),
                path=OutlinePath(
                    commands=(
                        OutlineCommand("M", (0.1, 0.1)),
                        OutlineCommand("L", (0.9, 0.1)),
                        OutlineCommand(
                            "C",
                            (0.9, 0.9),
                            controls=((1.0, 0.3), (1.0, 0.7)),
                        ),
                        OutlineCommand("L", (0.1, 0.1)),
                    ),
                    closed=True,
                ),
                notes=("traced from catalog silhouette",),
            ),
        ),
    )


def replace_first_coordinate(
    document: CatalogOutlineDocument, x: float, y: float
) -> CatalogOutlineDocument:
    hold = document.outlines[0]
    command = hold.path.commands[0]
    commands = (replace(command, to=(x, y)), *hold.path.commands[1:])
    return replace(
        document,
        outlines=(replace(hold, path=replace(hold.path, commands=commands)),),
    )


def with_commands(
    document: CatalogOutlineDocument, commands: tuple[OutlineCommand, ...]
) -> CatalogOutlineDocument:
    hold = document.outlines[0]
    return replace(
        document,
        outlines=(replace(hold, path=replace(hold.path, commands=commands)),),
    )


def test_round_trip_preserves_explicit_commands_and_bounds() -> None:
    document = sample_document()

    restored = CatalogOutlineDocument.from_json(document.to_json())

    assert restored == document
    validate_catalog_document(restored)
    assert restored.to_json() == {
        "schemaVersion": 1,
        "sourceImage": "board.png",
        "canvas": {"width": 100, "height": 100},
        "coordinateSpace": "normalized",
        "references": [
            {
                "title": "Manufacturer photo",
                "url": "https://example.com/board",
                "hints": ["front-lit", "square-on"],
            }
        ],
        "outlines": [
            {
                "id": "hold-01",
                "label": "Main edge",
                "kind": "edge",
                "confidence": 0.91,
                "bounds": [0.1, 0.1, 0.9, 0.8],
                "path": {
                    "closed": True,
                    "commands": [
                        {"command": "M", "to": [0.1, 0.1]},
                        {"command": "L", "to": [0.9, 0.1]},
                        {
                            "command": "C",
                            "controls": [[1.0, 0.3], [1.0, 0.7]],
                            "to": [0.9, 0.9],
                        },
                        {"command": "L", "to": [0.1, 0.1]},
                    ],
                },
                "notes": ["traced from catalog silhouette"],
            }
        ],
    }
    assert path_bounds(restored.outlines[0].path) == pytest.approx((0.1, 0.1, 0.9, 0.8))


def test_validator_rejects_coordinates_outside_normalized_canvas() -> None:
    document = replace_first_coordinate(sample_document(), 1.01, 0.4)

    with pytest.raises(ValueError, match="normalized"):
        validate_catalog_document(document)


def test_validator_rejects_open_or_degenerate_path() -> None:
    document = with_commands(sample_document(), (OutlineCommand("M", (0.1, 0.1)),))

    with pytest.raises(ValueError, match="closed"):
        validate_catalog_document(document)


def test_normalize_contour_emits_lines_and_curves_in_range() -> None:
    contour = np.array(
        [[10, 10], [90, 10], [100, 50], [90, 90], [10, 90]],
        dtype=float,
    )

    path = normalize_contour(contour, 100, 100)

    assert path.closed
    assert {command.command for command in path.commands} <= {"M", "L", "C"}
    assert any(command.command == "C" for command in path.commands)
    assert all(0.0 <= value <= 1.0 for value in path.all_coordinates())


def test_normalize_contour_keeps_persistent_corner_as_line_endpoint() -> None:
    contour = np.array(
        [
            [10, 10],
            [45, 10],
            [50, 12],
            [55, 10],
            [90, 10],
            [95, 50],
            [90, 90],
            [10, 90],
        ],
        dtype=float,
    )

    path = normalize_contour(contour, 100, 100)

    line_endpoints = {command.to for command in path.commands if command.command == "L"}
    assert (0.9, 0.1) in line_endpoints
    assert any(command.command == "C" for command in path.commands)


def test_write_catalog_document_is_stable_and_atomic(tmp_path: Path) -> None:
    output_path = tmp_path / "catalog-outlines.json"
    document = sample_document()

    write_catalog_document(document, output_path)

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted == document.to_json()
    assert not list(tmp_path.glob("*.tmp"))


def test_detector_returns_stable_candidates_for_synthetic_board(tmp_path: Path) -> None:
    source = write_synthetic_board(tmp_path / "synthetic.png")
    vectorize = getattr(
        importlib.import_module("hangboard_vectorizer.catalog_outlines"),
        "vectorize_catalog_image",
        None,
    )
    if vectorize is None:
        pytest.fail("vectorize_catalog_image is missing")

    first = vectorize(source)
    second = vectorize(source)

    assert first.to_json() == second.to_json()
    assert len(first.outlines) >= 2
    assert all(outline.confidence == "approximate" for outline in first.outlines)


def test_detector_falls_back_to_low_contrast_horizontal_rail_bands() -> None:
    image, board_mask = synthetic_low_contrast_white_rail_board()

    candidates = detect_hold_candidates(image, board_mask)

    assert len(candidates) == 3
    assert all(kind in {"rail", "edge"} for _, kind, _ in candidates)
    starts = [int(np.min(contour[:, 1])) for contour, _, _ in candidates]
    assert all(abs(actual - expected) <= 2 for actual, expected in zip(starts, (68, 94, 120)))
    assert all(np.ptp(contour[:, 0]) >= 240 for contour, _, _ in candidates)


def test_cli_check_rejects_missing_or_malformed_catalog_output(tmp_path: Path) -> None:
    try:
        cli = importlib.import_module("hangboard_vectorizer.catalog_outline_cli")
    except ModuleNotFoundError:
        pytest.fail("catalog_outline_cli module is missing")
    runner = cli.CliRunner()

    result = runner.invoke(
        cli.main,
        ["--source-dir", str(tmp_path), "--output-dir", str(tmp_path / "out"), "--check"],
    )

    assert result.exit_code != 0


def test_cli_excludes_contact_sheet_and_writes_review_overlay(tmp_path: Path) -> None:
    try:
        cli = importlib.import_module("hangboard_vectorizer.catalog_outline_cli")
    except ModuleNotFoundError:
        pytest.fail("catalog_outline_cli module is missing")
    runner = cli.CliRunner()
    write_synthetic_board(tmp_path / "board.png")
    write_synthetic_board(tmp_path / "contact-sheet-primary.png")

    result = runner.invoke(
        cli.main,
        [
            "--source-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--review-dir",
            str(tmp_path / "review"),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "out" / "board.json").exists()
    assert not (tmp_path / "out" / "contact-sheet-primary.json").exists()
    assert (tmp_path / "review" / "board.png").exists()


def test_review_overlay_labels_with_outline_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = write_synthetic_board(tmp_path / "board.png")
    outlines_module = importlib.import_module("hangboard_vectorizer.catalog_outlines")
    document = outlines_module.vectorize_catalog_image(source)
    document = replace(
        document,
        outlines=tuple(
            replace(outline, id=f"catalog-outline-{index}")
            for index, outline in enumerate(document.outlines, start=1)
        ),
    )

    labels: list[str] = []
    original_put_text = outlines_module.cv2.putText

    def capture_put_text(image: np.ndarray, text: str, *args: object) -> np.ndarray:
        labels.append(text)
        return original_put_text(image, text, *args)

    monkeypatch.setattr(outlines_module.cv2, "putText", capture_put_text)
    outlines_module.render_catalog_review_overlay(
        source, document, tmp_path / "review" / "board.png"
    )

    assert labels == [outline.id for outline in document.outlines for _ in range(2)]
