import FreeCAD as A,Part,json
from pathlib import Path
w=Path(__file__).resolve().parent;d=A.openDocument(str(w/'probe-source.FCStd'));d.recompute();body=d.BodySolid.Shape;c=d.Cutter_pocket_13_left.Shape;base=d.BodySolid.Base.Shape;r={}
for name,shape in [('body',body),('base',base),('cutter',c)]:
 try:shape.check(True);bop='pass'
 except Exception as e:bop=str(e)
 r[name]={'valid':shape.isValid(),'solids':len(shape.Solids),'bop':bop}
for name,shape in [('body',body),('base',base)]:
 cut=shape.cut(c);r[name]['afterIsolatedCut']={'valid':cut.isValid(),'solids':len(cut.Solids),'remainingCutterVolume':cut.common(c).Volume,'volumeRemoved':shape.Volume-cut.Volume,'faces':len(cut.Faces)}
(w/'cavity-boolean-diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
