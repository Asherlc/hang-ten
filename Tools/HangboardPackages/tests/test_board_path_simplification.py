from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest
from conftest import PRIMARY_PNG_BYTES, board_document
from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hangboard_packages.cli import main  # noqa: E402
from hangboard_packages.board_path_simplification import (  # noqa: E402
    simplify_package_hold_paths,
)


def _write_package(
    root: Path,
    holds: list[dict[str, object]],
    *,
    native_size: tuple[int, int] = (40, 20),
) -> Path:
    (root / "assets").mkdir(parents=True)
    if native_size == (40, 20):
        (root / "assets" / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    else:
        Image.new("RGB", native_size, "white").save(root / "assets" / "primary.png")
    document = board_document()
    document["aspectRatio"] = native_size[0] / native_size[1]
    document["holds"] = holds
    (root / "board.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return root


def _path(points: list[tuple[float, float]]) -> dict[str, object]:
    return {
        "type": "path",
        "commands": [
            {"command": "move", "to": list(points[0])},
            *({"command": "line", "to": list(point)} for point in points[1:]),
            {"command": "close"},
        ],
    }


def _rounded_rect_path(
    radius: float,
    *,
    native_width: float = 40,
    native_height: float = 20,
) -> dict[str, object]:
    """Return the literal path rendered by the schema roundedRect primitive."""
    corner = min(native_width, native_height) * radius
    horizontal = corner / native_width
    vertical = corner / native_height
    commands: list[dict[str, object]] = [
        {"command": "move", "to": [horizontal, 0]},
    ]
    if horizontal < 0.5:
        commands.append({"command": "line", "to": [1 - horizontal, 0]})
    commands.append(
        {"command": "quad", "control": [1, 0], "to": [1, vertical]}
    )
    if vertical < 0.5:
        commands.append({"command": "line", "to": [1, 1 - vertical]})
    commands.append(
        {"command": "quad", "control": [1, 1], "to": [1 - horizontal, 1]}
    )
    if horizontal < 0.5:
        commands.append({"command": "line", "to": [horizontal, 1]})
    commands.append(
        {"command": "quad", "control": [0, 1], "to": [0, 1 - vertical]}
    )
    if vertical < 0.5:
        commands.append({"command": "line", "to": [0, vertical]})
    commands.extend(
        (
            {"command": "quad", "control": [0, 0], "to": [horizontal, 0]},
            {"command": "close"},
        )
    )
    return {"type": "path", "commands": commands}


def _sampled_rounded_rect_path(radius: float) -> dict[str, object]:
    """Approximate a square rounded rect without including tangent anchors."""
    corners = (
        ((1 - radius, 0), (1, 0), (1, radius)),
        ((1, 1 - radius), (1, 1), (1 - radius, 1)),
        ((radius, 1), (0, 1), (0, 1 - radius)),
        ((0, radius), (0, 0), (radius, 0)),
    )
    points: list[tuple[float, float]] = []
    for start, control, end in corners:
        for t in (0.025, 0.25, 0.5, 0.75, 0.975):
            point = (
                (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0],
                (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1],
            )
            corner_x = 0 if point[0] < 0.5 else 1
            corner_y = 0 if point[1] < 0.5 else 1
            points.append(
                (
                    corner_x + (point[0] - corner_x) * 0.95,
                    corner_y + (point[1] - corner_y) * 0.95,
                )
            )
    minimum_x = min(point[0] for point in points)
    maximum_x = max(point[0] for point in points)
    minimum_y = min(point[1] for point in points)
    maximum_y = max(point[1] for point in points)
    return _path(
        [
            (
                (x - minimum_x) / (maximum_x - minimum_x),
                (y - minimum_y) / (maximum_y - minimum_y),
            )
            for x, y in points
        ]
    )


def _piece(
    shape: dict[str, object],
    *,
    frame: dict[str, float] | None = None,
) -> dict[str, object]:
    return {
        "frame": frame or {"x": 0, "y": 0, "width": 1, "height": 1},
        "shape": shape,
    }


def _hold(identifier: str, *shapes: dict[str, object]) -> dict[str, object]:
    return {
        "id": identifier,
        "name": identifier,
        "kind": "jug",
        "geometry": [_piece(shape) for shape in shapes],
    }


def _editable_points(shape: dict[str, object]) -> int:
    return sum(
        int("to" in command) + int("control" in command) + int("control1" in command) + int("control2" in command)
        for command in shape["commands"]
    )


def _independent_measurements(
    before: list[tuple[float, float]],
    after: list[tuple[float, float]],
    *,
    frame: dict[str, float] | None = None,
    width: int = 40,
    height: int = 20,
) -> tuple[float, float]:
    """Independently measure frame-projected polygon boundaries in native pixels."""
    frame = frame or {"x": 0, "y": 0, "width": 1, "height": 1}

    def project(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [
            ((frame["x"] + x * frame["width"]) * width, (frame["y"] + y * frame["height"]) * height)
            for x, y in points
        ]

    before, after = project(before), project(after)

    def mask(points: list[tuple[float, float]]) -> Image.Image:
        image = Image.new("1", (width * 4, height * 4), 0)
        ImageDraw.Draw(image).polygon(
            [(round(x * 4), round(y * 4)) for x, y in points],
            fill=1,
        )
        return image

    before_mask, after_mask = mask(before), mask(after)
    difference = ImageChops.logical_xor(before_mask, after_mask)
    ratio = difference.histogram()[255] / (width * 4 * height * 4)
    def distance_to_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
        dx, dy = end[0] - start[0], end[1] - start[1]
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            return math.dist(point, start)
        fraction = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared))
        return math.dist(point, (start[0] + dx * fraction, start[1] + dy * fraction))

    def directed(source: list[tuple[float, float]], target: list[tuple[float, float]]) -> float:
        target_segments = list(zip(target, target[1:] + target[:1]))
        maximum = 0.0
        for start, end in zip(source, source[1:] + source[:1]):
            steps = max(1, math.ceil(math.dist(start, end) * 4_096))
            for step in range(steps + 1):
                fraction = step / steps
                point = (start[0] + (end[0] - start[0]) * fraction, start[1] + (end[1] - start[1]) * fraction)
                maximum = max(maximum, min(distance_to_segment(point, *segment) for segment in target_segments))
        return maximum

    maximum = max(directed(before, after), directed(after, before))
    return maximum, ratio


def test_simplifies_duplicate_and_collinear_line_anchors_without_raster_error(tmp_path: Path) -> None:
    # Removing duplicate anchors or a collinear point must reduce editable points.
    source = [(0, 0), (0.5, 0), (1, 0), (1, 0), (1, 1), (0.5, 1), (0, 1), (0, 0)]
    package = _write_package(tmp_path / "board", [_hold("line-hold", _path(source))])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points) == (8, 4)
    assert (change.maximum_boundary_deviation_pixels, change.symmetric_difference_ratio) == (0.0, 0.0)
    assert change.changed is True
    assert _independent_measurements(source, [(0, 0), (1, 0), (1, 1), (0, 1)]) == (0.0, 0.0)


