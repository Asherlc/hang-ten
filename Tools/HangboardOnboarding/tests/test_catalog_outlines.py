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


def test_outline_models_canonicalize_nested_inputs_for_direct_and_json_construction() -> None:
    endpoint = [0.1, 0.2]
    controls = [[0.2, 0.3], [0.3, 0.4]]
    commands = [OutlineCommand("C", endpoint, controls=controls)]
    bounds = [0.1, 0.1, 0.8, 0.8]
    notes = ["editable"]
    references = [
        {
            "title": "Manufacturer photo",
            "url": "https://example.com/board",
            "hints": ["front-lit"],
        }
    ]
    outlines = [
        HoldOutline(
            id="hold-01",
            label="Main edge",
            kind="edge",
            confidence=0.91,
            bounds=bounds,
            path=OutlinePath(commands=commands, closed=True),
            notes=notes,
        )
    ]
    document = CatalogOutlineDocument(
        schema_version=1,
        source_image="board.png",
        canvas_width=100,
        canvas_height=100,
        coordinate_space="normalized",
        references=references,
        outlines=outlines,
    )

    endpoint[0] = 0.9
    controls[0][0] = 0.9
    commands.clear()
    bounds[0] = 0.9
    notes.append("changed")
    references[0]["title"] = "Changed"
    references[0]["hints"].append("changed")
    outlines.clear()
    restored = CatalogOutlineDocument.from_json(document.to_json())

    assert document.outlines[0].path.commands[0].to == (0.1, 0.2)
    assert document.outlines[0].path.commands[0].controls == ((0.2, 0.3), (0.3, 0.4))
    assert document.outlines[0].bounds == (0.1, 0.1, 0.8, 0.8)
    assert document.outlines[0].notes == ("editable",)
    assert document.references[0]["title"] == "Manufacturer photo"
    assert document.references[0]["hints"] == ("front-lit",)
    assert restored.references[0]["hints"] == ("front-lit",)
    with pytest.raises(TypeError):
        document.references[0]["title"] = "Changed"


def test_validator_rejects_coordinates_outside_normalized_canvas() -> None:
    document = replace_first_coordinate(sample_document(), 1.01, 0.4)

    with pytest.raises(ValueError, match="normalized"):
        validate_catalog_document(document)


@pytest.mark.parametrize(
    "bounds",
    [
        (0.1, 0.1, 0.91, 0.8),
        (0.1, 0.1, 0.9, 0.91),
    ],
    ids=["horizontal", "vertical"],
)
def test_validator_rejects_bounds_that_overflow_normalized_canvas(
    bounds: tuple[float, float, float, float],
) -> None:
    sample = sample_document()
    document = replace(sample, outlines=(replace(sample.outlines[0], bounds=bounds),))

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


def test_cli_stores_output_relative_source_image_and_check_resolves_it(tmp_path: Path) -> None:
    cli = importlib.import_module("hangboard_vectorizer.catalog_outline_cli")
    runner = cli.CliRunner()
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "artifacts" / "outlines"
    write_synthetic_board(source_dir / "board.png")

    result = runner.invoke(
        cli.main,
        ["--source-dir", str(source_dir), "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0
    output_path = output_dir / "board.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["sourceImage"] == "../../source/board.png"
    assert runner.invoke(
        cli.main,
        ["--source-dir", str(source_dir), "--output-dir", str(output_dir), "--check"],
    ).exit_code == 0

    payload["sourceImage"] = "../source/board.png"
    output_path.write_text(json.dumps(payload), encoding="utf-8")

    assert runner.invoke(
        cli.main,
        ["--source-dir", str(source_dir), "--output-dir", str(output_dir), "--check"],
    ).exit_code != 0


def test_overlay_samples_cubic_segments_instead_of_using_their_endpoint_chord() -> None:
    outlines_module = importlib.import_module("hangboard_vectorizer.catalog_outlines")
    path = OutlinePath(
        commands=(
            OutlineCommand("M", (0.1, 0.1)),
            OutlineCommand("C", (0.9, 0.1), controls=((0.3, 0.9), (0.7, 0.9))),
            OutlineCommand("L", (0.9, 0.2)),
            OutlineCommand("L", (0.1, 0.1)),
        ),
        closed=True,
    )

    pixels = outlines_module._outline_path_to_pixels(path, 100, 100)

    assert pixels[:, 1].max() > 60


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
