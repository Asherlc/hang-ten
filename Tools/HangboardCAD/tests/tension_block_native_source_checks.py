"""Native final-face membership and depth-edit checks for Tension's Block.

Run through ``run_freecad.py`` with a scratch FCStd path and a JSON result path.
No source document is saved. These checks exercise the saved feature graph
rather than rebuilding geometry through the temporary authoring script.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import FreeCAD as App
import Part


def assert_recomputed(document):
    """Recompute in memory and reject stale features or invalid nonempty shapes."""
    document.recompute()
    stale = {
        obj.Name: list(obj.State)
        for obj in document.Objects
        if {"Invalid", "Error", "Touched", "Recompute"} & set(obj.State)
    }
    assert not stale, f"feature graph did not recompute: {stale}"
    for obj in document.Objects:
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            assert obj.Shape.isValid(), f"invalid native shape: {obj.Name}"


def assert_final_face_contacts(document, solid):
    """Require each exported region to be the selected real finished faces."""
    contacts = [
        obj for obj in document.Objects
        if getattr(obj, "NodeRole", "") == "contact"
    ]
    assert contacts, "no native contacts"
    boundary = Part.makeCompound(solid.Shape.Faces)
    for contact in contacts:
        assert contact.TypeId == "PartDesign::SubShapeBinder", contact.Name
        assert contact.Support, f"detached contact: {contact.Name}"
        faces = []
        for target, elements in contact.Support:
            assert target == solid, f"{contact.Name} binds an intermediate solid"
            assert elements, f"{contact.Name} binds no finished faces"
            for element in elements:
                assert element.startswith("Face"), (contact.Name, element)
                faces.append(solid.Shape.getElement(element))
        expected = Part.makeCompound(faces)
        actual = contact.Shape
        assert actual.isValid() and actual.Area > 0, contact.Name
        # OCC's volume integral is nonzero even for some open face compounds;
        # topological solids, rather than that integral, identify capped tools.
        assert not actual.Solids, f"solid proxy contact: {contact.Name}"
        tolerance = max(1e-6, expected.Area * 1e-8)
        assert abs(actual.Area - expected.Area) < tolerance, contact.Name
        assert actual.cut(expected).Area < tolerance, f"stale contact: {contact.Name}"
        assert expected.cut(actual).Area < tolerance, f"missing contact face: {contact.Name}"
        # Check face interiors as well as boundaries: a capped recess tool can
        # share boundary vertices while spanning empty space instead of wood.
        for face in actual.Faces:
            u0, u1, v0, v1 = face.ParameterRange
            for s in (0.2, 0.5, 0.8):
                for t in (0.2, 0.5, 0.8):
                    point = face.valueAt(u0 + s * (u1 - u0), v0 + t * (v1 - v0))
                    vertex = Part.Vertex(point)
                    if face.distToShape(vertex)[0] < 1e-7:
                        gap = boundary.distToShape(vertex)[0]
                        assert gap < 1e-6, (contact.Name, "surface gap", gap)
    return contacts


def main():
    """Check reversible scratch-source edits and write a receipt only on success."""
    source = Path(sys.argv[1]).resolve()
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    document = App.openDocument(str(source))
    try:
        assert_recomputed(document)
        solid = document.getObject("BlockSolid")
        assert solid is not None and len(solid.Shape.Solids) == 1
        assert solid.Shape.Volume > 0
        contacts = assert_final_face_contacts(document, solid)
        identities = sorted((contact.NodeID, contact.ContactID) for contact in contacts)
        # Cover both an open edge and a narrow pocket, whose different cut
        # profiles could otherwise keep one contact family frozen after edits.
        for tool_name, contact_name in (
            ("Edge20Tool", "Edge20Contact"), ("MonoTool", "MonoContact"),
        ):
            tool = document.getObject(tool_name)
            contact = document.getObject(contact_name)
            assert tool is not None and contact is not None, (tool_name, contact_name)
            original_depth = float(tool.LengthFwd)
            original_span = contact.Shape.BoundBox.YLength
            original_volume = solid.Shape.Volume
            original_shape = solid.Shape.copy()
            tool.LengthFwd = original_depth + 1.0
            assert_recomputed(document)
            assert solid.Shape.Volume < original_volume - 1.0, tool_name
            assert abs(contact.Shape.BoundBox.YLength - original_span - 1.0) < 1e-6, contact_name
            assert_final_face_contacts(document, solid)
            assert sorted((obj.NodeID, obj.ContactID) for obj in contacts) == identities
            tool.LengthFwd = original_depth
            assert_recomputed(document)
            assert abs(solid.Shape.Volume - original_volume) < 1e-5, tool_name
            assert solid.Shape.cut(original_shape).Volume < 1e-5, tool_name
            assert original_shape.cut(solid.Shape).Volume < 1e-5, tool_name
            assert abs(contact.Shape.BoundBox.YLength - original_span) < 1e-6, contact_name
            assert_final_face_contacts(document, solid)
    finally:
        App.closeDocument(document.Name)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_digest
    Path(sys.argv[2]).write_text(json.dumps({
        "status": "passed",
        "sourceSHA256": original_digest,
        "editedTools": ["Edge20Tool", "MonoTool"],
    }) + "\n")
    print("native Block contact edit checks passed", flush=True)


if __name__ == "__main__":
    main()
