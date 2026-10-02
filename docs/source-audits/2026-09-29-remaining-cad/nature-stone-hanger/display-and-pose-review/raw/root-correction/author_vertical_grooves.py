from pathlib import Path
import json,hashlib
import FreeCAD as App,Part
w=Path(__file__).resolve().parent;before=w/'before/nature-stone-hanger.FCStd';out=w/'native-author/nature-stone-hanger.FCStd';doc=App.openDocument(str(before));doc.recompute();body=doc.getObject('Port_RightVisibleMouth');old=body.Shape.copy();manifest=doc.HangTenBoardManifest
old_contacts={o.ContactID:o.Shape.copy() for o in doc.Objects if hasattr(o,'ContactID')};node=body.NodeID;role=body.NodeRole
body.removeProperty('NodeID');body.removeProperty('NodeRole')
for label,sign in [('Left',-1),('Right',1)]:
 cylinder=doc.addObject('Part::Cylinder',label+'VerticalCordGroove');cylinder.Radius=1.75;cylinder.Height=110;cylinder.Placement.Base=App.Vector(sign*52.5,0,-55)
 cut=doc.addObject('Part::Cut','CordSeat_'+label);cut.Base=body;cut.Tool=cylinder;cut.Refine=False;doc.recompute();assert cut.Shape.isValid() and len(cut.Shape.Solids)==1;body=cut
body.addProperty('App::PropertyString','NodeID','HangTen');body.NodeID=node;body.addProperty('App::PropertyString','NodeRole','HangTen');body.NodeRole=role
skin=doc.getObject('BodySkin');skin.Support=[(body,['Face'+str(i+1) for i in range(len(body.Shape.Faces))])];doc.recompute()
assert doc.HangTenBoardManifest==manifest
contacts={}
for o in doc.Objects:
 if hasattr(o,'ContactID'):
  assert o.Shape.isValid() and o.Shape.Area>1
  prior=old_contacts[o.ContactID];contacts[o.ContactID]={'area':o.Shape.Area,'areaDelta':o.Shape.Area-prior.Area,'oldMinusNewArea':prior.cut(o.Shape).Area,'newMinusOldArea':o.Shape.cut(prior).Area}
  assert abs(contacts[o.ContactID]['areaDelta'])<1e-6 and contacts[o.ContactID]['oldMinusNewArea']<1e-6 and contacts[o.ContactID]['newMinusOldArea']<1e-6
assert len(contacts)==8
bbox=body.Shape.optimalBoundingBox(False,False);removed=old.cut(body.Shape);added=body.Shape.cut(old)
assert added.Volume<1e-7
report={'status':'pass-author-probe','bodyFeature':body.Name,'sourceBeforeSHA256':hashlib.sha256(before.read_bytes()).hexdigest(),'manifestRawPreserved':True,'nativeBodyValid':body.Shape.isValid(),'solidCount':len(body.Shape.Solids),'volume':body.Shape.Volume,'removedVolume':removed.Volume,'addedVolume':added.Volume,'envelopeMM':[bbox.XLength,bbox.YLength,bbox.ZLength],'contacts':contacts,'verticalGrooves':{'count':2,'nativeAxis':[0,0,1],'centerYMM':0,'centerAbsXMM':52.5,'radiusMM':1.75,'cutNativeZMM':[-55,55],'numericProvenance':'Operator display estimates; one vertical groove per side is owner/source-supported; not measured from pixels.'},'transverseNotchesPreserved':6}
# Save before tessellation so the retained source cannot inherit mesh caches.
doc.recompute();doc.saveAs(str(out));report['sourceSHA256']=hashlib.sha256(out.read_bytes()).hexdigest()
vertices,triangles=body.Shape.tessellate(float(doc.HangTenTessellationDeflection));mesh={'sourceSHA256':report['sourceSHA256'],'bodyFeature':body.Name,'coordinateFrame':'native-mm','deflectionMM':float(doc.HangTenTessellationDeflection),'vertices':[[v.x,v.y,v.z] for v in vertices],'triangles':triangles}
(w/'native-author/body-mesh.json').write_text(json.dumps(mesh,separators=(',',':'))+'\n');(w/'native-author/author-probe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
App.closeDocument(doc.Name)
