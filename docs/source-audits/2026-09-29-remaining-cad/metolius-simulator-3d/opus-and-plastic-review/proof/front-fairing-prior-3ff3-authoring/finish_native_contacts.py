"""One-off native outline and local shoulder-transition correction."""
import sys,json,hashlib,math
from pathlib import Path
import FreeCAD as A,Part,Sketcher
V=A.Vector
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-functional-lip-correction'
sys.path.insert(0,str(root/'.context/placid-badger/cad-wall-boards'))
from author_wall import sketch,bezier,front_place,loft,fuse,cut,compound,mirror,intersect,tag,face_overlap,normal,surface_clip,bind_cutter,prop
source=w/'probe-source.FCStd';d=A.openDocument(str(source));d.recompute();manifest=d.HangTenBoardManifest;metadata=json.loads(manifest)
body=d.getObject('BodySolid');smoothed=d.getObject('ShellWithContinuousShoulders');r=json.loads((w/'probe-design.json').read_text());spans=[[[p.x,p.y] for p in g.getPoles()] for g in d.Silhouette2.Geometry[:8]];section_report=r['transitionSections']
def vector(v):return tuple(round(float(x),7) for x in [v.x,v.y,v.z])
def carrier(surface):
 typ=type(surface).__name__
 if typ=='Plane':
  n=surface.Axis;sgn=next((1 if v>0 else -1 for v in [n.x,n.y,n.z] if abs(v)>1e-9),1);return (typ,vector(n*sgn),round(n.dot(surface.Position)*sgn,7))
 if typ=='BSplineSurface':
  return (typ,surface.UDegree,surface.VDegree,tuple(tuple(vector(v) for v in row) for row in surface.getPoles()),tuple(round(x,9) for x in surface.getUKnots()),tuple(round(x,9) for x in surface.getVKnots()),tuple(surface.getUMultiplicities()),tuple(surface.getVMultiplicities()),tuple(tuple(round(x,9) for x in row) for row in surface.getWeights()))
 return None
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
base_carriers={carrier(f.Surface) for f in smoothed.Shape.Faces};base_carriers.discard(None)
def local_grip(cid,limits):
 x0,x1,y0,y1,z0,z1=limits
 box=d.addObject('Part::Box','RegionBounds_'+cid.replace('-','_'));box.Length=x1-x0;box.Width=y1-y0;box.Height=z1-z0;box.Placement.Base=V(x0,y0,z0);d.recompute()
 names=[];selection=[]
 for i,f in enumerate(body.Shape.Faces):
  if carrier(f.Surface) not in base_carriers:continue
  bb=f.BoundBox
  if bb.XMax<x0-1e-5 or bb.XMin>x1+1e-5 or bb.YMax<y0-1e-5 or bb.YMin>y1+1e-5 or bb.ZMax<z0-1e-5 or bb.ZMin>z1+1e-5:continue
  local=f.common(box.Shape)
  normals=[normal(p).z for p in local.Faces if p.Area>1e-5]
  if any(n>.08 for n in normals):names.append('Face'+str(i+1));selection.append({'sourceFace':i+1,'localNormalZ':normals})
 assert names,cid
 pieces=[]
 for i,name in enumerate(names):
  binder=d.addObject('PartDesign::SubShapeBinder','Surface_'+cid.replace('-','_')+'_'+str(i));binder.Support=[(body,[name])];binder.MakeFace=False
  piece=d.addObject('Part::Common','LocalSurface_'+cid.replace('-','_')+'_'+str(i));piece.Base=binder;piece.Tool=box;pieces.append(piece)
 actual=d.addObject('Part::Compound','Contact_'+cid.replace('-','_'));actual.Links=pieces;tag(actual,cid);d.recompute()
 assert actual.Shape.Faces and not actual.Shape.Solids,cid
 assert all(p.Shape.isValid() for p in pieces),(cid,'invalid individual clipped face')
 grip_selections[cid]={'limits':limits,'localSelection':selection,'nativeConstruction':'Individual native final-BodySolid face binders each intersected with local bounds and aggregated as a contact Compound; follows final body and roof recomputation'}
 return actual
grip_selections={}
local_grip('jug-14-center',(-47,47,-94,-.001,182.8,222.01))
round_full=local_grip('round-sloper-3-center',(-148,148,-94,-29,145,215))
gap=d.addObject('Part::Box','RoundSloperCenterGap');gap.Length=94;gap.Width=120;gap.Height=110;gap.Placement.Base=V(-47,-110,135)
for key in ['NodeID','NodeRole','ContactID']:round_full.removeProperty(key)
round_split=cut(d,'RoundSloperPairedShoulders',round_full,gap);tag(round_split,'round-sloper-3-center')
for side,sign in [('left',-1),('right',1)]:
 a,b=(148,258) if sign==1 else (-258,-148)
 local_grip('flat-sloper-2-'+side,(a,b,-94,-39,135,215))
 a,b=(258,356) if sign==1 else (-356,-258)
 local_grip('jug-1-'+side,(a,b,-110,-.001,137,210))
d.recompute()
assert d.HangTenBoardManifest==manifest
bad=[(o.Name,list(o.State)) for o in d.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}];assert not bad,bad
contacts=[o for o in d.Objects if getattr(o,'NodeRole','')=='contact'];assert len(contacts)==30
for c in contacts:assert c.Shape.Faces and not c.Shape.Solids,c.Name
sketches=[o for o in d.Objects if o.TypeId=='Sketcher::SketchObject'];assert all(o.FullyConstrained for o in sketches)
folder=w/'candidate';folder.mkdir(exist_ok=True);(folder/'assets').mkdir(exist_ok=True);out=folder/'metolius-simulator-3d.FCStd';d.saveAs(str(out))
r={'sourceSHA256':hashlib.sha256(out.read_bytes()).hexdigest(),'silhouetteBezierSpansRightXZ':spans,'transitionSections':section_report,'depthFloorCorrections':corrections,'allNewGeometryValues':'Operator-selected display estimates; exact native section loops use existing CAD only, no pixels or reference mesh','finalBody':'BodySolid','contactCount':30,'fullyConstrainedSketchCount':len(sketches),'rawManifestUnchanged':True}
r.update({'gripSelections':grip_selections,'functionalProbe':json.loads((w/'probe-design.json').read_text())})
(w/'authored-design.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
