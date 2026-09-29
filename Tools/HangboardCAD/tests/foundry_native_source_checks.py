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
FACETED_RAIL_ROOT_BANDS_MM = {
    # The rear root may flare inward behind the pockets; a separate front
    # clearance facet (and the solid-overlap checks below) protects the holds.
    15: (219.0, 221.0),
    40: (209.0, 211.0),
    60: (194.0, 196.0),
    80: (179.0, 181.0),
    100: (164.0, 166.0),
    120: (144.0, 146.0),
    140: (129.0, 131.0),
    155: (124.0, 126.0),
    170: (126.0, 130.0),
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

    shoulder = document.getObject("RightContinuousShoulder")
    shoulder_sections = sorted(
        (
            obj
            for obj in document.Objects
            if obj.Name.startswith("RightContinuousShoulderSection")
        ),
        key=lambda obj: obj.Shape.BoundBox.ZMin,
    )
    check(
        "side rail uses the exact deliberately authored loft section set",
        shoulder is not None and len(shoulder_sections) == 25,
        f"sections={len(shoulder_sections)}",
    )
    check(
        "side rail is a longitudinal loft of explicit polygonal facets",
        shoulder is not None
        and not bool(shoulder.Ruled)
        and int(shoulder.MaxDegree) == 2
        and all(
            len(section.Geometry) == 7
            and all(
                type(geometry).__name__ == "LineSegment"
                for geometry in section.Geometry
            )
            for section in shoulder_sections
        ),
        f"ruled={bool(shoulder.Ruled) if shoulder is not None else None} "
        f"maxDegree={int(shoulder.MaxDegree) if shoulder is not None else None} "
        f"edges={sorted({len(section.Geometry) for section in shoulder_sections})}",
    )
    shoulder_bop_error = None
    if shoulder is not None:
        try:
            shoulder.Shape.check(True)
        except ValueError as error:
            shoulder_bop_error = str(error)
    check(
        "side rail facets have no B-rep self-intersections",
        shoulder is not None and shoulder_bop_error is None,
        shoulder_bop_error or "",
    )
    station_inner_x = {
        round(section.Shape.BoundBox.ZMin): section.Shape.BoundBox.XMin
        for section in shoulder_sections
    }
    for z, band in sorted(FACETED_RAIL_ROOT_BANDS_MM.items()):
        actual = station_inner_x.get(z)
        check(
            f"right rail root follows its reviewed clearance curve at Z={z} mm",
            actual is not None and band[0] <= actual <= band[1],
            f"inner X={actual} expected={band}",
        )

    for pocket_number in range(3, 8):
        cutter = document.getObject(f"Cutter_pocket_{pocket_number}_right")
        overlap = (
            cutter.Shape.common(shoulder.Shape).Volume
            if cutter is not None and shoulder is not None
            else None
        )
        check(
            f"pocket-{pocket_number} cutters do not cut into the side rails",
            overlap is not None and overlap < 1e-5,
            f"right overlap={overlap} mm^3",
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