def test_rejects_line_candidate_that_exceeds_one_native_pixel(tmp_path: Path) -> None:
    # Removing the inward corner changes the boundary by six native pixels.
    source = [(0, 0), (1, 0), (1, 1), (0.5, 0.7), (0, 1)]
    package = _write_package(tmp_path / "board", [_hold("notch", _path(source))])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points, change.changed) == (5, 5, False)
    assert change.eligible_candidates >= 1
    assert change.evaluated_candidates >= 1
    assert change.rejected_candidates >= 1
    maximum, ratio = _independent_measurements(source, [(0, 0), (1, 0), (1, 1), (0, 1)])
    assert maximum > 1.0
    assert ratio > 0.0025


def test_accepts_subpixel_line_candidate_within_the_global_error_limits(tmp_path: Path) -> None:
    source = [(0, 0), (0.5, 0.004), (1, 0), (1, 1), (0, 1)]
    package = _write_package(tmp_path / "board", [_hold("nearly-straight", _path(source))])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points, change.changed) == (5, 0, True)
    maximum, ratio = _independent_measurements(source, [(0, 0), (1, 0), (1, 1), (0, 1)])
    assert math.isclose(maximum, 0.08, abs_tol=0.0001)
    assert maximum < 1.0
    assert ratio <= 0.0025
    assert change.maximum_boundary_deviation_pixels <= 1.0
    assert change.symmetric_difference_ratio <= 0.0025


