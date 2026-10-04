"""Native cylinder binding: opposite bore and remote parallel plane regressions."""
from pathlib import Path
import sys
import FreeCAD as App
import Part
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_cord_features import extract_native_cord_features

doc=App.newDocument("CordFeatureChecks")
try:
    cylinders=[]
    for name,sign in (("Left",-1),("Right",1)):
        c=doc.addObject("Part::Cylinder",name);c.Radius=2;c.Height=8
        c.Placement=App.Placement(App.Vector(sign*47,0,0),App.Rotation(App.Vector(0,0,1),App.Vector(sign,0,0)))
        cylinders.append(c)
    doc.recompute()
    box=Part.makeBox(100,40,35,App.Vector(-50,-20,-17.5))
    # This attached ledge has an outer plane at X55 inside the right tool's
    # height, but it is remote from the actual aperture at X50/Y0/Z0.
    box=box.fuse(Part.makeBox(5,5,8,App.Vector(50,10,-4)))
    body=box.cut(cylinders[0].Shape).cut(cylinders[1].Shape)
    assert body.isValid() and len(body.Solids)==1
    features=extract_native_cord_features(doc,body,[],["Left","Right"])
    assert set(features["Left"]["wallFaces"]).isdisjoint(features["Right"]["wallFaces"])
    for record in features.values():
        assert record["axialBounds"][0]>=-1e-8
        assert abs(record["outerMouthStation"]-.003)<1e-8
        assert all(abs(x-.002)<1e-8 for x in record["outerPlaneApertureDistances"])
    print("PASS opposite coaxial bore binding; remote stepped face excluded; finite aperture distance exact")
    # Longitudinal guide intersects the transverse adjustment notch and bore.
    # Their union removes the circular rim at the actual exterior plane.
    box=Part.makeBox(105,40,105,App.Vector(-52.5,-20,-52.5))
    box=box.fuse(Part.makeBox(2.5,5,8,App.Vector(52.5,10,-4)))
    guides=[]
    for name,sign in (("LeftGuide",-1),("RightGuide",1)):
        c=doc.addObject("Part::Cylinder",name);c.Radius=1.75;c.Height=110
        c.Placement.Base=App.Vector(sign*52.5,0,-55);guides.append(c)
    doc.recompute()
    body=box
    for c in cylinders+guides:body=body.cut(c.Shape)
    for sign in (-1,1):
        body=body.cut(Part.makeCylinder(1.75,45,App.Vector(sign*52.5,-22.5,0),App.Vector(0,1,0)))
    assert body.isValid() and len(body.Solids)==1
    merged=extract_native_cord_features(doc,body,[x.Name for x in guides],["Left","Right"])
    for name in ("Left","Right"):
        r=merged[name]
        assert abs(r["outerMouthStation"]-.0055)<1e-8
        assert r["mergedApertureWitness"]["apertureMaterialAreaMM2"]<1e-8
        assert r["mergedApertureWitness"]["axisMaterialLengthMM"]<1e-8
        assert r["mergedApertureWitness"]["sharedWallEdges"]>0
    for selected in ([],["RightGuide"]):
        try:extract_native_cord_features(doc,body,selected,["Left"])
        except ValueError:pass
        else:raise AssertionError("Missing/opposite guide must not witness merged left aperture")
    print("PASS merged longitudinal/transverse/bore aperture; unrelated/opposite guide excluded")

finally:
    App.closeDocument(doc.Name)
