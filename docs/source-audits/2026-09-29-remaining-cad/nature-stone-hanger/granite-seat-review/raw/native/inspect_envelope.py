from pathlib import Path
import json
import FreeCAD as App
w=Path(__file__).resolve().parent
out={}
def bb(b):return {'lengths':[b.XLength,b.YLength,b.ZLength],'limits':[b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax]}
for name in ['prior.FCStd','nature-stone-hanger.FCStd']:
 doc=App.openDocument(str(w/name));doc.recompute();s=doc.CordSeat_Right.Shape
 r={'beforeTessellationDefault':bb(s.BoundBox),'beforeTessellationOptimalNoTriangulation':bb(s.optimalBoundingBox(False,False))}
 v,t=s.tessellate(.15)
 r['meshVertexBounds']={'lengths':[max(getattr(x,a)for x in v)-min(getattr(x,a)for x in v)for a in ['x','y','z']],'limits':[[min(getattr(x,a)for x in v),max(getattr(x,a)for x in v)]for a in ['x','y','z']]}
 r['afterTessellationDefault']=bb(s.BoundBox);r['afterTessellationOptimalNoTriangulation']=bb(s.optimalBoundingBox(False,False))
 r['outerOutlineOptimal']=bb(doc.OuterOutline.Shape.optimalBoundingBox(False,False));r['outerRoundoverOptimal']=bb(doc.OuterRoundover.Shape.optimalBoundingBox(False,False))
 out[name]=r;App.closeDocument(doc.Name)
(w/'envelope-diagnostic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
