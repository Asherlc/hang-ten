import FreeCAD as A,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'candidate/metolius-simulator-3d.FCStd'));d.recompute();r={}
for name in ['ForwardCenterJug','CenterJugFrontNose','FunctionalShellBeforeBlends','FunctionalShellWithRolledNose','CenterShoulderBoundedTransition','RoundFlatBoundedTransition','OuterShoulderBoundedTransition','ShellWithContinuousShoulders','BodySolid']:
 s=d.getObject(name).Shape;r[name]={'orientation':s.Orientation,'volume':s.Volume,'solids':[(x.Orientation,x.Volume) for x in s.Solids],'insideCenter':s.isInside(A.Vector(0,-60,200),1e-6,False),'insideSky':s.isInside(A.Vector(80,-60,210),1e-6,False)}
(w/'orientation-diagnosis.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
