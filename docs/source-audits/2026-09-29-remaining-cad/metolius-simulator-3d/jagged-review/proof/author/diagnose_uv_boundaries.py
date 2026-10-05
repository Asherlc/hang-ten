import FreeCAD as A,json,sys,math
from pathlib import Path
w=Path(__file__).resolve().parent;sys.path.insert(0,str(Path.cwd()/'Tools/HangboardCAD'));import compile_board as c
d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));shape=d.BodySolid.Shape;p,t=shape.tessellate(.28);bad=[r for r in json.loads((w/'final-normal-comparison.json').read_text())['comparisons'] if r['angleDegrees']>.001];ids=sorted(set(r['triangle'] for r in bad));cache=c._uv_node_normal_cache(shape,p,[t[i] for i in ids],.28);rows=[]
for row in bad:
 idx=ids.index(row['triangle']);r=dict(row)
 if idx not in cache:r['nowLegacyFallback']=True;rows.append(r);continue
 fi=cache[idx][0];f=shape.Faces[fi];point=p[t[row['triangle']][row['corner']]];uv=min(f.getUVNodes(),key=lambda v:(f.Surface.value(*v)-point).Length);inverse=f.Surface.parameter(point);s=f.Surface
 r.update({'face':fi+1,'point':[*point],'nativeUV':uv,'inverseUV':inverse,'parameterRange':f.ParameterRange,'UVPositionErrorMM':(s.value(*uv)-point).Length,'inversePositionErrorMM':(s.value(*inverse)-point).Length})
 for axis in ['U','V']:
  if hasattr(s,axis+'Degree'):
   degree=getattr(s,axis+'Degree');ks=getattr(s,'get'+axis+'Knots')();ms=getattr(s,'get'+axis+'Multiplicities')();r[axis+'Degree']=degree;r[axis+'C0Knots']=[k for k,m in zip(ks,ms) if m>=degree]
 rows.append(r)
(w/'uv-boundary-diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
