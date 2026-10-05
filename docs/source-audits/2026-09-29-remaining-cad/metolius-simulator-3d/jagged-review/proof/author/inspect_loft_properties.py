import FreeCAD as A,Part
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));o=d.CenterShoulderTransitionLoft
for p in o.PropertiesList:print(p,str(getattr(o,p))[:300])
print(Part.makeLoft.__doc__)