def test_rejects_candidate_when_exact_reverse_boundary_distance_exceeds_one_pixel(tmp_path: Path) -> None:
    # The old 0.25 px sampler reported 0.99825 px; dense bidirectional measurement is > 1 px.
    global_points = [
        (24.446249049378977, 10.000878848533924),
        (22.34452858238905, 10.529251661114513),
        (22.745586716420352, 11.700391576864027),
        (20.00897006704638, 11.281684405421895),
        (18.824286298348305, 8.670208535604958),
    ]
    minimum_x = min(x for x, _ in global_points)
    maximum_x = max(x for x, _ in global_points)
    minimum_y = min(y for _, y in global_points)
    maximum_y = max(y for _, y in global_points)
    frame = {
        "x": minimum_x / 40,
        "y": minimum_y / 20,
        "width": (maximum_x - minimum_x) / 40,
        "height": (maximum_y - minimum_y) / 20,
    }
    source = [
        ((x - minimum_x) / (maximum_x - minimum_x), (y - minimum_y) / (maximum_y - minimum_y))
        for x, y in global_points
    ]
    shape = _path(source)
    package = _write_package(tmp_path / "board", [{"id": "near-limit", "name": "near-limit", "kind": "jug", "geometry": [_piece(shape, frame=frame)]}])

    result = simplify_package_hold_paths(package, write=False)

    maximum, ratio = _independent_measurements(source, source[:1] + source[2:], frame=frame)
    assert maximum > 1.0
    assert ratio <= 0.0025
    assert result.pieces[0].changed is False


def test_fails_closed_and_reports_when_exact_measurement_exceeds_the_complexity_cap(tmp_path: Path, capsys) -> None:
    source = [
        (0.5 + 0.5 * math.cos(2 * math.pi * index / 16), 0.5 + 0.5 * math.sin(2 * math.pi * index / 16))
        for index in range(16)
    ]
    package = _write_package(tmp_path / "board", [_hold("many-anchors", _path(source))])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points, change.changed) == (16, 16, False)
    assert change.complexity_capped is True
    assert main(["simplify-hold-paths", "--root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["boards"][0]["skippedPieces"] == [{
        "afterEditablePoints": 16,
        "beforeEditablePoints": 16,
        "holdId": "many-anchors",
        "pieceIndex": 0,
        "reason": "exactHausdorffComplexityCap",
    }]


def test_preserves_curve_when_its_polygon_approximation_is_not_cheaper(tmp_path: Path) -> None:
    curve = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0, 0]},
            {"command": "curve", "control1": [0.2, 0.1], "control2": [0.8, 0.1], "to": [1, 0]},
            {"command": "curve", "control1": [0.9, 0.2], "control2": [0.9, 0.8], "to": [1, 1]},
            {"command": "curve", "control1": [0.8, 0.9], "control2": [0.2, 0.9], "to": [0, 1]},
            {"command": "curve", "control1": [0.1, 0.8], "control2": [0.1, 0.2], "to": [0, 0]},
            {"command": "close"},
        ],
    }
    package = _write_package(tmp_path / "board", [_hold("curve", curve)])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points, change.changed) == (13, 13, False)


