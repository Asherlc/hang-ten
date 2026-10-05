import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'probe-source.FCStd'));r=[]
for i in range(4):
 g=d.getObject('CenterShoulderTransitionSection'+str(i)).Geometry[1];points=g.discretize(Number=601);c=Part.BSplineCurve();c.approximate(Points=points,DegMin=3,DegMax=3,Tolerance=.003);c.setPole(1,g.StartPoint);c.setPole(c.NbPoles,g.EndPoint);edge=c.toShape();errors=[edge.distToShape(Part.Vertex(p))[0] for p in g.discretize(Number=1001)];r.append({'section':i,'oldDegree':g.Degree,'oldPoles':g.NbPoles,'newDegree':c.Degree,'newPoles':c.NbPoles,'maxSampledDeviationMm':max(errors),'first':str(c.StartPoint),'last':str(c.EndPoint)})
(w/'curve-refit-probe.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
