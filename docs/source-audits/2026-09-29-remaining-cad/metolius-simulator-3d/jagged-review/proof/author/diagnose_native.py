import sys,json,math,hashlib
from pathlib import Path
import FreeCAD as A
import Part
root=Path.cwd();w=root/'.context/placid-badger/metolius-simulator-3d-jagged/native-author'
source=w/'before/metolius-simulator-3d.FCStd';d=A.openDocument(str(source));d.recompute();body=d.getObject('BodySolid');sk=d.getObject('Silhouette2')
rows=[]
for i,g in enumerate(sk.Geometry):
 h=sk.Geometry[(i+1)%len(sk.Geometry)];a=g.tangent(g.LastParameter)[0];b=h.tangent(h.FirstParameter)[0];angle=math.degrees(math.acos(max(-1,min(1,a.dot(b)/(a.Length*b.Length)))))
 rows.append({'edge':i,'joinXZ':[g.EndPoint.x,g.EndPoint.y],'tangentDiscontinuityDegrees':angle})
seams=[]
for x in [47,148,258]:
 for yy in [-10,-40,-55,-65]:
  vals=[]
  for offset in [-.01,.01]:
   line=Part.makeLine(A.Vector(x+offset,yy,100),A.Vector(x+offset,yy,230));common=body.Shape.common(line)
   vals.append(max([v.Point.z for v in common.Vertexes],default=None))
  seams.append({'x':x,'y':yy,'leftTopZ':vals[0],'rightTopZ':vals[1],'heightJumpMm':abs(vals[0]-vals[1]) if all(v is not None for v in vals) else None})
roof_faces=[]
for i,f in enumerate(body.Shape.Faces):
 if f.BoundBox.ZMax>149 and f.BoundBox.ZLength>1 and f.BoundBox.YLength>5 and f.BoundBox.XLength<1e-5:
  roof_faces.append({'face':i+1,'x':f.CenterOfMass.x,'area':f.Area,'zRange':[f.BoundBox.ZMin,f.BoundBox.ZMax],'yRange':[f.BoundBox.YMin,f.BoundBox.YMax]})
r={'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'nativeValid':body.Shape.isValid(),'nativeFaceCount':len(body.Shape.Faces),'tessellationDeflectionMm':d.HangTenTessellationDeflection,'analyticNormalsEnabled':d.HangTenSurfaceNormals,'silhouetteJoinMeasurements':rows,'roofSectionJumps':seams,'verticalRoofStepFaces':roof_faces}
(w/'diagnosis-native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));A.closeDocument(d.Name)
