import FreeCAD as A,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'probe-source.FCStd'));d.recompute();names=['UnpocketedShell','RoundSloperRoof','FlatSloperRoof','ShellWithDistinctSlopers','ForwardCenterJug','ForwardJugEnvelope','ForwardCenterJugWithinEnvelope','ShellWithoutRearJugRidge','FunctionalShellBeforeBlends','CenterShoulderTransitionLoft','CenterShoulderBoundedTransition','RoundFlatBoundedTransition','OuterShoulderBoundedTransition','ShoulderTransitionBandsRemoved','ShellWithContinuousShoulders','BodySolid'];rows=[]
for name in names:
 o=d.getObject(name);b=o.Shape.optimalBoundingBox();rows.append({'name':name,'ymin':b.YMin,'ymax':b.YMax,'volume':o.Shape.Volume,'state':list(o.State)})
(w/'bounds-diagnosis.json').write_text(json.dumps(rows,indent=2));print(rows)
