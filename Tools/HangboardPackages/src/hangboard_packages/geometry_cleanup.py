#!/usr/bin/env python3
"""Programmatic hold geometry cleanup: detect regular shapes, apply constraints, smooth paths."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

# Add parent directories to path using repository root relative to this file
REPO_ROOT = Path(__file__).resolve().parents[4]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
PACKAGES_ROOT = REPO_ROOT / "Tools" / "HangboardPackages" / "src"
sys.path.insert(0, str(WORKBENCH_ROOT))
sys.path.insert(0, str(PACKAGES_ROOT))

from board_geometry import (
    ClosedPath,
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    flattened_shape_bounds,
    normalized_frame_for_path,
    parse_closed_path,
    shape_for_path,
    union_normalized_frames,
)
from board_geometry_schema import BoardShapeDocument, NormalizedFrame as SchemaNormalizedFrame


@dataclass
class ShapeMatch:
    constraint_type: str  # "roundedRect", "circle", "oval", "pill", "rectangle"
    confidence: float
    corner_radius_fraction: float | None = None
    rotation_degrees: float = 0.0


def analyze_path_for_shape_constraint(path: ClosedPath, frame: NormalizedFrame) -> ShapeMatch | None:
    """Analyze a flattened path to detect if it matches a regular shape constraint."""
    contour = path.contour
    if len(contour) < 4:
        return None

    # Get bounds in frame-local [0,1] space
    min_x = min(p[0] for p in contour)
    max_x = max(p[0] for p in contour)
    min_y = min(p[1] for p in contour)
    max_y = max(p[1] for p in contour)

    width = max_x - min_x
    height = max_y - min_y
    if width <= 0 or height <= 0:
        return None

    aspect = width / height

    def point_in_rounded_rect(px: float, py: float, rx: float, ry: float, r: float) -> bool:
        dx = abs(px - (rx + width / 2))
        dy = abs(py - (ry + height / 2))
        if dx > width / 2 - r and dy > height / 2 - r:
            corner_dx = dx - (width / 2 - r)
            corner_dy = dy - (height / 2 - r)
            return corner_dx * corner_dx + corner_dy * corner_dy <= r * r
        return dx <= width / 2 and dy <= height / 2

    # Test roundedRect: find best corner radius using boundary fidelity
    def _rounded_rect_boundary_score(r_frac: float) -> float:
        r = min(width, height) * r_frac
        if r <= 0:
            return 0.0
        band = 0.02 * min(width, height)
        on_boundary = 0
        for p in contour:
            inside = point_in_rounded_rect(p[0], p[1], min_x, min_y, r)
            if not inside:
                continue
            # Check if point is near the boundary (not deep inside)
            dx = max(abs(p[0] - (min_x + max_x) / 2) - width / 2, 0)
            dy = max(abs(p[1] - (min_y + max_y) / 2) - height / 2, 0)
            dist_to_edge = math.hypot(dx, dy)
            if r > 0:
                # For rounded corners, also check distance to corner arc
                corner_cx = min_x + r if p[0] < (min_x + max_x) / 2 else max_x - r
                corner_cy = min_y + r if p[1] < (min_y + max_y) / 2 else max_y - r
                corner_dx = abs(p[0] - corner_cx)
                corner_dy = abs(p[1] - corner_cy)
                if corner_dx > (width / 2 - r) and corner_dy > (height / 2 - r):
                    dist_to_edge = abs(math.hypot(corner_dx, corner_dy) - r)
            if dist_to_edge <= band:
                on_boundary += 1
        return on_boundary / len(contour)

    best_rounded_rect_score = 0.0
    best_radius = 0.0
    for r_frac in [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
        score = _rounded_rect_boundary_score(r_frac)
        if score > best_rounded_rect_score:
            best_rounded_rect_score = score
            best_radius = r_frac

    # Test circle (aspect ~1, radius fits)
    circle_score = 0.0
    if 0.9 < aspect < 1.1:
        cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
        r = min(width, height) / 2
        inside = sum(1 for p in contour if (p[0] - cx) ** 2 + (p[1] - cy) ** 2 <= r * r * 1.01)
        circle_score = inside / len(contour)

    # Test pill (capsule): one dimension much larger, ends are semicircles
    pill_score = 0.0
    pill_vertical = False
    if aspect > 2.0:  # horizontal pill
        r = height / 2
        cx1, cx2 = min_x + r, max_x - r
        cy = (min_y + max_y) / 2
        inside = 0
        for p in contour:
            if p[0] <= cx1:
                inside += (p[0] - cx1) ** 2 + (p[1] - cy) ** 2 <= r * r * 1.01
            elif p[0] >= cx2:
                inside += (p[0] - cx2) ** 2 + (p[1] - cy) ** 2 <= r * r * 1.01
            else:
                inside += abs(p[1] - cy) <= r * 1.01
        pill_score = inside / len(contour)
    elif aspect < 0.5:  # vertical pill
        pill_vertical = True
        r = width / 2
        cy1, cy2 = min_y + r, max_y - r
        cx = (min_x + max_x) / 2
        inside = 0
        for p in contour:
            if p[1] <= cy1:
                inside += (p[0] - cx) ** 2 + (p[1] - cy1) ** 2 <= r * r * 1.01
            elif p[1] >= cy2:
                inside += (p[0] - cx) ** 2 + (p[1] - cy2) ** 2 <= r * r * 1.01
            else:
                inside += abs(p[0] - cx) <= r * 1.01
        pill_score = inside / len(contour)

    # Test oval (ellipse)
    oval_score = 0.0
    if 0.3 < aspect < 3.0 and aspect != 1.0:
        cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
        rx, ry = width / 2, height / 2
        inside = sum(1 for p in contour if ((p[0] - cx) / rx) ** 2 + ((p[1] - cy) / ry) ** 2 <= 1.01)
        oval_score = inside / len(contour)

    # Test rectangle (sharp corners) - check if corners are actually sharp
    rect_score = 0.0
    corner_tolerance = 0.01 * min(width, height)
    edge_slack = 0.005 * min(width, height)
    corner_points = [
        (min_x, min_y),  # top-left
        (max_x, min_y),  # top-right
        (min_x, max_y),  # bottom-left
        (max_x, max_y),  # bottom-right
    ]
    # Check if contour actually goes into corners (sharp) or curves away (rounded)
    sharp_corners = 0
    for cx, cy in corner_points:
        # Find closest contour point to this corner
        closest_dist = min(math.hypot(p[0] - cx, p[1] - cy) for p in contour)
        if closest_dist < corner_tolerance:  # Very close to corner = sharp
            sharp_corners += 1
    if sharp_corners >= 3:  # At least 3 sharp corners
        inside = sum(
            1
            for p in contour
            if min_x - edge_slack <= p[0] <= max_x + edge_slack
            and min_y - edge_slack <= p[1] <= max_y + edge_slack
        )
        rect_score = inside / len(contour)

    # Pick best match with threshold
    matches = [
        ("roundedRect", best_rounded_rect_score, best_radius),
        ("circle", circle_score, None),
        ("pill", pill_score, None),
        ("oval", oval_score, None),
        ("rectangle", rect_score, None),
    ]
    matches.sort(key=lambda m: m[1], reverse=True)

    if matches[0][1] < 0.85:  # Need good fit
        return None

    constraint_type, confidence, radius_frac = matches[0]
    rotation = 0.0
    if constraint_type == "pill" and pill_vertical:
        rotation = 90.0

    return ShapeMatch(
        constraint_type=constraint_type,
        confidence=confidence,
        corner_radius_fraction=radius_frac,
        rotation_degrees=rotation,
    )


def normalize_path_to_frame(commands: list[dict[str, Any]], tolerance: float = 5e-7) -> list[dict[str, Any]]:
    """Rescale path commands so the path fills the [0,1]x[0,1] local frame."""
    if not commands:
        return commands

    # Collect all points from the path
    xs: list[float] = []
    ys: list[float] = []
    current = None

    for cmd in commands:
        if cmd["command"] in ("move", "line"):
            current = cmd["to"]
            xs.append(current[0])
            ys.append(current[1])
        elif cmd["command"] == "quad":
            control = cmd["control"]
            end = cmd["to"]
            # Sample the curve
            for step in range(1, 33):
                t = step / 32
                inverse = 1 - t
                xs.append(inverse * inverse * current[0] + 2 * inverse * t * control[0] + t * t * end[0])
                ys.append(inverse * inverse * current[1] + 2 * inverse * t * control[1] + t * t * end[1])
            current = end
        elif cmd["command"] == "curve":
            control1 = cmd["control1"]
            control2 = cmd["control2"]
            end = cmd["to"]
            for step in range(1, 33):
                t = step / 32
                inverse = 1 - t
                xs.append(
                    inverse ** 3 * current[0]
                    + 3 * inverse * inverse * t * control1[0]
                    + 3 * inverse * t * t * control2[0]
                    + t ** 3 * end[0]
                )
                ys.append(
                    inverse ** 3 * current[1]
                    + 3 * inverse * inverse * t * control1[1]
                    + 3 * inverse * t * t * control2[1]
                    + t ** 3 * end[1]
                )
            current = end

    if not xs or not ys:
        return commands

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Check if already fills frame
    if (min_x <= tolerance and min_y <= tolerance and
        max_x >= 1 - tolerance and max_y >= 1 - tolerance):
        return commands

    # Compute scale and translation
    width = max_x - min_x
    height = max_y - min_y
    if width <= 0 or height <= 0:
        return commands

    scale_x = 1.0 / width
    scale_y = 1.0 / height
    translate_x = -min_x * scale_x
    translate_y = -min_y * scale_y

    # Apply transformation to all commands
    normalized = []
    for cmd in commands:
        new_cmd = dict(cmd)
        if "to" in cmd:
            new_cmd["to"] = [
                cmd["to"][0] * scale_x + translate_x,
                cmd["to"][1] * scale_y + translate_y,
            ]
        if "control" in cmd:
            new_cmd["control"] = [
                cmd["control"][0] * scale_x + translate_x,
                cmd["control"][1] * scale_y + translate_y,
            ]
        if "control1" in cmd:
            new_cmd["control1"] = [
                cmd["control1"][0] * scale_x + translate_x,
                cmd["control1"][1] * scale_y + translate_y,
            ]
        if "control2" in cmd:
            new_cmd["control2"] = [
                cmd["control2"][0] * scale_x + translate_x,
                cmd["control2"][1] * scale_y + translate_y,
            ]
        normalized.append(new_cmd)

    return normalized


def simplify_path_commands(commands: list[dict[str, Any]], tolerance: float = 0.001) -> list[dict[str, Any]]:
    """Simplify path by removing redundant points and merging nearly-collinear segments."""
    if not commands:
        return commands

    # Always preserve the first command (must be move) and last (must be close)
    if len(commands) < 3:
        return commands

    first_cmd = commands[0]
    last_cmd = commands[-1]
    middle_commands = commands[1:-1]

    simplified_middle = []
    for cmd in middle_commands:
        if cmd["command"] == "close":
            simplified_middle.append(cmd)
            continue

        last = simplified_middle[-1] if simplified_middle else first_cmd
        if last["command"] in ("line", "move") and cmd["command"] == "line":
            # Check if three points are nearly collinear
            p1 = last.get("to", first_cmd.get("to") if not simplified_middle else None)
            p2 = last["to"]
            p3 = cmd["to"]
            if p1 and p2 and p3:
                # Cross product for collinearity
                cross = abs((p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0]))
                dist = math.hypot(p3[0] - p1[0], p3[1] - p1[1])
                if dist > 0 and cross / dist < tolerance:
                    # Merge: replace last line with this one
                    if simplified_middle:
                        simplified_middle[-1] = cmd
                    else:
                        # Can't merge with first_cmd if it's a move
                        pass
                    continue

        simplified_middle.append(cmd)

    return [first_cmd] + simplified_middle + [last_cmd]


def clean_board_geometry(board_path: Path, dry_run: bool = False) -> dict[str, Any]:
    """Clean up hold geometry in a board.json file."""
    board = json.loads(board_path.read_text(encoding="utf-8"))

    for presentation in board.get("presentations", []):
        media = presentation.get("media", {})
        if media.get("type") != "raster":
            continue

        contact_geometry = media.get("contactGeometry", {})
        if not contact_geometry:
            continue

        # Use a reasonable canvas size for parsing
        width = 2000
        height = 2000

        for contact_id, pieces in contact_geometry.items():
            for piece_index, piece in enumerate(pieces):
                frame = piece["frame"]
                shape = piece["shape"]

                if shape["type"] == "path":
                    try:
                        # Convert canonical format to display path for analysis
                        path = display_path_for_shape(frame, shape, width, height, label=f"contact {contact_id}[{piece_index}]")

                        # Check for shape constraint match
                        match = analyze_path_for_shape_constraint(path, NormalizedFrame.from_json(frame, "frame"))
                        if match and match.confidence > 0.9:
                            # Replace with shape constraint
                            # Derive tight frame from the original path BEFORE
                            # replacing the shape, so the replacement doesn't
                            # expand to fill the old (possibly larger) frame.
                            tight_frame, _ = shape_for_path(path, width, height)

                            constraint_shape = match.constraint_type
                            if match.constraint_type in ("pill", "circle"):
                                piece["shape"] = {"type": "roundedRect", "cornerRadiusFraction": 0.5}
                                piece["frame"] = tight_frame.to_json()
                            elif match.constraint_type == "oval":
                                # Keep oval as a path — roundedRect cannot
                                # represent continuous ellipse curvature.
                                # Use shape_for_path for consistent frame+shape.
                                new_frame, new_shape = shape_for_path(path, width, height)
                                piece["frame"] = new_frame.to_json()
                                piece["shape"] = new_shape
                            elif match.constraint_type == "rectangle":
                                piece["shape"] = {"type": "roundedRect", "cornerRadiusFraction": 0.0}
                                piece["frame"] = tight_frame.to_json()
                            else:
                                piece["shape"] = {"type": match.constraint_type}
                                if match.corner_radius_fraction is not None:
                                    piece["shape"]["cornerRadiusFraction"] = round(match.corner_radius_fraction, 3)
                                piece["frame"] = tight_frame.to_json()

                            # Map shape type to constraint shape name
                            if match.constraint_type == "roundedRect":
                                constraint_shape = "roundedRectangle"

                            piece["shapeConstraint"] = {
                                "shape": constraint_shape,
                                "rotationDegrees": match.rotation_degrees
                            }
                            if "treatment" not in piece:
                                piece["treatment"] = {"type": "surface"}
                            print(f"  {contact_id}[{piece_index}]: Applied {match.constraint_type} constraint (confidence: {match.confidence:.2f})")
                            continue

                        # Convert canonical display path into tight frame and local shape
                        try:
                            new_frame, new_shape = shape_for_path(path, width, height)
                            piece["frame"] = new_frame.to_json()
                            piece["shape"] = new_shape
                            print(f"  {contact_id}[{piece_index}]: Normalized path to fill frame")
                        except GeometryError as e:
                            print(f"  {contact_id}[{piece_index}]: Frame recomputation failed - {e}")

                        # Skip simplification for now - it was removing critical segments
                        # simplified = simplify_path_commands(piece["shape"]["commands"])
                        # if len(simplified) < len(piece["shape"]["commands"]):
                        #     piece["shape"]["commands"] = simplified
                        #     print(f"  {contact_id}[{piece_index}]: Simplified path ({len(normalized_commands)} -> {len(simplified)} commands)")

                    except GeometryError as e:
                        print(f"  {contact_id}[{piece_index}]: Geometry error - {e}")

    if not dry_run:
        board_path.write_text(json.dumps(board, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved cleaned board to {board_path}")

    return board


def main():
    if len(sys.argv) < 2:
        print("Usage: python geometry_cleanup.py <board.json> [--dry-run]")
        sys.exit(1)

    board_path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    print(f"Cleaning geometry for {board_path}")
    clean_board_geometry(board_path, dry_run=dry_run)


if __name__ == "__main__":
    from dataclasses import dataclass
    main()