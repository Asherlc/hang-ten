"""One-off migration: author Hangboards/metolius-prime-rib/metolius-prime-rib.FCStd natively.

This script is a MIGRATION TOOL, not a build input. The saved FCStd must stand
alone: the shared compiler never runs this file, and nothing here is required to
rebuild the published runtime asset.

Acceptance bar (declared up front): the Prime Rib is a constant cross-section
board (three full-width rungs), so it is a swept profile, not a sculpted shell.
The reference cross-section is constant along X from -252.8 to +252.8 mm with a
1.2 mm round-over on both end perimeters; the only other features in the
reference body are the four flat mounting-bore cap patches left by
``Tools/HangboardModels/mounting_bore_repairs.json`` (x = +/-223 mm), which this
source deliberately does not author (screw-hole/hardware omission policy).

Provenance of every number written into the document:

* PUBLISHED (manufacturer page https://www.metoliusclimbing.com/products/prime-rib,
  "Specs & Details", fetched 2026-09-24; mirrored in ``board.json``):
  size 20" x 4.2" x 1.5" (50.8 x 10.66 x 3.8 cm) -> 508 x 106.68 x 38.1 mm, and
  edge depths 38 / 23 / 15 mm. The 38 mm top edge spans the full 1.5" (38.1 mm)
  board thickness; the compiler's published-depth gate tolerates the 0.1 mm.
* MEASURED from the approved reference asset, resolved from Git (never from the
  live runtime path), and then AUTHORED AS VECTOR PRIMITIVES: the end-cap
  boundary of the reference body is exactly (to <= 0.001 mm on every measured
  vertex) a chain of 11 straight lines, 12 tangent circular arcs and two cubic
  Bezier spans with round-number control points. Those primitives, their
  tangencies and their dimensions are what this script authors; no mesh vertex
  is copied into the sketch. The script re-measures the reference and refuses to
  save if any reference profile vertex lies more than
  ``PROFILE_FIT_TOLERANCE_MM`` from the authored sketch.
* The two top-surface spans (the rear lip and the shallow dip behind the top
  rung's crest) are genuinely free-form in the reference: no circle fits them
  (best single-arc residual 0.3-1.1 mm) but a cubic Bezier with round-number
  poles reproduces every sampled vertex to 6e-5 mm. They are authored as
  Sketcher B-splines (degree 3, clamped, unit weights), i.e. true Beziers, with
  every pole dimensioned. No polyline is used anywhere in the profile.
* Contact runs are the reference contact nodes' own profile runs (each spans
  X -252.8..+252.8, the prismatic span inside the end round-overs):
  edge-15: front face from the bottom round to the 15 mm slot's back-wall fillet;
  edge-23: same for the 23 mm slot; edge-38: front face above the top rung's
  lower nose, the crest, the top surface and the rear top round.
* Display material (``prime_rib_neutral_wood``, roughness 0.58, metallic 0) and
  its texture are carried over from the reference; base colour
  ``0.72,0.55,0.36`` is a stated display choice (same as the pilot).

The result is a measured, vector-authored approximation of a display mesh. It is
NOT recovered manufacturing geometry, and nothing here supports a product-
accuracy or load-bearing claim.

Sketch frame: local (u, v) maps to native (x, y, z) = (0, -u, v). u is the
distance from the back (wall) face toward the front, v the height above the
bottom face, so every authored coordinate and every driving dimension is
positive. Note on Sketcher sign semantics (verified on FreeCAD 1.1.3):
``DistanceX(g1, p1, g2, p2, d)`` solves ``x(g2.p2) - x(g1.p1) = d``, so the
argument ORDER sets the sign; ``DistanceX(point, -1, 1, d)`` therefore puts the
point at x = -d. Every dimension here is written low -> high.
"""

from __future__ import annotations

import json
import math
import os
import sys
import zipfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    part
    for part in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep)
    if part
]
# Shared helpers live one level up, next to compile_board.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
import Sketcher  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

from reference import load_reference  # noqa: E402

PACKAGE = "metolius-prime-rib"
BOARD_JSON = REPOSITORY / "Hangboards" / PACKAGE / "board.json"
DESTINATION = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
SCRATCH = Path(
    os.environ.get("HANGTEN_CAD_SCRATCH", str(REPOSITORY / ".context" / f"freecad-{PACKAGE}"))
)
BODY_PRIM = "/root/body/body_mesh_001"
CONTACT_PRIMS = {
    "edge-15": "/root/edge_15/edge_15_mesh_001",
    "edge-23": "/root/edge_23/edge_23_mesh_001",
    "edge-38": "/root/edge_38/edge_38_mesh_001",
}
PROFILE_FIT_TOLERANCE_MM = 0.01

# --- Published facts (manufacturer page and board.json) --------------------
INCH = 25.4
BOARD_WIDTH = 20.0 * INCH  # 508.0
BOARD_HEIGHT = 4.2 * INCH  # 106.68
BOARD_THICKNESS = 1.5 * INCH  # 38.1
GRIP_DEPTH_MM = {"edge-38": 38.0, "edge-23": 23.0, "edge-15": 15.0}

