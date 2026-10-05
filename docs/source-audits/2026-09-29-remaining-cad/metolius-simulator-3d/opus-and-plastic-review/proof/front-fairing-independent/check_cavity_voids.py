import sys,json,hashlib
from pathlib import Path
import FreeCAD as A
p=Path(__file__).resolve().parent;source=Path(sys.argv[1]);out=Path(sys.argv[2]);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();h=sha(source);d=A.openDocument(str(source.resolve()));d.recompute();body=d.BodySolid.Shape;manifest=json.loads(d.HangTenBoardManifest);rows=[];fail=[]
for contact in manifest['contacts']:
 cid=contact['id'];cutter=d.getObject('Cutter_'+cid.replace('-','_'))
 if cutter is None:continue
 intersection=body.common(cutter.Shape);row={'contactID':cid,'cutterValid':cutter.Shape.isValid(),'cutterSolidCount':len(cutter.Shape.Solids),'bodyIntersectionVolumeMM3':intersection.Volume,'bodyIntersectionSolidCount':len(intersection.Solids)};rows.append(row)
 if not row['cutterValid'] or row['cutterSolidCount']!=1 or row['bodyIntersectionVolumeMM3']!=0 or row['bodyIntersectionSolidCount']!=0:fail.append(cid+' cavity subtracts entire native cutter intersection')
 print(cid,row['bodyIntersectionVolumeMM3'],flush=True)
if len(rows)!=24:fail.append('24 native cavity cutters')
if sha(source)!=h:fail.append('source bytes unchanged')
r={'status':'pass' if not fail else 'fail','blockingFindings':fail,'sourceSHA256':h,'cavityChecks':rows,'sourceBytesUnchanged':sha(source)==h,'limits':['Native full-cutter intersection detects silently filled cavities directly; exact zero-volume/zero-solid result required.','This complements published-depth/contact checks and does not infer hole dimensions from images.']};out.write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);print(json.dumps({'status':r['status'],'blockingFindings':fail}));raise SystemExit(bool(fail))
