from __future__ import annotations

from typing import Any

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


def board_positions_document(document: dict[str, Any]) -> dict[str, Any]:
    """Add front and inverted-front positions to a single-presentation fixture."""
    document["presentations"].append(
        {
            "id": "front-inverted",
            "name": "Front inverted",
            "assetPath": "assets/front-inverted.png",
            "aspectRatio": 2,
            "default": False,
            "sourcePresentationID": "primary",
            "isInverted": True,
        }
    )
    document["positions"] = [
        {"id": "front", "presentationID": "primary"},
        {"id": "flipped", "presentationID": "front-inverted"},
    ]
    document["positionTransitions"] = [
        {
            "fromPositionID": "front",
            "toPositionID": "flipped",
            "kind": "seamless",
        }
    ]
    return document
