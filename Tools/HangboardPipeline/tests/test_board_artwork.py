from __future__ import annotations

import pytest

from hangboard_vectorizer.board_artwork import BoardShapeDocument, PathCommand


def _move(x: float, y: float) -> dict:
    return {"command": "move", "to": [x, y]}


def _line(x: float, y: float) -> dict:
    return {"command": "line", "to": [x, y]}


def _close() -> dict:
    return {"command": "close"}


def test_path_command_rejects_coordinates_outside_the_normalized_canvas() -> None:
    with pytest.raises(ValueError, match=r"must be at most 1|must be at least 0"):
        PathCommand.from_json(_line(1.5, 0.5), "commands[0]")
    with pytest.raises(ValueError, match=r"must be at most 1|must be at least 0"):
        PathCommand.from_json(_line(0.5, -0.1), "commands[0]")


def test_shape_document_requires_a_path_to_start_with_move() -> None:
    with pytest.raises(ValueError, match="must start with move"):
        BoardShapeDocument.from_json(
            {"type": "path", "commands": [_line(0.1, 0.1), _close()]},
            "shape",
        )


def test_shape_document_requires_a_path_to_end_with_close() -> None:
    with pytest.raises(ValueError, match="must end with close"):
        BoardShapeDocument.from_json(
            {"type": "path", "commands": [_move(0.1, 0.1), _line(0.2, 0.2)]},
            "shape",
        )


def test_shape_document_requires_a_non_empty_command_list() -> None:
    with pytest.raises(ValueError, match="non-empty array"):
        BoardShapeDocument.from_json({"type": "path", "commands": []}, "shape")


def test_shape_document_accepts_a_valid_path() -> None:
    shape = BoardShapeDocument.from_json(
        {
            "type": "path",
            "commands": [_move(0.1, 0.1), _line(0.2, 0.2), _close()],
        },
        "shape",
    )
    assert shape.type == "path"
    assert [command.command for command in shape.commands] == ["move", "line", "close"]
