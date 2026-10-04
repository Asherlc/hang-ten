import sys,json,hashlib,math
from pathlib import Path
import FreeCAD as A,Part
p=Path(__file__).resolve().parent;source=Path(sys.argv[1]);out=Path(sys.argv[2]);before=p/'before-metolius-simulator-3d.FCStd';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();hs,hb=sha(source),sha(before);d=A.openDocument(str(source.resolve()));d.recompute();old=A.openDocument(str(before.resolve()));old.recompute();fail=[]
def check(k,v):
 if not v:fail.append(k)
curves=[g for g in d.ContinuousFrontRelief.Geometry if isinstance(g,Part.BSplineCurve)];lower=[g for g in curves if g.value(g.FirstParameter).y<=135+1e-7];expected=[(-72.128,135.,-.528),(-65.,117.,-.35),(-55.,87.,-.364),(-44.,59.,-.394),(-32.,29.,-.414),(-18.,-4.,-.43)];check('five lower fairing spans',len(lower)==5);rows=[]
for i,g in enumerate(lower):
 a,b=g.value(g.FirstParameter),g.value(g.LastParameter);ta,tb=g.tangent(g.FirstParameter)[0],g.tangent(g.LastParameter)[0];m0,m1=ta.x/ta.y,tb.x/tb.y;pol=g.getPoles();weights=g.getWeights();monotonic=(g.Degree==3 and len(pol)==4 and len(g.getKnots())==2 and all(abs(v-1)<1e-12 for v in weights) and all(pol[j+1].x>pol[j].x and pol[j+1].y<pol[j].y for j in range(3)));check('strict monotonic Bernstein control differences '+str(i),monotonic)
 if i<len(expected)-1:
  aa,bb=expected[i],expected[i+1];check('exact lower native anchor '+str(i),max(abs(a.x-aa[0]),abs(a.y-aa[1]),abs(b.x-bb[0]),abs(b.y-bb[1]))<1e-7);check('authored shared slopes '+str(i),max(abs(m0-aa[2]),abs(m1-bb[2]))<1e-10)
 rows.append({'span':i,'startYZ':[a.x,a.y],'endYZ':[b.x,b.y],'startDyDz':m0,'endDyDz':m1,'monotonicityProvedByPositiveDepthAndNegativeHeightBezierDerivativeControlPoints':monotonic,'normalTiltDegreesAtStartEnd':[math.degrees(math.atan(abs(m0))),math.degrees(math.atan(abs(m1)))]})
for i in range(len(lower)-1):
 a,b=lower[i],lower[i+1];check('exact native span position join '+str(i),(a.value(a.LastParameter)-b.value(b.FirstParameter)).Length<1e-7);ta,tb=a.tangent(a.LastParameter)[0],b.tangent(b.FirstParameter)[0];check('shared nonzero physical derivative '+str(i),abs(ta.x/ta.y-tb.x/tb.y)<1e-10 and abs(ta.x/ta.y)>.1)
uppercurves=[g for g in curves if g.value(g.FirstParameter).y>135+1e-7 and abs(g.value(g.LastParameter).y-135)<1e-7];check('one protected-to-fair boundary curve',len(uppercurves)==1)
if uppercurves and lower:
 u,l=uppercurves[0],lower[0];tu,tl=u.tangent(u.LastParameter)[0],l.tangent(l.FirstParameter)[0];check('exact position at135', (u.value(u.LastParameter)-l.value(l.FirstParameter)).Length<1e-7);check('exact tangent at135',abs(tu.x/tu.y-tl.x/tl.y)<1e-10)
print('Native fairing anchors, shared slopes and monotonicity checked',flush=True)
box=Part.makeBox(800,140,120,A.Vector(-400,-110,135));a=old.BodySolid.Shape.common(box);b=d.BodySolid.Shape.common(box);ab=a.cut(b);ba=b.cut(a);volumes=[ab.Volume,ba.Volume];check('upper final body bidirectional zero-volume difference',volumes==[0.0,0.0]);upper={'beforeVolumeMM3':a.Volume,'afterVolumeMM3':b.Volume,'differenceVolumesMM3':volumes,'differenceSolidCounts':[len(ab.Solids),len(ba.Solids)],'beforeShapeValid':a.isValid(),'afterShapeValid':b.isValid()};check('upper clipped shapes valid',a.isValid() and b.isValid())
# Compare the underlying upper construction controls, not serialized OCCT flags.
control_names=['ForwardCenterJug','ForwardCenterJugWithinEnvelope','CenterNoseLoft','FlatSloperRoof','RoundSloperRoof'];controls=[]
for name in control_names:
 x,y=old.getObject(name),d.getObject(name)
 if x is None or y is None:continue
 bx,by=x.Shape.optimalBoundingBox(),y.Shape.optimalBoundingBox();delta=max(abs(getattr(bx,k)-getattr(by,k)) for k in ['XMin','XMax','YMin','YMax','ZMin','ZMax']);controls.append({'object':name,'boundsDeltaMM':delta,'areaDeltaMM2':y.Shape.Area-x.Shape.Area,'volumeDeltaMM3':y.Shape.Volume-x.Shape.Volume});check('upper construction bounds '+name,delta<1e-7)
check('source files unchanged',sha(source)==hs and sha(before)==hb);r={'status':'pass' if not fail else 'fail','blockingFindings':fail,'sourceSHA256':hs,'beforeSourceSHA256':hb,'nativeProfileSpans':rows,'upperBodyAboveZ135':upper,'upperConstructionControls':controls,'sourceBytesUnchanged':sha(source)==hs,'limits':['Native curve anchors and slopes are operator display estimates, not manufacturer dimensions.','Monotonicity follows the positive/negative derivative Bernstein controls of each nonrational cubic, not pixel fitting.','Published depths, all30 contacts, functional grips and native edit/restoration remain separate unchanged gates.','Exact zero-volume directional differences establish unchanged upper solid for this OCCT operation; no manufacturing certification.']};out.write_text(json.dumps(r,indent=2)+'\n');A.closeDocument(d.Name);A.closeDocument(old.Name);print(json.dumps({'status':r['status'],'blockingFindings':fail,'report':str(out)},indent=2));raise SystemExit(bool(fail))
