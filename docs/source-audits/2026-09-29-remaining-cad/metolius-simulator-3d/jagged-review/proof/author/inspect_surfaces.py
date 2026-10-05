import FreeCAD as A
from pathlib import Path
w=Path.cwd()/'.context/placid-badger/metolius-simulator-3d-jagged/native-author';d=A.openDocument(str(w/'probe-source.FCStd'));d.recompute()
body=d.getObject('BodySolid');base=d.getObject('ShellWithContinuousShoulders');bs=[f.Surface for f in base.Shape.Faces]
print('isSame doc',bs[0].isSame.__doc__)
print('native-carrier-matches',sum(any(type(f.Surface)==type(s) and f.Surface.isSame(s,1e-7,1e-7) for s in bs) for f in body.Shape.Faces),'of',len(body.Shape.Faces),flush=True)
A.closeDocument(d.Name)
