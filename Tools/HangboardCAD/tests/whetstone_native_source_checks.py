"""Reopen Whetstone, edit named native features, and verify live contact bindings.

Run with Tools/HangboardCAD/run_freecad.py. Optional argv[1] selects an FCStd.
All edits stay in memory; the source file is never saved.
"""

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part


def snapshot(body, contact, unrelated):
    return {
        "volume": body.Shape.Volume,
        "depth": contact.Shape.BoundBox.YLength,
        "area": contact.Shape.Area,
        "unrelatedArea": unrelated.Shape.Area,
    }


def assert_on_boundary(region, body):
    boundary = Part.makeShell(body.Shape.Faces)
    assert not region.Shape.Solids, "contact regions must be open surfaces"
    for face in region.Shape.Faces:
        u0, u1, v0, v1 = face.ParameterRange
        for u_fraction, v_fraction in ((0.25, 0.25), (0.5, 0.5), (0.75, 0.75)):
            u = u0 + (u1 - u0) * u_fraction
            v = v0 + (v1 - v0) * v_fraction
            if face.isPartOfDomain(u, v):
                distance = boundary.distToShape(Part.Vertex(face.valueAt(u, v)))[0]
                assert distance < 1e-5, (region.Name, distance)
                point = face.valueAt(u, v)
                normal = face.normalAt(u, v)
                matches = []
                for body_face in body.Shape.Faces:
                    box = body_face.BoundBox
                    box.enlarge(1e-5)
                    if not box.isInside(point):
                        continue
                    if body_face.distToShape(Part.Vertex(point))[0] < 1e-5:
                        bu, bv = body_face.Surface.parameter(point)
                        matches.append(normal.dot(body_face.normalAt(bu, bv)))
                assert matches and max(matches) > 0.99, (region.Name, "reversed normal", matches)


def main():
    source = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[3]
        / "Hangboards/tension-whetstone/tension-whetstone.FCStd"
    )
    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    document = App.openDocument(str(source))
    try:
        document.recompute()
        body = document.PocketCut11
        contact = document.CenterIncutContact
        unrelated = document.LeftTwoFingerContact
        contacts = [obj for obj in document.Objects if getattr(obj, "NodeRole", "") == "contact"]
        assert len(contacts) == 12
        for region in contacts:
            assert_on_boundary(region, body)
        before = snapshot(body, contact, unrelated)
        document.CenterIncutSection2.Placement.Base.y += 0.5
        document.recompute()
        after = snapshot(body, contact, unrelated)
        assert body.Shape.isValid() and len(body.Shape.Solids) == 1
        assert abs(after["depth"] - before["depth"] - 0.5) < 1e-6
        assert abs(after["volume"] - before["volume"]) > 1
        assert abs(after["area"] - before["area"]) > 1
        assert abs(after["unrelatedArea"] - before["unrelatedArea"]) < 1e-6
        assert_on_boundary(contact, body)

        jug = document.ContinuousErgoJugSurface
        jug_before = jug.Shape.Area
        document.UpperSilhouette2.Placement.Base.z += 0.5
        document.recompute()
        jug_after = jug.Shape.Area
        assert abs(jug_after - jug_before) > 0.1
        assert_on_boundary(jug, body)
        assert body.Shape.isValid()
        assert all(obj.TypeId not in {"Part::FeaturePython", "Mesh::Feature"} for obj in document.Objects)
        report = {
            "reopenRecompute": True,
            "namedEdit": "CenterIncutSection2.Placement.Base.y + 0.5 mm",
            "before": before,
            "after": after,
            "unrelatedContactUnchanged": True,
            "jugEdit": "UpperSilhouette2.Placement.Base.z + 0.5 mm",
            "jugAreaBefore": jug_before,
            "jugAreaAfter": jug_after,
            "allNative": True,
        }
    finally:
        App.closeDocument(document.Name)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before_hash
    report["sourceBytesUnchanged"] = True
    print(json.dumps(report, indent=2))
    print("Whetstone native edit checks passed")


if __name__ == "__main__":
    main()
