import FreeCAD as App,Part,json,math,hashlib,sys
from pathlib import Path
base=Path(__file__).resolve().parent;pkg=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else base/'isolated-root/Hangboards/frictitious-port-a-board';data=json.loads((pkg/'suspension.json').read_text());desc=json.loads((pkg/'assets/primary.model.json').read_text());doc=App.openDocument(str(pkg/'frictitious-port-a-board.FCStd'));shape=doc.getObject('RightBackEntryCut').Shape
vec=lambda p:App.Vector(*p);native=lambda p:App.Vector(p[0]*1000,-p[2]*1000,p[1]*1000);bounds=desc['modelBounds'];anchor=vec([(bounds['min'][i]+bounds['max'][i])/2 for i in range(3)]);anchor.y=bounds['max'][1];anchor+=vec(data['suspension']['anchor']['offsetFromBoardBounds']);rows=[]
for pid,pose in data['suspension']['canonicalPoses'].items():
 support=App.Rotation(*pose['rotation']).inverted().multVec(anchor-vec(pose['translation']));radii={s['id']:s['radius'] for s in data['suspension']['strands']}
 for sid,route in pose['wrappedRoutes'].items():
  path=[list(support)]+route
  for i in range(1,len(path)-1):
   a=vec(path[i-1])-vec(path[i]);a.normalize();b=vec(path[i+1])-vec(path[i]);b.normalize();turn=math.degrees(math.acos(max(-1,min(1,-a.dot(b)))))
   if turn<1:continue
   dist,pairs,info=shape.distToShape(Part.Vertex(native(path[i])));q=pairs[0][0];fs=[];force=a+b
   for fi,f in enumerate(shape.Faces,1):
    if f.distToShape(Part.Vertex(q))[0]>1e-5:continue
    u,v=f.Surface.parameter(q);n=f.normalAt(u,v);n=App.Vector(n.x,n.z,-n.y);tan=(force-n*force.dot(n)).Length
    fs.append({'face':fi,'normalRuntime':list(n),'tangentUnitTension':tan,'normalUnitTension':force.dot(n)})
   rows.append({'pose':pid,'strand':sid,'index':i,'pointRuntime':path[i],'turnDegrees':turn,'centerlineWoodDistanceMM':dist,'radiusMM':radii[sid]*1000,'surfaceGapMM':dist-radii[sid]*1000,'faces':fs})
report={'candidateSHA256':hashlib.sha256((pkg/'suspension.json').read_bytes()).hexdigest(),'turnsOverOneDegree':rows,'notes':'Point-normal diagnostic only. Finite polyline bearing arcs cannot establish equilibrium from individual vertex normals. Free-air corners over 5 degrees and 0.25 mm physical surface gap warrant inspection.'};(base/(sys.argv[2] if len(sys.argv)>2 else 'candidate-native-turns.json')).write_text(json.dumps(report,indent=2)+'\n');App.closeDocument(doc.Name);print('turns',len(rows));print('max turn',max([r['turnDegrees'] for r in rows],default=0));print('free-air over5',json.dumps([r for r in rows if r['turnDegrees']>5 and r['surfaceGapMM']>.25]))
