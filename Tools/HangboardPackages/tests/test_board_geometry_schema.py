from __future__ import annotations

import pytest

from hangboard_packages.board_geometry_schema import BoardShapeDocument, NormalizedFrame, PathCommand


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


def test_normalized_frame_allows_manual_off_canvas_bounds() -> None:
    frame = NormalizedFrame.from_json(
        {"x": -0.003741228478, "y": -0.004892401544, "width": 0.165800496, "height": 0.243309389961},
        "frame",
    )

    assert frame == NormalizedFrame(
        x=-0.003741228478,
        y=-0.004892401544,
        width=0.165800496,
        height=0.243309389961,
    )


def _curve(control1: tuple[float, float], control2: tuple[float, float], x: float, y: float) -> dict:
    return {"command": "curve", "control1": list(control1), "control2": list(control2), "to": [x, y]}


def test_path_command_allows_a_control_point_outside_the_normalized_canvas() -> None:
    command = PathCommand.from_json(_curve((1.5, -0.5), (0.5, 0.5), 1, 1), "commands[0]")
    assert command.control1 == (1.5, -0.5)


def test_path_command_rejects_a_control_point_too_large_to_quantize_safely() -> None:
    # A control point only needs to be finite, but the app quantizes
    # flattened contour coordinates into an Int64 by scaling by 1e12, which
    # traps outside Int64's range. Reject an oversized-but-finite control
    # here instead of accepting a board.json that would crash the app later.
    with pytest.raises(ValueError, match="must be at most|must be at least"):
        PathCommand.from_json(_curve((2_000_000, 0.5), (0.5, 0.5), 1, 1), "commands[0]")


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
