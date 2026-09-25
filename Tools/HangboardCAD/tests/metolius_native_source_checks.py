"""Genuine native checks for the metolius-rock-rings-3d v2 source document.

Run under FreeCAD's own interpreter:

    HANGTEN_CAD_PYTHONPATH=<extra> \
      /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
      Tools/HangboardCAD/tests/metolius_native_source_checks.py <path-to.FCStd>

The board is descriptor schema v2 with a single reusable unit: one node per
contact slot serves both physical rings. These checks reopen the saved document
in a fresh process, recompute it, and exercise a real edit, including the
slot/instance relationship, which a v1 board cannot exercise.
"""

from __future__ import annotations

import hashlib
import json
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

REPOSITORY = Path(__file__).resolve().parents[3]
# board.json is generated from the FCStd's HangTenBoardManifest (never committed).
BOARD_SOURCE = REPOSITORY / "Hangboards" / "metolius-rock-rings-3d" / "metolius-rock-rings-3d.FCStd"

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}", flush=True)
    if not condition:
        FAILURES.append(label)


def surface_distance(document, point) -> float:
    """Distance from a point to the board surface.

    The board surface is the body node plus the jug, which is split off the
    rounded solid (``Solid``). The seam between them is on both.
    """
    vertex = Part.Vertex(point)
    return min(
        document.getObject("Body").Shape.distToShape(vertex)[0],
        document.getObject("Solid").Shape.Shells[0].distToShape(vertex)[0],
    )


def is_jug_seam(face) -> bool:
    """A jug face on the split planes, internal to the board by design."""
    if face.Surface.__class__.__name__ != "Plane":
        return False
    point = face.CenterOfMass
    normal = face.normalAt(*face.Surface.parameter(point))
    return abs(abs(normal.x) - 1.0) < 1e-9 or abs(normal.z + 1.0) < 1e-9


def bound_objects(document):
    return [
        obj
        for obj in document.Objects
        if "NodeID" in obj.PropertiesList and getattr(obj, "NodeID", "")
    ]


def published_depths(board):
    by_id = {contact["id"]: contact for contact in board.get("contacts", [])}
    depths = {}
    for presentation in board.get("presentations", []):
        for instance in presentation.get("media", {}).get("instances", []):
            for slot, contact_id in instance.get("contactIDsBySlotID", {}).items():
                span = ((by_id.get(contact_id) or {}).get("depth") or {}).get("range") or {}
                low, high = span.get("minimum"), span.get("maximum")
                if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low == high:
                    depths[slot] = float(low)
    return depths