def test_simplifies_exact_redundancies_in_a_mixed_curve_and_line_contour(tmp_path: Path) -> None:
    mixed = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0, 0]},
            {"command": "curve", "control1": [0.1, 0], "control2": [0.2, 0.125], "to": [0.3, 0.25]},
            {"command": "line", "to": [0.714285714286, 0.25]},
            {"command": "line", "to": [1, 0.25]},
            {"command": "line", "to": [1, 1]},
            {"command": "line", "to": [0.285714285714, 1]},
            {"command": "quad", "control": [0.142857142857, 1], "to": [0, 1]},
            {"command": "line", "to": [0, 0]},
            {"command": "close"},
        ],
    }
    package = _write_package(tmp_path / "board", [_hold("mixed", mixed)])

    result = simplify_package_hold_paths(package, write=True)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points, change.changed) == (11, 8, True)
    assert (change.eligible_candidates, change.evaluated_candidates, change.rejected_candidates) == (3, 3, 0)
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    commands = document["holds"][0]["geometry"][0]["shape"]["commands"]
    assert commands[1]["command"] == "curve"
    assert all(command["command"] != "quad" for command in commands)


def test_evaluates_curve_immediately_before_close(tmp_path: Path) -> None:
    mixed = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0, 0]},
            {"command": "line", "to": [1, 0]},
            {"command": "line", "to": [1, 1]},
            {"command": "line", "to": [0, 1]},
            {"command": "curve", "control1": [0, 0.75], "control2": [0, 0.25], "to": [0, 0]},
            {"command": "close"},
        ],
    }
    package = _write_package(tmp_path / "board", [_hold("final-curve", mixed)])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert change.changed is True
    assert change.after_editable_points == 0


def test_reports_interior_move_as_unsupported_without_modifying_the_path(tmp_path: Path) -> None:
    invalid_mixed = {
        "type": "path",
        "commands": [
            {"command": "move", "to": [0, 0]},
            {"command": "line", "to": [1, 0]},
            {"command": "move", "to": [1, 1]},
            {"command": "line", "to": [0, 1]},
            {"command": "close"},
        ],
    }
    package = _write_package(tmp_path / "board", [_hold("interior-move", invalid_mixed)])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.changed, change.unsupported_pieces, change.eligible_candidates) == (False, 1, 0)


def test_handles_multiple_and_mirrored_pieces_but_leaves_rounded_rectangles(tmp_path: Path) -> None:
    left = _path([(0, 0), (0.5, 0), (1, 0), (1, 1), (0.5, 1), (0, 1)])
    right = _path([(1, 0), (0.5, 0), (0, 0), (0, 1), (0.5, 1), (1, 1)])
    rounded = {"type": "roundedRect", "cornerRadiusFraction": 0.2}
    package = _write_package(tmp_path / "board", [_hold("paired", left, right), _hold("round", rounded)])

    result = simplify_package_hold_paths(package, write=False)

    assert [(piece.hold_id, piece.piece_index, piece.before_editable_points, piece.after_editable_points, piece.changed) for piece in result.pieces] == [
        ("paired", 0, 6, 0, True),
        ("paired", 1, 6, 0, True),
        ("round", 0, 0, 0, False),
    ]


@pytest.mark.parametrize("radius", (0.0, 0.2, 0.5))
def test_reduces_exact_rectangles_rounded_corners_and_capsules_to_primitives(
    tmp_path: Path, radius: float
) -> None:
    source = _path([(0, 0), (1, 0), (1, 1), (0, 1)]) if radius == 0 else _rounded_rect_path(radius)
    package = _write_package(tmp_path / "board", [_hold("primitive", source)])

    result = simplify_package_hold_paths(package, write=True)

    change = result.pieces[0]
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert document["holds"][0]["geometry"][0]["shape"] == {
        "type": "roundedRect",
        "cornerRadiusFraction": radius,
    }
    assert change.after_editable_points == 0
    assert change.after_editable_points < change.before_editable_points
    assert change.maximum_boundary_deviation_pixels == 0
    assert change.symmetric_difference_ratio == 0


