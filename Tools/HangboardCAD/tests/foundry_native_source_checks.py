"""Native-source checks for the Metolius Foundry FCStd document.

Run under FreeCAD's interpreter.  The checks exercise the saved document,
including a real published-depth edit, rather than inspecting its XML.
"""

from __future__ import annotations

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


def rail_section_pieces(rail_shape, z: float) -> list[dict]:
    """Return collinear-merged facets from a physical transverse section."""
    plane = Part.makePlane(
        400,
        200,
        App.Vector(0, -100, z),
        App.Vector(0, 0, 1),
    )

    def piece(start, end) -> dict:
        angle = math.degrees(math.atan2(end.y - start.y, end.x - start.x))
        return {
            "x0": start.x,
            "y0": start.y,
            "x1": end.x,
            "y1": end.y,
            "mid_y": (start.y + end.y) / 2.0,
            "angle": angle,
            "span": end.x - start.x,
        }

    raw = []
    for edge in rail_shape.section(plane).Edges:
        points = [vertex.Point for vertex in edge.Vertexes]
        if len(points) != 2:
            continue
        start, end = sorted(points, key=lambda point: point.x)
        if max(abs(start.y), abs(end.y)) < 1e-6:
            continue
        raw.append(piece(start, end))
    raw.sort(key=lambda item: (item["x0"] + item["x1"]) / 2.0)

    # OCCT may split one physical facet where a loft profile crosses an arch
    # vertex. Merge only connected segments with the same physical normal so
    # the output metric does not depend on that incidental edge split.
    merged = []
    for item in raw:
        if merged:
            previous = merged[-1]
            connected = math.hypot(
                previous["x1"] - item["x0"],
                previous["y1"] - item["y0"],
            ) < 1e-4
            if connected and abs(previous["angle"] - item["angle"]) < 1.0:
                start = App.Vector(previous["x0"], previous["y0"], z)
                end = App.Vector(item["x1"], item["y1"], z)
                merged[-1] = piece(start, end)
                continue
        merged.append(item)
    return merged


def rail_crown_sections(rail_shape) -> list[dict]:
    """Measure the rail's real five-facet transverse crown at four heights."""
    results = []
    for z in (35.0, 80.0, 125.0, 170.0):
        pieces = rail_section_pieces(rail_shape, z)
        if not pieces:
            results.append({"z": z, "passed": False, "detail": "no crown edges"})
            continue
        width = max(piece["x1"] for piece in pieces) - min(
            piece["x0"] for piece in pieces
        )
        nose_index = min(
            range(len(pieces)),
            key=lambda index: pieces[index]["mid_y"],
        )
        angles = [piece["angle"] for piece in pieces]
        turns = [end - start for start, end in zip(angles, angles[1:])]
        shoulders = (
            [abs(angles[nose_index - 1]), abs(angles[nose_index + 1])]
            if 0 < nose_index < len(pieces) - 1
            else []
        )
        nose_fraction = pieces[nose_index]["span"] / width
        passed = (
            len(pieces) == 5
            and len(turns) == 4
            and all(turn > 5.0 for turn in turns)
            and 0.12 <= nose_fraction <= 0.30
            and len(shoulders) == 2
            and all(8.0 <= angle <= 35.0 for angle in shoulders)
            and abs(angles[0]) > shoulders[0] + 12.0
            and abs(angles[-1]) > shoulders[1] + 12.0
        )
        results.append(
            {
                "z": z,
                "passed": passed,
                "nose_fraction": nose_fraction,
                "angles": angles,
            }
        )
    return results


