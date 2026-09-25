"""Genuine native checks for the metolius-prime-rib FCStd source.

Run under FreeCAD's own interpreter:

    python3 Tools/HangboardCAD/run_freecad.py \
      Tools/HangboardCAD/tests/prime_rib_native_source_checks.py \
      Hangboards/metolius-prime-rib/metolius-prime-rib.FCStd

The profile is authored from vector primitives (lines, tangent arcs and two
cubic Bezier spans) with named driving dimensions, so the edits below are made
through those names rather than through vertex indices. Exit status is non-zero
if any check fails.
"""

from __future__ import annotations

import hashlib
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
PUBLISHED = {"edge-15": 15.0, "edge-23": 23.0, "edge-38": 38.1}


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}", flush=True)
    if not condition:
        FAILURES.append(label)


def contacts(document):
    return {
        obj.ContactID: obj
        for obj in document.Objects
        if "NodeID" in obj.PropertiesList and getattr(obj, "NodeRole", "") == "contact"
    }


def spans(document) -> dict[str, tuple[float, float, float]]:
    out = {}
    for contact_id, obj in contacts(document).items():
        box = obj.Shape.optimalBoundingBox()
        out[contact_id] = (round(box.YLength, 3), round(box.ZLength, 3), round(box.XLength, 3))
    return out


def surface_gap(body, obj) -> float:
    worst = 0.0
    for face in obj.Shape.Faces:
        u0, u1, v0, v1 = face.ParameterRange
        for s in (0.1, 0.5, 0.9):
            for t in (0.1, 0.5, 0.9):
                point = face.valueAt(u0 + s * (u1 - u0), v0 + t * (v1 - v0))
                worst = max(worst, body.Shape.distToShape(Part.Vertex(point))[0])
    return worst


def constraint_index(sketch, name: str):
    for index, constraint in enumerate(sketch.Constraints):
        if constraint.Name == name:
            return index
    return None


def main() -> int:
    source = Path(sys.argv[1]).resolve()
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()

    document = App.openDocument(str(source))
    document.recompute()
    print("reopen and recompute", flush=True)
    stale = [o.Name for o in document.Objects if {"Invalid", "Error", "Touched"} & set(o.State)]
    check("every object recomputes", not stale, f"{stale}")
    sketch = document.getObject("Profile")
    pad = document.getObject("Pad")
    body = document.getObject("EndRoundover")
    check("sketch/pad/end round-over present", all((sketch, pad, body)))
    check("profile sketch is fully constrained", bool(sketch.FullyConstrained))
    kinds = sorted(
        type(g).__name__
        for i, g in enumerate(sketch.Geometry)
        if not sketch.getConstruction(i)
    )
    check(
        "profile is vector primitives, not a polyline",
        kinds.count("LineSegment") == 11
        and kinds.count("ArcOfCircle") == 12
        and kinds.count("BSplineCurve") == 2
        and len(kinds) == 25,
        f"{ {k: kinds.count(k) for k in set(kinds)} }",
    )
    for name in ("BoardThickness", "BoardHeight", "Edge15Depth", "Edge23Depth", "CrestRadius"):
        check(f"named dimension {name} exists", constraint_index(sketch, name) is not None)
    check(
        "curved-region partition is opted in",
        bool(getattr(document, "HangTenCurvedRegionPartition", False)),
    )

    box = body.Shape.optimalBoundingBox()
    check(
        "body occupies the published native envelope (508 x 38.1 x 106.68 mm)",
        abs(box.XMin + 254) < 1e-3 and abs(box.XMax - 254) < 1e-3
        and abs(box.YMin + 38.1) < 1e-3 and abs(box.YMax) < 1e-3
        and abs(box.ZMin) < 1e-3 and abs(box.ZMax - 106.68) < 1e-3,
        f"({box.XMin:.3f},{box.YMin:.3f},{box.ZMin:.3f})-({box.XMax:.3f},{box.YMax:.3f},{box.ZMax:.3f})",
    )
    before = spans(document)
    check("bound contact inventory", sorted(before) == sorted(PUBLISHED), f"{sorted(before)}")
    for contact_id, depth in PUBLISHED.items():
        check(
            f"{contact_id} depth matches its published grip depth",
            abs(before[contact_id][0] - depth) < 0.01,
            f"authored={before[contact_id][0]}",
        )
    for contact_id, obj in contacts(document).items():
        gap = surface_gap(body, obj)
        check(f"{contact_id} surface lies on the board surface", gap < 1e-3, f"max {gap:.6f} mm")

    print("edit 1: pad length 508 -> 600 mm", flush=True)
    pad.Length = 600.0
    document.recompute()
    after = spans(document)
    check(
        "length edit reaches the body",
        abs(body.Shape.optimalBoundingBox().XLength - 600.0) < 1e-3,
    )
    for contact_id in PUBLISHED:
        check(
            f"{contact_id} follows the length edit inside the end round-over",
            abs(after[contact_id][2] - (600.0 - 2 * 1.2)) < 1e-3
            and after[contact_id][:2] == before[contact_id][:2],
            f"{after[contact_id]}",
        )
    pad.Length = 508.0
    document.recompute()

    print("edit 2: Edge23Depth 23 -> 26 mm", flush=True)
    index = constraint_index(sketch, "Edge23Depth")
    sketch.setDatum(index, App.Units.Quantity("26.0 mm"))
    document.recompute()
    after = spans(document)
    check(
        "Edge23Depth edit deepens the edge-23 contact",
        abs(after["edge-23"][0] - 26.0) < 0.01,
        f"{before['edge-23'][0]} -> {after['edge-23'][0]}",
    )
    check(
        "unrelated contacts keep their depth",
        after["edge-15"] == before["edge-15"] and after["edge-38"] == before["edge-38"],
        f"edge-15={after['edge-15']} edge-38={after['edge-38']}",
    )
    for contact_id, obj in contacts(document).items():
        gap = surface_gap(body, obj)
        check(f"{contact_id} still lies on the board surface after the edit", gap < 1e-3, f"max {gap:.6f} mm")
    stale = [o.Name for o in document.Objects if {"Invalid", "Error", "Touched"} & set(o.State)]
    check("every object recomputes after the profile edit", not stale, f"{stale}")
    sketch.setDatum(index, App.Units.Quantity("23.0 mm"))
    document.recompute()

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
