import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'probe-source.FCStd'));d.recompute();r={};base=d.ShellWithContinuousShoulders.Shape
r['C0Faces']=[]
for i,f in enumerate(base.Faces):
 try:f.check(True)
 except Exception as e:r['C0Faces'].append({'face':i+1,'bounds':str(f.BoundBox),'error':str(e)})
allCutters=Part.makeCompound([o.Shape for o in d.Objects if o.Name.startswith('Cutter_')]);box=Part.makeBox(800,150,140,A.Vector(-400,-120,-5));lower=d.UnpocketedShell.Shape.common(box)
try:lower.check(True);r['lowerBOP']='pass'
except Exception as e:r['lowerBOP']=str(e)
result=lower.cut(allCutters);r['lowerValid']=result.isValid();r['lowerSolids']=len(result.Solids);r['remainingPocket13']={side:result.common(d.getObject('Cutter_pocket_13_'+side).Shape).Volume for side in ['left','right']}
(w/'lower-cut-diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
