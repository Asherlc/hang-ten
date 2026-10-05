import sys,json,hashlib,math,time
from pathlib import Path
import FreeCAD as A,Part,Sketcher
V=A.Vector;root=Path.cwd();w=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'.context/placid-badger/cad-wall-boards'))
from author_wall import sketch,bezier,front_place,loft,fuse,cut,compound,mirror,intersect,tag,normal,face_overlap,bind_cutter
source=w/'before/metolius-simulator-3d.FCStd';d=A.openDocument(str(source));d.recompute();manifest=d.HangTenBoardManifest
started=time.monotonic()
def progress(stage):
 (w/'progress.json').write_text(json.dumps({'stage':stage,'seconds':time.monotonic()-started}));print(stage,flush=True)
def replace(s,ge):
 for i in reversed(range(s.ConstraintCount)):s.delConstraint(i)
 for i in reversed(range(s.GeometryCount)):s.delGeometry(i)
 for g in ge:
  i=s.addGeometry(g,False);s.addConstraint(Sketcher.Constraint('Block',i))
for o in list(reversed(d.Objects)):
 if o.Name.startswith(('Contact_','Surface_','RegionBounds_')) or o.Name in ['RoundSloperPairedShoulders','RoundSloperCenterGap']:d.removeObject(o.Name)
progress('Opened frozen source; native contacts removed for rebuild')
def relief_at(z):
 for g in d.ContinuousFrontRelief.Geometry:
  if not isinstance(g,Part.BSplineCurve):continue
  a=g.value(g.FirstParameter);b=g.value(g.LastParameter)
  if min(a.y,b.y)-1e-9<=z<=max(a.y,b.y)+1e-9:
   lo,hi=g.FirstParameter,g.LastParameter
   for _ in range(80):
    mid=(lo+hi)/2;p=g.value(mid)
    if p.y>z:lo=mid
    else:hi=mid
   p=g.value((lo+hi)/2);t=g.tangent((lo+hi)/2)[0]
   return p.x,-t.x/t.y
 raise ValueError(z)
profiles=[]
for label,x0,x1,t0,t1,floor in [('Round',47,148,188,178,145),('Flat',148,258,178,163,135)]:
 front_base,slope=relief_at(floor)
 for i,(x,t) in enumerate([(x0,t0),(x1,t1)]):
  rear=Part.LineSegment(V(0,floor,0),V(0,t,0))
  if label=='Round':
   roof=[bezier([(0,t),(-51,t),(-94,t-6),(-94,t-17)])];end_z=t-17
  else:
   k=9.5/55.;z88=t-88*k
   roof=[Part.LineSegment(V(0,t,0),V(-88,z88,0)),bezier([(-88,z88),(-92,z88-4*k),(-94,t-16.5),(-94,t-17)])];end_z=t-17
  h=min(5,(end_z-floor)/3)
  roll=bezier([(-94,end_z),(-94,end_z-h),(front_base-slope*h,floor+h),(front_base,floor)])
  outer=roof[0].toBSpline()
  for curve in roof[1:]:assert outer.join(curve.toBSpline())
  ge=[rear,outer,roll,Part.LineSegment(V(front_base,floor,0),V(0,floor,0))]
  replace(d.getObject(label+'SloperSection'+str(i)),ge)
  profiles.append({'label':label,'x':x,'topRearZ':t,'floorZ':floor,'frontY':-94,'frontRollStartZ':end_z,'nativeLowerJoinY':front_base,'nativeLowerTangentDyDz':-slope,'outerCurveDegree':outer.Degree,'outerCurvePoles':outer.NbPoles})
 d.getObject(label+'SloperRoof').Ruled=True
# Round/flat surfaces reach the same forward envelope; contact spans are assigned later.
d.recompute();progress('Simple forward sloper profiles recomputed')
# Native depth-wise center cap, above the existing pocket15 ceiling.
center_stations=[(0,188.),(-6,188.2),(-25,190.),(-45,207.),(-65,222.),(-70,221.8),(-84,210.),(-94,190.)]
center_sections=[]
def center_ge(height,factor=1):
 h=187+(height-187)*factor;k=(h-187)/35
 right=bezier([(0,h),(24,h),(42,187+24*k),(47,188)])
 left=bezier([(-47,188),(-42,187+24*k),(-24,h),(0,h)])
 return [right,Part.LineSegment(V(47,188,0),V(47,187,0)),Part.LineSegment(V(47,187,0),V(-47,187,0)),Part.LineSegment(V(-47,187,0),V(-47,188,0)),left]
