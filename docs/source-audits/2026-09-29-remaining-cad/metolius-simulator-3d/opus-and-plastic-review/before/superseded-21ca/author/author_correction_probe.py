"""One-off native outline and local shoulder-transition correction."""
import sys,json,hashlib,math
from pathlib import Path
import FreeCAD as A,Part,Sketcher
V=A.Vector
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-opus-corrections'
sys.path.insert(0,str(root/'.context/placid-badger/cad-wall-boards'))
from author_wall import sketch,bezier,front_place,loft,fuse,cut,compound,mirror,intersect,tag,face_overlap,normal,surface_clip,bind_cutter,prop
source=w/'plastic-before/metolius-simulator-3d.FCStd';d=A.openDocument(str(source));d.recompute();manifest=d.HangTenBoardManifest;metadata=json.loads(manifest)
# Preserve all native cavities and named depth parameters; rebuild only their
# final-solid supports after changing the native outer/shoulder construction.
for o in list(reversed(d.Objects)):
 if o.Name.startswith(('Contact_','Surface_','RegionBounds_')) or o.Name in ['RoundSloperPairedShoulders','RoundSloperCenterGap']:
  d.removeObject(o.Name)
# Exact envelope extrema retained; the shared tangent directions are deliberately
# chosen display geometry, not measurements from manufacturer pixels.
spans=[[(0,222),(24,222),(42,211),(47,188)],[(47,188),(83,185),(222,162),(245,162)],[(245,162),(267,162),(278,180),(294,180)],[(294,180),(322,180),(355.5,156),(355.5,134)],[(355.5,134),(355.5,104),(288,0),(261,0)],[(261,0),(244,0),(219,7.65),(190,12)],[(190,12),(110,24),(56,30.25),(31,24)],[(31,24),(15,20),(18,18),(0,18)]]
for i,scale in [(0,.985),(1,1),(2,1)]:
 s=d.getObject('Silhouette'+str(i))
 for index in reversed(range(s.ConstraintCount)):s.delConstraint(index)
 for index in reversed(range(s.GeometryCount)):s.delGeometry(index)
 ps=spans+[[(-x,z) for x,z in reversed(seg)] for seg in reversed(spans)]
 for seg in ps:
  j=s.addGeometry(bezier([(x*scale,z*scale) for x,z in seg]),False);s.addConstraint(Sketcher.Constraint('Block',j))
