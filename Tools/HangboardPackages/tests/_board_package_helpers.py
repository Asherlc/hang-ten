from __future__ import annotations

from hangboard_packages.board_catalog import NormalizedFrame


def presentation_frame(
    frame: NormalizedFrame, size: tuple[int, int]
) -> tuple[float, float, float, float]:
    width, height = size
    return (
        frame.x * width,
        frame.y * height,
        frame.width * width,
        frame.height * height,
    )


def serialize_geometry(hold: object) -> tuple[dict[str, object], ...]:
    return tuple(serialize_piece(piece) for piece in hold.geometry)


def serialize_piece(piece: object) -> dict[str, object]:
    return {
        "frame": {
            "x": piece.frame.x,
            "y": piece.frame.y,
            "width": piece.frame.width,
            "height": piece.frame.height,
        },
        "commands": tuple(serialize_command(command) for command in piece.shape.commands),
    }


def serialize_command(command: object) -> dict[str, object]:
    serialized: dict[str, object] = {"command": command.command}
    for key in ("to", "control", "control1", "control2"):
        value = getattr(command, key)
        if value is not None:
            serialized[key] = tuple(value)
    return serialized