def test_chooses_the_same_best_radius_deterministically(tmp_path: Path) -> None:
    package = _write_package(
        tmp_path / "board", [_hold("rounded", _rounded_rect_path(0.2))]
    )

    first = simplify_package_hold_paths(package, write=False)
    second = simplify_package_hold_paths(package, write=False)

    assert first == second
    simplify_package_hold_paths(package, write=True)
    shape = json.loads((package / "board.json").read_text(encoding="utf-8"))[
        "holds"
    ][0]["geometry"][0]["shape"]
    assert shape == {"type": "roundedRect", "cornerRadiusFraction": 0.2}


def test_rejects_an_irregular_near_miss_instead_of_erasing_its_shape(tmp_path: Path) -> None:
    source = _rounded_rect_path(0.2)
    source["commands"][2]["to"] = [1, 0.45]
    package = _write_package(tmp_path / "board", [_hold("near-miss", source)])

    result = simplify_package_hold_paths(package, write=True)

    assert result.pieces[0].after_editable_points > 0
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert document["holds"][0]["geometry"][0]["shape"]["type"] == "path"


def test_rejects_a_primitive_whose_reverse_native_boundary_error_exceeds_one_pixel(
    tmp_path: Path,
) -> None:
    source = _rounded_rect_path(0.2)
    source["commands"].insert(2, {"command": "line", "to": [0.94, 0.08]})
    package = _write_package(tmp_path / "board", [_hold("native-gate", source)])

    result = simplify_package_hold_paths(package, write=True)

    assert result.pieces[0].after_editable_points > 0
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert document["holds"][0]["geometry"][0]["shape"]["type"] == "path"


def test_rejects_primitive_when_exact_boundary_is_1_1_pixels_despite_raster_quantization(
    tmp_path: Path,
) -> None:
    # The narrow 1.1 px notch occupies <0.25% of the image, while the 4x
    # distance transform quantizes its boundary deviation down to 1.0 px.
    source = [
        (0, 0),
        (1, 0),
        (1, 1),
        (0.54, 1),
        (0.5, 0.945),
        (0.46, 1),
        (0, 1),
    ]
    package = _write_package(tmp_path / "board", [_hold("exact-gate", _path(source))])

    result = simplify_package_hold_paths(package, write=True)

    maximum, ratio = _independent_measurements(
        source,
        [(0, 0), (1, 0), (1, 1), (0, 1)],
    )
    assert math.isclose(maximum, 1.1, abs_tol=0.0001)
    assert ratio <= 0.0025
    assert result.pieces[0].after_editable_points > 0
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert document["holds"][0]["geometry"][0]["shape"]["type"] == "path"


def test_finds_radius_point_25_on_complete_canvas_derived_grid(
    tmp_path: Path,
) -> None:
    package = _write_package(
        tmp_path / "board",
        [_hold("quarter-radius", _sampled_rounded_rect_path(0.25))],
        native_size=(100, 100),
    )

    result = simplify_package_hold_paths(package, write=True)

    assert result.pieces[0].after_editable_points == 0
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert document["holds"][0]["geometry"][0]["shape"] == {
        "type": "roundedRect",
        "cornerRadiusFraction": 0.25,
    }


