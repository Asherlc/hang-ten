"""Reopen Evo, verify its physical contracts, and persist real pocket edits.

Run with run_freecad.py and pass a workspace-owned scratch directory.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Part

REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = REPOSITORY / "Hangboards/yy-verticalboard-evo.FCStd"


def bound(document):
    nodes = [obj for obj in document.Objects if "NodeRole" in obj.PropertiesList]
    return (
        next(obj for obj in nodes if obj.NodeRole == "body"),
        {obj.ContactID: obj for obj in nodes if obj.NodeRole == "contact"},
    )


def main():
    scratch = Path(sys.argv[1]).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    original = SOURCE.read_bytes()
    document = App.openDocument(str(SOURCE))
    document.recompute()
    body, contacts = bound(document)
    manifest = json.loads(document.HangTenBoardManifest)
    assert len(contacts) == 25
    assert set(contacts) == {contact["id"] for contact in manifest["contacts"]}
    sketches = [obj for obj in document.Objects if obj.TypeId == "Sketcher::SketchObject"]
    assert sketches and all(obj.FullyConstrained for obj in sketches)
    assert body.Shape.isValid() and len(body.Shape.Solids) == 1
    assert all(obj.TypeId not in {"Part::Feature", "PartDesign::Feature", "Part::FeaturePython"}
               for obj in document.Objects), "Frozen/imported shape feature"
    assert all(not ({"Invalid", "Error"} & set(obj.State)) for obj in document.Objects)
    bounds = body.Shape.optimalBoundingBox()
    for actual, expected in [(bounds.XLength, 650), (bounds.YLength, 55), (bounds.ZLength, 140)]:
        assert abs(actual - expected) < 0.001
    for contact in manifest["contacts"]:
        region = contacts[contact["id"]]
        if "depth" in contact:
            expected = contact["depth"]["range"]["maximum"]
            assert abs(region.Shape.BoundBox.YLength - expected) < 0.01, contact["id"]
        for vertex in region.Shape.Vertexes:
            assert body.Shape.Shells[0].distToShape(Part.Vertex(vertex.Point))[0] < 0.001

    # Published slope angles are geometry contracts, independent of the feature tree.
    angles = {"sloper-30-center": 30}
    for side in ("left", "right"):
        angles.update({f"sloper-43-{side}": 43, f"sloper-38-{side}": 38,
                       f"pocket-inclined-{side}": 30, f"edge-inclined-30-{side}": 35})
    for contact_id, expected_angle in angles.items():
        measured = []
        for face in contacts[contact_id].Shape.Faces:
            u0, u1, v0, v1 = face.ParameterRange
            normal = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
            if abs(normal.x) < 1e-6 and abs(normal.z) > 0.1:
                measured.append(math.degrees(math.atan2(abs(normal.y), abs(normal.z))))
        assert any(abs(value - expected_angle) < 0.01 for value in measured), (contact_id, measured)

    # Each edit has to remove additional wood, move its semantic surface, survive
    # save/reopen, and leave an unrelated contact unchanged. Source bytes stay intact.
    for contact_id, edited_depth in [("edge-25-left", 27), ("edge-18-right", 21),
                                     ("edge-40-center", 42)]:
        feature_name = "Pocket_" + contact_id.replace("-", "_")
        feature = document.getObject(feature_name)
        original_depth = feature.Length.Value
        original_volume = body.Shape.Volume
        unrelated_depth = contacts["edge-20-outer-right"].Shape.BoundBox.YLength
        feature.Length = edited_depth
        document.recompute()
        assert body.Shape.isValid() and body.Shape.Volume < original_volume
        assert abs(contacts[contact_id].Shape.BoundBox.YLength - edited_depth) < 0.001
        assert abs(contacts["edge-20-outer-right"].Shape.BoundBox.YLength - unrelated_depth) < 0.001
        saved = scratch / (contact_id + "-edited.FCStd")
        document.saveAs(str(saved))
        App.closeDocument(document.Name)
        document = App.openDocument(str(saved))
        document.recompute()
        body, contacts = bound(document)
        assert abs(contacts[contact_id].Shape.BoundBox.YLength - edited_depth) < 0.001
        assert body.Shape.isValid()
        document.getObject(feature_name).Length = original_depth
        document.recompute()
        print("PASS persisted depth edit", contact_id, original_depth, edited_depth)
    App.closeDocument(document.Name)
    assert SOURCE.read_bytes() == original
    print("all Evo native source checks passed")


if __name__ == "__main__":
    main()
