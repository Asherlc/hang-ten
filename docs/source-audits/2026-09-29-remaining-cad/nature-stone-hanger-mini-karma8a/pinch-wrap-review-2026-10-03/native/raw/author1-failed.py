from pathlib import Path
import FreeCAD as App,Part,json,hashlib
OUT=Path(__file__).resolve().parent
assert App.Version()[:3]==['1','1','3'] and Part.OCC_VERSION=='7.8.1'
d=App.openDocument(str(OUT/'prior/nature-stone-hanger-mini-karma8a.FCStd'));d.recompute()
body=d.FinalSolid.Shape.copy();manifest=d.HangTenBoardManifest
names=['nature_wood','nature_stone','nature_pinch']
original={n:d.getObject(n).Shape.copy() for n in names}
def binder(name,support,elements):
 o=d.addObject('PartDesign::SubShapeBinder',name);o.Support=[(support,elements)];return o
lip=binder('UpperRailMouthLipReference',d.FinalSolid,['Face25'])
mask=d.addObject('Part::Box','UpperRailPressureMask');mask.Length=130;mask.Width=50;mask.Height=50;mask.Placement.Base=App.Vector(-65,-25,19.5)
mask.setExpression('Placement.Base.z','UpperRailMouthLipReference.Shape.BoundBox.ZMax')
lower=d.addObject('Part::Box','LowerRailPressureMask');lower.Length=130;lower.Width=50;lower.Height=50;lower.Placement.Base=App.Vector(-65,-25,-68)
lower.setExpression('Placement.Base.z','GraniteInsert.Shape.BoundBox.ZMin - 50 mm')
external_faces=[5,6,7,17,18,34,37,38,40,48,51,53,55,60,63,66,68,70,71,74]
pressure_base=binder('RailPressureExteriorFaces',d.FinalSolid,['Face'+str(i) for i in external_faces]);pressure_base.Refine=False
upper=d.addObject('Part::Common','UpperRailPressureBand');upper.Base=pressure_base;upper.Tool=mask;upper.Refine=False
bottom=d.addObject('Part::Common','LowerRailPressureBand');bottom.Base=pressure_base;bottom.Tool=lower;bottom.Refine=False
shoulders=binder('RailEndShoulders',d.FinalSolid,['Face'+str(i) for i in [15,16,19,20,32,33,41,42,45,52,59,65]]);shoulders.Refine=False
pressure=d.addObject('Part::Compound','BothRailPressureBands');pressure.Links=[upper,bottom,shoulders]
surface=binder('CompleteExteriorSurface',d.FinalSolid,['Shell1']);surface.Refine=False
remainder=d.addObject('Part::Cut','ExteriorWithoutPressureBand');remainder.Base=surface;remainder.Tool=pressure;remainder.Refine=False
export=d.addObject('Part::Compound','ExportBodySurface');export.Links=[remainder,pressure]
contact=binder('nature_pinch_pressure',pressure,[''])
for o,props in [(export,[('NodeID','nature_body'),('NodeRole','body')]),(contact,[('NodeID','nature_pinch_pressure'),('NodeRole','contact'),('ContactID','pinch-60')])]:
 for p,v in props:o.addProperty('App::PropertyString',p,'HangTen');setattr(o,p,v)
contact.addProperty('App::PropertyBool','HangTenUseBodyTriangles','HangTen');contact.HangTenUseBodyTriangles=True
contact.addProperty('App::PropertyString','HangTenDepthAxis','HangTen');contact.HangTenDepthAxis='Z'
for p in ['NodeID','NodeRole']:d.FinalSolid.removeProperty(p)
d.recompute()
def eq(a,b):
 ab=a.cut(b);ba=b.cut(a)
 return {'aMinusBVolume':ab.Volume,'bMinusAVolume':ba.Volume,'aMinusBArea':ab.Area,'bMinusAArea':ba.Area}
