from pathlib import Path
import json,hashlib
import FreeCAD as A
w=Path(__file__).resolve().parent;p=w/'native-author/nature-stone-hanger.FCStd';sha=hashlib.sha256(p.read_bytes()).hexdigest();d=A.openDocument(str(p));d.recompute();s=d.getObject('CordSeat_Right').Shape
m=A.Matrix();m.A11=-1;t=s.copy();t.transformShape(m,False,False)
a=s.cut(t);b=t.cut(s)
r={'sourceSHA256':sha,'plane':'native X=0','originalValid':s.isValid(),'reflectedValid':t.isValid(),'originalVolumeMM3':s.Volume,'reflectedVolumeMM3':t.Volume,'originalMinusReflectedMM3':a.Volume,'reflectedMinusOriginalMM3':b.Volume}
assert s.isValid() and t.isValid() and abs(a.Volume)<1e-7 and abs(b.Volume)<1e-7,r
assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
r['status']='pass';(w/'native-symmetry-isometry.json').write_text(json.dumps(r,indent=2)+'\n');print(r);A.closeDocument(d.Name)
