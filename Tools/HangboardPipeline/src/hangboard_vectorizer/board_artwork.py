"""Compatibility dataclasses for canonical board artwork geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


def _float(value: Any, *, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not _finite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} must be at most {maximum}")
    return value


def _finite(value: float) -> bool:
    try:
        return value == value and abs(value) != float("inf")
    except TypeError:
        return False


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _closed(payload: Mapping[str, Any], label: str, required: set[str], *, optional: set[str] | None = None) -> None:
    required = set(required)
    unknown = set(payload) - required
    if optional is not None:
        unknown -= optional
        required -= optional
    if unknown:
        raise ValueError(f"{label} has unknown keys: {sorted(unknown)}")
    missing = required - set(payload)
    if missing:
        raise ValueError(f"{label} is missing keys: {sorted(missing)}")


@dataclass(frozen=True)
class NormalizedFrame:
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_json(cls, value: Any, label: str = "frame") -> "NormalizedFrame":
        payload = _mapping(value, label)
        _closed(payload, label, required={"x", "y", "width", "height"})
        x = _float(payload["x"], label=f"{label}.x", minimum=0)
        y = _float(payload["y"], label=f"{label}.y", minimum=0)
        width = _float(payload["width"], label=f"{label}.width", minimum=0)
        height = _float(payload["height"], label=f"{label}.height", minimum=0)
        if width <= 0 or height <= 0:
            raise ValueError(f"{label}.width and {label}.height must be positive")
        if x + width > 1 or y + height > 1:
            raise ValueError(f"{label} must be inside the normalized canvas")
        return cls(x, y, width, height)


@dataclass(frozen=True)
class PathCommand:
    command: str
    to: tuple[float, float] | None = None
    control: tuple[float, float] | None = None
    control1: tuple[float, float] | None = None
    control2: tuple[float, float] | None = None

    @staticmethod
    def _point(value: Any, label: str, *, constrain: bool = True) -> tuple[float, float]:
        if not isinstance(value, Sequence) or isinstance(value, str):
            raise ValueError(f"{label} must be a point")
        if len(value) != 2:
            raise ValueError(f"{label} must contain exactly two numbers")
        minimum = 0 if constrain else None
        maximum = 1 if constrain else None
        return (
            _float(value[0], label=f"{label}[0]", minimum=minimum, maximum=maximum),
            _float(value[1], label=f"{label}[1]", minimum=minimum, maximum=maximum),
        )

    @classmethod
    def from_json(cls, value: Any, label: str) -> "PathCommand":
        payload = _mapping(value, label)
        command = _string(payload.get("command"), label=f"{label}.command")
        if command == "move":
            _closed(payload, label, required={"command", "to"})
            to = cls._point(payload["to"], f"{label}.to")
            return cls(command="move", to=to)
        if command == "line":
            _closed(payload, label, required={"command", "to"})
            to = cls._point(payload["to"], f"{label}.to")
            return cls(command="line", to=to)
        if command == "quad":
            _closed(payload, label, required={"command", "control", "to"})
            control = cls._point(payload["control"], f"{label}.control", constrain=False)
            to = cls._point(payload["to"], f"{label}.to")
            return cls(command="quad", control=control, to=to)
        if command == "curve":
            _closed(payload, label, required={"command", "control1", "control2", "to"})
            control1 = cls._point(payload["control1"], f"{label}.control1", constrain=False)
            control2 = cls._point(payload["control2"], f"{label}.control2", constrain=False)
            to = cls._point(payload["to"], f"{label}.to")
            return cls(command="curve", control1=control1, control2=control2, to=to)
        if command == "close":
            _closed(payload, label, required={"command"})
            return cls(command="close")
        raise ValueError(f"{label}.command is unsupported")


@dataclass(frozen=True)
class BoardShapeDocument:
    type: str
    corner_radius_fraction: float | None = None
    commands: tuple[PathCommand, ...] = ()

    @classmethod
    def from_json(cls, value: Any, source: str) -> "BoardShapeDocument":
        payload = _mapping(value, source)
        shape_type = _string(payload.get("type"), label=f"{source}.type")
        if shape_type == "roundedRect":
            _closed(payload, source, required={"type", "cornerRadiusFraction"})
            corner_radius_fraction = _float(
                payload["cornerRadiusFraction"],
                label=f"{source}.cornerRadiusFraction",
                minimum=0,
                maximum=0.5,
            )
            return cls(type="roundedRect", corner_radius_fraction=corner_radius_fraction)
        if shape_type == "path":
            _closed(payload, source, required={"type", "commands"})
            raw_commands = payload["commands"]
            if not isinstance(raw_commands, list):
                raise ValueError(f"{source}.commands must be an array")
            commands = tuple(
                PathCommand.from_json(item, f"{source}.commands[{index}]")
                for index, item in enumerate(raw_commands)
            )
            if not commands:
                raise ValueError(f"{source}.commands must be a non-empty array")
            if commands[0].command != "move":
                raise ValueError(f"{source}.commands must start with move")
            if commands[-1].command != "close":
                raise ValueError(f"{source}.commands must end with close")
            return cls(type="path", commands=commands)
        raise ValueError(f"{source}.type must be roundedRect or path")
