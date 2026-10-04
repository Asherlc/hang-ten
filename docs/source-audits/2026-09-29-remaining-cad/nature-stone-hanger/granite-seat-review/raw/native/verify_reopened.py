from pathlib import Path
import json,hashlib
import FreeCAD as App,Part
w=Path(__file__).resolve().parent
before=App.openDocument(str(w/'prior.FCStd'));before.recompute();after=App.openDocument(str(w/'nature-stone-hanger.FCStd'));after.recompute()
assert all(not(set(o.State)&{'Invalid','Error','Touched','Recompute'})for o in after.Objects)
assert before.HangTenBoardManifest==after.HangTenBoardManifest
assert after.Region_edge_front_20mm_granite.Shape.common(after.GraniteInsertSeat.Shape).Area<1e-6
checks={}
for name in ['LeftAdjustment0','LeftAdjustment1','LeftAdjustment2','RightAdjustment0','RightAdjustment1','RightAdjustment2','LeftVisibleMouth','RightVisibleMouth','LeftVerticalCordGroove','RightVerticalCordGroove']:
 a=before.getObject(name).Shape;b=after.getObject(name).Shape
 checks[name]={'beforeMinusAfterMM3':a.cut(b).Volume,'afterMinusBeforeMM3':b.cut(a).Volume};assert max(checks[name].values())<1e-7
# Existing physical side material around passage/notches/grooves is identical.
for name,x in [('leftSide',-55),('rightSide',45)]:
 box=Part.makeBox(10,40,110,App.Vector(x,-20,-55));a=before.CordSeat_Right.Shape.common(box);b=after.CordSeat_Right.Shape.common(box)
 checks[name]={'beforeMinusAfterMM3':a.cut(b).Volume,'afterMinusBeforeMM3':b.cut(a).Volume};assert max(checks[name].values())<1e-6
# Recompute after harmless document recompute confirms no external import dependencies.
external=[]
for o in after.Objects:
 for linked in o.OutList:
  if linked.Document!=after:external.append([o.Name,linked.Name])
assert not external
r={'status':'pass-reopened','sourceSHA256':hashlib.sha256((w/'nature-stone-hanger.FCStd').read_bytes()).hexdigest(),'rawManifestPreserved':True,'graniteContactWoodCommonAreaMM2':after.Region_edge_front_20mm_granite.Shape.common(after.GraniteInsertSeat.Shape).Area,'nativeReferencesExternal':external,'cordInputAndSideVolumeChecks':checks,'nativeObjectTypes':{n:after.getObject(n).TypeId for n in ['GraniteInsertSeat','StoneRoundover','InsertUnion','BodySkin','StoneSkin']}}
(w/'reopened-verification.json').write_text(json.dumps(r,indent=2)+'\n')
mesh=json.loads((w/'native-preview-meshes.json').read_text())
vs,ts=before.Region_edge_front_20mm_granite.Shape.tessellate(0.16);mesh['priorGraniteContact']={'vertices':[[v.x,v.y,v.z]for v in vs],'triangles':ts};(w/'native-preview-meshes.json').write_text(json.dumps(mesh,separators=(',',':'))+'\n')
V=App.Vector;plane=Part.Face(Part.makePolygon([V(0,-30,-60),V(0,30,-60),V(0,30,60),V(0,-30,60),V(0,-30,-60)]));sections={}
for name,s in [('priorBody',before.CordSeat_Right.Shape),('priorStone',before.StoneRoundover.Shape),('body',after.CordSeat_Right.Shape),('stone',after.StoneRoundover.Shape)]:sections[name]=[[[v.x,v.y,v.z]for v in e.discretize(Deflection=0.12)]for e in s.section(plane).Edges]
(w/'native-sections.json').write_text(json.dumps(sections)+'\n');assert all(sections.values());print(json.dumps(r,indent=2));App.closeDocument(before.Name);App.closeDocument(after.Name)
