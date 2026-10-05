"""One-off native outline and local shoulder-transition correction."""
import sys,json,hashlib,math
from pathlib import Path
import FreeCAD as A,Part,Sketcher
V=A.Vector
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author'
sys.path.insert(0,str(root/'.context/placid-badger/cad-wall-boards'))
from author_wall import sketch,bezier,front_place,loft,fuse,cut,compound,mirror,intersect,tag,face_overlap,normal,surface_clip,bind_cutter,prop
source=w/'before/metolius-simulator-3d.FCStd';d=A.openDocument(str(source));d.recompute();manifest=d.HangTenBoardManifest;metadata=json.loads(manifest)
# Preserve all native cavities and named depth parameters; rebuild only their
# final-solid supports after changing the native outer/shoulder construction.
for o in list(reversed(d.Objects)):
 if o.Name.startswith(('Contact_','Surface_','RegionBounds_')) or o.Name in ['RoundSloperPairedShoulders','RoundSloperCenterGap']:
  d.removeObject(o.Name)
# Exact envelope extrema retained; the shared tangent directions are deliberately
# chosen display geometry, not measurements from manufacturer pixels.
spans=[[(0,222),(24,222),(31,189.3333333333),(47,188)],[(47,188),(83,185),(222,162),(245,162)],[(245,162),(267,162),(278,180),(294,180)],[(294,180),(322,180),(355.5,156),(355.5,134)],[(355.5,134),(355.5,104),(288,0),(261,0)],[(261,0),(244,0),(219,7.65),(190,12)],[(190,12),(110,24),(56,30.25),(31,24)],[(31,24),(15,20),(18,18),(0,18)]]
for i,scale in [(0,.985),(1,1),(2,1)]:
 s=d.getObject('Silhouette'+str(i))
 for index in reversed(range(s.ConstraintCount)):s.delConstraint(index)
 for index in reversed(range(s.GeometryCount)):s.delGeometry(index)
 ps=spans+[[(-x,z) for x,z in reversed(seg)] for seg in reversed(spans)]
 for seg in ps:
  j=s.addGeometry(bezier([(x*scale,z*scale) for x,z in seg]),False);s.addConstraint(Sketcher.Constraint('Block',j))
