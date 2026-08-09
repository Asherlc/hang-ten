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
        source_width=100,
        source_height=100,
        holds=(
            HoldOutline(
                hold_id="hold-01",
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
            ),
        ),
    )


def replace_first_coordinate(
    document: CatalogOutlineDocument, x: float, y: float
) -> CatalogOutlineDocument:
    hold = document.holds[0]
    command = hold.path.commands[0]
    commands = (replace(command, to=(x, y)), *hold.path.commands[1:])
    return replace(
        document,
        holds=(replace(hold, path=replace(hold.path, commands=commands)),),
    )


def with_commands(
    document: CatalogOutlineDocument, commands: tuple[OutlineCommand, ...]
) -> CatalogOutlineDocument:
    hold = document.holds[0]
    return replace(
        document,
        holds=(replace(hold, path=replace(hold.path, commands=commands)),),
    )


def test_round_trip_preserves_explicit_commands_and_bounds() -> None:
    document = sample_document()

    restored = CatalogOutlineDocument.from_json(document.to_json())

    assert restored == document
    validate_catalog_document(restored)
    assert path_bounds(restored.holds[0].path) == pytest.approx((0.1, 0.1, 0.9, 0.8))


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


def test_write_catalog_document_is_stable_and_atomic(tmp_path: Path) -> None:
    output_path = tmp_path / "catalog-outlines.json"
    document = sample_document()

    write_catalog_document(document, output_path)

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted == document.to_json()
    assert not list(tmp_path.glob("*.tmp"))