# --- Measured, authored as named driving dimensions (mm) --------------------
END_ROUNDOVER_RADIUS = 1.2
EDGE15_LEDGE_HEIGHT = 18.0  # bottom face -> 15 mm edge ledge
EDGE15_SLOT_HEIGHT = 21.0  # 15 mm ledge -> underside of the middle rung
MIDDLE_RUNG_THICKNESS = 18.0  # underside of the middle rung -> 23 mm ledge
EDGE23_SLOT_HEIGHT = 26.0  # 23 mm ledge -> underside of the top rung
REAR_TOP_HEIGHT = 103.0  # top surface height at the back edge
TOP_DIP_JOIN_DEPTH = 6.0  # rear-lip / dip Bezier join, from the back face
RADII = {
    "BackBottomRadius": 2.0,
    "FrontBottomRadius": 2.0,
    "Edge15LipRadius": 2.2,
    "Edge15SlotFloorFilletRadius": 3.4,
    "Edge15SlotCeilingFilletRadius": 3.4,
    "MiddleRungNoseRadius": 2.6,
    "Edge23LipRadius": 3.5,
    "Edge23SlotFloorFilletRadius": 6.0,
    "Edge23SlotCeilingFilletRadius": 6.0,
    "TopRungNoseRadius": 4.0,
    "CrestRadius": 7.5,
    "BackTopRadius": 2.0,
}
# Bezier handle dimensions (pole offsets), measured and rounded to the 0.1 mm the
# reference poles sit on.
REAR_LIP_HANDLE_OUT = 1.1  # rear-top round -> first pole, along u
REAR_LIP_HANDLE_IN = 1.5  # second pole -> dip join, along u
DIP_HANDLE_OUT = 9.0  # dip join -> first dip pole, along u
DIP_HANDLE_DROP = 1.5  # dip join height - first dip pole height
DIP_HANDLE_IN = 6.6  # second dip pole -> crest top, along u

MATERIAL_NAME = "prime_rib_neutral_wood"
MATERIAL_BASE_COLOR = "0.72,0.55,0.36"
MATERIAL_ROUGHNESS = 0.58
MATERIAL_METALLIC = 0.0


def _derived_profile():
    """Every profile coordinate, derived from the named dimensions above."""
    t = BOARD_THICKNESS
    r = RADII
    wall15 = t - GRIP_DEPTH_MM["edge-15"]  # 23.1
    wall23 = t - GRIP_DEPTH_MM["edge-23"]  # 15.1
    ledge15 = EDGE15_LEDGE_HEIGHT
    under23 = ledge15 + EDGE15_SLOT_HEIGHT
    ledge23 = under23 + MIDDLE_RUNG_THICKNESS
    under38 = ledge23 + EDGE23_SLOT_HEIGHT
    top = BOARD_HEIGHT
    crest_c = (t - r["CrestRadius"], top - r["CrestRadius"])
    join = (TOP_DIP_JOIN_DEPTH, REAR_TOP_HEIGHT)
    rear_start = (r["BackTopRadius"], REAR_TOP_HEIGHT)
    dip_p1 = (join[0] + DIP_HANDLE_OUT, join[1] - DIP_HANDLE_DROP)
    # G1 at the join: the rear-lip's last handle is collinear with the dip's first.
    slope = (join[1] - dip_p1[1]) / (join[0] - dip_p1[0])
    rear_p2 = (join[0] - REAR_LIP_HANDLE_IN, join[1] - slope * REAR_LIP_HANDLE_IN)
    return {
        "t": t, "wall15": wall15, "wall23": wall23, "ledge15": ledge15,
        "under23": under23, "ledge23": ledge23, "under38": under38, "top": top,
        "crest_c": crest_c, "join": join, "rear_start": rear_start,
        "rear_poles": [
            rear_start,
            (rear_start[0] + REAR_LIP_HANDLE_OUT, rear_start[1]),
            rear_p2,
            join,
        ],
        "dip_poles": [
            join,
            dip_p1,
            (crest_c[0] - DIP_HANDLE_IN, top),
            (crest_c[0], top),
        ],
    }


def _world_points(stage, cache, path: str):
    prim = stage.GetPrimAtPath(path)
    mesh = UsdGeom.Mesh(prim)
    matrix = cache.GetLocalToWorldTransform(prim)
    out = []
    for point in mesh.GetPointsAttr().Get():
        world = matrix.Transform(point) * 1000.0
        out.append((world[0], -world[2], world[1]))
    return out


def _reference_texture(reference: Path) -> tuple[str, Path]:
    with zipfile.ZipFile(reference) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".png")]
        if len(names) != 1:
            raise ValueError(f"expected exactly one reference texture, found {names}")
        data = archive.read(names[0])
    SCRATCH.mkdir(parents=True, exist_ok=True)
    target = SCRATCH / os.path.basename(names[0])
    target.write_bytes(data)
    return os.path.basename(names[0]), target


