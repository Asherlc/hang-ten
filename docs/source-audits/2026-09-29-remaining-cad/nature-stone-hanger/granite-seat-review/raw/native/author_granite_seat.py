from pathlib import Path
import json,hashlib,math
import FreeCAD as App,Part,Sketcher
w=Path(__file__).resolve().parent;doc=App.openDocument(str(w/'prior.FCStd'));doc.recompute()
manifest=doc.HangTenBoardManifest
old_contacts={o.ContactID:o.Shape.copy()for o in doc.Objects if hasattr(o,'ContactID')}
old_body=doc.CordSeat_Right.Shape.copy();old_wood=doc.Cavity3.Shape.copy();old_stone=doc.StoneRoundover.Shape.copy()
# Read-only regression before edit: intersection of pre-union wood and stone.
red={'woodSource':'Cavity3','combinedBody':'CordSeat_Right','combinedBodyContainsStoneExpected':True,'woodStoneOverlapMM3':old_wood.common(old_stone).Volume,'woodStoneMustNotOverlap':old_wood.common(old_stone).Volume<1e-6,'graniteContactAreaMM2':old_contacts['edge-front-20mm-granite'].Area}
assert red['woodStoneMustNotOverlap'] is False
(w/'red-regression.json').write_text(json.dumps(red,indent=2)+'\n')
# Deliberate analytic lower outline. Preserve upper rail arcs and line verbatim.
V=App.Vector
for i in range(5):
 profile=doc.getObject('FrontTwentyProfile'+str(i));upper=[g.copy()for g in profile.Geometry[:3]]
 right=upper[2].EndPoint;left=upper[0].StartPoint
 # Existing geometry follows upper-left -> upper-right clockwise.
 assert right.x>0 and left.x<0
 rr=2.4;rightcorner=V(40,-36.6,0);leftcorner=V(-40,-36.6,0)
 lower=[Part.LineSegment(right,V(40,-26,0)),Part.LineSegment(V(40,-26,0),rightcorner),Part.Arc(rightcorner,V(37.6+rr/math.sqrt(2),-36.6-rr/math.sqrt(2),0),V(37.6,-39,0)),Part.LineSegment(V(37.6,-39,0),V(-37.6,-39,0)),Part.Arc(V(-37.6,-39,0),V(-37.6-rr/math.sqrt(2),-36.6-rr/math.sqrt(2),0),leftcorner),Part.LineSegment(leftcorner,V(-40,-26,0)),Part.LineSegment(V(-40,-26,0),left)]
 for sketch,geoms in [(profile,upper+lower),(doc.getObject('FrontTwentyLower'+str(i)),lower)]:
  for j in reversed(range(sketch.ConstraintCount)):sketch.delConstraint(j)
  for j in reversed(range(sketch.GeometryCount)):sketch.delGeometry(j)
  for g in geoms:
   n=sketch.addGeometry(g,False);sketch.addConstraint(Sketcher.Constraint('Block',n))
# Keep depth corners at the bottom; round only the front lip at the top.
edge_indices=[]
for i,e in enumerate(doc.StoneInsert.Shape.Edges):
 b=e.BoundBox
 if (b.YLength>19.9 and abs(b.ZMin+39)<1e-6) or (b.XLength>79.9 and abs(b.YMin+17.5)<1e-6 and abs(b.ZMin+26)<1e-6):edge_indices.append(i+1)
assert len(edge_indices)==3,edge_indices
doc.StoneRoundover.Edges=[(i,2.4,2.4)for i in edge_indices]
doc.recompute()
seat=doc.addObject('Part::Cut','GraniteInsertSeat');seat.Base=doc.Cavity3;seat.Tool=doc.StoneRoundover;seat.Refine=False
doc.InsertUnion.Base=seat;doc.recompute()
body=doc.CordSeat_Right;stone=doc.StoneRoundover
skin=doc.BodySkin;skin.Support=[(body,['Face'+str(i+1)for i in range(len(body.Shape.Faces))])];doc.recompute()
exposed=[];exposure=[]
for i,f in enumerate(stone.Shape.Faces):
 area=f.common(skin.Shape).Area;exposure.append({'face':i+1,'area':f.Area,'exposedArea':area})
 if area>1e-6:
  assert abs(area-f.Area)<1e-4,exposure[-1]
  exposed.append('Face'+str(i+1))
