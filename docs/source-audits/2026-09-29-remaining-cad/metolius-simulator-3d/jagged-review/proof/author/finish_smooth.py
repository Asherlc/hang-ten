import sys,json,hashlib,math
from pathlib import Path
import FreeCAD as A,Part,Sketcher
V=A.Vector
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author'
sys.path.insert(0,str(root/'.context/placid-badger/cad-wall-boards'))
from author_wall import cut,tag,face_overlap,normal,surface_clip,bind_cutter
# Resume from the already-built native geometry checkpoint; no reconstruction.
d=A.openDocument(str(w/'probe-source.FCStd'));d.recompute();manifest=d.HangTenBoardManifest;metadata=json.loads(manifest);body=d.getObject('BodySolid');smoothed=d.getObject('ShellWithContinuousShoulders')
spans=[[[p.x,p.y] for p in g.getPoles()] for g in d.getObject('Silhouette2').Geometry[:8]]
section_report=[]
for label,x0,x1,zfloor in [('CenterShoulder',35.,65.,145.),('RoundFlat',130.,166.,135.),('OuterShoulder',238.,278.,135.)]:
 for j in range(4):
  obj=d.getObject(label+'TransitionSection'+str(j));section_report.append({'transition':label,'x':obj.Placement.Base.x,'floorZ':zfloor,'edgeCount':obj.GeometryCount,'origin':'Exact joined analytic native section, aligned rear/outer/floor edges'})
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
predicate=lambda f:normal(f).z>.08 and carrier(f.Surface) in base_carriers
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
