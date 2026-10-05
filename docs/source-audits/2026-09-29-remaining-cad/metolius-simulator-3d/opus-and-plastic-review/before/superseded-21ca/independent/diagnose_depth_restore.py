from pathlib import Path
import json,hashlib,sys
import FreeCAD as A
p=Path(__file__).resolve().parent;source=p.parent/'candidate/metolius-simulator-3d.FCStd';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();h=sha(source);d=A.openDocument(str(source));d.recompute();obj=d.getObject('BodySolid');params=d.getObject('Parameters')
def stats(s):
 b=s.optimalBoundingBox();return {'volumeMM3':s.Volume,'areaMM2':s.Area,'boundsMM':[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],'valid':s.isValid(),'solids':len(s.Solids),'faces':len(s.Faces),'edges':len(s.Edges),'vertices':len(s.Vertexes),'maximumToleranceMM':s.getTolerance(1)}
initial=obj.Shape.copy();rows=[{'phase':'before','geometry':stats(initial)}];regions={o.ContactID:o.Shape.copy() for o in d.Objects if getattr(o,'NodeRole','')=='contact'}
params.Depth_edge_11_left=16;d.recompute();rows.append({'phase':'edited16','geometry':stats(obj.Shape)})
params.Depth_edge_11_left=14;d.recompute();restored=obj.Shape.copy();rows.append({'phase':'restored14','geometry':stats(restored)})
d.recompute();rows.append({'phase':'repeatRecompute','geometry':stats(obj.Shape)})
contacts=[]
for o in d.Objects:
 if getattr(o,'NodeRole','')=='contact':
  a,b=stats(regions[o.ContactID]),stats(o.Shape);contacts.append({'id':o.ContactID,'areaDeltaMM2':b['areaMM2']-a['areaMM2'],'maximumBoundDeltaMM':max(abs(x-y) for x,y in zip(a['boundsMM'],b['boundsMM'])),'valid':b['valid']})
missing=initial.cut(restored);added=restored.cut(initial);delta=restored.Volume-initial.Volume
r={'sourceSHA256':h,'sourceBytesUnchanged':sha(source)==h,'states':[(o.Name,list(o.State)) for o in d.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}],'phases':rows,'restoreVolumeDeltaMM3':delta,'relativeVolumeDelta':delta/initial.Volume,'bidirectionalDifference':{'missingVolumeMM3':missing.Volume,'addedVolumeMM3':added.Volume,'missingSolids':len(missing.Solids),'addedSolids':len(added.Solids)},'contacts':contacts,'scope':'Read-only edit/restore diagnosis, no tolerances changed and no save.'};(p/'depth-restore-diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
