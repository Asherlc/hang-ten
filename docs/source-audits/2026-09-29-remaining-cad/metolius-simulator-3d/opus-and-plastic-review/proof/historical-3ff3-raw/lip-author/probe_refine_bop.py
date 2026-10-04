import FreeCAD as A,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'probe-source.FCStd'));d.recompute();r=[]
def check(stage):
 rows=[]
 for o in d.Objects:
  if o.Name in ['CenterShoulderTransition','CenterShoulderBoundedTransition','ShellWithContinuousShoulders','BodySolid','FunctionalShellWithRolledNose']:
   errors=[]
   for i,f in enumerate(o.Shape.Faces):
    b=f.optimalBoundingBox()
    if b.XMin>45 and b.XMax<62 and b.ZMax>190:
     try:f.check(True)
     except Exception as e:errors.append({'face':i+1,'error':str(e)})
   rows.append({'object':o.Name,'errors':errors})
 r.append({'stage':stage,'objects':rows})
check('original')
for name in ['FunctionalShellWithRolledNose','ShellWithContinuousShoulders']:
 d.getObject(name).Refine=False;d.recompute();check('RefineFalse '+name)
(w/'refine-bop-probe.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