def main() -> int:
    source = Path(sys.argv[1]).resolve()
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    sys.path.insert(0, str(REPOSITORY / "Tools" / "HangboardCAD"))
    import use_hangboard_packages  # noqa: F401
    from hangboard_packages import cad_source

    board = json.loads(cad_source.generate_board_json(BOARD_SOURCE))
    expected_depths = published_depths(board)

    document = App.openDocument(str(source))
    document.recompute()

    print("reopen and recompute", flush=True)
    check("source document reopens", document is not None)
    check(
        "document declares schema version 2",
        document.getPropertyByName("HangTenSchemaVersion") == 2,
        str(document.getPropertyByName("HangTenSchemaVersion")),
    )
    stale = [
        f"{obj.Name}={obj.State}"
        for obj in document.Objects
        if set(obj.State) & {"Invalid", "Error", "Touched", "Recompute"}
    ]
    check("every object recomputes cleanly", not stale, "; ".join(stale))

    outline = document.getObject("Outline")
    check("outline sketch is fully constrained", bool(outline.FullyConstrained))

    # The source is vector primitives: Bezier spans, stadiums, ellipses and
    # circles, with no measured polyline anywhere.
    sketches = [obj for obj in document.Objects if obj.TypeId == "Sketcher::SketchObject"]
    loose = [s.Name for s in sketches if not s.FullyConstrained]
    check("every sketch is fully constrained", not loose, ", ".join(loose))
    outline_kinds = sorted(
        {type(g).__name__ for i, g in enumerate(outline.Geometry) if not outline.getConstruction(i)}
    )
    spans = [g for i, g in enumerate(outline.Geometry) if not outline.getConstruction(i)]
    check(
        "outline is 14 cubic Bezier spans",
        outline_kinds == ["BSplineCurve"] and len(spans) == 14
        and all(g.Degree == 3 and g.NbPoles == 4 for g in spans),
        f"{outline_kinds} x{len(spans)}",
    )
    polylines = [
        s.Name for s in sketches
        if sum(1 for i, g in enumerate(s.Geometry)
               if not s.getConstruction(i) and type(g).__name__ == "LineSegment") > 4
    ]
    check("no sketch is a polyline", not polylines, ", ".join(polylines))

    # Every exported region faces out of the body, into its cavity.
    inward = []
    for obj in bound_objects(document):
        if obj.NodeRole == "body":
            continue
        for face in obj.Shape.Faces:
            if obj.NodeID == "unit_jug_001" and is_jug_seam(face):
                continue
            u0, u1, v0, v1 = face.ParameterRange
            u, v = (u0 + u1) / 2.0, (v0 + v1) / 2.0
            probe = face.valueAt(u, v) + face.normalAt(u, v) * 0.3
            # Outside the finished board: neither in the body nor in the jug.
            if any(
                document.getObject(name).Shape.isInside(probe, 1e-6, True)
                for name in ("Body", "Region_jug")
            ):
                inward.append(obj.NodeID)
    check("every region face points out of the body", not inward, ", ".join(sorted(set(inward))))

    nodes = bound_objects(document)
    inventory = sorted((obj.NodeID, obj.NodeRole) for obj in nodes)
    check("bound node inventory", len(nodes) == 7, f"{inventory}")
    body = next((obj for obj in nodes if obj.NodeRole == "body"), None)
    contacts = {obj.ContactSlotID: obj for obj in nodes if obj.NodeRole == "contact"}
    attachments = [obj for obj in nodes if obj.NodeRole == "attachment"]
    check("one body node", body is not None)
    check("four contact slots", sorted(contacts) == ["jug", "pocket-25", "pocket-32", "pocket-40"])
    check("two attachment nodes", len(attachments) == 2)

    # The jug is the crown hump: its top and both round-overs, split off the
    # rounded solid geometrically, so the hold is visible from the front.
    jug = contacts["jug"].Shape
    jug_faces = len(jug.Faces)
    check(
        "jug covers the crown's front round-over",
        jug.BoundBox.YMin < -28.4 and jug.BoundBox.YMax > 28.4 and jug.BoundBox.ZMax > 86.9,
        f"y {jug.BoundBox.YMin:.2f}..{jug.BoundBox.YMax:.2f}, z max {jug.BoundBox.ZMax:.2f}",
    )
    check("body occupies the native frame", abs(body.Shape.BoundBox.XLength - 146.0) < 1.0
          and abs(body.Shape.BoundBox.YLength - 57.0) < 0.1
          and abs(body.Shape.BoundBox.ZLength - 184.0) < 1.0,
          f"({body.Shape.BoundBox.XLength:.2f},{body.Shape.BoundBox.YLength:.2f},{body.Shape.BoundBox.ZLength:.2f})")

    # Each pocket's authored region depth must equal the published grip depth.
    for slot, depth in sorted(expected_depths.items()):
        obj = contacts.get(slot)
        measured = round(float(obj.Shape.BoundBox.YLength), 3) if obj else None
        check(
            f"{slot} authored depth matches its published grip depth",
            obj is not None and abs(measured - depth) < 0.25,
            f"authored={measured} published={depth}",
        )

    # Every contact region must be a region of the body surface, not a proxy.
    for slot, obj in sorted(contacts.items()):
        worst = 0.0
        for vertex in obj.Shape.Vertexes:
            worst = max(worst, surface_distance(document, vertex.Point))
        check(
            f"{slot} region lies on the body surface",
            worst < 0.01,
            f"max distance to body = {worst:.5f} mm",
        )

    print("edit: pocket-40 floor depth 40 -> 34 mm", flush=True)
    floor = document.getObject("Floor_pocket_40")
    before = {slot: round(float(obj.Shape.BoundBox.YLength), 3) for slot, obj in contacts.items()}
    floor.Placement.Base.y = floor.Placement.Base.y - 6.0
    document.recompute()
    after = {slot: round(float(obj.Shape.BoundBox.YLength), 3) for slot, obj in contacts.items()}
    check(
        "the depth edit moves the intended pocket region",
        abs(after["pocket-40"] - (before["pocket-40"] - 6.0)) < 0.05,
        f"{before['pocket-40']} -> {after['pocket-40']} mm",
    )
    check(
        "unrelated pocket regions keep their depth",
        all(abs(after[slot] - before[slot]) < 0.05 for slot in ("pocket-25", "pocket-32")),
        f"pocket-25={after['pocket-25']} pocket-32={after['pocket-32']}",
    )
    # Station 3 sits at 0.74 of the opening-to-floor depth: 34 mm now, not 40.
    station = document.getObject("Station3_pocket_40").Placement.Base.y
    check(
        "the inner pocket stations follow the floor",
        abs(station - (-28.5 + 0.74 * 34.0)) < 1e-6,
        f"Station3 y = {station:.3f} mm",
    )
    floor.Placement.Base.y = floor.Placement.Base.y + 6.0
    document.recompute()

    print("edit: right lower-flank pole x 55 -> 53 mm", flush=True)
    outline.setDatum("LowerFlankP1X", App.Units.Quantity("53 mm"))
    document.recompute()
    box = document.getObject("Body").Shape.BoundBox
    poles = [
        (round(p.x, 6), round(p.y, 6))
        for i, g in enumerate(outline.Geometry)
        if not outline.getConstruction(i)
        for p in g.getPoles()
    ]
    mirrored = {(-x, y) for x, y in poles}
    check(
        "a right-hand outline edit is mirrored on the left",
        (-53.0, -17.0 + 92.0) in {(x, y) for x, y in poles} and mirrored == set(poles),
        f"outline x span {box.XMin:.3f}..{box.XMax:.3f}",
    )
    worst = max(surface_distance(document, v.Point) for v in contacts["jug"].Shape.Vertexes)
    check(
        "the jug survives an outline edit",
        len(contacts["jug"].Shape.Faces) == jug_faces and worst < 0.01,
        f"{len(contacts['jug'].Shape.Faces)} faces, max distance to body {worst:.5f} mm",
    )
    outline.setDatum("LowerFlankP1X", App.Units.Quantity("55 mm"))
    document.recompute()

    print("edit: crown centre height 87 -> 86 mm", flush=True)
    outline.setDatum("CrownP3Z", App.Units.Quantity(f"{86 + 92} mm"))
    document.recompute()
    jug = contacts["jug"].Shape
    worst = max(surface_distance(document, v.Point) for v in jug.Vertexes)
    crown = outline.Geometry[6]  # RightCrown: its interior poles still reach z 87
    crown_top = max(
        outline.Placement.multVec(crown.value(crown.FirstParameter + (crown.LastParameter - crown.FirstParameter) * k / 200)).z
        for k in range(201)
    )
    check(
        "the jug follows a crown edit",
        len(jug.Faces) == jug_faces and abs(jug.optimalBoundingBox().ZMax - crown_top) < 0.01 and crown_top < 86.5 and worst < 0.01,
        f"{len(jug.Faces)} faces, z max {jug.optimalBoundingBox().ZMax:.3f} (crown {crown_top:.3f}), max distance to body {worst:.5f} mm",
    )
    outline.setDatum("CrownP3Z", App.Units.Quantity(f"{87 + 92} mm"))
    document.recompute()

    # The same node must still serve both physical contacts of a slot: the
    # board's two instances map the slot to distinct contacts, and the slot
    # declares exactly one node.
    descriptor = json.loads(
        (REPOSITORY / "Hangboards" / "metolius-rock-rings-3d" / "assets" / "primary.model.json").read_text()
    )
    instances = board["presentations"][0]["media"]["instances"]
    left = instances[0]["contactIDsBySlotID"]
    right = instances[1]["contactIDsBySlotID"]
    shared = [
        slot
        for slot in descriptor["contactSlots"]
        if left.get(slot) != right.get(slot)
        and descriptor["contactSlots"][slot]["nodeIDs"] == [contacts[slot].NodeID]
    ]
    check(
        "each slot node serves both left and right contacts",
        len(shared) == 4,
        f"slots={sorted(shared)}",
    )

    check(
        "source bytes are unchanged by reopen and edits",
        hashlib.sha256(source.read_bytes()).hexdigest() == original_digest,
    )

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed:", flush=True)
        for label in FAILURES:
            print(f"  - {label}", flush=True)
        return 1
    print("\nall native source checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
