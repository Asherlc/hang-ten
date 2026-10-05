"""Native-source checks for the Metolius Foundry FCStd document.

Run under FreeCAD's interpreter.  The checks exercise the saved document,
including a real published-depth edit, rather than inspecting its XML.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
import hashlib
import json
import math
import os
import sys
from pathlib import Path

sys.path[:0] = [
    part
    for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep)
    if part
]

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402


FAILURES: list[str] = []
PUBLISHED_DEPTHS = {
    "pocket-3-left": 32.0,
    "pocket-3-right": 32.0,
    "pocket-4-left": 22.0,
    "pocket-4-right": 22.0,
    "pocket-5-left": 30.0,
    "pocket-5-right": 30.0,
    "pocket-6-left": 15.0,
    "pocket-6-right": 15.0,
    "pocket-7-left": 21.0,
    "pocket-7-right": 21.0,
    "sloper-8-center": 53.0,
    "edge-9-center": 16.0,
    "edge-10-center": 30.0,
    "edge-11-center": 23.0,
}
GRID_AUDITED_CENTERS_MM = {
    # Operator-read from the manufacturer diagram on a 40 x 16 normalized
    # envelope grid (14.45 x 13.5 mm minor cells), not image extraction.
    "pocket-3-left": (-138.0, 130.0),
    "pocket-3-right": (138.0, 130.0),
    "pocket-4-left": (-178.0, 92.0),
    "pocket-4-right": (178.0, 92.0),
    "pocket-5-left": (-118.0, 97.0),
    "pocket-5-right": (118.0, 97.0),
    "pocket-6-left": (-178.0, 58.0),
    "pocket-6-right": (178.0, 58.0),
    "pocket-7-left": (-118.0, 63.0),
    "pocket-7-right": (118.0, 63.0),
    "edge-9-center": (0.0, 160.0),
    "edge-10-center": (0.0, 112.0),
    "edge-11-center": (0.0, 65.0),
}
GRID_AUDITED_ANGLES_DEG = {
    "pocket-3-left": 3.0,
    "pocket-3-right": -3.0,
    "pocket-4-left": 6.0,
    "pocket-4-right": -6.0,
    "pocket-5-left": 6.0,
    "pocket-5-right": -6.0,
    "pocket-6-left": 7.0,
    "pocket-6-right": -7.0,
    "pocket-7-left": 6.0,
    "pocket-7-right": -6.0,
}
EXPECTED_CONTACTS = {
    "pinch-1-left",
    "pinch-1-right",
    "jug-2-left",
    "jug-2-right",
    *PUBLISHED_DEPTHS,
}


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}", flush=True)
    if not condition:
        FAILURES.append(label)


def contacts(document) -> dict[str, object]:
    return {
        obj.ContactID: obj
        for obj in document.Objects
        if getattr(obj, "NodeRole", "") == "contact"
        and getattr(obj, "ContactID", "")
    }


def spans(document) -> dict[str, tuple[float, float, float]]:
    return {
        contact_id: (
            round(obj.Shape.optimalBoundingBox().YLength, 3),
            round(obj.Shape.optimalBoundingBox().ZLength, 3),
            round(obj.Shape.optimalBoundingBox().XLength, 3),
        )
        for contact_id, obj in contacts(document).items()
    }


def surface_gap(body, region) -> float:
    """Maximum sampled distance from a contact surface to the board solid."""
    worst = 0.0
    for face in region.Shape.Faces:
        points, triangles = face.copy().tessellate(0.35)
        if not triangles:
            continue
        triangle = max(
            triangles,
            key=lambda item: (
                (points[item[1]] - points[item[0]])
                .cross(points[item[2]] - points[item[0]])
                .Length
            ),
        )
        chord_point = sum((points[index] for index in triangle), App.Vector()) / 3.0
        u, v = face.Surface.parameter(chord_point)
        exact_point = face.valueAt(u, v)
        worst = max(worst, body.Shape.distToShape(Part.Vertex(exact_point))[0])
    return worst


def mounting_plane_area(region) -> float:
    """Area of triangles lying on the inaccessible wall-side Y=0 plane."""
    area = 0.0
    for face in region.Shape.Faces:
        points, triangles = face.copy().tessellate(0.35)
        for a, b, c in triangles:
            pa, pb, pc = points[a], points[b], points[c]
            if max(abs(pa.y), abs(pb.y), abs(pc.y)) < 1e-6:
                area += 0.5 * (pb - pa).cross(pc - pa).Length
    return area


def shape_axis_angle_degrees(shape_object) -> float:
    """Principal X/Z axis of native geometry."""
    points = [vertex.Point for vertex in shape_object.Shape.Vertexes]
    mean_x = sum(point.x for point in points) / len(points)
    mean_z = sum(point.z for point in points) / len(points)
    covariance_xx = sum((point.x - mean_x) ** 2 for point in points)
    covariance_zz = sum((point.z - mean_z) ** 2 for point in points)
    covariance_xz = sum(
        (point.x - mean_x) * (point.z - mean_z) for point in points
    )
    angle = math.degrees(
        0.5 * math.atan2(2.0 * covariance_xz, covariance_xx - covariance_zz)
    )
    if angle > 90.0:
        angle -= 180.0
    elif angle <= -90.0:
        angle += 180.0
    return angle


def aperture_section(document, contact_id: str):
    """Return the native cutting section which directly drives the opening."""
    source_id = (
        contact_id.removesuffix("left") + "right"
        if contact_id.endswith("left")
        else contact_id
    )
    return document.getObject(f"Cutter_{source_id.replace('-', '_')}_Section2")


def manifest(document) -> dict:
    return json.loads(document.HangTenBoardManifest)


def rail_section_polyline(
    rail_shape, z: float, step: float = 1.0
) -> tuple[list[tuple[float, float]], list]:
    """Return the ordered X/Y section polyline and its native edges at Z.

    The inaccessible mounting-plane chord (Y = 0) is dropped, so the polyline
    runs from the inner rear corner over the crown to the outer rear corner.
    """
    plane = Part.makePlane(400, 200, App.Vector(0, -100, z), App.Vector(0, 0, 1))
    edges = [
        edge
        for edge in rail_shape.section(plane).Edges
        if max(abs(vertex.Point.y) for vertex in edge.Vertexes) > 1e-6
        or abs(edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0).y) > 1e-6
    ]
    if not edges:
        return [], []
    wire_edges = Part.__sortEdges__(edges)
    points = []
    for edge in wire_edges:
        count = max(2, int(math.ceil(edge.Length / step)) + 1)
        sampled = [point for point in edge.discretize(count)]
        if points and (sampled[0] - points[-1]).Length > (sampled[-1] - points[-1]).Length:
            sampled.reverse()
        points.extend(sampled if not points else sampled[1:])
    if points[0].x > points[-1].x:
        points.reverse()
    return [(point.x, point.y) for point in points], wire_edges


def section_tangent_breaks(wire_edges, straight_only=False) -> list[float]:
    """Measure native tangent jumps at joins, regardless of edge orientation.

    Use the closest endpoints to orient each tangent along the open section;
    CAD edge parameter directions need not agree with the sorted wire order.
    With straight_only, measure only joins between polygonal facets.
    """
    def ends(edge):
        first, last = edge.FirstParameter, edge.LastParameter
        return (
            edge.valueAt(first), edge.tangentAt(first),
            edge.valueAt(last), edge.tangentAt(last),
        )

    def is_straight(edge):
        chord = (edge.valueAt(edge.LastParameter) - edge.valueAt(edge.FirstParameter)).Length
        return abs(edge.Length - chord) <= 1e-7 * edge.Length

    breaks = []
    for a, b in zip(wire_edges, wire_edges[1:]):
        if straight_only and not (is_straight(a) and is_straight(b)):
            continue
        a_start, a_leave, a_end, a_arrive = ends(a)
        b_start, b_leave, b_end, b_arrive = ends(b)
        candidates = [
            ((a_end - b_start).Length, a_arrive, b_leave),
            ((a_end - b_end).Length, a_arrive, -b_arrive),
            ((a_start - b_start).Length, -a_leave, b_leave),
            ((a_start - b_end).Length, -a_leave, -b_arrive),
        ]
        _, incoming, outgoing = min(candidates, key=lambda item: item[0])
        breaks.append(math.degrees(incoming.getAngle(outgoing)))
    return breaks


def crown_metrics(polyline: list[tuple[float, float]]) -> dict:
    """Turning behaviour of a sampled crown: convexity and the sharpest crease."""
    headings = [
        math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        for a, b in zip(polyline, polyline[1:])
        if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6
    ]
    turns = []
    for before, after in zip(headings, headings[1:]):
        turn = after - before
        turn = (turn + 180.0) % 360.0 - 180.0
        turns.append(turn)
    absolute_turns = [abs(turn) for turn in turns]
    sample_distances = [0.0]
    for before, after in zip(polyline, polyline[1:]):
        sample_distances.append(
            sample_distances[-1] + math.hypot(after[0] - before[0], after[1] - before[1])
        )
    turn_distances = sample_distances[1:-1]
    # Measure concentration over a physical arc length so changing the section
    # discretization cannot hide several nearby polygon creases in one window.
    turn_window_half_width_mm = 5.0
    turn_concentrations = []
    for index, value in enumerate(absolute_turns):
        window_start = bisect_left(
            turn_distances, turn_distances[index] - turn_window_half_width_mm
        )
        window_end = bisect_right(
            turn_distances, turn_distances[index] + turn_window_half_width_mm
        )
        local_turn = sum(absolute_turns[window_start:window_end])
        turn_concentrations.append(value / max(1e-9, local_turn))
    nose_depth = min(point[1] for point in polyline)
    return {
        "max_turn": max((abs(turn) for turn in turns), default=float("nan")),
        "concave_turns": sum(turn < -0.05 for turn in turns),
        "max_concave_turn": max((-turn for turn in turns if turn < 0), default=0.0),
        "max_turn_concentration": max(turn_concentrations, default=float("nan")),
        "total_turn": sum(turns),
        "nose_depth": nose_depth,
    }


def rail_crown_sections(rail_shape) -> list[dict]:
    """The crown is a convex arch at four heights, without polygonal faceting."""
    results = []
    for z in (35.0, 80.0, 125.0, 170.0):
        polyline, edges = rail_section_polyline(rail_shape, z)
        if len(polyline) < 10:
            results.append({"z": z, "passed": False, "max_turn": float("nan")})
            continue
        metrics = crown_metrics(polyline)
        metrics["max_tangent_break"] = max(section_tangent_breaks(edges), default=0.0)
        # The authored curved shoulders meet a flat nose with retained tangent
        # jumps. Reject polygonal crowns by testing joins between straight
        # facets directly, independently of facet spacing or sampled turns.
        metrics["max_facet_break"] = max(
            section_tangent_breaks(edges, straight_only=True), default=0.0
        )
        passed = (
            metrics["max_turn"] < 20.0
            and metrics["max_facet_break"] < 0.001
            and metrics["max_turn_concentration"] < 0.45
            and metrics["max_concave_turn"] < 3.0
            and metrics["total_turn"] > 90.0
            and metrics["nose_depth"] < -20.0
        )
        results.append({"z": z, "passed": passed, **metrics})
    return results


def rail_longitudinal_continuity(rail_shape) -> dict:
    """Crown shape stays continuous every 2.5 mm through the visible rail height."""
    fractions = [index / 20.0 for index in range(21)]
    sampled = []
    for index in range(81):
        z = 10.0 + index * 2.5
        polyline, _ = rail_section_polyline(rail_shape, z)
        if len(polyline) < 10:
            sampled.append(None)
            continue
        x0, x1 = polyline[0][0], polyline[-1][0]
        depth = min(point[1] for point in polyline)
        if x1 - x0 < 1e-6 or depth > -1e-6:
            sampled.append(None)
            continue
        # Normalized depth profile at fixed normalized widths.
        profile = []
        for fraction in fractions:
            x = x0 + fraction * (x1 - x0)
            best = min(polyline, key=lambda point: abs(point[0] - x))
            profile.append(best[1] / depth)
        sampled.append({"z": z, "depth": depth, "profile": profile})
    if any(section is None for section in sampled):
        return {"passed": False, "detail": f"missing sections={sum(s is None for s in sampled)}"}
    pairs = list(zip(sampled, sampled[1:]))
    profile_steps = [
        max(abs(b["profile"][k] - a["profile"][k]) for k in range(len(fractions)))
        for a, b in pairs
    ]
    depth_deltas = [b["depth"] - a["depth"] for a, b in pairs]
    depth_accelerations = [abs(after - before) for before, after in zip(depth_deltas, depth_deltas[1:])]
    depth_reversals = sum(
        before * after < 0 and abs(before) > 0.02 and abs(after) > 0.02
        for before, after in zip(depth_deltas, depth_deltas[1:])
    )
    passed = max(profile_steps) < 0.09 and max(depth_accelerations) < 0.35 and depth_reversals == 0
    return {
        "passed": passed,
        "detail": (
            f"samples={len(sampled)} max-profile-step={max(profile_steps):.4f} "
            f"max-depth-accel={max(depth_accelerations):.4f} depth-reversals={depth_reversals}"
        ),
    }


def faceted_rail_control():
    """A valid five-facet crown prism: the superseded faceted rail topology."""
    points = [
        App.Vector(0, 0, 0),
        App.Vector(8, -25, 0),
        App.Vector(38, -34, 0),
        App.Vector(62, -34, 0),
        App.Vector(92, -25, 0),
        App.Vector(100, 0, 0),
    ]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0, 0, 220))


def shallow_faceted_rail_control():
    """A many-sided shallow crown: 15 degree creases evade a 20 degree cap."""
    points = [
        App.Vector(50 + 50 * math.cos(math.pi + index * math.pi / 12),
                   50 * math.sin(math.pi + index * math.pi / 12), 0)
        for index in range(13)
    ]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0, 0, 220))


def closely_faceted_rail_control(facets=32):
    """A 130 mm arc crown with shallow, closely spaced creases."""
    points = [
        App.Vector(
            42 + 42 * math.cos(math.pi + index * math.pi / facets),
            42 * math.sin(math.pi + index * math.pi / facets),
            0,
        )
        for index in range(facets + 1)
    ]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0, 0, 220))


def lumpy_rail_control():
    """A valid smooth-section loft whose crown depth repeatedly swells and shrinks."""
    wires = []
    for z, nose in ((0.0, -34.0), (40.0, -46.0), (80.0, -33.0), (120.0, -47.0), (160.0, -34.0), (200.0, -45.0), (220.0, -34.0)):
        arc = Part.Arc(App.Vector(0, 0, z), App.Vector(50, nose, z), App.Vector(100, 0, z)).toShape()
        chord = Part.makeLine(App.Vector(100, 0, z), App.Vector(0, 0, z))
        wires.append(Part.Wire([arc, chord]))
    return Part.makeLoft(wires, True, False)


def main() -> int:
    source = Path(sys.argv[1]).resolve()
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()

    document = App.openDocument(str(source))
    document.recompute()
    print("reopen and recompute", flush=True)
    stale = [
        obj.Name
        for obj in document.Objects
        if {"Invalid", "Error", "Touched", "Recompute"} & set(obj.State)
    ]
    check("every object recomputes", not stale, f"{stale}")

    body = document.getObject("BodySolid")
    parameters = document.getObject("Parameters")
    check("body and driving parameters are present", body is not None and parameters is not None)
    if body is not None:
        check(
            "body is one valid solid",
            body.Shape.isValid() and len(body.Shape.Solids) == 1,
            f"solids={len(body.Shape.Solids)}",
        )
        box = body.Shape.optimalBoundingBox()
        check(
            "body matches the published 578 x 216 mm envelope",
            abs(box.XLength - 578.0) < 0.02
            and abs(box.ZLength - 216.0) < 0.02
            and abs(box.YMax) < 0.02,
            f"X={box.XLength:.3f} Y={box.YMin:.3f}..{box.YMax:.3f} Z={box.ZLength:.3f}",
        )

    sketches = [obj for obj in document.Objects if obj.TypeId == "Sketcher::SketchObject"]
    check("native Sketcher profiles drive the saved model", bool(sketches))
    loose = [obj.Name for obj in sketches if not obj.FullyConstrained]
    check("every native sketch is fully constrained", bool(sketches) and not loose, ", ".join(loose))

    bound = contacts(document)
    check(
        "all 18 semantic contacts are bound",
        set(bound) == EXPECTED_CONTACTS,
        f"missing={sorted(EXPECTED_CONTACTS - set(bound))} extra={sorted(set(bound) - EXPECTED_CONTACTS)}",
    )
    before = spans(document)
    for contact_id, depth in sorted(PUBLISHED_DEPTHS.items()):
        check(
            f"{contact_id} span matches its published dimension",
            contact_id in before and abs(before[contact_id][0] - depth) < 0.02,
            f"authored={before.get(contact_id)} published={depth}",
        )

    for contact_id, expected_center in sorted(GRID_AUDITED_CENTERS_MM.items()):
        section = aperture_section(document, contact_id)
        box = section.Shape.optimalBoundingBox() if section is not None else None
        actual_center = (
            ((box.XMin + box.XMax) / 2.0, (box.ZMin + box.ZMax) / 2.0)
            if box is not None
            else None
        )
        if actual_center is not None and contact_id.endswith("left"):
            actual_center = (-actual_center[0], actual_center[1])
        check(
            f"{contact_id} aperture stays on its manually grid-audited center",
            actual_center is not None
            and abs(actual_center[0] - expected_center[0]) < 0.75
            and abs(actual_center[1] - expected_center[1]) < 0.75,
            f"actual={actual_center} expected={expected_center}",
        )

    for contact_id, expected_angle in sorted(GRID_AUDITED_ANGLES_DEG.items()):
        section = aperture_section(document, contact_id)
        actual_angle = (
            shape_axis_angle_degrees(section)
            if section is not None
            else None
        )
        if actual_angle is not None and contact_id.endswith("left"):
            actual_angle = -actual_angle
        check(
            f"{contact_id} follows the manually reviewed side-hold fan",
            actual_angle is not None and abs(actual_angle - expected_angle) < 1.0,
            f"actual={actual_angle} expected={expected_angle}",
        )

    right_rail = document.getObject("RightContinuousShoulder")
    left_rail = document.getObject("LeftContinuousShoulder")
    rail_profiles = sorted(
        (obj for obj in document.Objects if obj.Name.startswith("RightCrownProfile")),
        key=lambda obj: int(obj.Name.removeprefix("RightCrownProfile")),
    )
    check(
        "side rail uses deliberately authored full-height crown profiles",
        len(rail_profiles) >= 3
        and all(profile.Shape.BoundBox.ZLength > 190.0 for profile in rail_profiles),
        f"profiles={len(rail_profiles)} "
        f"heights={[round(profile.Shape.BoundBox.ZLength, 3) for profile in rail_profiles]}",
    )
    check(
        "side rail is one smooth longitudinal loft without horizontal stations",
        right_rail is not None
        and right_rail.TypeId == "Part::Loft"
        and not bool(right_rail.Ruled)
        and list(right_rail.Sections) == rail_profiles,
        f"type={right_rail.TypeId if right_rail is not None else None} "
        f"ruled={bool(right_rail.Ruled) if right_rail is not None else None}",
    )

    crown_sections = (
        rail_crown_sections(right_rail.Shape) if right_rail is not None else []
    )
    check(
        "side rail has a convex curved crown without polygonal facets",
        len(crown_sections) == 4
        and all(section["passed"] for section in crown_sections),
        "; ".join(
            f"z={section['z']:.0f} max-turn={section.get('max_turn', float('nan')):.2f} "
            f"concentration={section.get('max_turn_concentration', float('nan')):.2f} "
            f"tangent-break={section.get('max_tangent_break', float('nan')):.2f} "
            f"concave={section.get('concave_turns')} "
            f"nose={section.get('nose_depth', float('nan')):.1f}"
            for section in crown_sections
        ),
    )

    continuity = (
        rail_longitudinal_continuity(right_rail.Shape)
        if right_rail is not None
        else {"passed": False, "detail": "missing rail"}
    )
    check(
        "side rail crown stays continuous without longitudinal lumps",
        continuity["passed"],
        continuity["detail"],
    )

    faceted_control = faceted_rail_control()
    faceted_sections = rail_crown_sections(faceted_control)
    check(
        "crown gate rejects a valid deliberately faceted control",
        faceted_control.isValid()
        and len(faceted_sections) == 4
        and not any(section["passed"] for section in faceted_sections),
        "; ".join(
            f"z={section['z']:.0f} max-turn={section.get('max_turn', float('nan')):.2f}"
            for section in faceted_sections
        ),
    )

    shallow_faceted_control = shallow_faceted_rail_control()
    shallow_faceted_sections = rail_crown_sections(shallow_faceted_control)
    check(
        "crown gate rejects shallow creases distributed across many facets",
        shallow_faceted_control.isValid()
        and len(shallow_faceted_sections) == 4
        and not any(section["passed"] for section in shallow_faceted_sections),
        "; ".join(
            f"z={section['z']:.0f} max-turn={section.get('max_turn', float('nan')):.2f} "
            f"concentration={section.get('max_turn_concentration', float('nan')):.2f}"
            for section in shallow_faceted_sections
        ),
    )

    for facets in (32, 64):
        closely_faceted_control = closely_faceted_rail_control(facets)
        closely_faceted_sections = rail_crown_sections(closely_faceted_control)
        check(
            f"crown gate rejects closely spaced shallow creases ({facets} facets)",
            closely_faceted_control.isValid()
            and len(closely_faceted_sections) == 4
            and not any(section["passed"] for section in closely_faceted_sections),
            "; ".join(
                f"z={section['z']:.0f} max-turn={section.get('max_turn', float('nan')):.2f} "
                f"concentration={section.get('max_turn_concentration', float('nan')):.2f} "
                f"facet-break={section.get('max_facet_break', float('nan')):.2f}"
                for section in closely_faceted_sections
            ),
        )

    lumpy_control = lumpy_rail_control()
    lumpy_continuity = rail_longitudinal_continuity(lumpy_control)
    check(
        "continuity gate rejects a valid deliberately lumpy control",
        lumpy_control.isValid() and not lumpy_continuity["passed"],
        lumpy_continuity["detail"],
    )

    rail_bop_errors = []
    for rail in (left_rail, right_rail):
        if rail is None:
            rail_bop_errors.append("missing rail")
            continue
        try:
            rail.Shape.check(True)
        except ValueError as error:
            rail_bop_errors.append(f"{rail.Name}: {error}")
    check(
        "side rail has no B-rep self-intersections",
        not rail_bop_errors,
        "; ".join(rail_bop_errors),
    )
    check(
        "left side rail is the native mirror of the authored right rail",
        left_rail is not None
        and right_rail is not None
        and left_rail.TypeId == "Part::Mirroring"
        and left_rail.Source == right_rail,
    )

    for side, rail in (("left", left_rail), ("right", right_rail)):
        for pocket_number in range(3, 8):
            cutter = document.getObject(f"Cutter_pocket_{pocket_number}_{side}")
            overlap = (
                cutter.Shape.common(rail.Shape).Volume
                if cutter is not None and rail is not None
                else None
            )
            check(
                f"pocket-{pocket_number}-{side} cutter does not cut into its side rail",
                overlap is not None and overlap < 1e-5,
                f"overlap={overlap} mm^3",
            )

    if body is not None:
        for contact_id, obj in sorted(bound.items()):
            gap = surface_gap(body, obj)
            check(
                f"{contact_id} lies on the final board surface",
                gap < 1e-3,
                f"max sampled gap={gap:.6f} mm",
            )
            rear_area = mounting_plane_area(obj)
            check(
                f"{contact_id} excludes inaccessible mounting-plane faces",
                rear_area < 1e-4,
                f"rear area={rear_area:.3f} mm^2",
            )

    for left_id in sorted(contact_id for contact_id in EXPECTED_CONTACTS if contact_id.endswith("left")):
        right_id = left_id.removesuffix("left") + "right"
        left = bound.get(left_id)
        right = bound.get(right_id)
        if left is None or right is None:
            continue
        lb = left.Shape.optimalBoundingBox()
        rb = right.Shape.optimalBoundingBox()
        mirrored = (
            abs(lb.XMin + rb.XMax) < 1e-4
            and abs(lb.XMax + rb.XMin) < 1e-4
            and abs(lb.YMin - rb.YMin) < 1e-4
            and abs(lb.YMax - rb.YMax) < 1e-4
            and abs(lb.ZMin - rb.ZMin) < 1e-4
            and abs(lb.ZMax - rb.ZMax) < 1e-4
            and abs(left.Shape.Area - right.Shape.Area) < 1e-3
        )
        check(f"{left_id}/{right_id} are exact native mirrors", mirrored)

    by_id = {contact["id"]: contact for contact in manifest(document)["contacts"]}
    sloper_range = ((by_id["sloper-8-center"].get("depth") or {}).get("range") or {})
    check(
        "the published 53 mm sloper dimension is a structured compiler gate",
        sloper_range == {"minimum": 53, "maximum": 53},
        f"{sloper_range}",
    )

    print("edit: Pocket3Depth 32 -> 34 mm", flush=True)
    if parameters is not None and "Pocket3Depth" in parameters.PropertiesList:
        original = parameters.Pocket3Depth
        parameters.Pocket3Depth = 34.0
        document.recompute()
        after = spans(document)
        check(
            "Pocket3Depth edit reaches both mirrored pocket contacts",
            abs(after["pocket-3-left"][0] - 34.0) < 0.02
            and abs(after["pocket-3-right"][0] - 34.0) < 0.02,
            f"left={after['pocket-3-left'][0]} right={after['pocket-3-right'][0]}",
        )
        check(
            "Pocket3Depth edit leaves unrelated contact spans unchanged",
            all(
                after[contact_id] == before[contact_id]
                for contact_id in EXPECTED_CONTACTS - {"pocket-3-left", "pocket-3-right"}
            ),
        )
        if body is not None:
            for contact_id in ("pocket-3-left", "pocket-3-right"):
                gap = surface_gap(body, contacts(document)[contact_id])
                check(
                    f"{contact_id} remains on the edited body",
                    gap < 1e-3,
                    f"max sampled gap={gap:.6f} mm",
                )
        parameters.Pocket3Depth = original
        document.recompute()
    else:
        check("Pocket3Depth is an exposed driving dimension", False)

    stale = [
        obj.Name
        for obj in document.Objects
        if {"Invalid", "Error", "Touched", "Recompute"} & set(obj.State)
    ]
    check("every object recomputes after the edit", not stale, f"{stale}")
    check(
        "source bytes are unchanged by reopen and edits",
        hashlib.sha256(source.read_bytes()).hexdigest() == original_digest,
    )

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed:", flush=True)
        for label in FAILURES:
            print(f"  - {label}", flush=True)
        return 1
    print("\nall Foundry native source checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