for i,(y,h) in enumerate(center_stations):center_sections.append(sketch(d,'ForwardJugSection'+str(i),center_ge(h),front_place(0,y,0)))
cap=loft(d,'ForwardCenterJug',center_sections,True,False);cap.MaxDegree=3;d.recompute();assert cap.Shape.isValid() and len(cap.Shape.Solids)==1
initial_height=cap.Shape.optimalBoundingBox().ZMax;factor=35/(initial_height-187)
for section,(_,h) in zip(center_sections,center_stations):replace(section,center_ge(h,factor))
d.recompute();assert cap.Shape.isValid() and len(cap.Shape.Solids)==1
# Remove only center material above Z187; pocket15 remains below this cut.
box=d.addObject('Part::Box','CenterJugReplacementBounds');box.Length=94;box.Width=120;box.Height=100;box.Placement.Base=V(-47,-110,187)
without=cut(d,'ShellWithoutRearJugRidge',d.ShellWithDistinctSlopers,box)
base=fuse(d,'FunctionalShellBeforeBlends',[without,cap]);d.recompute();assert base.Shape.isValid() and len(base.Shape.Solids)==1
progress('Forward center crest and rear return recomputed')
rot=A.Rotation(V(0,1,0),V(0,0,1),V(1,0,0),'ZXY')
section_report=[]
for label,x0,x1,zfloor,stations in [('CenterShoulder',46.5,61.,145.,[46.5,46.9,59.5,61.]),('RoundFlat',110.,185.,135.,[110.,112.,183.,185.]),('OuterShoulder',238.,278.,135.,[238.,240.,276.,278.])]:
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
  lip_end=next((i+1 for i in range(rear_count,floor_start) if abs(ge[i].EndPoint.x+94)<1e-5),None)
  assert lip_end and lip_end<floor_start,(label,j,'forwardmost semantic roof endpoint missing',[(g.StartPoint.x,g.StartPoint.y,g.EndPoint.x,g.EndPoint.y) for g in ge])
  outer=ge[rear_count].toBSpline()
  for curve in ge[rear_count+1:lip_end]:assert outer.join(curve.toBSpline()),(label,j,'exact roof join')
  front_return=ge[lip_end].toBSpline()
  for curve in ge[lip_end+1:floor_start]:assert front_return.join(curve.toBSpline()),(label,j,'exact return join')
  section=d.getObject(label+'TransitionSection'+str(j))
  for index in reversed(range(section.ConstraintCount)):section.delConstraint(index)
  for index in reversed(range(section.GeometryCount)):section.delGeometry(index)
  section.Placement=placement
  for g in [rear,outer,front_return,floor]:
   index=section.addGeometry(g,False);section.addConstraint(Sketcher.Constraint('Block',index))
  # Defer dependent recompute until all four sections are authored.
  section_report.append({'transition':label,'x':x,'floorZ':zfloor,'rearNativeEdgesMerged':rear_count,'rearRoofZ':rear.EndPoint.y,'nativeOuterCurveDegree':outer.Degree,'nativeOuterCurvePoles':outer.NbPoles})
 d.recompute();blend=d.getObject(label+'BoundedTransition')
 assert not blend.Shape.isNull() and blend.Shape.isValid() and len(blend.Shape.Solids)==1 and blend.Shape.Volume>1000,(label,'bounded transition')
 progress('Transition authored: '+label)
d.ShoulderTransitionBandsRemoved.Base=base
smoothed=d.ShellWithContinuousShoulders;body=d.BodySolid;d.recompute()
assert not smoothed.Shape.isNull() and smoothed.Shape.isValid() and len(smoothed.Shape.Solids)==1
assert body.Shape.isValid() and len(body.Shape.Solids)==1
bad=[(o.Name,list(o.State)) for o in d.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}];assert not bad,bad
assert d.HangTenBoardManifest==manifest
bounds=body.Shape.optimalBoundingBox();d.saveAs(str(w/'probe-source.FCStd'));body.Shape.exportBrep(str(w/'probe-body.brep'))
v,t=body.Shape.tessellate(.28);(w/'probe-body-mesh.json').write_text(json.dumps({'p':[[p.x,p.y,p.z] for p in v],'t':t}))
r={'sourceSHA256':hashlib.sha256((w/'probe-source.FCStd').read_bytes()).hexdigest(),'nativeSolidCount':len(body.Shape.Solids),'nativeFaceCount':len(body.Shape.Faces),'profiles':profiles,'centerStationsYHeightEstimatedMm':center_stations,'centerHeightNormalizationFactor':factor,'initialCapMaxZ':initial_height,'centerCapMaxZ':d.ForwardCenterJug.Shape.optimalBoundingBox().ZMax,'transitionSections':section_report,'envelopeXYZMm':[bounds.XLength,bounds.YLength,bounds.ZLength],'rawManifestExact':True,'triangleCount':len(t),'allNewGeometryValues':'Explicit operator-selected display adaptation for user grasp intent; not manufacturer incut measurements.'};(w/'probe-design.json').write_text(json.dumps(r,indent=2)+'\n');progress('PROBE COMPLETE');print(json.dumps(r));A.closeDocument(d.Name)