def rail_longitudinal_continuity(rail_shape) -> dict:
    """Measure crown stability every 2.5 mm through the visible rail height."""
    sampled = []
    for index in range(81):
        z = 10.0 + index * 2.5
        pieces = rail_section_pieces(rail_shape, z)
        section = {"z": z, "count": len(pieces)}
        if len(pieces) == 5:
            points = [(pieces[0]["x0"], pieces[0]["y0"])] + [
                (piece["x1"], piece["y1"]) for piece in pieces
            ]
            width = points[-1][0] - points[0][0]
            depth = min(point[1] for point in points)
            if width > 1e-6 and depth < -1e-6:
                section.update(
                    {
                        "x": [(point[0] - points[0][0]) / width for point in points],
                        "depth": [point[1] / depth for point in points],
                        "angles": [piece["angle"] for piece in pieces],
                    }
                )
        sampled.append(section)

    complete = all("x" in section for section in sampled)
    counts = sorted({section["count"] for section in sampled})
    if not complete:
        return {
            "passed": False,
            "detail": f"samples={len(sampled)} facet-counts={counts}",
        }

    pairs = list(zip(sampled, sampled[1:]))

    def change_metrics(key: str, noise: float) -> tuple[float, float, int]:
        steps = []
        accelerations = []
        most_reversals = 0
        for feature in range(len(sampled[0][key])):
            deltas = [
                right[key][feature] - left[key][feature]
                for left, right in pairs
            ]
            steps.extend(abs(delta) for delta in deltas)
            accelerations.extend(
                abs(after - before)
                for before, after in zip(deltas, deltas[1:])
            )
            most_reversals = max(
                most_reversals,
                sum(
                    before * after < 0
                    and abs(before) > noise
                    and abs(after) > noise
                    for before, after in zip(deltas, deltas[1:])
                ),
            )
        return max(steps), max(accelerations), most_reversals

    x_step, x_acceleration, x_reversals = change_metrics("x", 1e-5)
    depth_step, depth_acceleration, depth_reversals = change_metrics(
        "depth", 1e-5
    )
    angle_step, angle_acceleration, angle_reversals = change_metrics(
        "angles", 1e-3
    )
    passed = (
        x_step < 0.025
        and depth_step < 0.005
        and angle_step < 2.0
        and x_reversals <= 2
        and depth_acceleration < 0.0002
        and depth_reversals == 0
        and angle_reversals <= 2
    )
    return {
        "passed": passed,
        "detail": (
            f"samples={len(sampled)} facet-counts={counts} "
            f"steps(x/depth/angle)={x_step:.5f}/{depth_step:.5f}/{angle_step:.3f} "
            f"accel(x/depth/angle)={x_acceleration:.5f}/"
            f"{depth_acceleration:.5f}/{angle_acceleration:.3f} "
            f"reversals(x/depth/angle)={x_reversals}/"
            f"{depth_reversals}/{angle_reversals}"
        ),
    }


def flat_rail_control():
    """A valid five-facet prism whose center facet is intentionally too wide."""
    points = [
        App.Vector(0, 0, 0),
        App.Vector(8, -25, 0),
        App.Vector(18, -30, 0),
        App.Vector(82, -30, 0),
        App.Vector(92, -25, 0),
        App.Vector(100, 0, 0),
    ]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0, 0, 220))


def lumpy_rail_control():
    """A valid five-facet loft with repeated depth and direction reversals."""
    wires = []
    for z, shoulder, nose, skew in (
        (0.0, -32.0, -38.0, 0.0),
        (40.0, -42.0, -48.0, 4.0),
        (80.0, -34.0, -40.0, -3.0),
        (120.0, -45.0, -51.0, 4.0),
        (160.0, -35.0, -41.0, -3.0),
        (200.0, -43.0, -49.0, 3.0),
        (220.0, -32.0, -38.0, 0.0),
    ):
        points = [
            App.Vector(0.0, 0.0, z),
            App.Vector(18.0 + skew, shoulder, z),
            App.Vector(38.0 + skew, nose, z),
            App.Vector(62.0 + skew, nose, z),
            App.Vector(82.0 + skew, shoulder, z),
            App.Vector(100.0, 0.0, z),
        ]
        wires.append(Part.makePolygon(points + [points[0]]))
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
        (
            obj
            for obj in document.Objects
            if obj.Name.startswith("RightLongitudinalRailProfile")
        ),
        key=lambda obj: obj.Name,
    )
    check(
        "side rail uses three deliberately authored full-height profiles",
        len(rail_profiles) == 3
        and all(profile.Shape.BoundBox.ZLength > 190.0 for profile in rail_profiles),
        f"profiles={len(rail_profiles)} "
        f"heights={[round(profile.Shape.BoundBox.ZLength, 3) for profile in rail_profiles]}",
    )
    check(
        "side rail is one ruled longitudinal loft without horizontal stations",
        right_rail is not None
        and right_rail.TypeId == "Part::Loft"
        and bool(right_rail.Ruled)
        and list(right_rail.Sections) == rail_profiles
        and not any(
            obj.Name.startswith("RightContinuousShoulderSection")
            for obj in document.Objects
        ),
        f"type={right_rail.TypeId if right_rail is not None else None} "
        f"ruled={bool(right_rail.Ruled) if right_rail is not None else None}",
    )

    crown_sections = (
        rail_crown_sections(right_rail.Shape) if right_rail is not None else []
    )
    check(
        "side rail has the reviewed shallow five-facet convex crown",
        len(crown_sections) == 4
        and all(section["passed"] for section in crown_sections),
        "; ".join(
            f"z={section['z']:.0f} "
            f"nose={section.get('nose_fraction', float('nan')):.3f} "
            f"angles={[round(angle, 2) for angle in section.get('angles', [])]}"
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

    flat_control = flat_rail_control()
    flat_sections = rail_crown_sections(flat_control)
    check(
        "crown gate rejects a valid deliberately flat control",
        flat_control.isValid()
        and len(flat_sections) == 4
        and not all(section["passed"] for section in flat_sections),
        "; ".join(
            f"z={section['z']:.0f} nose="
            f"{section.get('nose_fraction', float('nan')):.3f}"
            for section in flat_sections
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
        "side rail facets have no B-rep self-intersections",
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