def test_primitive_conversion_preserves_frame_treatment_order_and_non_shape_fields(
    tmp_path: Path,
) -> None:
    frame = {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.4}
    piece = _piece(_rounded_rect_path(0.25, native_width=20, native_height=8), frame=frame)
    piece["treatment"] = {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    hold = _hold("metadata", _path([(0, 0), (1, 0), (1, 1), (0, 1)]))
    hold.update(
        {
            "name": "Metadata hold",
            "kind": "edge",
            "sizeMillimeters": 20,
            "features": ["incutEdge"],
        }
    )
    hold["geometry"] = [piece, _piece(_path([(0, 0), (1, 0), (0.5, 1)]))]
    package = _write_package(tmp_path / "board", [hold])
    before = json.loads((package / "board.json").read_text(encoding="utf-8"))

    simplify_package_hold_paths(package, write=True)

    after = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert [value for key, value in before["holds"][0].items() if key != "geometry"] == [
        value for key, value in after["holds"][0].items() if key != "geometry"
    ]
    assert after["holds"][0]["geometry"][0]["frame"] == frame
    assert after["holds"][0]["geometry"][0]["treatment"] == piece["treatment"]
    assert after["holds"][0]["geometry"][1] == before["holds"][0]["geometry"][1]
    assert len(after["holds"][0]["geometry"]) == 2


def test_primitive_write_changes_only_the_shape_bytes(tmp_path: Path) -> None:
    package = tmp_path / "board"
    (package / "assets").mkdir(parents=True)
    (package / "assets" / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    source_shape = _rounded_rect_path(0.2)
    document = board_document()
    document["subtitle"] = 'A literal "shape": marker is ordinary metadata.'
    document["holds"] = [_hold("compact", source_shape)]
    before = json.dumps(document, separators=(",", ":")) + "\n"
    (package / "board.json").write_text(before, encoding="utf-8")
    replacement = json.dumps(
        {"type": "roundedRect", "cornerRadiusFraction": 0.2},
        separators=(",", ":"),
    )
    expected = before.replace(
        json.dumps(source_shape, separators=(",", ":")), replacement
    )

    simplify_package_hold_paths(package, write=True)

    assert (package / "board.json").read_text(encoding="utf-8") == expected


def test_primitive_write_failure_leaves_the_package_unchanged_and_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hangboard_packages import board_path_simplification

    package = _write_package(
        tmp_path / "board", [_hold("rounded", _rounded_rect_path(0.2))]
    )
    before = (package / "board.json").read_bytes()

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated atomic replacement failure")

    monkeypatch.setattr(board_path_simplification.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic replacement failure"):
        simplify_package_hold_paths(package, write=True)

    assert (package / "board.json").read_bytes() == before
    assert list(package.glob(".board.json.*.tmp")) == []


def test_dry_run_is_immutable_write_is_atomic_and_second_run_is_idempotent(tmp_path: Path) -> None:
    package = _write_package(
        tmp_path / "root" / "board",
        [_hold("line", _path([(0, 0), (0.5, 0), (1, 0), (1, 1), (0.5, 1), (0, 1)]))],
    )
    before = (package / "board.json").read_bytes()

    dry_run = simplify_package_hold_paths(package, write=False)
    assert dry_run.changed is True
    assert (package / "board.json").read_bytes() == before

    written = simplify_package_hold_paths(package, write=True)
    assert written.changed is True
    document = json.loads((package / "board.json").read_text(encoding="utf-8"))
    assert document["holds"][0]["geometry"][0]["shape"] == {
        "type": "roundedRect",
        "cornerRadiusFraction": 0.0,
    }
    assert simplify_package_hold_paths(package, write=True).changed is False


def test_rejects_invalid_self_intersecting_candidate_and_cli_reports_drafts(tmp_path: Path, capsys) -> None:
    # A bow-tie must never be rewritten, even if it contains removable-looking anchors.
    package = _write_package(
        tmp_path / "root" / "board",
        [_hold("bow-tie", _path([(0, 0), (1, 1), (0.5, 0.5), (0, 1), (1, 0)]))],
    )
    draft_assets = tmp_path / "root" / "draft" / "assets"
    draft_assets.mkdir(parents=True)
    (draft_assets / "primary.png").write_bytes(PRIMARY_PNG_BYTES)

    assert simplify_package_hold_paths(package, write=False).changed is False
    assert main(["simplify-hold-paths", "--root", str(tmp_path / "root")]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["draftCount"] == 1
    assert payload["boards"][0]["id"] == "fixture.board"
    assert payload["boards"][0]["pieces"] == []