d.recompute();base=d.getObject('ShellWithDistinctSlopers');assert base.Shape.isValid()
rot=A.Rotation(V(0,1,0),V(0,0,1),V(1,0,0),'ZXY')
transitions=[];removals=[];section_report=[]
for label,x0,x1,zfloor in [('CenterShoulder',35.,65.,145.),('RoundFlat',130.,166.,135.),('OuterShoulder',238.,278.,135.)]:
 bounds=d.addObject('Part::Box',label+'TransitionBounds');bounds.Length=x1-x0;bounds.Width=120;bounds.Height=120;bounds.Placement.Base=V(x0,-110,zfloor)
 cap=base.Shape.common(Part.makeBox(800,120,120,V(-400,-110,zfloor)))
 sections=[]
 for j,x in enumerate([x0,x0+2,x1-2,x1]):
  wires=cap.slice(V(1,0,0),x);assert len(wires)==1,(label,x,len(wires))
  placement=A.Placement(V(x,0,0),rot);wire=wires[0].copy();wire.transformShape(placement.inverse().toMatrix())
  ordered=list(wire.OrderedEdges)
  target=V(0,zfloor,0)
  k=min(range(len(ordered)),key=lambda i:(ordered[i].firstVertex(True).Point-target).Length)
  ordered=ordered[k:]+ordered[:k]
  if ordered[0].lastVertex(True).Point.y<zfloor+.001:
   wire.reverse();ordered=list(wire.OrderedEdges)
   k=min(range(len(ordered)),key=lambda i:(ordered[i].firstVertex(True).Point-target).Length);ordered=ordered[k:]+ordered[:k]
  assert (ordered[0].firstVertex(True).Point-target).Length<1e-5,(label,j,'rear bottom section origin',[(e.firstVertex(True).Point.x,e.firstVertex(True).Point.y,e.firstVertex(True).Point.z) for e in ordered])
  ge=[]
  for edge in ordered:
   if isinstance(edge.Curve,Part.Line):g=Part.LineSegment(edge.firstVertex(True).Point,edge.lastVertex(True).Point)
   else:
    g=edge.Curve.toBSpline(edge.FirstParameter,edge.LastParameter)
    if edge.Orientation=='Reversed':g.reverse()
   ge.append(g)
  assert abs(ge[0].StartPoint.x)<1e-5 and abs(ge[0].EndPoint.x)<1e-5 and abs(ge[-1].StartPoint.y-zfloor)<1e-5 and abs(ge[-1].EndPoint.y-zfloor)<1e-5,(label,j,'rear/floor classification')
  ge[0]=Part.LineSegment(ge[0].StartPoint,ge[0].EndPoint);ge[-1]=Part.LineSegment(ge[-1].StartPoint,ge[-1].EndPoint)
  outer=ge[1].toBSpline()
  for curve in ge[2:-1]:assert outer.join(curve.toBSpline()),(label,j,'exact native outer curve join')
  ge=[ge[0],outer,ge[-1]]
  section=sketch(d,label+'TransitionSection'+str(j),ge,placement);sections.append(section)
  d.recompute();assert section.Shape.Wires and section.Shape.Wires[0].isClosed(),(label,j,'not closed')
  section_report.append({'transition':label,'x':x,'floorZ':zfloor,'edgeCount':len(ge),'origin':'Exact analytic section of existing native shoulder shell, no mesh or imagery sampling'})
 blend=loft(d,label+'TransitionLoft',sections,True,False);d.recompute();assert blend.Shape.isValid() and len(blend.Shape.Solids)==1,(label,'bad loft')
 # Keep local interpolating lofts inside the
 # frozen 94 mm front envelope. This bounds interpolation, not shape repair.
 clip=d.addObject('Part::Box',label+'TransitionClip');clip.Length=800;clip.Width=94;clip.Height=300;clip.Placement.Base=V(-400,-94,-1)
 blend.Shape.exportBrep(str(w/(label+'-loft.brep')));print(label,'LOFT',blend.Shape.BoundBox,'VOLUME',blend.Shape.Volume,flush=True)
 blend=intersect(d,label+'BoundedTransition',blend,clip);d.recompute();assert not blend.Shape.isNull() and blend.Shape.isValid() and len(blend.Shape.Solids)==1 and blend.Shape.Volume>1000,(label,'bounded transition')
 transitions += [blend,mirror(d,label+'TransitionLeft',blend)]
 removals += [bounds,mirror(d,label+'TransitionBoundsLeft',bounds)]
remaining=cut(d,'ShoulderTransitionBandsRemoved',base,compound(d,'ShoulderTransitionRemovalBounds',removals))
smoothed=fuse(d,'ShellWithContinuousShoulders',[remaining]+transitions);d.recompute();assert smoothed.Shape.isValid() and len(smoothed.Shape.Solids)==1
body=d.getObject('BodySolid');body.Base=smoothed;d.recompute();assert body.Shape.isValid()
(w/'diagnosis-construction.json').write_text(json.dumps([{'name':o.Name,'type':o.TypeId,'state':list(o.State),'bounds':str(o.Shape.BoundBox),'volume':o.Shape.Volume,'solidCount':len(o.Shape.Solids)} for o in d.Objects if hasattr(o,'Shape') and not o.Shape.isNull() and o.TypeId!='Sketcher::SketchObject'],indent=2))
d.saveAs(str(w/'probe-source.FCStd'))
body.Shape.exportBrep(str(w/'probe-body.brep'))
print('BODY',body.Shape.BoundBox,'faces',len(body.Shape.Faces),'solids',len(body.Shape.Solids),'tool',body.Tool.Name,'toolbbox',body.Tool.Shape.BoundBox,flush=True)
for cid in ['pocket-4-left','pocket-4-right','edge-11-left']:
 cutter=d.getObject('Cutter_'+cid.replace('-','_'));ratios=[face_overlap(f,cutter.Shape)/f.Area for f in body.Shape.Faces if f.Area>1e-5]
 print('CAVITY',cid,cutter.Shape.BoundBox,'maxOverlap',max(ratios),flush=True)
