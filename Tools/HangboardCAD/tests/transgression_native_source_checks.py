"""Native checks of saved Transgression sources. Run with run_freecad.py."""
import FreeCAD as App, Part
from pathlib import Path
import hashlib, sys
DEPTHS=(18,14,12,10,9,8,7,6)
def assert_close(a,b): assert abs(a-b)<0.001,(a,b)
def bounds(obj):
    b=obj.Shape.BoundBox
    return (b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax)
def on_shell(document):
    shell=Part.makeCompound(document.Pad.Shape.Faces)
    for obj in document.Objects:
        if getattr(obj,"NodeRole","")!="contact": continue
        points=[v.Point for v in obj.Shape.Vertexes]
        for face in obj.Shape.Faces:
            u0,u1,v0,v1=face.ParameterRange
            points.extend(face.valueAt(u0+(u1-u0)*u,v0+(v1-v0)*v) for u in (0.2,0.5,0.8) for v in (0.2,0.5,0.8))
            u,v=(u0+u1)/2,(v0+v1)/2
            midpoint=face.valueAt(u,v)
            body_face=next(f for f in document.Pad.Shape.Faces if f.distToShape(Part.Vertex(midpoint))[0]<1e-6)
            bu,bv=body_face.Surface.parameter(midpoint)
            assert face.normalAt(u,v).dot(body_face.normalAt(bu,bv))>0.999,"inward contact normal: "+obj.ContactID
        assert max(shell.distToShape(Part.Vertex(p))[0] for p in points)<0.00001,obj.ContactID
for source in map(Path,sys.argv[1:]):
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    doc=App.openDocument(str(source.resolve())); doc.recompute()
    assert doc.Profile.FullyConstrained
    assert doc.Pad.Shape.isValid() and len(doc.Pad.Shape.Solids)==1
    assert_close(doc.Pad.Shape.BoundBox.XLength,540)
    assert_close(doc.Pad.Shape.BoundBox.YLength,150)
    assert_close(doc.Pad.Shape.BoundBox.ZLength,400)
    assert not doc.Pad.Shape.isInside(App.Vector(0,-10,200),0.0001,True),"rear must remain concave/open"
    assert doc.Pad.Shape.isInside(App.Vector(0,-60,200),0.0001,True),"shell must exist ahead of rear void"
    contacts={o.ContactID:o for o in doc.Objects if getattr(o,"NodeRole","")=="contact"}
    assert set(contacts)=={"jug-top"}|{f"edge-{d}" for d in DEPTHS}
    for d in DEPTHS: assert_close(contacts[f"edge-{d}"].Shape.BoundBox.YLength,d)
    for o in contacts.values(): assert o.Base.TypeId=="PartDesign::SubShapeBinder" and o.Base.Support[0][0]==doc.Profile
    on_shell(doc)
    original={cid:bounds(o) for cid,o in contacts.items()}
    doc.Pad.Length=600; doc.recompute()
    assert_close(doc.Pad.Shape.BoundBox.XLength,600)
    for cid,obj in contacts.items():
        assert_close(obj.Shape.BoundBox.XLength,600)
        assert all(abs(a-b)<0.0001 for a,b in zip(bounds(obj)[2:],original[cid][2:])),cid
    on_shell(doc)
    doc.Pad.Length=540; doc.recompute()
    ci=next(i for i in range(doc.Profile.ConstraintCount) if doc.Profile.Constraints[i].Name=="Flat_edge_18")
    original_flat=doc.Profile.Constraints[ci].Value
    volume_before=doc.Pad.Shape.Volume
    doc.Profile.setDatum(ci,App.Units.Quantity(str(original_flat+2)+" mm")); doc.recompute()
    assert doc.Pad.Shape.isValid() and doc.Profile.FullyConstrained
    assert abs(doc.Pad.Shape.Volume-volume_before)>1
    assert_close(contacts["edge-18"].Shape.BoundBox.YLength,20)
    for cid,obj in contacts.items():
        if cid!="edge-18": assert all(abs(a-b)<0.0001 for a,b in zip(bounds(obj),original[cid])),cid
    on_shell(doc)
    doc.Profile.setDatum(ci,App.Units.Quantity(str(original_flat)+" mm")); doc.recompute()
    assert_close(contacts["edge-18"].Shape.BoundBox.YLength,18)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    App.closeDocument(doc.Name)
    print("PASS",source.name,"native reopen, 8 sourced depths, live width +60, isolated edge 18→20, rear void, analytic surface samples, original bytes preserved",flush=True)
