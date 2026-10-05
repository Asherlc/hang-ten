import FreeCAD as App, Part, json, hashlib, math
from pathlib import Path
root=Path.cwd(); base=root/'.context/placid-badger/port-cord-physics/physical-review'; pkg=root/'.context/placid-badger/port-cord-physics/solver/anchor-astar/isolated-root/Hangboards/frictitious-port-a-board'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((pkg/'suspension.json').read_text());desc=json.loads((pkg/'assets/primary.model.json').read_text());doc=App.openDocument(str(pkg/'frictitious-port-a-board.FCStd'));body=doc.getObject('RightBackEntryCut');shape=body.Shape
vec=lambda p:App.Vector(*p)
rt=lambda p:[p.x/1000,p.z/1000,-p.y/1000]
native=lambda p:App.Vector(p[0]*1000,-p[2]*1000,p[1]*1000)
pose=data['suspension']['canonicalPoses']['front-upright']; bounds=desc['modelBounds'];anchor=[(bounds['min'][i]+bounds['max'][i])/2 for i in range(3)];anchor[1]=bounds['max'][1]
anchor=[anchor[i]+data['suspension']['anchor']['offsetFromBoardBounds'][i]-pose['translation'][i] for i in range(3)]
rows={}
for sid,route in pose['wrappedRoutes'].items():
 p=native(route[0]);vertex=Part.Vertex(p);dist,pairs,info=shape.distToShape(vertex);q=pairs[0][0];fs=[]
 for i,f in enumerate(shape.Faces,1):
  fd=f.distToShape(Part.Vertex(q))[0]
  if fd<1e-5:
   u,v=f.Surface.parameter(q);n=f.normalAt(u,v);fs.append({'face':i,'type':str(type(f.Surface)),'normalRuntime':[n.x,n.z,-n.y]})
 a=vec(anchor)-vec(route[0]);a.normalize();b=vec(route[1])-vec(route[0]);b.normalize();force=a+b
 rows[sid]={'firstRoutePointRuntime':route[0],'nextPointRuntime':route[1],'supportLocalRuntime':anchor,'distanceToNativeWoodMM':dist,'nearestWoodPointRuntime':rt(q),'nearestFaces':fs,'unitTensionSumRuntime':list(force),'kinkTurnDegrees':math.degrees(math.acos(max(-1,min(1,-a.dot(b))))),'tangentForceMagnitudeByFace':[{'face':f['face'],'magnitude':(force-vec(f['normalRuntime'])*force.dot(vec(f['normalRuntime']))).Length} for f in fs]}
objects=[]
for o in doc.Objects:
 if 'Entry' in o.Name or 'Well' in o.Name:
  objects.append({'name':o.Name,'type':o.TypeId,'shapeBounds':str(o.Shape.BoundBox) if hasattr(o,'Shape') else None,'radius':float(o.Radius) if hasattr(o,'Radius') else None,'height':float(o.Height) if hasattr(o,'Height') else None})
report={'hashes':{str(p.relative_to(pkg)):sha(p) for p in [pkg/'frictitious-port-a-board.FCStd',pkg/'assets/primary.usdz',pkg/'assets/primary.model.json',pkg/'suspension.json']},'bodyValid':shape.isValid(),'bodySolids':len(shape.Solids),'bodyFaces':len(shape.Faces),'nativeFeatures':objects,'uprightFirstBearingAnalysis':rows,'sourceSaved':False}
(base/'anchor-first-bearing.json').write_text(json.dumps(report,indent=2)+'\n');App.closeDocument(doc.Name);print(json.dumps(report,indent=2))
