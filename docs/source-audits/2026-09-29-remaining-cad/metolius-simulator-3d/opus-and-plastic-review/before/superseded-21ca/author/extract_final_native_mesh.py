import sys,json
from pathlib import Path
import FreeCAD as A,Part
w=Path.cwd()/'.context/placid-badger/metolius-simulator-3d-opus-corrections'
d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));d.recompute();s=d.getObject('BodySolid').Shape;v,f=s.tessellate(.28);(w/'final-native-body-mesh.json').write_text(json.dumps({'p':[[p.x,p.y,p.z] for p in v],'t':f,'bounds':str(s.BoundBox),'volume':s.Volume,'solids':len(s.Solids)}))
print(str(s.BoundBox),len(s.Solids))
