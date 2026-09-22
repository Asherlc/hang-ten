from pathlib import Path
import sys,json,hashlib,numpy as np
native=Path.cwd()/"docs/source-audits/2026-09-20-hangboards-batch-05-migration/native";sys.path.insert(0,str(native/"trango-authoring"));import author_trango as author
ctx=Path.cwd()/".context/hangboards-batch-05-astra-migration";results={}
for product,offset in [("forge",76.2),("natural",50)]:
 rows={};thick=getattr(author,product+"_thickness")
 for variant in ["checkpoint","final"]:
  path=ctx/("trango-seam-original-location-"+variant)/("trango-rock-prodigy-"+product+"-samples.json");samples=json.loads(path.read_text());errors=[];flat=[]
  for sample in samples:
   if not sample["hit"]:continue
   p=np.array(sample["point"]);v=np.array(sample["vertices"]);ns=np.array(sample["normals"]);basis=np.stack([v[1]-v[0],v[2]-v[0]],axis=1);uv=np.linalg.lstsq(basis,p-v[0],rcond=None)[0];weights=np.array([1-uv.sum(),*uv]);n=weights@ns;n/=np.linalg.norm(n)
   x=abs(p[0])*1000-offset;z=p[2]*1000;eps=.001;expected=np.array([-np.sign(p[0])*(thick(x+eps,z)-thick(x-eps,z))/(2*eps),-1,-(thick(x,z+eps)-thick(x,z-eps))/(2*eps)]);expected/=np.linalg.norm(expected);error=float(np.rad2deg(np.arccos(np.clip(n@expected,-1,1))));errors.append(error)
   depth=author.recess_depth(x,z,author.FORGE_RECESS if product=="forge" else author.NATURAL_RECESS,7.5 if product=="forge" else 10,2 if product=="forge" else 2.1)
   if depth<1e-10:flat.append(error)
  rows[variant]={"modelSHA256":samples[0]["modelSHA256"],"probeSHA256":hashlib.sha256(path.read_bytes()).hexdigest(),"samples":len(errors),"flatSamples":len(flat),"maxWholePatchNormalErrorDegrees":max(errors),"maxFlatFaceNormalErrorDegrees":max(flat)}
 results[product]=rows
print(json.dumps(results,indent=2));(native/"trango-authoring/original-location-native-regression.json").write_text(json.dumps(results,indent=2)+"\n")
assert all(r["checkpoint"]["maxFlatFaceNormalErrorDegrees"]>1 and r["final"]["maxFlatFaceNormalErrorDegrees"]<.5 for r in results.values())
