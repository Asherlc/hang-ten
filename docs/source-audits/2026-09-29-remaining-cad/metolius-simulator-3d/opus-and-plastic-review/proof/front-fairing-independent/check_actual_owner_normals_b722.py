import FreeCAD as A
import json, math, hashlib, sys
from pathlib import Path
here=Path(__file__).resolve().parent; folder=here.parent
sys.path.insert(0,str(Path.cwd()/"Tools/HangboardCAD"));import compile_board as c
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=folder/"candidate/metolius-simulator-3d.FCStd";compiler=Path("Tools/HangboardCAD/compile_board.py")
raw=folder/"final-normal-comparison.json";original=json.loads(raw.read_text())
source_sha=sha(source);raw_sha=sha(raw);compiler_sha=sha(compiler)
assert source_sha==original["sourceSHA256"]=="b7223032abe4b5c00a8b16d8ddcafed8b836d806795f1d37bbffab80ce5560ef"
assert compiler_sha==original["compilerSHA256"]=="f4c0d4c2a9c79c02d349be2f71a14962fde3c5c2fa13b24b0b34d425272fc50d"
d=A.openDocument(str(source));shape=d.BodySolid.Shape;points,triangles=shape.tessellate(.28)
indices=sorted({row["triangle"] for row in original["comparisons"]});selected=[triangles[i] for i in indices]
xyz=lambda p:(p.x,p.y,p.z)
signature=lambda ps,t:tuple(sorted(xyz(ps[i]) for i in t))
wanted={signature(points,t):i for i,t in zip(indices,selected)};owners={}
for fi,face in enumerate(shape.Faces):
    fp,ft=face.tessellate(.28)
    for t in ft:
        sig=signature(fp,t)
        if sig in wanted:owners.setdefault(wanted[sig],set()).add(fi)
old=c._surface_normals(shape,points,selected,.28);new=c._surface_normals(shape,points,selected,.28,uv_nodes=True)
cache=c._uv_node_normal_cache(shape,points,selected,.28)
angle=lambda a,b:math.degrees(math.acos(max(-1,min(1,a.dot(b)))))
rows=[];failures=[]
for n,ti in enumerate(indices):
    t=triangles[ti];flat=(points[t[1]]-points[t[0]]).cross(points[t[2]]-points[t[0]])
    for j,pi in enumerate(t):
        op=old[0][old[1][n][j]];np=new[0][new[1][n][j]];on=old[2][old[1][n][j]];nn=new[2][new[1][n][j]]
        row={"triangle":ti,"corner":j,"legacyAngleDegrees":angle(on,nn),"positionDifferenceMM":(op-np).Length,"normalLength":nn.Length,"nativeFacetOwners":sorted(owners.get(ti,()))}
        row["basis"]="legacy agreement"
        row["passed"]=row["legacyAngleDegrees"]<.001 and row["positionDifferenceMM"]==0 and abs(nn.Length-1)<1e-10
        if n in cache:
            fi=cache[n][0];face=shape.Faces[fi];p=points[pi]
            u,v=face.Surface.parameter(p);inverse=face.normalAt(u,v);inverse.normalize()
            if inverse.dot(flat)<0:inverse=-inverse
            uv_matches=[uv for uv in face.getUVNodes() if (face.Surface.value(*uv)-p).Length<=.00002]
            row.update(cachedOwner=fi,ownerInversePositionErrorMM=(face.Surface.value(u,v)-p).Length,ownerInverseNormalAngleDegrees=angle(nn,inverse),ownerUVMatchCount=len(uv_matches))
            if len(uv_matches)==1:
                uv=uv_matches[0];un=face.normalAt(*uv);un.normalize()
                if un.dot(flat)<0:un=-un
                row.update(ownerUVPositionErrorMM=(face.Surface.value(*uv)-p).Length,ownerUVInverseNormalAngleDegrees=angle(un,inverse))
            if not row["passed"]:
                row["basis"]="unique exact native facet owner and same-owner UV/inverse agreement"
                row["passed"]=(owners.get(ti)=={fi} and len(uv_matches)==1 and row["positionDifferenceMM"]==0 and abs(nn.Length-1)<1e-10 and row["ownerInversePositionErrorMM"]<=.00002 and row["ownerUVPositionErrorMM"]<=.00002 and row["ownerInverseNormalAngleDegrees"]<.001 and row["ownerUVInverseNormalAngleDegrees"]<.001)
        if not row["passed"]:failures.append(row)
        rows.append(row)
assert sha(source)==source_sha and sha(raw)==raw_sha and sha(compiler)==compiler_sha
report={"status":"pass" if not failures else "fail","sourceSHA256":source_sha,"compilerSHA256":compiler_sha,"rawLegacyComparison":{"path":str(raw),"sha256":raw_sha,"status":original["status"],"maxAngleDegrees":original["maxNormalAngleDegrees"]},"cornersCompared":len(rows),"legacyAgreementCorners":sum(r["basis"]=="legacy agreement" for r in rows),"actualOwnerDispositionCorners":sum(r["basis"]!="legacy agreement" for r in rows),"tolerances":{"angleDegreesStrictlyLessThan":.001,"uvPositionMM":.00002,"exportPositionDifferenceMM":0},"sourceAndCompilerAndRawComparisonUnchanged":True,"interpretation":"Opt-in exact unique native facet ownership takes precedence over legacy nearest-centroid ownership. One legacy-normal behavior difference is resolved by actual-owner inverse evaluation; no angular or position tolerance is widened. This finite sample is not a universal normal-equivalence certificate.","blockingFindings":failures,"comparisons":rows}
(here/"actual-owner-normal-supplement-b722.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="comparisons"},indent=2));A.closeDocument(d.Name)
raise SystemExit(bool(failures))