def _apply_material(obj, texture_source: Path | None) -> None:
    obj.addProperty("App::PropertyString", "MaterialName", "HangTen")
    obj.addProperty("App::PropertyString", "BaseColor", "HangTen")
    obj.addProperty("App::PropertyFloat", "Roughness", "HangTen")
    obj.addProperty("App::PropertyFloat", "Metallic", "HangTen")
    if texture_source is not None:
        obj.addProperty("App::PropertyFileIncluded", "TextureFile", "HangTen")
    obj.MaterialName = MATERIAL_NAME
    obj.BaseColor = MATERIAL_BASE_COLOR
    obj.Roughness = MATERIAL_ROUGHNESS
    obj.Metallic = MATERIAL_METALLIC
    if texture_source is not None:
        obj.TextureFile = str(texture_source)


class ProfileBuilder:
    """Collects sketch primitives in traversal order with their traversal ends."""

    def __init__(self) -> None:
        self.geometry: list = []
        self.names: list[str] = []
        # (start_pos, end_pos) in traversal order; sketch arcs are always CCW.
        self.ends: list[tuple[int, int]] = []
        self.kind: list[str] = []
        self.arc_sense: list[str] = []

    # Lines and Beziers are stored against the (clockwise) traversal, i.e. in the
    # same sense as the sketch's always-CCW convex arcs. An extruded sketch edge's
    # face normal follows the edge's stored direction, so this makes every
    # extruded region face point out of the board except the concave slot
    # fillets, which the region construction reverses explicitly.
    def line(self, name: str, p, q) -> int:
        self.geometry.append(Part.LineSegment(App.Vector(*q, 0), App.Vector(*p, 0)))
        self.names.append(name)
        self.ends.append((2, 1))
        self.kind.append("line")
        self.arc_sense.append("")
        return len(self.geometry) - 1

    def arc(self, name: str, center, radius: float, p, q, clockwise: bool) -> int:
        a_p = math.atan2(p[1] - center[1], p[0] - center[0])
        a_q = math.atan2(q[1] - center[1], q[0] - center[0])
        first, second = (a_q, a_p) if clockwise else (a_p, a_q)
        while second <= first:
            second += 2.0 * math.pi
        circle = Part.Circle(App.Vector(*center, 0), App.Vector(0, 0, 1), radius)
        self.geometry.append(Part.ArcOfCircle(circle, first, second))
        self.names.append(name)
        self.ends.append((2, 1) if clockwise else (1, 2))
        self.kind.append("arc")
        # The traversal is clockwise, so a clockwise arc is a convex corner.
        self.arc_sense.append("convex" if clockwise else "concave")
        return len(self.geometry) - 1

    def bezier(self, name: str, poles) -> int:
        curve = Part.BSplineCurve()
        curve.buildFromPolesMultsKnots(
            [App.Vector(*pole, 0) for pole in reversed(poles)], [4, 4], [0.0, 1.0], False, 3
        )
        self.geometry.append(curve)
        self.names.append(name)
        self.ends.append((2, 1))
        self.kind.append("bezier")
        self.arc_sense.append("")
        return len(self.geometry) - 1


