import FreeCAD as A,json,sys,math,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent;w=p.parent;root=Path.cwd();sys.path.insert(0,str(root/'.context/placid-badger/pxr311'));sys.path.insert(0,str(root/'Tools/HangboardCAD'));import compile_board as c
source=w/'candidate/metolius-simulator-3d.FCStd';h=hashlib.sha256(source.read_bytes()).hexdigest();assert h=='b7223032abe4b5c00a8b16d8ddcafed8b836d806795f1d37bbffab80ce5560ef';d=A.openDocument(str(source));shape=d.BodySolid.Shape;points,triangles=shape.tessellate(.28);ti=37634;triangle=triangles[ti];cache=c._uv_node_normal_cache(shape,points,[triangle],.28);r={'sourceSHA256':h,'compilerSHA256':hashlib.sha256(Path('Tools/HangboardCAD/compile_board.py').read_bytes()).hexdigest(),'triangle':ti,'indices':triangle,'cacheOwner':cache[0][0] if 0 in cache else None};a,b,cc=[points[i] for i in triangle];flat=(b-a).cross(cc-a);flat.normalize();center=(a+b+cc)/3;matches=[]
for i,f in enumerate(shape.Faces):
 box=f.BoundBox;box.enlarge(.56)
 if not box.isInside(center):continue
 uv=f.Surface.parameter(center);distance=(f.Surface.value(*uv)-center).Length
 if distance>.420001 or not f.isPartOfDomain(*uv):continue
 normal=f.normalAt(*uv);matches.append({'face':i,'centroidUV':uv,'distanceMM':distance,'alignment':abs(normal.dot(flat)),'range':f.ParameterRange})
matches.sort(key=lambda x:(x['distanceMM'],-x['alignment']));r['legacyOwnerCandidates']=matches[:6];owners=sorted(set([x['face'] for x in matches[:2]]+[cache[0][0]] if 0 in cache else [x['face'] for x in matches[:2]]));rows=[]
for fi in owners:
 f=shape.Faces[fi];surface=f.Surface
 for corner,index in enumerate(triangle):
  q=points[index];nodes=f.getUVNodes();uv=min(nodes,key=lambda v:(surface.value(*v)-q).Length);inverse=surface.parameter(q);un=f.normalAt(*uv);vn=f.normalAt(*inverse);dot=un.dot(vn)/(un.Length*vn.Length);row={'face':fi,'corner':corner,'pointMM':[q.x,q.y,q.z],'uv':uv,'inverseUV':inverse,'uvPositionErrorMM':(surface.value(*uv)-q).Length,'inversePositionErrorMM':(surface.value(*inverse)-q).Length,'normalDifferenceDegrees':math.degrees(math.acos(max(-1,min(1,dot)))),'cachedNormal':[un.x,un.y,un.z],'inverseNormal':[vn.x,vn.y,vn.z],'parameterRange':f.ParameterRange,'surfaceType':type(surface).__name__}
  for axis in ['U','V']:
   if hasattr(surface,axis+'Degree'):row[axis+'Degree']=getattr(surface,axis+'Degree');row[axis+'Knots']=getattr(surface,'get'+axis+'Knots')();row[axis+'Multiplicities']=getattr(surface,'get'+axis+'Multiplicities')()
  rows.append(row)
r['corners']=rows
legacy=c._surface_normals(shape,points,[triangle],.28);fast=c._surface_normals(shape,points,[triangle],.28,uv_nodes=True);r['isolatedAnglesDegrees']=[math.degrees(math.acos(max(-1,min(1,legacy[2][legacy[1][0][j]].dot(fast[2][fast[1][0][j]]))))) for j in range(3)];r['sourceBytesUnchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==h;(p/'uv-normal-b722-diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);print(json.dumps({'triangle':ti,'cachedOwner':r['cacheOwner'],'legacyOwner':matches[0]['face'],'isolatedAngles':r['isolatedAnglesDegrees']},indent=2))
