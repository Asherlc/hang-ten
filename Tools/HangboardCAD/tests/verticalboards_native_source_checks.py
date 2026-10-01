"""Reopen and edit a YY VerticalBoard source under native FreeCAD.

Usage: verticalboards_native_source_checks.py <source.FCStd> <owned-scratch-dir>

Expected dimensions and contact facts below are independent of the embedded
manifest and source features. They preserve the approved manufacturer evidence
recorded in docs/source-audits/2026-09-29-yy-verticalboard-*-cad.md. No workspace
outputs or one-off authoring scripts are read. Only the supplied scratch copy is
saved; the committed source archive must remain byte-identical.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path[:0] = [p for p in os.environ.get("HANGTEN_CAD_PYTHONPATH", "").split(os.pathsep) if p]

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
from pxr import Usd  # noqa: E402

# Native axis order is X width, Y thickness, Z height, in millimetres.
EXPECTED = {
    "yy-verticalboard-first": {
        "envelope": (540.0, 50.0, 130.0),
        "contacts": {
            "jug-left": None, "jug-right": None,
            "sloper-35-left": None, "sloper-35-right": None,
            "sloper-20-center": None,
            "edge-25-left": 25.0, "edge-25-right": 25.0,
            "edge-45-left": 45.0, "edge-45-right": 45.0,
            "edge-33-left": 33.0, "edge-33-right": 33.0,
            "edge-40-center": 40.0,
            "edge-20-left": 20.0, "edge-20-right": 20.0,
            "edge-22-left": 22.0, "edge-22-right": 22.0,
            "edge-24-center": 24.0,
        },
        "edit": ("edge_25_leftFloor", "GripDepth", 27.0, ("edge-25-left",)),
    },
    "yy-verticalboard-light": {
        "envelope": (540.0, 50.0, 90.0),
        "contacts": {
            "jug-left": None, "jug-right": None,
            "sloper-30-left": None, "sloper-30-right": None,
            "sloper-20-center": None,
            "edge-20-left": 20.0, "edge-20-right": 20.0,
            "edge-45-left": 45.0, "edge-45-right": 45.0,
            "edge-25-left": 25.0, "edge-25-right": 25.0,
            "edge-40-center": 40.0,
        },
        "edit": ("BoardBlank", "Edge20Depth", 23.0, ("edge-20-left", "edge-20-right")),
    },
    "yy-verticalboard-one": {
        "envelope": (620.0, 55.0, 130.0),
        "contacts": {
            "jug-left": None, "jug-right": None,
            "sloper-35-left": None, "sloper-35-right": None,
            "sloper-20-center": None,
            "edge-25-left": 25.0, "edge-25-right": 25.0,
            "edge-45-left": 45.0, "edge-45-right": 45.0,
            "pocket-50-left": 50.0, "pocket-50-right": 50.0,
            "edge-inclined-25-left": 25.0, "edge-inclined-25-right": 25.0,
            "pocket-30-left": 30.0, "pocket-30-right": 30.0,
            "center-handle": None,
            "edge-20-left": 20.0, "edge-20-right": 20.0,
            "edge-18-left": 18.0, "edge-18-right": 18.0,
        },
        "edit": ("Edge25LeftDepth", "GripDepth", 28.0, ("edge-25-left",)),
    },
}
TOLERANCE_MM = 1e-3
FAILURES: list[str] = []


def check(label: str, condition: bool, detail="", *, fatal: bool = False) -> None:
    """Report independent failures together; stop only when a prerequisite is unsafe."""
    print(f"{'PASS' if condition else 'FAIL'} {label}: {detail}", flush=True)
    if not condition:
        FAILURES.append(f"{label}: {detail}")
        if fatal:
            raise AssertionError("\n".join(FAILURES))


def finish_checks() -> None:
    """Fail with every collected validation label after independent checks finish."""
    if FAILURES:
        raise AssertionError("Native validation failures:\n" + "\n".join(FAILURES))


def inventory(document):
    """Return the single exported body and uniquely bound contact surfaces from the document."""
    bodies = [o for o in document.Objects if getattr(o, "NodeRole", "") == "body"]
    regions = [o for o in document.Objects if getattr(o, "NodeRole", "") == "contact"]
    check("one exported body", len(bodies) == 1, fatal=True)
    contacts = {o.ContactID: o for o in regions}
    check("unique contact bindings", len(contacts) == len(regions))
    return bodies[0], contacts


def graph_is_valid(document, body):
    """Require a fully recomputed feature graph and one valid, closed body solid."""
    stale = [(o.Name, list(o.State)) for o in document.Objects
             if set(o.State) & {"Invalid", "Error", "Touched", "Recompute"}]
    check("all native objects recompute", not stale, stale)
    check("connected valid closed body", body.Shape.isValid()
          and len(body.Shape.Solids) == 1 and body.Shape.isClosed())


def depths(contacts):
    """Measure each contact surface’s front-to-back extent in native millimetres."""
    return {cid: obj.Shape.optimalBoundingBox().YLength for cid, obj in contacts.items()}


def check_boundary_and_cavity(cid, obj, shell, depth):
    """Verify body-bound contact surfaces and, when specified, the physical recessed cavity depth."""
    shape = obj.Shape
    check(f"{cid} is an open contact surface", shape.isValid()
          and bool(shape.Faces) and not shape.Solids)
    covered_area = shape.common(shell).Area
    check(f"{cid} lies on actual body boundary",
          abs(covered_area - shape.Area) < max(1e-3, shape.Area * 1e-7),
          f"area gap {abs(covered_area - shape.Area):.6g} mm2")
    if depth is None:
        return
    region_box = shape.optimalBoundingBox()
    check(f"{cid} exact cavity depth", abs(region_box.YLength - depth) < TOLERANCE_MM,
          region_box.YLength)
    front = region_box.YMin
    faces = [face.optimalBoundingBox() for face in shape.Faces]
    # A flush filled mouth may look like a pocket in a front image while hiding
    # the real cavity. Require its physical back floor and forbid the front cap.
    check(f"{cid} has no front cavity cap", not any(
        box.YLength < TOLERANCE_MM and abs(box.YMin - front) < TOLERANCE_MM
        for box in faces
    ))
    check(f"{cid} has a physical recessed floor", any(
        box.YLength < TOLERANCE_MM
        and abs(box.YMin - (front + depth)) < TOLERANCE_MM for box in faces
    ))


def verify_edit(document, before, edited_ids, new_depth):
    """Verify edited depths, unchanged contact inventory and bindings after recompute or saved reopen."""
    body, contacts = inventory(document)
    graph_is_valid(document, body)
    after = depths(contacts)
    check("edited contact inventory stable", set(after) == set(before))
    for cid, previous in before.items():
        if cid not in after:
            check(f"{cid} depth after edit", False, "contact missing")
            continue
        expected = new_depth if cid in edited_ids else previous
        check(f"{cid} depth after edit", abs(after[cid] - expected) < TOLERANCE_MM,
              f"expected {expected:.6f}, actual {after[cid]:.6f}")
    # Rechecking the changed binders catches element-map fallback to the whole
    # body, stale floor faces and contact surfaces detached from the new cavity.
    shell = Part.makeShell(body.Shape.Faces)
    for cid in edited_ids:
        if cid in contacts:
            check_boundary_and_cavity(cid, contacts[cid], shell, new_depth)


def main() -> int:
    """Validate the pinned native source, edit a scratch copy, reopen it and preserve original source bytes."""
    FAILURES.clear()
    source = Path(sys.argv[1]).resolve()
    scratch = Path(sys.argv[2]).resolve()
    spec = EXPECTED[source.stem]
    check("scratch is separate from source package", scratch != source.parent
          and source.parent not in scratch.parents, fatal=True)
    scratch.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    document = None
    try:
        check("pinned FreeCAD version", App.Version()[:3] == ["1", "1", "3"], App.Version()[:3], fatal=True)
        check("pinned OpenUSD version", Usd.GetVersion() == (0, 26, 8), Usd.GetVersion(), fatal=True)
        document = App.openDocument(str(source))
        document.recompute()
        body, contacts = inventory(document)
        graph_is_valid(document, body)
        check("native parametric source kind",
              document.HangTenSourceKind == "native-parametric-measured-profile")
        sketches = [o for o in document.Objects if o.TypeId == "Sketcher::SketchObject"]
        check("fully constrained native sketches", bool(sketches)
              and all(o.FullyConstrained for o in sketches))
        check("native solid-building features", any(
            o.TypeId in {"Part::Extrusion", "Part::Loft", "PartDesign::Pad"}
            for o in document.Objects
        ))
        frozen = [o.Name for o in document.Objects if o.TypeId in
                  {"Part::Feature", "Mesh::Feature", "PartDesign::Feature"}
                  or "Python" in o.TypeId]
        check("no frozen or Python geometry features", not frozen, frozen)
        box = body.Shape.optimalBoundingBox()
        envelope = (box.XLength, box.YLength, box.ZLength)
        check("published physical envelope", all(
            abs(a - b) < TOLERANCE_MM for a, b in zip(envelope, spec["envelope"])
        ), envelope)
        expected = spec["contacts"]
        check("independent exact contact inventory", set(contacts) == set(expected), sorted(contacts))
        manifest = json.loads(document.HangTenBoardManifest)
        facts = {c["id"]: c for c in manifest["contacts"]}
        check("manifest has exact contact inventory", set(facts) == set(expected)
              and len(facts) == len(manifest["contacts"]))
        shell = Part.makeShell(body.Shape.Faces)
        for cid, published in expected.items():
            if published is not None:
                check(f"{cid} manifest depth fact", facts.get(cid, {}).get("depth") == {
                    "range": {"minimum": published, "maximum": published}
                })
            if cid not in contacts:
                check(f"{cid} contact exists", False, "contact missing")
                continue
            try:
                check_boundary_and_cavity(cid, contacts[cid], shell, published)
            except Exception as error:
                check(f"{cid} boundary/cavity evaluation", False, repr(error))
        before = depths(contacts)
        feature_name, property_name, edited_depth, edited_ids = spec["edit"]
        feature = document.getObject(feature_name)
        check("native edit parameter exists", feature is not None
              and property_name in feature.PropertiesList, f"{feature_name}.{property_name}", fatal=True)
        setattr(feature, property_name, edited_depth)
        document.recompute()
        verify_edit(document, before, edited_ids, edited_depth)
        edited_source = scratch / f"{source.stem}-edited.FCStd"
        document.saveAs(str(edited_source))
        App.closeDocument(document.Name)
        document = None
        document = App.openDocument(str(edited_source))
        document.recompute()
        parameter = getattr(document.getObject(feature_name), property_name)
        value = parameter.Value if hasattr(parameter, "Value") else float(parameter)
        check("parameter survives saved reopen", abs(value - edited_depth) < TOLERANCE_MM)
        verify_edit(document, before, edited_ids, edited_depth)

    finally:
        if document is not None:
            App.closeDocument(document.Name)
        check("original source bytes unchanged", hashlib.sha256(source.read_bytes()).hexdigest() == digest)
    finish_checks()
    print(f"all {source.stem} native source checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