def _author_profile(sketch, dims) -> dict:
    """Author the closed profile as named, fully constrained vector primitives.

    Traversal is clockwise in (u, v): up the back face, forward across the top,
    down the front and back along the bottom.
    """
    t, r = dims["t"], RADII
    b = ProfileBuilder()
    g = {}
    g["BackFace"] = b.line("BackFace", (0.0, 2.0), (0.0, 101.0))
    g["BackTopRound"] = b.arc("BackTopRound", (2.0, 101.0), r["BackTopRadius"], (0.0, 101.0), dims["rear_start"], True)
    g["RearLipCurve"] = b.bezier("RearLipCurve", dims["rear_poles"])
    g["TopDipCurve"] = b.bezier("TopDipCurve", dims["dip_poles"])
    g["Crest"] = b.arc("Crest", dims["crest_c"], r["CrestRadius"], (dims["crest_c"][0], dims["top"]), (t, dims["crest_c"][1]), True)
    g["TopRungFront"] = b.line("TopRungFront", (t, dims["crest_c"][1]), (t, dims["under38"] + r["TopRungNoseRadius"]))
    nose38 = (t - r["TopRungNoseRadius"], dims["under38"] + r["TopRungNoseRadius"])
    g["TopRungNose"] = b.arc("TopRungNose", nose38, r["TopRungNoseRadius"], (t, nose38[1]), (nose38[0], dims["under38"]), True)
    c23u = (dims["wall23"] + r["Edge23SlotCeilingFilletRadius"], dims["under38"] - r["Edge23SlotCeilingFilletRadius"])
    g["TopRungUnderside"] = b.line("TopRungUnderside", (nose38[0], dims["under38"]), (c23u[0], dims["under38"]))
    g["Edge23SlotCeilingFillet"] = b.arc("Edge23SlotCeilingFillet", c23u, r["Edge23SlotCeilingFilletRadius"], (c23u[0], dims["under38"]), (dims["wall23"], c23u[1]), False)
    c23l = (dims["wall23"] + r["Edge23SlotFloorFilletRadius"], dims["ledge23"] + r["Edge23SlotFloorFilletRadius"])
    g["Edge23BackWall"] = b.line("Edge23BackWall", (dims["wall23"], c23u[1]), (dims["wall23"], c23l[1]))
    g["Edge23SlotFloorFillet"] = b.arc("Edge23SlotFloorFillet", c23l, r["Edge23SlotFloorFilletRadius"], (dims["wall23"], c23l[1]), (c23l[0], dims["ledge23"]), False)
    lip23 = (t - r["Edge23LipRadius"], dims["ledge23"] - r["Edge23LipRadius"])
    g["Edge23Ledge"] = b.line("Edge23Ledge", (c23l[0], dims["ledge23"]), (lip23[0], dims["ledge23"]))
    g["Edge23Lip"] = b.arc("Edge23Lip", lip23, r["Edge23LipRadius"], (lip23[0], dims["ledge23"]), (t, lip23[1]), True)
    nose23 = (t - r["MiddleRungNoseRadius"], dims["under23"] + r["MiddleRungNoseRadius"])
    g["MiddleRungFront"] = b.line("MiddleRungFront", (t, lip23[1]), (t, nose23[1]))
    g["MiddleRungNose"] = b.arc("MiddleRungNose", nose23, r["MiddleRungNoseRadius"], (t, nose23[1]), (nose23[0], dims["under23"]), True)
    c15u = (dims["wall15"] + r["Edge15SlotCeilingFilletRadius"], dims["under23"] - r["Edge15SlotCeilingFilletRadius"])
    g["MiddleRungUnderside"] = b.line("MiddleRungUnderside", (nose23[0], dims["under23"]), (c15u[0], dims["under23"]))
    g["Edge15SlotCeilingFillet"] = b.arc("Edge15SlotCeilingFillet", c15u, r["Edge15SlotCeilingFilletRadius"], (c15u[0], dims["under23"]), (dims["wall15"], c15u[1]), False)
    c15l = (dims["wall15"] + r["Edge15SlotFloorFilletRadius"], dims["ledge15"] + r["Edge15SlotFloorFilletRadius"])
    g["Edge15BackWall"] = b.line("Edge15BackWall", (dims["wall15"], c15u[1]), (dims["wall15"], c15l[1]))
    g["Edge15SlotFloorFillet"] = b.arc("Edge15SlotFloorFillet", c15l, r["Edge15SlotFloorFilletRadius"], (dims["wall15"], c15l[1]), (c15l[0], dims["ledge15"]), False)
    lip15 = (t - r["Edge15LipRadius"], dims["ledge15"] - r["Edge15LipRadius"])
    g["Edge15Ledge"] = b.line("Edge15Ledge", (c15l[0], dims["ledge15"]), (lip15[0], dims["ledge15"]))
    g["Edge15Lip"] = b.arc("Edge15Lip", lip15, r["Edge15LipRadius"], (lip15[0], dims["ledge15"]), (t, lip15[1]), True)
    fb = (t - r["FrontBottomRadius"], r["FrontBottomRadius"])
    g["BottomRungFront"] = b.line("BottomRungFront", (t, lip15[1]), (t, fb[1]))
    g["FrontBottomRound"] = b.arc("FrontBottomRound", fb, r["FrontBottomRadius"], (t, fb[1]), (fb[0], 0.0), True)
    bb = (r["BackBottomRadius"], r["BackBottomRadius"])
    g["BottomFace"] = b.line("BottomFace", (fb[0], 0.0), (bb[0], 0.0))
    g["BackBottomRound"] = b.arc("BackBottomRound", bb, r["BackBottomRadius"], (bb[0], 0.0), (0.0, bb[1]), True)

    count = len(b.geometry)
    ids = sketch.addGeometry(b.geometry, False)
    if list(ids) != list(range(count)):
        raise ValueError(f"unexpected sketch geometry ids {ids}")

    def named(constraint, name: str) -> int:
        index = sketch.addConstraint(constraint)
        sketch.renameConstraint(index, name)
        return index

    # Every joint is G1: an endpoint-to-endpoint Tangent is coincidence plus
    # tangency, so the profile is one smooth closed chain.
    for i in range(count):
        j = (i + 1) % count
        sketch.addConstraint(Sketcher.Constraint("Tangent", i, b.ends[i][1], j, b.ends[j][0]))
    for name in ("BackFace", "TopRungFront", "Edge23BackWall", "MiddleRungFront", "Edge15BackWall", "BottomRungFront"):
        sketch.addConstraint(Sketcher.Constraint("Vertical", g[name]))
    for name in ("TopRungUnderside", "Edge23Ledge", "MiddleRungUnderside", "Edge15Ledge", "BottomFace"):
        sketch.addConstraint(Sketcher.Constraint("Horizontal", g[name]))
    # The three rung fronts are one plane: the front face of the board.
    for name in ("MiddleRungFront", "TopRungFront"):
        sketch.addConstraint(Sketcher.Constraint("PointOnObject", g[name], 1, g["BottomRungFront"]))
    # Anchor: the back face on the sketch V axis, the bottom face on the H axis.
    sketch.addConstraint(Sketcher.Constraint("PointOnObject", g["BackFace"], 1, -2))
    sketch.addConstraint(Sketcher.Constraint("PointOnObject", g["BottomFace"], 1, -1))

    arc_for_radius = {
        "BackBottomRadius": "BackBottomRound",
        "FrontBottomRadius": "FrontBottomRound",
        "Edge15LipRadius": "Edge15Lip",
        "Edge15SlotFloorFilletRadius": "Edge15SlotFloorFillet",
        "Edge15SlotCeilingFilletRadius": "Edge15SlotCeilingFillet",
        "MiddleRungNoseRadius": "MiddleRungNose",
        "Edge23LipRadius": "Edge23Lip",
        "Edge23SlotFloorFilletRadius": "Edge23SlotFloorFillet",
        "Edge23SlotCeilingFilletRadius": "Edge23SlotCeilingFillet",
        "TopRungNoseRadius": "TopRungNose",
        "CrestRadius": "Crest",
        "BackTopRadius": "BackTopRound",
    }
    for name, value in RADII.items():
        named(Sketcher.Constraint("Radius", g[arc_for_radius[name]], value), name)

    start = lambda name: (g[name], b.ends[g[name]][0])  # noqa: E731
    end = lambda name: (g[name], b.ends[g[name]][1])  # noqa: E731

    def dx(a, c, value, name):
        return named(Sketcher.Constraint("DistanceX", a[0], a[1], c[0], c[1], value), name)

    def dy(a, c, value, name):
        return named(Sketcher.Constraint("DistanceY", a[0], a[1], c[0], c[1], value), name)

    dx(start("BackFace"), start("BottomRungFront"), BOARD_THICKNESS, "BoardThickness")
    dy(start("BottomFace"), start("Crest"), BOARD_HEIGHT, "BoardHeight")
    dx(start("Edge15BackWall"), start("BottomRungFront"), GRIP_DEPTH_MM["edge-15"], "Edge15Depth")
    dx(start("Edge23BackWall"), start("MiddleRungFront"), GRIP_DEPTH_MM["edge-23"], "Edge23Depth")
    dy(start("BottomFace"), start("Edge15Ledge"), EDGE15_LEDGE_HEIGHT, "Edge15LedgeHeight")
    dy(start("Edge15Ledge"), start("MiddleRungUnderside"), EDGE15_SLOT_HEIGHT, "Edge15SlotHeight")
    dy(start("MiddleRungUnderside"), start("Edge23Ledge"), MIDDLE_RUNG_THICKNESS, "MiddleRungThickness")
    dy(start("Edge23Ledge"), start("TopRungUnderside"), EDGE23_SLOT_HEIGHT, "Edge23SlotHeight")
    dy(start("BottomFace"), start("RearLipCurve"), REAR_TOP_HEIGHT, "RearTopHeight")
    dx(start("BackFace"), end("RearLipCurve"), TOP_DIP_JOIN_DEPTH, "TopDipJoinDepth")
    dy(start("BottomFace"), end("RearLipCurve"), REAR_TOP_HEIGHT, "TopDipJoinHeight")

    # Bezier poles: expose the construction pole circles, then dimension the
    # interior poles. End poles are the curve ends (already constrained above);
    # G1 at each Bezier end fixes the handle directions.
    poles = {}
    for name in ("RearLipCurve", "TopDipCurve"):
        before = sketch.GeometryCount
        sketch.exposeInternalGeometry(g[name])
        circles = [
            i for i in range(before, sketch.GeometryCount)
            if sketch.Geometry[i].TypeId == "Part::GeomCircle"
        ]
        expected = dims["rear_poles"] if name == "RearLipCurve" else dims["dip_poles"]
        ordered = []
        for pole in expected:
            match = [
                i for i in circles
                if (sketch.Geometry[i].Center - App.Vector(*pole, 0)).Length < 1e-9
            ]
            if len(match) != 1:
                raise ValueError(f"{name} pole {pole} has no unique construction circle")
            ordered.append(match[0])
        poles[name] = ordered
    rear, dip = poles["RearLipCurve"], poles["TopDipCurve"]
    dx((rear[0], 3), (rear[1], 3), REAR_LIP_HANDLE_OUT, "RearLipHandleOut")
    dx((rear[2], 3), (rear[3], 3), REAR_LIP_HANDLE_IN, "RearLipHandleIn")
    dx((dip[0], 3), (dip[1], 3), DIP_HANDLE_OUT, "TopDipHandleOut")
    dy((dip[1], 3), (dip[0], 3), DIP_HANDLE_DROP, "TopDipHandleDrop")
    dx((dip[2], 3), (dip[3], 3), DIP_HANDLE_IN, "TopDipHandleIn")
    # On FreeCAD 1.1.3 an endpoint Tangent between a circular arc and a B-spline
    # end leaves the B-spline's end handle free to rotate (one DoF per joint);
    # the Bezier-to-Bezier Tangent does bind. Both arc joints here meet the curve
    # where the arc's tangent is horizontal, so the end handles are levelled
    # explicitly. G1 at every joint is asserted numerically below.
    named(Sketcher.Constraint("Horizontal", rear[0], 3, rear[1], 3), "RearLipHandleLevel")
    named(Sketcher.Constraint("Horizontal", dip[2], 3, dip[3], 3), "TopDipHandleLevel")

    status = sketch.solve()
    if status != 0:
        raise ValueError(f"profile sketch failed to solve (status {status})")
    if not sketch.FullyConstrained:
        raise ValueError("authored profile sketch is not fully constrained")
    for i, original in enumerate(b.geometry):
        solved = sketch.Geometry[i]
        for a, c in ((original.StartPoint, solved.StartPoint), (original.EndPoint, solved.EndPoint)):
            if (a - c).Length > 1e-6:
                raise ValueError(f"{b.names[i]} moved while solving: {a} -> {c}")
    for i in range(count):
        j = (i + 1) % count
        first, second = sketch.Geometry[i], sketch.Geometry[j]
        out_param = first.LastParameter if b.ends[i][1] == 2 else first.FirstParameter
        in_param = second.FirstParameter if b.ends[j][0] == 1 else second.LastParameter
        out_dir = first.tangent(out_param)[0] * (1 if b.ends[i][1] == 2 else -1)
        in_dir = second.tangent(in_param)[0] * (1 if b.ends[j][0] == 1 else -1)
        if out_dir.getAngle(in_dir) > 1e-6:
            raise ValueError(f"{b.names[i]} -> {b.names[j]} is not tangent-continuous")
    return {"ids": g, "names": b.names, "kinds": b.kind, "arc_sense": b.arc_sense, "count": count}


