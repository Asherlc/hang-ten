"""Reopen Honestone, inspect physical surfaces, and persist a real depth edit.

Run with run_freecad.py and a workspace-owned scratch directory argument.
"""

from pathlib import Path
import hashlib
import json
import math
import sys

import FreeCAD as App


def main():
    source = Path(sys.argv[1]).resolve()
    scratch = Path(sys.argv[2]).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    document = App.openDocument(str(source))
    document.recompute()
    nodes = [obj for obj in document.Objects if "NodeID" in obj.PropertiesList]
    body = next(obj for obj in nodes if obj.NodeRole == "body")
    regions = {obj.ContactID: obj for obj in nodes if obj.NodeRole == "contact"}
    contacts = json.loads(document.HangTenBoardManifest)["contacts"]
    assert len(nodes) == 16 and set(regions) == {contact["id"] for contact in contacts}
    assert body.Shape.isValid() and len(body.Shape.Solids) == 1
    bounds = body.Shape.optimalBoundingBox()
    assert abs(bounds.XLength - 635) < 0.01
    assert abs(bounds.YLength - 63.5) < 0.01
    assert abs(bounds.ZLength - 152.4) < 0.01
    for obj in document.Objects:
        assert not set(obj.State) & {"Invalid", "Error", "Touched", "Recompute"}, obj.Name
        assert obj.TypeId not in {"Part::Feature", "PartDesign::Feature", "Part::FeaturePython"}
        if obj.TypeId == "Sketcher::SketchObject":
            assert obj.FullyConstrained, obj.Name
    for contact in contacts:
        region = regions[contact["id"]]
        if "depth" in contact:
            assert abs(region.Shape.BoundBox.YLength - contact["depth"]["range"]["minimum"]) < 0.01
        for face in region.Shape.Faces:
            assert body.Shape.Shells[0].distToShape(face)[0] < 1e-6

    # The bearing floor is incut, not merely a 25 mm straight pocket carrying
    # an angle property. Its actual upward normal tilts ten degrees toward the back.
    center = regions["edge-25-center"]
    floor_angles = []
    for face in center.Shape.Faces:
        u0, u1, v0, v1 = face.ParameterRange
        normal = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        if normal.z > 0.95 and face.Area > 500:
            floor_angles.append(math.degrees(math.atan2(abs(normal.y), normal.z)))
    assert any(abs(angle - 10) < 0.01 for angle in floor_angles), floor_angles

    # Macro slopers must have varying geometric slopes and four physical regions.
    for contact_id, region in regions.items():
        if not contact_id.startswith("macro-sloper"):
            continue
        angles = []
        for face in region.Shape.Faces:
            u0, u1, v0, v1 = face.ParameterRange
            for fraction in (0.15, 0.35, 0.55, 0.75, 0.9):
                normal = face.normalAt(u0 + (u1 - u0) * .5, v0 + (v1 - v0) * fraction)
                angles.append(math.degrees(math.acos(min(1, max(-1, normal.z)))))
        assert max(angles) - min(angles) > 10, (contact_id, angles)
    for contact_id in ("edge-10-left", "edge-8-left", "edge-10-right", "edge-8-right"):
        radii = [
            getattr(face.Surface, "Radius", 0.0)
            for face in regions[contact_id].Shape.Faces
        ]
        assert any(abs(radius - 3.175) < 1e-6 for radius in radii), (contact_id, radii)

    # Check the connected cavities have genuine differently deep floors and that
    # the right side follows the manufacturer's engraved left-to-right ordering.
    assert regions["edge-20-right"].Shape.BoundBox.Center.x < regions["edge-15-right"].Shape.BoundBox.Center.x
    assert regions["edge-10-right"].Shape.BoundBox.Center.x < regions["edge-8-right"].Shape.BoundBox.Center.x
    before_volume = body.Shape.Volume
    document.getObject("Edge20LeftPocket").Length = 22
    document.recompute()
    assert body.Shape.Volume < before_volume - 100
    assert abs(regions["edge-20-left"].Shape.BoundBox.YLength - 22) < .01
    assert abs(regions["edge-15-left"].Shape.BoundBox.YLength - 15) < .01
    edited = scratch / "honestone-depth-edit.FCStd"
    document.saveAs(str(edited))
    App.closeDocument(document.Name)
    reopened = App.openDocument(str(edited))
    reopened.recompute()
    assert abs(reopened.getObject("RegionEdge20Left").Shape.BoundBox.YLength - 22) < .01
    assert reopened.getObject("Edge20LeftPocket").Length.Value == 22
    for obj in reopened.Objects:
        assert not set(obj.State) & {"Invalid", "Error", "Touched", "Recompute"}, obj.Name
    App.closeDocument(reopened.Name)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_digest
    print("all Honestone native source checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
