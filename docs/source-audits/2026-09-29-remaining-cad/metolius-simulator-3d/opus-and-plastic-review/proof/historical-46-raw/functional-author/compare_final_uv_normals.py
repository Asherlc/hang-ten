import FreeCAD as A,json,time,sys,math,hashlib
from pathlib import Path
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'));import compile_board as c
source=w/'candidate/metolius-simulator-3d.FCStd';d=A.openDocument(str(source));shape=d.BodySolid.Shape;p,t=shape.tessellate(.28);cache=c._uv_node_normal_cache(shape,p,t,.28);chosen={}
counts={}
for owner,_ in cache.values():counts[owner]=counts.get(owner,0)+1
heavy=sorted(counts,key=counts.get,reverse=True)[:5]
for fi in heavy:
 ids=[i for i,v in cache.items() if v[0]==fi]
 for axis in range(3):
  for extreme in [min,max]:
   index=extreme(ids,key=lambda i:extreme(getattr(p[j],['x','y','z'][axis]) for j in t[i]));chosen[index]='heavy-face spatial boundary'
 for index in ids[::max(1,len(ids)//4)][:4]:chosen[index]='heavy-face interior'
for index in [i for i in range(len(t)) if i not in cache][:24]:chosen[index]='legacy fallback boundary'
regression=w/'superseded-uv-boundary/final-normal-comparison.json'
if regression.exists():chosen={r['triangle']:r['category'] for r in json.loads(regression.read_text())['comparisons']}
indices=sorted(chosen);triangles=[t[i] for i in indices];start=time.monotonic();a=c._surface_normals(shape,p,triangles,.28);legacySeconds=time.monotonic()-start;start=time.monotonic();b=c._surface_normals(shape,p,triangles,.28,uv_nodes=True);uvSeconds=time.monotonic()-start;rows=[]
for n,index in enumerate(indices):
 for j in range(3):
  ap=a[0][a[1][n][j]];bp=b[0][b[1][n][j]];assert (ap-bp).Length==0
  an=a[2][a[1][n][j]];bn=b[2][b[1][n][j]];angle=math.degrees(math.acos(max(-1,min(1,an.dot(bn)))))
  rows.append({'triangle':index,'category':chosen[index],'corner':j,'angleDegrees':angle})
r={'status':'pass' if max(x['angleDegrees'] for x in rows)<.001 else 'review-required','sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'compilerSHA256':hashlib.sha256(Path('Tools/HangboardCAD/compile_board.py').read_bytes()).hexdigest(),'trianglesCompared':len(indices),'cornersCompared':len(rows),'allPositionsExact':True,'maxNormalAngleDegrees':max(x['angleDegrees'] for x in rows),'legacySeconds':legacySeconds,'uvSeconds':uvSeconds,'categoryCounts':{key:sum(x['category']==key for x in rows) for key in set(chosen.values())},'comparisons':rows}
(w/'final-normal-comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='comparisons'},indent=2))
