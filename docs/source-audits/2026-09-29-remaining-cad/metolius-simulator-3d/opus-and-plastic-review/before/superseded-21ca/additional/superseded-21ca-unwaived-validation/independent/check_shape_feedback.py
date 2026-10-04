import json,hashlib,math,sys
from pathlib import Path
import FreeCAD as A
import Part
p=Path(__file__).resolve().parent
source=Path(sys.argv[1]);out=Path(sys.argv[2]);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=sha(source);original=p/'original-9449.FCStd';docs=[];fail=[]
def check(k,v):
 if not v:fail.append(k)
def load(f):
 d=A.openDocument(str(f.resolve()));docs.append(d);d.recompute();return d,d.getObject('BodySolid').Shape
new,body=load(source);old,reference=load(original)
bbox=body.optimalBoundingBox();envelope=[bbox.XLength,bbox.YLength,bbox.ZLength]
check('single valid body',body.isValid() and len(body.Solids)==1)
curves=[]
for name in ['Silhouette0','Silhouette1','Silhouette2']:
 a,b=old.getObject(name).Geometry[0],new.getObject(name).Geometry[0]
 ap,bp=a.getPoles(),b.getPoles();gap=max((x-y).Length for x,y in zip(ap,bp)) if len(ap)==len(bp) else float('inf')
 curves.append({'sketch':name,'originalPoles':[[v.x,v.y,v.z] for v in ap],'candidatePoles':[[v.x,v.y,v.z] for v in bp],'maximumPoleDifferenceMM':gap});check(name+' original dome poles exact',gap<1e-10)
# Restrict the comparison to the author-declared unchanged center core.
box=Part.makeBox(92.98,130,110,A.Vector(-46.49,-120,145));a=reference.common(box);b=body.common(box)
missing=a.cut(b).Volume;added=b.cut(a).Volume
check('unchanged dome core volume',missing<.001 and added<.001)
print('Dome curves/core checked',flush=True)
def intersections(shape,x0,x1,y,z):
 cut=shape.common(Part.makeLine(A.Vector(x0,y,z),A.Vector(x1,y,z)))
 return sorted(v.Point.x for v in cut.Vertexes)
widths=[]
for y in [-5,-30,-60]:
 for z in [190,195,200,210,218]:
  aa=intersections(reference,-70,70,y,z);bb=intersections(body,-70,70,y,z)
  err=max(abs(x-v) for x,v in zip(aa,bb)) if len(aa)==len(bb) and aa else None
  widths.append({'yMM':y,'zMM':z,'originalIntersectionsXMM':aa,'candidateIntersectionsXMM':bb,'maxDifferenceMM':err})
  if aa and all(abs(x)<46.49 for x in aa):check('dome width preserved '+str((y,z)),err is not None and err<.02)
def roof(shape,x,y):
 hit=shape.common(Part.makeLine(A.Vector(x,y,125),A.Vector(x,y,240)))
 return max((v.Point.z for v in hit.Vertexes),default=None)
sections=[]
for y in [-.01,-10,-40,-54.9,-64.9]:
 xs=[110+2.5*i for i in range(31)];zs=[roof(body,x,y) for x in xs];mins=[]
 for i in range(1,len(xs)-1):
  if None not in zs[i-1:i+2] and zs[i]<min(zs[i-1],zs[i+1])-.0001:mins.append({'xMM':xs[i],'zMM':zs[i],'dropBelowBothNeighborsMM':min(zs[i-1],zs[i+1])-zs[i]})
 valid=[z for z in zs if z is not None];sections.append({'yMM':y,'xMM':xs,'zMM':zs,'sampledLocalMinima':mins,'totalHeightRangeMM':max(valid)-min(valid) if valid else None})
 # Rear/top roof must not have the diagnosed spurious localized notch.
 if y in [-.01,-10]:check('no localized rear roof dip y'+str(y),not mins and all(z is not None for z in zs))
print('Roof grids checked',flush=True)
sym=[]
for x in [0,20,40,46.5,46.9,50,59.5,61,110,112,125,148,170,183,185,238,278]:
 for y in [-.01,-40,-54.9]:
  a,b=roof(body,x,y),roof(body,-x,y)
  if a is not None and b is not None:sym.append(abs(a-b))
check('sampled roof mirror symmetry',max(sym,default=0)<.002)
check('source unchanged',sha(source)==before)
r={'status':'pass' if not fail else 'fail','blockingFindings':fail,'sourceSHA256':before,'originalSourceSHA256':sha(original),'envelopeXYZMM':envelope,'domePoles':curves,'domeCore':{'clipXMM':[-46.49,46.49],'clipZMM':[145,255],'missingVolumeMM3':missing,'addedVolumeMM3':added},'domeWidths':widths,'roundFlatRoofSections':sections,'maximumSampledMirrorHeightErrorMM':max(sym,default=0),'sourceBytesUnchanged':sha(source)==before,'limits':['Native analytic section probes, no image measurement.','Probe source may lack contacts; no contact/depth/edit gate claimed by this geometry-only report.','No sampled local minimum is not proof of global monotonicity; Opus whole-image verdict remains required.','Display rounding/blend intervals/thickness are estimates, not manufacturer dimensions.']}
out.write_text(json.dumps(r,indent=2)+'\n')
for d in docs:A.closeDocument(d.Name)
print(json.dumps({'status':r['status'],'blockingFindings':fail,'report':str(out)},indent=2));raise SystemExit(bool(fail))
