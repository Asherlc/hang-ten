import FreeCAD as A, json,time,statistics
from pathlib import Path
w=Path(__file__).resolve().parent
d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'))
rows=[]
for i,f in enumerate(d.BodySolid.Shape.Faces):
 t=time.monotonic();p,tri=f.tessellate(.28);ts=time.monotonic()-t
 costs=[]
 for k in range(min(7,len(tri))):
  indices=tri[int(k*len(tri)/min(7,len(tri)))];q=sum((p[j] for j in indices),A.Vector())*(1/3)
  t=time.monotonic();f.Surface.parameter(q);costs.append(time.monotonic()-t)
 s=f.Surface;b=f.BoundBox;o=f.optimalBoundingBox();r={'face':i+1,'surface':str(type(s)),'triangles':len(tri),'tessellateSeconds':ts,'parameterMedianSeconds':statistics.median(costs) if costs else 0,'parameterMaxSeconds':max(costs,default=0),'bounds':[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],'optimalBounds':[o.XMin,o.YMin,o.ZMin,o.XMax,o.YMax,o.ZMax]}
 for name in ['UDegree','VDegree','NbUPoles','NbVPoles','NbUKnots','NbVKnots']:
  if hasattr(s,name):r[name]=getattr(s,name)
 rows.append(r)
 (w/'face-cost-progress.json').write_text(json.dumps({'lastFace':i+1,'faceCount':len(d.BodySolid.Shape.Faces),'rows':rows},indent=2))
report={'rows':rows,'estimatedOwnFaceCentroidSeconds':sum(r['triangles']*r['parameterMedianSeconds'] for r in rows),'triangleCount':sum(r['triangles'] for r in rows)}
(w/'face-cost.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
print(json.dumps(sorted(rows,key=lambda r:r['triangles']*r['parameterMedianSeconds'],reverse=True)[:16],indent=2))