def surface_coverage(source,target):
 mapping={i:[] for i in range(len(source.Faces))};details=[]
 for j,new in enumerate(target.Faces):
  candidates=[];nb=new.BoundBox
  for i,old in enumerate(source.Faces):
   ob=old.BoundBox
   if new.Area>old.Area+1e-7:continue
   if any(getattr(nb,a+'Min')<getattr(ob,a+'Min')-1e-6 or getattr(nb,a+'Max')>getattr(ob,a+'Max')+1e-6 for a in 'XYZ'):continue
   delta=new.cut(old).Area
   if delta<1e-7:candidates.append((i,delta))
  if len(candidates)!=1:
   (OUT/'unmatched-export-face.json').write_text(json.dumps({'exportFace':j+1,'area':new.Area,'bounds':str(nb),'surface':str(type(new.Surface)),'candidates':candidates,'objects':{n:{'shapeType':d.getObject(n).Shape.ShapeType,'faces':len(d.getObject(n).Shape.Faces),'solids':len(d.getObject(n).Shape.Solids),'area':d.getObject(n).Shape.Area,'properties':{k:str(getattr(d.getObject(n),k)) for k in ['MakeFace','Fuse','Refine','Support'] if k in d.getObject(n).PropertiesList}} for n in ['CompleteExteriorSurface','BothRailPressureBands','ExteriorWithoutPressureBand','ExportBodySurface']}},indent=2)+'\n')
   raise AssertionError((j,candidates))
  i,delta=candidates[0];mapping[i].append(new);details.append({'exportFace':j+1,'originalFace':i+1,'offOriginalArea':delta})
 missing=[]
 for i,old in enumerate(source.Faces):
  assert mapping[i],i
  remainder=old.cut(Part.makeCompound(mapping[i]));missing.append(remainder.Area)
 assert max(missing)<1e-7
 return {'aMinusBArea':sum(missing),'bMinusAArea':sum(v['offOriginalArea'] for v in details),'faceMapping':details,'originalFaceCount':len(source.Faces),'exportFaceCount':len(target.Faces)}
r={'passed':False,'bodyEquality':eq(body,d.FinalSolid.Shape),'exportSurfaceEquality':surface_coverage(body,export.Shape),'exportComponentsOverlapArea':remainder.Shape.common(pressure.Shape).Area,'pressureAreaMm2':contact.Shape.Area,'pressureBounds':[contact.Shape.BoundBox.XMin,contact.Shape.BoundBox.XMax,contact.Shape.BoundBox.YMin,contact.Shape.BoundBox.YMax,contact.Shape.BoundBox.ZMin,contact.Shape.BoundBox.ZMax],'pressureFaceCount':len(contact.Shape.Faces),'cutoffMm':mask.Placement.Base.z,'lowerCutoffMm':lower.Placement.Base.z+lower.Height.Value,'maskExpression':str(mask.ExpressionEngine),'originalContactEquality':{n:eq(original[n],d.getObject(n).Shape) for n in names},'newContactOverlapArea':{n:contact.Shape.common(d.getObject(n).Shape).Area for n in names},'pressureOffBodyArea':contact.Shape.cut(d.FinalSolid.Shape).Area,'manifestIdentical':d.HangTenBoardManifest==manifest,'badStates':{o.Name:list(o.State) for o in d.Objects if set(o.State)&{'Invalid','Error','Touched','Recompute'}},'exportValid':export.Shape.isValid(),'nativeBodySolids':len(d.FinalSolid.Shape.Solids)}
(OUT/'author-probe.json').write_text(json.dumps(r,indent=2)+'\n')
assert not r['badStates'] and r['manifestIdentical'] and r['exportValid'] and r['nativeBodySolids']==1
assert max(abs(v) for v in r['bodyEquality'].values())<1e-7
assert max(abs(r['exportSurfaceEquality'][k]) for k in ['aMinusBArea','bMinusAArea'])<1e-7
assert abs(export.Shape.Area-body.Area)<1e-7 and r['exportComponentsOverlapArea']<1e-7
assert max(abs(v) for x in r['originalContactEquality'].values() for v in x.values())<1e-7
assert max(r['newContactOverlapArea'].values())<1e-7 and r['pressureOffBodyArea']<1e-7
assert abs(r['cutoffMm']-19.5)<1e-9 and contact.Shape.Area>1000
out=OUT/'candidate/nature-stone-hanger-mini-karma8a.FCStd';out.parent.mkdir(exist_ok=True);d.saveAs(str(out));App.closeDocument(d.Name)
r.update(passed=True,sourceSHA256=hashlib.sha256(out.read_bytes()).hexdigest())
(OUT/'native-author-proof.json').write_text(json.dumps(r,indent=2)+'\n')
