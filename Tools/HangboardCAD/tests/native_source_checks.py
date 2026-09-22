"""Genuine native checks for an authored FCStd source document.

Run under FreeCAD's own interpreter:

    HANGTEN_CAD_PYTHONPATH=<extra> \
      /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
      Tools/HangboardCAD/tests/native_source_checks.py <path-to.FCStd>

Each check reopens the saved document in a fresh process, recomputes it, and
exercises a real edit. Exit status is non-zero if any check fails, so a pytest
wrapper can invoke this as a subprocess.
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
import Sketcher  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}", flush=True)
    if not condition:
        FAILURES.append(label)


def bound_objects(document):
    return [
        obj
        for obj in document.Objects
        if "NodeID" in obj.PropertiesList and getattr(obj, "NodeID", "")
    ]


def contact_spans(document) -> dict[str, tuple[float, float, float]]:
    spans = {}
    for obj in bound_objects(document):
        if obj.NodeRole != "contact":
            continue
        box = obj.Shape.BoundBox
        spans[obj.ContactID] = (round(box.YLength, 3), round(box.ZLength, 3), round(box.XLength, 3))
    return spans


def main() -> int:
    source = Path(sys.argv[1]).resolve()
    original_bytes = source.read_bytes()
    original_digest = hashlib.sha256(original_bytes).hexdigest()

    document = App.openDocument(str(source))
    document.recompute()

    print("reopen and recompute", flush=True)
    check("source document reopens", document is not None)
    body = document.getObject("Body")
    sketch = document.getObject("Profile")
    pad = document.getObject("Pad")
    check("body/pad/sketch present", all((body, sketch, pad)))
    check("profile sketch is fully constrained", bool(sketch.FullyConstrained))
    check("pad recomputes a solid", pad.Shape.Volume > 0, f"volume={pad.Shape.Volume:.1f} mm^3")

    box = pad.Shape.BoundBox
    check(
        "pad occupies the native frame",
        abs(box.XMin + 275) < 0.05
        and abs(box.XMax - 275) < 0.05
        and abs(box.YMin + 50) < 0.05
        and abs(box.YMax) < 0.05
        and abs(box.ZMin) < 0.05
        and abs(box.ZMax - 130) < 0.05,
        f"({box.XMin:.2f},{box.YMin:.2f},{box.ZMin:.2f})-({box.XMax:.2f},{box.YMax:.2f},{box.ZMax:.2f})",
    )

    nodes = bound_objects(document)
    roles = sorted((obj.NodeID, obj.NodeRole, getattr(obj, "ContactID", "")) for obj in nodes)
    check("bound node inventory", len(nodes) == 4, f"{roles}")

    spans = contact_spans(document)
    expected_depth = {"edge-10": 10.0, "edge-20": 20.0, "edge-45": 45.0}
    for contact_id, depth in sorted(expected_depth.items()):
        check(
            f"{contact_id} contact depth matches its published grip depth",
            contact_id in spans and abs(spans[contact_id][0] - depth) < 0.1,
            f"authored={spans.get(contact_id)} published={depth}",
        )

    # Every contact surface must be a subset of the body surface, not a floating
    # proxy: sample contact vertices and measure their distance to the solid.
    for obj in nodes:
        if obj.NodeRole != "contact":
            continue
        worst = 0.0
        for vertex in obj.Shape.Vertexes:
            distance = pad.Shape.distToShape(Part.Vertex(vertex.Point))[0]
            worst = max(worst, distance)
        check(
            f"{obj.ContactID} surface lies on the board surface",
            worst < 0.01,
            f"max distance to solid = {worst:.5f} mm",
        )

    print("edit 1: pad length 550 -> 620 mm", flush=True)
    before_profile = contact_spans(document)
    pad.Length = 620.0
    document.recompute()
    box = pad.Shape.BoundBox
    check("pad length edit changes the body", abs(box.XLength - 620.0) < 0.05, f"XLength={box.XLength:.2f}")
    after_length = contact_spans(document)
    for contact_id in expected_depth:
        check(
            f"{contact_id} follows the pad length edit",
            abs(after_length[contact_id][2] - 620.0) < 0.05,
            f"contact XLength={after_length[contact_id][2]}",
        )
    for contact_id in expected_depth:
        check(
            f"{contact_id} cross-section unchanged by the length edit",
            after_length[contact_id][:2] == before_profile[contact_id][:2],
        )
    pad.Length = 550.0
    document.recompute()

    print("edit 2: profile dimension at the deepest profile vertex 50 -> 56 mm", flush=True)
    deepest = max(range(sketch.GeometryCount), key=lambda i: sketch.Geometry[i].StartPoint.x)
    target = None
    for index, constraint in enumerate(sketch.Constraints):
        if (
            constraint.Type == "DistanceX"
            and constraint.First == deepest
            and constraint.FirstPos == 1
        ):
            target = index
    check(
        "found the deepest-vertex driving dimension",
        target is not None,
        f"constraint={target} vertex={deepest} x={sketch.Geometry[deepest].StartPoint.x:.3f}",
    )
    if target is not None:
        before = contact_spans(document)
        sketch.setDatum(target, App.Units.Quantity("56.0 mm"))
        document.recompute()
        after = contact_spans(document)
        check(
            "profile dimension edit moves the edge-45 contact surface",
            after["edge-45"][0] > before["edge-45"][0] + 5.0,
            f"{before['edge-45'][0]:.2f} -> {after['edge-45'][0]:.2f} mm",
        )
        check(
            "unrelated contacts keep their measured depth",
            abs(after["edge-10"][0] - 10.0) < 0.1 and abs(after["edge-20"][0] - 20.0) < 0.1,
            f"edge-10={after['edge-10'][0]:.2f} edge-20={after['edge-20'][0]:.2f}",
        )
        for obj in nodes:
            if obj.NodeRole != "contact":
                continue
            worst = max(
                pad.Shape.distToShape(Part.Vertex(vertex.Point))[0] for vertex in obj.Shape.Vertexes
            )
            check(
                f"{obj.ContactID} still lies on the board surface after the edit",
                worst < 0.01,
                f"max distance = {worst:.5f} mm",
            )
        sketch.setDatum(target, App.Units.Quantity("50.0 mm"))
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
