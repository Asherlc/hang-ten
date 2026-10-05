import FreeCAD as A,Part,json,hashlib,math
from pathlib import Path
w=Path(__file__).resolve().parent;p=w/'candidate/metolius-simulator-3d.FCStd';sha=hashlib.sha256(p.read_bytes()).hexdigest();d=A.openDocument(str(p));d.recompute();body=d.BodySolid.Shape;manifest=d.HangTenBoardManifest;metadata=json.loads(manifest);contacts={o.ContactID:o for o in d.Objects if getattr(o,'NodeRole','')=='contact'};assert len(contacts)==30
facts=[]
for c in metadata['contacts']:
 cid=c['id'];o=contacts[cid];assert o.Shape.Faces and not o.Shape.Solids and o.Shape.isValid(),cid
 if 'depth' in c and c['depth']['range']['minimum'] is not None:
  expected=c['depth']['range']['minimum'];actual=o.Shape.optimalBoundingBox().YLength;facts.append({'id':cid,'expectedMM':expected,'actualMM':actual,'errorMM':abs(expected-actual)})
assert len(facts)==27 and max(x['errorMM'] for x in facts)<.002,facts
assert body.isValid() and len(body.Solids)==1
before=A.openDocument(str(w/'frozen-3ff3/metolius-simulator-3d.FCStd'));before.recompute();upper=Part.makeBox(800,140,120,A.Vector(-400,-110,135));a=before.BodySolid.Shape.common(upper);b=body.common(upper);diff=[a.cut(b).Volume,b.cut(a).Volume];assert max(diff)<1e-5,diff
profiles={}
for label,doc in [('before3ff3',before),('candidate',d)]:
 curves=[]
 for i,g in enumerate(doc.ContinuousFrontRelief.Geometry):
  if not isinstance(g,Part.BSplineCurve):continue
  samples=[]
  for j in range(101):
   u=g.FirstParameter+(g.LastParameter-g.FirstParameter)*j/100;v=g.value(u);t=g.tangent(u)[0];samples.append({'yz':[v.x,v.y],'tiltDegrees':math.degrees(math.atan2(t.x,-t.y))})
  curves.append({'index':i,'polesYZ':[[v.x,v.y] for v in g.getPoles()],'samples':samples})
 profiles[label]=curves
sections=[]
for x in [0,40,100,210]:
 plane=Part.Face(Part.makePolygon([A.Vector(x,-110,-5),A.Vector(x,20,-5),A.Vector(x,20,255),A.Vector(x,-110,255),A.Vector(x,-110,-5)]));sections.append({'xMM':x,'bodyEdges':[[[v.y,v.z] for v in e.discretize(Deflection=.05)] for e in body.section(plane).Edges]})
v,t=body.tessellate(.28);(w/'final-native-body-mesh.json').write_text(json.dumps({'p':[[v.x,v.y,v.z] for v in v],'t':t}))
raw=manifest==before.HangTenBoardManifest;assert raw
joins=[];gs=[(i,g) for i,g in enumerate(d.ContinuousFrontRelief.Geometry) if isinstance(g,Part.BSplineCurve)]
for (ia,a),(ib,b) in zip(gs,gs[1:]):
 if a.EndPoint.y>135.00001:continue
 ta=a.tangent(a.LastParameter)[0];tb=b.tangent(b.FirstParameter)[0];joins.append({'indices':[ia,ib],'joinYZ':[a.EndPoint.x,a.EndPoint.y],'gapMM':(a.EndPoint-b.StartPoint).Length,'tangentAngleDegrees':math.degrees(ta.getAngle(tb))})
assert all(x['gapMM']<1e-8 and x['tangentAngleDegrees']<1e-5 for x in joins),joins
r={'status':'pass','sourceSHA256':sha,'beforeSourceSHA256':hashlib.sha256((w/'frozen-3ff3/metolius-simulator-3d.FCStd').read_bytes()).hexdigest(),'rawManifestExact':raw,'surfaceFinish':metadata['surfaceFinish'],'bodyValid':body.isValid(),'bodySolidCount':len(body.Solids),'contactCount':len(contacts),'depthFactCount':len(facts),'depthFacts':facts,'normalFlags':{'analytic':d.HangTenSurfaceNormals,'uvNative':d.HangTenUVNodeSurfaceNormals},'fullyConstrainedSketchCount':len([o for o in d.Objects if o.TypeId=='Sketcher::SketchObject' and o.FullyConstrained]),'measuredEnvelopeXYZMM':list((body.optimalBoundingBox().XLength,body.optimalBoundingBox().YLength,body.optimalBoundingBox().ZLength)),'upperProtectedZMinimumMM':135,'upperBodyBidirectionalDifferenceVolumesMM3':diff,'nativeLowerTangentJoins':joins,'profiles':profiles,'sections':sections,'sourceUnchanged':hashlib.sha256(p.read_bytes()).hexdigest()==sha}
(w/'author-native-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['profiles','sections','depthFacts']},indent=2));A.closeDocument(before.Name);A.closeDocument(d.Name)