doc.StoneSkin.Support=[(stone,exposed)];doc.recompute()
contact=doc.Region_edge_front_20mm_granite
assert contact.Base==skin or contact.Tool==skin
assert contact.Base==doc.StoneSkin or contact.Tool==doc.StoneSkin
contacts={}
for o in doc.Objects:
 if hasattr(o,'ContactID'):
  prior=old_contacts[o.ContactID];new=o.Shape
  contacts[o.ContactID]={'areaMM2':new.Area,'oldMinusNewAreaMM2':prior.cut(new).Area,'newMinusOldAreaMM2':new.cut(prior).Area,'bboxYDepthMM':new.BoundBox.YLength,'valid':new.isValid()}
  if o.ContactID!='edge-front-20mm-granite':
   assert contacts[o.ContactID]['oldMinusNewAreaMM2']<1e-6 and contacts[o.ContactID]['newMinusOldAreaMM2']<1e-6,contacts[o.ContactID]
  assert new.isValid() and new.Area>1
assert len(contacts)==8
assert doc.HangTenBoardManifest==manifest
assert seat.Shape.isValid() and body.Shape.isValid() and len(body.Shape.Solids)==1
assert seat.Shape.common(stone.Shape).Volume<1e-6
assert abs(contact.Shape.BoundBox.YLength-20)<1e-6
assert contact.Shape.cut(doc.StoneSkin.Shape).Area<1e-6
assert contact.Shape.cut(skin.Shape).Area<1e-6
assert all(not(set(o.State)&{'Invalid','Error','Touched','Recompute'})for o in doc.Objects)
b=body.Shape.optimalBoundingBox(False,False)
assert max(abs(a-bb)for a,bb in zip([b.XLength,b.YLength,b.ZLength],[105,35,105]))<1e-6
report={'status':'native-author-pass','priorSHA256':hashlib.sha256((w/'prior.FCStd').read_bytes()).hexdigest(),'red':red,'woodSeatStoneOverlapMM3':seat.Shape.common(stone.Shape).Volume,'woodSeatValid':seat.Shape.isValid(),'combinedBodyValid':body.Shape.isValid(),'combinedSolidCount':len(body.Shape.Solids),'combinedEnvelopeMM':[b.XLength,b.YLength,b.ZLength],'manifestRawPreserved':True,'contacts':contacts,'exposedStoneFaceSelection':exposed,'stoneFaceExposure':exposure,'changedExistingObjects':['FrontTwentyProfile0…4','FrontTwentyLower0…4','StoneRoundover','InsertUnion','BodySkin','StoneSkin'],'addedObjects':['GraniteInsertSeat'],'stoneFilletEdges':edge_indices,'removedBodyVolumeMM3':old_body.cut(body.Shape).Volume,'addedBodyVolumeMM3':body.Shape.cut(old_body).Volume,'estimates':'80x20x13 insert and existing placement retained; 2.4mm bottom corner and front lip radius retained from existing author as display estimates; lower sidewalls at x=+-40 chosen to meet existing insert and upper rail endpoints retained verbatim. Source-supported 20mm granite grip depth preserved.'}
out=w/'nature-stone-hanger.FCStd';doc.saveAs(str(out));report['sourceSHA256']=hashlib.sha256(out.read_bytes()).hexdigest();(w/'green-native-report.json').write_text(json.dumps(report,indent=2)+'\n')
# Retain exact native meshes for whole-board engineering previews (not product rendering).
meshes={}
for name,shape in [('priorBody',old_body),('priorStone',old_stone),('body',body.Shape),('wood',seat.Shape),('stone',stone.Shape),('graniteContact',contact.Shape)]:
 vs,ts=shape.tessellate(0.16);meshes[name]={'vertices':[[v.x,v.y,v.z]for v in vs],'triangles':ts}
(w/'native-preview-meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
# Native section wires through center support overlap/seam review.
sections={}
plane=Part.makePlane(120,60,V(0,-30,-60),V(1,0,0))
for name,shape in [('priorBody',old_body),('priorStone',old_stone),('body',body.Shape),('stone',stone.Shape)]:
 sections[name]=[[[v.x,v.y,v.z]for v in e.discretize(Deflection=0.12)]for e in shape.section(plane).Edges]
(w/'native-sections.json').write_text(json.dumps(sections)+'\n')
print(json.dumps(report,indent=2));App.closeDocument(doc.Name)
