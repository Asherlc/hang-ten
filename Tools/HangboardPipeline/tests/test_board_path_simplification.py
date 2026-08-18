from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from conftest import PRIMARY_PNG_BYTES, board_document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hangboard_vectorizer.board_path_simplification import (  # noqa: E402
    simplify_package_hold_paths,
)
from hangboard_vectorizer.board_catalog_cli import main  # noqa: E402


def _write_package(root: Path, holds: list[dict[str, object]]) -> Path:
    (root / "assets").mkdir(parents=True)
    (root / "assets" / "primary.png").write_bytes(PRIMARY_PNG_BYTES)
    document = board_document()
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
    maximum, ratio = _independent_measurements(source, [(0, 0), (1, 0), (1, 1), (0, 1)])
    assert maximum > 1.0
    assert ratio > 0.0025


def test_accepts_subpixel_line_candidate_within_the_global_error_limits(tmp_path: Path) -> None:
    source = [(0, 0), (0.5, 0.004), (1, 0), (1, 1), (0, 1)]
    package = _write_package(tmp_path / "board", [_hold("nearly-straight", _path(source))])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points, change.changed) == (5, 4, True)
    maximum, ratio = _independent_measurements(source, [(0, 0), (1, 0), (1, 1), (0, 1)])
    assert math.isclose(maximum, 0.08, abs_tol=0.0001)
    assert maximum < 1.0
    assert ratio <= 0.0025
    assert math.isclose(change.maximum_boundary_deviation_pixels, 0.08, abs_tol=0.0001)
    assert math.isclose(change.symmetric_difference_ratio, ratio, abs_tol=0.0)


def test_rejects_candidate_when_exact_reverse_boundary_distance_exceeds_one_pixel(tmp_path: Path) -> None:
    # The old 0.25 px sampler reported 0.99825 px; dense bidirectional measurement is > 1 px.
    global_points = [
        (24.446249049378977, 10.000878848533924),
        (22.34452858238905, 10.529251661114513),
        (22.745586716420352, 11.700391576864027),
        (20.00897006704638, 11.281684405421895),
        (18.824286298348305, 8.670208535604958),
    ]
    frame = {"x": 0.4, "y": 0.3, "width": 0.25, "height": 0.4}
    source = [((x / 40 - frame["x"]) / frame["width"], (y / 20 - frame["y"]) / frame["height"]) for x, y in global_points]
    shape = _path(source)
    package = _write_package(tmp_path / "board", [{"id": "near-limit", "name": "near-limit", "kind": "jug", "geometry": [_piece(shape, frame=frame)]}])

    result = simplify_package_hold_paths(package, write=False)

    maximum, ratio = _independent_measurements(source, source[:1] + source[2:], frame=frame)
    assert maximum > 1.0
    assert ratio <= 0.0025
    assert result.pieces[0].changed is False


def test_fails_closed_and_reports_when_exact_measurement_exceeds_the_complexity_cap(tmp_path: Path, capsys) -> None:
    source = [
        (0.5 + 0.4 * math.cos(2 * math.pi * index / 16), 0.5 + 0.4 * math.sin(2 * math.pi * index / 16))
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
            {"command": "curve", "control1": [0.2, 0], "control2": [0.8, 0], "to": [1, 0]},
            {"command": "curve", "control1": [1, 0.2], "control2": [1, 0.8], "to": [1, 1]},
            {"command": "curve", "control1": [0.8, 1], "control2": [0.2, 1], "to": [0, 1]},
            {"command": "curve", "control1": [0, 0.8], "control2": [0, 0.2], "to": [0, 0]},
            {"command": "close"},
        ],
    }
    package = _write_package(tmp_path / "board", [_hold("curve", curve)])

    result = simplify_package_hold_paths(package, write=False)

    change = result.pieces[0]
    assert (change.before_editable_points, change.after_editable_points, change.changed) == (13, 13, False)


def test_handles_multiple_and_mirrored_pieces_but_leaves_rounded_rectangles(tmp_path: Path) -> None:
    left = _path([(0, 0), (0.5, 0), (1, 0), (1, 1), (0.5, 1), (0, 1)])
    right = _path([(1, 0), (0.5, 0), (0, 0), (0, 1), (0.5, 1), (1, 1)])
    rounded = {"type": "roundedRect", "cornerRadiusFraction": 0.2}
    package = _write_package(tmp_path / "board", [_hold("paired", left, right), _hold("round", rounded)])

    result = simplify_package_hold_paths(package, write=False)

    assert [(piece.hold_id, piece.piece_index, piece.before_editable_points, piece.after_editable_points, piece.changed) for piece in result.pieces] == [
        ("paired", 0, 6, 4, True),
        ("paired", 1, 6, 4, True),
        ("round", 0, 0, 0, False),
    ]


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
    assert _editable_points(document["holds"][0]["geometry"][0]["shape"]) == 4
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
