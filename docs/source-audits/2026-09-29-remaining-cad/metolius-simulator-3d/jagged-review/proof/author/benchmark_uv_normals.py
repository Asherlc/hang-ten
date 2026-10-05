import FreeCAD as A,Part,json,time,sys,math,collections,itertools,random
from pathlib import Path
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'))
import compile_board as compiler
d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));shape=d.BodySolid.Shape
points,triangles=shape.tessellate(.28);start=time.monotonic();grid=collections.defaultdict(list);tol=.00002
for fi,f in enumerate(shape.Faces):
 f.tessellate(.28)
 for uv in f.getUVNodes():
  q=f.Surface.value(*uv);n=f.normalAt(*uv);n.normalize();key=tuple(math.floor(v/tol) for v in q);grid[key].append((q,fi,n))
indexSeconds=time.monotonic()-start;start=time.monotonic();matches=[];missing=0
for p in points:
 key=tuple(math.floor(v/tol) for v in p);found={}
 for delta in itertools.product([-1,0,1],repeat=3):
  for q,fi,n in grid.get(tuple(a+b for a,b in zip(key,delta)),[]):
   distance=(p-q).Length
   if distance<=tol and (fi not in found or distance<found[fi][0]):found[fi]=(distance,n)
 matches.append(found)
 if not found:missing+=1
matchSeconds=time.monotonic()-start;owners=[];counts=collections.Counter()
for t in triangles:
 ids=set(matches[t[0]])&set(matches[t[1]])&set(matches[t[2]])
 counts[len(ids)]+=1;owners.append(next(iter(ids)) if len(ids)==1 else None)
chosen=[]
for fi in [25,26,41,44,46]:
 own=[i for i,v in enumerate(owners) if v==fi]
 chosen+=own[::max(1,len(own)//4)][:4]
start=time.monotonic();errors=[]
for i in chosen:
 t=triangles[i];outp,outt,outn=compiler._surface_normals(shape,points,[t],.28);fi=owners[i];flat=(points[t[1]]-points[t[0]]).cross(points[t[2]]-points[t[0]]);flat.normalize()
 for vi,old in zip(t,outn):
  new=matches[vi][fi][1]
  if new.dot(flat)<0:new=-new
  angle=math.degrees(math.acos(max(-1,min(1,new.dot(old)))))
  errors.append({'triangle':i,'face':fi+1,'vertex':vi,'normalAngleDegrees':angle})
report={'sourceSHA256':'40e42ed072a72946d11756cd6f92047fd0d5acd79eb33946cb2188441babbbde','triangles':len(triangles),'points':len(points),'indexSeconds':indexSeconds,'matchSeconds':matchSeconds,'unmatchedVertices':missing,'triangleOwnerMultiplicity':dict(counts),'legacyComparisonSeconds':time.monotonic()-start,'legacyComparisonCorners':len(errors),'maximumNormalAngleDegrees':max((r['normalAngleDegrees'] for r in errors),default=None),'comparisons':errors,'limits':'Scratch performance feasibility probe. Unique native UV owner only; ambiguous or unmatched triangles require legacy fallback. No compiler replacement or export.'}
(w/'uv-normal-benchmark.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
