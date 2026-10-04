import FreeCAD as A, pathlib,json,hashlib,sys
root=pathlib.Path.cwd()
for slug in ["nature-stone-hanger"]:
 path=pathlib.Path(__file__).resolve().parent/'native-author'/('nature-stone-hanger.FCStd');sha=hashlib.sha256(path.read_bytes()).hexdigest();d=A.openDocument(str(path));d.recompute();body=next(o for o in d.Objects if getattr(o,'NodeRole','')=='body');contacts=[o for o in d.Objects if getattr(o,'NodeRole','')=='contact'];p=d.getObject('Parameters')
 assert body.Shape.isValid() and len(body.Shape.Solids)==1
 assert not [(o.Name,o.State)for o in d.Objects if 'Invalid'in o.State]
 assert all(o.FullyConstrained for o in d.Objects if o.TypeId=='Sketcher::SketchObject')
 assert all(o.Shape.isValid() and o.Shape.Area>1 and not o.Shape.Solids for o in contacts)
 orig=body.Shape.Volume;depths={o.Name:o.Shape.BoundBox.YLength for o in contacts};count=len(contacts)
 name='TopSixDepth'if slug=='yy-baguette-evo'else'Thickness'if slug.startswith('captain-')else'FrontDepthScale';old=getattr(p,name);new=old*1.025;setattr(p,name,new);d.recompute()
 assert not [(o.Name,o.State)for o in d.Objects if 'Invalid'in o.State]
 assert body.Shape.isValid() and abs(body.Shape.Volume-orig)>1
 if name=='FrontDepthScale':assert all(o.Shape.BoundBox.YLength>depths[o.Name]for o in contacts if o.ContactID.startswith('edge-front-15'))
 if name=='TopSixDepth':assert all((o.HangTenGripDepthStart-o.HangTenGripDepthEnd).Length>old for o in contacts if o.ContactID in ['edge-6-upper','edge-6-lower'])
 changed=body.Shape.Volume;setattr(p,name,old);d.recompute();delta=body.Shape.Volume-orig
 assert abs(delta)<max(1,orig*1e-5),(slug,delta)
 assert body.Shape.isValid() and all(o.Shape.isValid() for o in contacts)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
 report={'sourceSHA256':sha,'nativeReopenRecompute':'passed','oneValidSolid':True,'contactNodeCount':count,'allContactShapesOpenValid':True,'fullyConstrainedSketches':True,'edit':{'parameter':name,'from':old,'to':new,'bodyVolumeBeforeMM3':orig,'bodyVolumeEditedMM3':changed,'restoredVolumeDeltaMM3':delta},'sourceBytesUnchanged':True}
 (pathlib.Path(__file__).resolve().parent/'native-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(slug,report);A.closeDocument(d.Name)