def _profile_fit(sketch, reference_profile) -> float:
    wire_edges = [edge for edge in sketch.Shape.Edges]
    compound = Part.Compound(wire_edges)
    worst = 0.0
    for y, z in reference_profile:
        worst = max(worst, compound.distToShape(Part.Vertex(App.Vector(0.0, y, z)))[0])
    return worst


def main() -> int:
    board = json.loads(BOARD_JSON.read_text())
    published = {c["id"]: c["depth"]["range"]["minimum"] for c in board["contacts"]}
    if published != GRIP_DEPTH_MM:
        raise ValueError(f"board.json depths {published} disagree with {GRIP_DEPTH_MM}")
    if board["dimensions"] != "20 × 4.2 × 1.5 in":
        raise ValueError(f"board.json dimensions changed: {board['dimensions']}")

    reference, reference_digest = load_reference(PACKAGE, "primary.usdz", SCRATCH / "ref")
    stage = Usd.Stage.Open(str(reference))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    body_points = _world_points(stage, cache, BODY_PRIM)
    measured_box = [
        min(p[i] for p in body_points) for i in range(3)
    ] + [max(p[i] for p in body_points) for i in range(3)]
    expected_box = [-BOARD_WIDTH / 2, -BOARD_THICKNESS, 0.0, BOARD_WIDTH / 2, 0.0, BOARD_HEIGHT]
    if any(abs(a - e) > 0.01 for a, e in zip(measured_box, expected_box)):
        raise ValueError(f"reference envelope {measured_box} disagrees with published {expected_box}")
    prismatic = BOARD_WIDTH / 2 - END_ROUNDOVER_RADIUS
    reference_profile = sorted(
        {(round(p[1], 4), round(p[2], 4)) for p in body_points if abs(p[0] - prismatic) < 0.01}
    )
    reference_runs = {}
    for contact_id, prim in CONTACT_PRIMS.items():
        points = _world_points(stage, cache, prim)
        reference_runs[contact_id] = (
            (min(p[0] for p in points), max(p[0] for p in points)),
            (min(p[1] for p in points), max(p[1] for p in points)),
            (min(p[2] for p in points), max(p[2] for p in points)),
        )

    texture_member, texture_source = _reference_texture(reference)

    if DESTINATION.exists():
        DESTINATION.unlink()
    document = App.newDocument(PACKAGE)
    document.Label = board["name"]
    for kind, name in (
        ("App::PropertyString", "HangTenBoardID"),
        ("App::PropertyString", "HangTenPresentationID"),
        ("App::PropertyInteger", "HangTenSchemaVersion"),
        ("App::PropertyString", "HangTenSourceKind"),
        ("App::PropertyString", "HangTenCoordinateFrame"),
        ("App::PropertyFloat", "HangTenTessellationDeflection"),
    ):
        document.addProperty(kind, name, "HangTen")
    document.HangTenBoardID = board["id"]
    document.HangTenPresentationID = board["presentations"][0]["id"]
    document.HangTenSchemaVersion = 1
    document.HangTenSourceKind = "native-parametric-measured-profile"
    document.HangTenCoordinateFrame = "freecad-mm-z-up-front-negative-y"
    document.HangTenTessellationDeflection = 0.08
    # The contact runs include arcs and Bezier spans, so their body triangles are
    # chords of curved faces; opt in to the curved-region partition so the body
    # does not keep a duplicate of each curved hold surface (compile_board).
    document.addProperty("App::PropertyBool", "HangTenCurvedRegionPartition", "HangTen")
    document.HangTenCurvedRegionPartition = True

    body = document.addObject("PartDesign::Body", "Body")
    sketch = body.newObject("Sketcher::SketchObject", "Profile")
    # local X -> native -Y (toward the front), local Y -> native +Z, normal -> -X.
    frame = App.Matrix(
        0.0, 0.0, -1.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    sketch.MapMode = "Deactivated"
    sketch.AttachmentSupport = []
    sketch.Placement = App.Placement(App.Vector(0.0, 0.0, 0.0), App.Rotation(frame))
    document.recompute()
    resolved = sketch.getGlobalPlacement()
    for local, expected in (
        (App.Vector(0, 0, 0), App.Vector(0, 0, 0)),
        (App.Vector(1, 0, 0), App.Vector(0, -1, 0)),
        (App.Vector(0, 1, 0), App.Vector(0, 0, 1)),
    ):
        if (resolved.multVec(local) - expected).Length > 1e-9:
            raise ValueError("profile sketch frame does not map local (u, v) to native (0, -u, v)")

    dims = _derived_profile()
    profile = _author_profile(sketch, dims)
    document.recompute()

    fit = _profile_fit(sketch, reference_profile)
    if fit > PROFILE_FIT_TOLERANCE_MM:
        raise ValueError(
            f"authored profile deviates {fit:.4f} mm from the reference cross-section "
            f"(limit {PROFILE_FIT_TOLERANCE_MM} mm)"
        )

    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sketch
    pad.SideType = "Symmetric"
    pad.Length = BOARD_WIDTH
    document.recompute()

    end_edges = [
        f"Edge{i + 1}"
        for i, edge in enumerate(pad.Shape.Edges)
        if edge.BoundBox.XLength < 1e-6 and abs(abs(edge.BoundBox.XMin) - BOARD_WIDTH / 2) < 1e-6
    ]
    if len(end_edges) != 2 * profile["count"]:
        raise ValueError(f"expected {2 * profile['count']} end-perimeter edges, found {len(end_edges)}")
    fillet = body.newObject("PartDesign::Fillet", "EndRoundover")
    fillet.Base = (pad, end_edges)
    fillet.Radius = END_ROUNDOVER_RADIUS
    document.recompute()
    if not fillet.Shape.isValid() or fillet.Shape.Volume <= 0:
        raise ValueError("end round-over fillet did not produce a valid solid")

    # The sketch's Edge<n> sub-element names follow its Shape.Edges order (the
    # sketch sorts its output into a wire), not the geometry index. Resolve each
    # profile geometry to its shape edge by position; FreeCAD then stores the
    # binding under the geometry's element-map name, so it follows that
    # geometry through later dimension edits (checked by the native checks).
    edge_name = {}
    for i in range(profile["count"]):
        geo = sketch.Geometry[i]
        mid = geo.value((geo.FirstParameter + geo.LastParameter) / 2.0)
        expected = [
            sketch.Placement.multVec(point) for point in (geo.StartPoint, geo.EndPoint, mid)
        ]
        matches = []
        for n, edge in enumerate(sketch.Shape.Edges):
            edge_mid = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2.0)
            ends = [vertex.Point for vertex in edge.Vertexes]
            if (edge_mid - expected[2]).Length < 1e-6 and all(
                min((point - end).Length for end in ends) < 1e-6 for point in expected[:2]
            ):
                matches.append(n)
        if len(matches) != 1:
            raise ValueError(f"{profile['names'][i]} resolves to sketch edges {matches}")
        edge_name[profile["names"][i]] = f"Edge{matches[0] + 1}"

    runs = {
        "edge-38": ["TopRungFront", "Crest", "TopDipCurve", "RearLipCurve", "BackTopRound"],
        "edge-23": ["MiddleRungFront", "Edge23Lip", "Edge23Ledge", "Edge23SlotFloorFillet"],
        "edge-15": ["BottomRungFront", "Edge15Lip", "Edge15Ledge", "Edge15SlotFloorFillet"],
    }
    node_ids = {
        "edge-15": "edge_15_mesh_001",
        "edge-23": "edge_23_mesh_001",
        "edge-38": "edge_38_mesh_001",
    }
    concave = {name for name, kind in zip(profile["names"], profile["arc_sense"]) if kind == "concave"}

    def extruded_run(label: str, names: list[str]):
        binder = document.addObject("PartDesign::SubShapeBinder", f"Region_{label}")
        binder.Support = [(sketch, edge_name[name]) for name in names]
        binder.MakeFace = False
        binder.Refine = False
        extrusion = document.addObject("Part::Extrusion", f"Surface_{label}")
        extrusion.Base = binder
        extrusion.DirMode = "Custom"
        extrusion.Dir = App.Vector(1.0, 0.0, 0.0)
        extrusion.Symmetric = True
        extrusion.Solid = False
        # The region is the prismatic span of the board: it follows the pad
        # length and stops where the end round-over begins, through native
        # expressions rather than copied constants.
        extrusion.setExpression("LengthFwd", "Pad.Length - 2 * EndRoundover.Radius")
        return extrusion

    contact_objects = {}
    for contact_id, names in sorted(runs.items()):
        suffix = contact_id.replace("-", "_")
        outward = [name for name in names if name not in concave]
        inward = [name for name in names if name in concave]
        if not inward:
            contact_objects[contact_id] = extruded_run(suffix, outward)
            continue
        # A concave fillet's extruded face points into the board; reverse it
        # parametrically (Part::Reverse keeps the Source link) and combine the
        # run into one contact surface.
        forward = extruded_run(f"{suffix}_convex", outward)
        flipped = document.addObject("Part::Reverse", f"Reversed_{suffix}_fillet")
        flipped.Source = extruded_run(f"{suffix}_fillet", inward)
        combined = document.addObject("Part::Compound", f"Surface_{suffix}")
        combined.Links = [forward, flipped]
        contact_objects[contact_id] = combined
    document.recompute()
    for contact_id, obj in contact_objects.items():
        for face in obj.Shape.Faces:
            u0, u1, v0, v1 = face.ParameterRange
            u, v = (u0 + u1) / 2.0, (v0 + v1) / 2.0
            probe = face.valueAt(u, v) + face.normalAt(u, v) * 0.5
            if fillet.Shape.isInside(probe, 1e-6, True):
                raise ValueError(f"{contact_id} has a face whose normal points into the board")

    # optimalBoundingBox: the plain BoundBox of the filleted body is loose
    # (-38.72 / 107.30 mm) around the end round-over's toroidal patches.
    box = fillet.Shape.optimalBoundingBox()
    actual_box = [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]
    if any(abs(a - e) > 1e-4 for a, e in zip(actual_box, expected_box)):
        raise ValueError(f"authored body frame {actual_box} does not match {expected_box}")

    report_runs = {}
    for contact_id, extrusion in contact_objects.items():
        rbox = extrusion.Shape.optimalBoundingBox()
        ref = reference_runs[contact_id]
        authored = ((rbox.XMin, rbox.XMax), (rbox.YMin, rbox.YMax), (rbox.ZMin, rbox.ZMax))
        for axis in range(3):
            for k in range(2):
                if abs(authored[axis][k] - ref[axis][k]) > 0.01:
                    raise ValueError(f"{contact_id} run {authored} disagrees with reference {ref}")
        if abs(rbox.YLength - GRIP_DEPTH_MM[contact_id]) > 0.25:
            raise ValueError(f"{contact_id} depth {rbox.YLength:.3f} disagrees with published")
        report_runs[contact_id] = round(rbox.YLength, 3)
        for kind, name in (
            ("App::PropertyString", "NodeID"),
            ("App::PropertyString", "NodeRole"),
            ("App::PropertyString", "ContactID"),
            ("App::PropertyString", "HangTenHoldOutline"),
        ):
            extrusion.addProperty(kind, name, "HangTen")
        extrusion.NodeID = node_ids[contact_id]
        extrusion.NodeRole = "contact"
        extrusion.ContactID = contact_id
        # Front-plane (XZ) footprint of the band: the region an operator selects.
        extrusion.HangTenHoldOutline = json.dumps([
            [round(rbox.XMin, 4), round(rbox.ZMin, 4)],
            [round(rbox.XMax, 4), round(rbox.ZMin, 4)],
            [round(rbox.XMax, 4), round(rbox.ZMax, 4)],
            [round(rbox.XMin, 4), round(rbox.ZMax, 4)],
        ])
        _apply_material(extrusion, None)

    fillet.addProperty("App::PropertyString", "NodeID", "HangTen")
    fillet.addProperty("App::PropertyString", "NodeRole", "HangTen")
    fillet.NodeID = "body_mesh_001"
    fillet.NodeRole = "body"
    _apply_material(fillet, texture_source)

    document.recompute()
    stale = [obj.Name for obj in document.Objects if "Invalid" in obj.State or "Touched" in obj.State]
    if stale:
        raise ValueError(f"objects failed to recompute: {stale}")

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(DESTINATION))

    constraint_names = [c.Name for c in sketch.Constraints if c.Name]
    kinds = {k: profile["kinds"].count(k) for k in sorted(set(profile["kinds"]))}
    print(f"authored {DESTINATION} ({DESTINATION.stat().st_size} bytes)")
    print(f"reference {reference_digest} texture {texture_member}")
    print(f"profile primitives: {kinds}; named dimensions: {constraint_names}")
    print(f"reference cross-section fit: max {fit:.5f} mm over {len(reference_profile)} vertices")
    print(f"authored contact depths mm: {report_runs} (published {GRIP_DEPTH_MM})")
    print(f"body volume mm^3: {fillet.Shape.Volume:.1f} bbox: {fillet.Shape.optimalBoundingBox()}")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