d.recompute();base=d.getObject('ShellWithDistinctSlopers');assert base.Shape.isValid()
rot=A.Rotation(V(0,1,0),V(0,0,1),V(1,0,0),'ZXY')
section_report=[]
for label,x0,x1,zfloor,stations in [('CenterShoulder',46.5,61.,145.,[46.5,46.9,59.5,61.]),('RoundFlat',110.,185.,135.,[110.,112.,183.,185.])]:
 bounds=d.getObject(label+'TransitionBounds');bounds.Length=x1-x0;bounds.Placement.Base=V(x0,-110,zfloor)
 cap=base.Shape.common(Part.makeBox(800,120,120,V(-400,-110,zfloor)))
 for j,x in enumerate(stations):
  wires=cap.slice(V(1,0,0),x);assert len(wires)==1,(label,x,len(wires))
  placement=A.Placement(V(x,0,0),rot);wire=wires[0].copy();wire.transformShape(placement.inverse().toMatrix())
  def order(wire):
   ordered=list(wire.OrderedEdges);target=V(0,zfloor,0)
   k=min(range(len(ordered)),key=lambda i:(ordered[i].firstVertex(True).Point-target).Length)
   return ordered[k:]+ordered[:k]
  ordered=order(wire)
  if ordered[0].lastVertex(True).Point.y<zfloor+.001:wire.reverse();ordered=order(wire)
  assert (ordered[0].firstVertex(True).Point-V(0,zfloor,0)).Length<1e-5
  ge=[]
  for edge in ordered:
   if isinstance(edge.Curve,Part.Line):g=Part.LineSegment(edge.firstVertex(True).Point,edge.lastVertex(True).Point)
   else:
    g=edge.Curve.toBSpline(edge.FirstParameter,edge.LastParameter)
    if edge.Orientation=='Reversed':g.reverse()
   ge.append(g)
  rear_count=0
  for g in ge:
   if all(abs(p.x)<1e-5 for p in ([g.StartPoint,g.EndPoint] if isinstance(g,Part.LineSegment) else g.getPoles())):rear_count+=1
   else:break
  floor_start=len(ge)
  for g in reversed(ge):
   if all(abs(p.y-zfloor)<1e-5 for p in ([g.StartPoint,g.EndPoint] if isinstance(g,Part.LineSegment) else g.getPoles())):floor_start-=1
   else:break
  assert rear_count>=1 and floor_start<len(ge) and rear_count<floor_start,(label,j,'semantic profile',rear_count,floor_start,[(str(type(g)),str(g.StartPoint),str(g.EndPoint)) for g in ge])
  rear=Part.LineSegment(ge[0].StartPoint,ge[rear_count-1].EndPoint)
  floor=Part.LineSegment(ge[floor_start].StartPoint,ge[-1].EndPoint)
  outer=ge[rear_count].toBSpline()
  for curve in ge[rear_count+1:floor_start]:assert outer.join(curve.toBSpline()),(label,j,'exact outer join')
  section=d.getObject(label+'TransitionSection'+str(j))
  for index in reversed(range(section.ConstraintCount)):section.delConstraint(index)
  for index in reversed(range(section.GeometryCount)):section.delGeometry(index)
  section.Placement=placement
  for g in [rear,outer,floor]:
   index=section.addGeometry(g,False);section.addConstraint(Sketcher.Constraint('Block',index))
  d.recompute();assert section.Shape.Wires and section.Shape.Wires[0].isClosed()
  section_report.append({'transition':label,'x':x,'floorZ':zfloor,'rearNativeEdgesMerged':rear_count,'rearRoofZ':rear.EndPoint.y,'nativeOuterCurveDegree':outer.Degree,'nativeOuterCurvePoles':outer.NbPoles})
 d.recompute();blend=d.getObject(label+'BoundedTransition')
 assert not blend.Shape.isNull() and blend.Shape.isValid() and len(blend.Shape.Solids)==1 and blend.Shape.Volume>1000,(label,'bounded transition')
 print(label,blend.Shape.BoundBox,'VOLUME',blend.Shape.Volume,flush=True)
smoothed=d.getObject('ShellWithContinuousShoulders');body=d.getObject('BodySolid');d.recompute()
assert not smoothed.Shape.isNull() and smoothed.Shape.isValid() and len(smoothed.Shape.Solids)==1
assert not body.Shape.isNull() and body.Shape.isValid() and len(body.Shape.Solids)==1
(w/'diagnosis-construction.json').write_text(json.dumps([{'name':o.Name,'type':o.TypeId,'state':list(o.State),'bounds':str(o.Shape.BoundBox),'volume':o.Shape.Volume,'solidCount':len(o.Shape.Solids)} for o in d.Objects if hasattr(o,'Shape') and not o.Shape.isNull() and o.TypeId!='Sketcher::SketchObject'],indent=2))
d.saveAs(str(w/'probe-source.FCStd'))
body.Shape.exportBrep(str(w/'probe-body.brep'))
print('BODY',body.Shape.BoundBox,'faces',len(body.Shape.Faces),'solids',len(body.Shape.Solids),'tool',body.Tool.Name,'toolbbox',body.Tool.Shape.BoundBox,flush=True)
v,f=body.Shape.tessellate(.28)
(w/'probe-body-mesh.json').write_text(json.dumps({'p':[[p.x,p.y,p.z] for p in v],'t':f,'volume':body.Shape.Volume,'bounds':str(body.Shape.optimalBoundingBox())}))
(w/'probe-design.json').write_text(json.dumps({'spans':spans,'sections':section_report,'manifestExact':d.HangTenBoardManifest==manifest,'sourceEstimate':'Operator-selected analytic geometry. No image measurement.','states':[(o.Name,list(o.State)) for o in d.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}]},indent=2))
print('PROBE COMPLETE',len(f),flush=True)
A.closeDocument(d.Name)
