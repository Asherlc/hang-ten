import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));f=d.BodySolid.Shape.Faces[44];p,t=f.tessellate(.28);uv=f.getUVNodes();print(f.getUVNodes.__doc__);print('ParameterRange',f.ParameterRange);print('UV range',min(x[0] for x in uv),max(x[0] for x in uv),min(x[1] for x in uv),max(x[1] for x in uv))
for i in range(5):print('point',p[i],'uv',uv[i],'surfacevalue',f.Surface.value(*uv[i]),'inverse',f.Surface.parameter(p[i]))
