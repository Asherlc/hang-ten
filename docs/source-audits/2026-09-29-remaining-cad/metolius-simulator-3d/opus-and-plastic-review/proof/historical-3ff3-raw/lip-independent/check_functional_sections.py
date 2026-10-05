import json,hashlib,math,sys
from pathlib import Path
import FreeCAD as A
import Part
p=Path(__file__).resolve().parent;source=Path(sys.argv[1]);out=Path(sys.argv[2]);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();h=sha(source);d=A.openDocument(str(source.resolve()));d.recompute();body=d.BodySolid.Shape;contacts={o.ContactID:o.Shape for o in d.Objects if getattr(o,'NodeRole','')=='contact'};fail=[]
def check(k,v):
 if not v:fail.append(k)
def roof(x,y):
 s=body.common(Part.makeLine(A.Vector(x,y,120),A.Vector(x,y,245)))
 return max((v.Point.z for v in s.Vertexes),default=None)
def plane(x):return Part.Face(Part.makePolygon([A.Vector(x,-110,-5),A.Vector(x,5,-5),A.Vector(x,5,255),A.Vector(x,-110,255),A.Vector(x,-110,-5)]))
slopers=[]
for cid,x,depth in [('flat-sloper-2-left',-210,55),('flat-sloper-2-right',210,55),('round-sloper-3-center',-95,65),('round-sloper-3-center',95,65)]:
 contact=contacts[cid];bb=contact.optimalBoundingBox();section=contact.section(plane(x));bodysection=body.slice(A.Vector(1,0,0),x);front=min(w.BoundBox.YMin for w in bodysection);sb=section.BoundBox;samples=[]
 for frac in [.02,.2,.4,.6,.8,.98]:
  y=-94+depth*frac;z=roof(x,y);dist=contact.distToShape(Part.Vertex(A.Vector(x,y,z)))[0] if z is not None else None;samples.append({'yMM':y,'roofZMM':z,'contactDistanceMM':dist});check(cid+' actual roof membership '+str((x,frac)),dist is not None and dist<.002)
 check(cid+' global support depth',abs(bb.YLength-depth)<.02);check(cid+' front anchored',abs(bb.YMin+94)<.02 and abs(bb.YMax-(-94+depth))<.02);check(cid+' local support reaches body front '+str(x),abs(sb.YMin-front)<.02)
 slopers.append({'id':cid,'xMM':x,'expectedDepthMM':depth,'globalYBoundsMM':[bb.YMin,bb.YMax],'localContactYBoundsMM':[sb.YMin,sb.YMax],'bodyFrontYMM':front,'roofSamples':samples})
print('Sloper sections checked',flush=True)
jugs=[]
for x in [0,30,-30]:
 ys=[-2*i for i in range(48)];zs=[roof(x,y) for y in ys];pairs=[(y,z) for y,z in zip(ys,zs) if z is not None];cy,cz=max(pairs,key=lambda v:v[1]);rear=roof(x,0);nearback=roof(x,-10);front=roof(x,-93.9);samples=[]
 for y in [-35,-50,cy,-80]:
  z=roof(x,y);dist=contacts['jug-14-center'].distToShape(Part.Vertex(A.Vector(x,y,z)))[0] if z is not None else None;samples.append({'yMM':y,'zMM':z,'contactDistanceMM':dist});check('jug curved roof contact '+str((x,y)),dist is not None and dist<.002)
 approach=body.common(Part.makeLine(A.Vector(x,0,cz-5),A.Vector(x,cy,cz-5)));hit=sorted((-v.Point.y for v in approach.Vertexes));clear=hit[0] if hit else -cy
 check('jug crest forward '+str(x),60<=-cy<=75);check('jug rear return lower '+str(x),rear is not None and cz-rear>5 and nearback is not None and cz-nearback>5);check('jug front return lower '+str(x),front is not None and cz-front>5);check('positive rear approach '+str(x),clear>5)
 jugs.append({'xMM':x,'yMM':ys,'roofZMM':zs,'crestYMM':cy,'crestZMM':cz,'rearWallRoofZMM':rear,'nearRearRoofZMM':nearback,'frontRoofZMM':front,'rearApproachAtCrestMinus5MM':clear,'contactSamples':samples})
check('center pocket15 published50mm',abs(contacts['pocket-15-center'].optimalBoundingBox().YLength-50)<.02)
sym=[]
for x in [10,30,46,60,95,148,210,260,293,320]:
 for y in [-10,-40,-70,-90]:
  a,b=roof(x,y),roof(-x,y)
  if a is not None and b is not None:sym.append(abs(a-b))
check('roof symmetry',max(sym,default=0)<.002);check('source bytes unchanged',sha(source)==h)
r={'status':'pass' if not fail else 'fail','blockingFindings':fail,'sourceSHA256':h,'slopers':slopers,'centerJug':jugs,'maximumMirrorHeightDifferenceMM':max(sym,default=0),'sourceBytesUnchanged':sha(source)==h,'limits':['Crest placement60–75mmforward and5mm diagnostic return/approach witnesses validate the operator-authored display intent, not sourced manufacturing or ergonomic dimensions.','Finite section samples cannot certify every finger approach or fit. Opus/user visual grasp verdict remains separate.','Published55/65/50mm depths are strict native spans; front anchoring is explicit current correction intent.']};out.write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);print(json.dumps({'status':r['status'],'blockingFindings':fail,'report':str(out)},indent=2));raise SystemExit(bool(fail))