params=d.getObject('Parameters');corrections=[]
for c in metadata['contacts']:
 cid=c['id'];cutter=d.getObject('Cutter_'+cid.replace('-','_'))
 if not cutter:continue
 contact=bind_cutter(d,body,cid,cutter);d.recompute()
 depth=c['depth']['range']['minimum'];delta=depth-contact.Shape.optimalBoundingBox().YLength
 if abs(delta)>.0001:
  floor=cutter.Sections[-1];key='Depth_'+cid.replace('-','_');offset=floor.Placement.Base.y-getattr(params,key)+delta
  floor.setExpression('Placement.Base.y',f'{offset}+Parameters.{key}');corrections.append({'contactID':cid,'floorTranslationMm':delta})
d.recompute()
for c in metadata['contacts']:
 cid=c['id'];cutter=d.getObject('Cutter_'+cid.replace('-','_'))
 if not cutter:continue
 obj=d.getObject('Contact_'+cid.replace('-','_'));obj.Support=[(body,[f'Face{i+1}' for i,f in enumerate(body.Shape.Faces) if face_overlap(f,cutter.Shape)>.97*f.Area and f.Area>1e-5])]
d.recompute()
base_surface=Part.makeCompound(smoothed.Shape.Faces)
predicate=lambda f:normal(f).z>.08 and face_overlap(f,base_surface)>.97*f.Area
surface_clip(d,body,'jug-14-center',(-47,47,-110,-.001,187,230),predicate)
round_full=surface_clip(d,body,'round-sloper-3-center',(-148,148,-65,0,145,215),predicate)
gap=d.addObject('Part::Box','RoundSloperCenterGap');gap.Length=94;gap.Width=120;gap.Height=100;gap.Placement.Base=V(-47,-120,140)
for key in ['NodeID','NodeRole','ContactID']:round_full.removeProperty(key)
round_split=cut(d,'RoundSloperPairedShoulders',round_full,gap);tag(round_split,'round-sloper-3-center')
for side,sign in [('left',-1),('right',1)]:
 a,b=(148,258) if sign==1 else (-258,-148)
 surface_clip(d,body,'flat-sloper-2-'+side,(a,b,-55,0,140,210),predicate)
 a,b=(258,356) if sign==1 else (-356,-258)
 surface_clip(d,body,'jug-1-'+side,(a,b,-110,-.001,137,210),predicate)
d.recompute()
assert d.HangTenBoardManifest==manifest
bad=[(o.Name,list(o.State)) for o in d.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}];assert not bad,bad
contacts=[o for o in d.Objects if getattr(o,'NodeRole','')=='contact'];assert len(contacts)==30
for c in contacts:assert c.Shape.Faces and not c.Shape.Solids,c.Name
sketches=[o for o in d.Objects if o.TypeId=='Sketcher::SketchObject'];assert all(o.FullyConstrained for o in sketches)
folder=w/'candidate';folder.mkdir(exist_ok=True);(folder/'assets').mkdir(exist_ok=True);out=folder/'metolius-simulator-3d.FCStd';d.saveAs(str(out))
r={'sourceSHA256':hashlib.sha256(out.read_bytes()).hexdigest(),'silhouetteBezierSpansRightXZ':spans,'transitionSections':section_report,'depthFloorCorrections':corrections,'allNewGeometryValues':'Operator-selected display estimates; exact native section loops use existing CAD only, no pixels or reference mesh','finalBody':'BodySolid','contactCount':30,'fullyConstrainedSketchCount':len(sketches),'rawManifestUnchanged':True}
(w/'authored-design.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
