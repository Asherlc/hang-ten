from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
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
