import FreeCAD as A,Part,json,time
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));rows=[]
for index in [25,26,41,44,46]:
 f=d.BodySolid.Shape.Faces[index];p,t=f.tessellate(.28);start=time.monotonic();uv=f.getUVNodes();elapsed=time.monotonic()-start
 errs=[(f.Surface.value(v[0],v[1])-q).Length for q,v in zip(p,uv)]
 start=time.monotonic();nn=[f.normalAt(v[0],v[1]) for v in uv];normalSeconds=time.monotonic()-start
 rows.append({'face':index+1,'points':len(p),'uvCount':len(uv),'triangles':len(t),'maximumPointReconstructionErrorMm':max(errs),'getUVSeconds':elapsed,'allAnalyticVertexNormalsSeconds':normalSeconds})
(w/'face-uv-probe.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
