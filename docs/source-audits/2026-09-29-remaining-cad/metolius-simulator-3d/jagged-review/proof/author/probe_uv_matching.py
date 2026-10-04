import FreeCAD as A,json,collections,math
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));rows=[]
for index in [25,26,41,44,46]:
 f=d.BodySolid.Shape.Faces[index];p,t=f.tessellate(.28);uv=f.getUVNodes();pts=[f.Surface.value(*v) for v in uv]
 lookup=collections.defaultdict(list)
 for i,q in enumerate(pts):lookup[tuple(round(x,5) for x in q)].append(i)
 matches=0;maxerr=0
 for q in p:
  choices=lookup.get(tuple(round(x,5) for x in q),[])
  if choices:matches+=1;maxerr=max(maxerr,min((q-pts[i]).Length for i in choices))
 rows.append({'face':index+1,'points':len(p),'UVNodes':len(uv),'matchedAt1e5Quantization':matches,'maxMatchedDistanceMM':maxerr})
(w/'uv-matching.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
