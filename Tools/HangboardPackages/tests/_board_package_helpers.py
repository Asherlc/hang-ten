from __future__ import annotations

import copy
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


def document_hold_geometry(document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return canonical raster geometry keyed by logical hold ID."""
    result: dict[str, list[dict[str, Any]]] = {}
    for presentation in document["presentations"]:
        if presentation["derivation"]["type"] != "original":
            continue
        for hold_id, geometry in presentation["media"]["holdGeometry"].items():
            if hold_id in result:
                raise AssertionError(f"duplicate original geometry for {hold_id}")
            result[hold_id] = geometry
    return result


def board_hold_geometry(board: object) -> dict[str, tuple[object, ...]]:
    """Return parsed canonical raster geometry keyed by logical hold ID."""
    result: dict[str, tuple[object, ...]] = {}
    for presentation in board.presentations:
        if presentation.source_presentation_id is not None:
            continue
        media = presentation.media
        if not hasattr(media, "hold_geometry"):
            continue
        for hold_id, geometry in media.hold_geometry.items():
            if hold_id in result:
                raise AssertionError(f"duplicate original geometry for {hold_id}")
            result[hold_id] = geometry
    return result


def serialize_geometry(geometry: tuple[object, ...]) -> tuple[dict[str, object], ...]:
    return tuple(serialize_piece(piece) for piece in geometry)


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
            "aspectRatio": 2,
            "isDefault": False,
            "derivation": {
                "type": "derived",
                "sourcePresentationID": "primary",
                "isInverted": True,
            },
            "media": {
                "type": "raster",
                "assetPath": "assets/front-inverted.png",
                "holdGeometry": copy.deepcopy(
                    document["presentations"][0]["media"]["holdGeometry"]
                ),
            },
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
