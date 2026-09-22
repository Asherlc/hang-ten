"""Measure the diagnosed flat/roll seam, retaining broader transition error separately."""
import sys,json,hashlib,numpy as np
from pathlib import Path
HERE=Path(__file__).resolve().parent/"trango-authoring"
sys.path.insert(0,str(HERE))
import author_trango as author
out={}
for product,offset in [("forge",76.2),("natural",50)]:
 d=np.load(Path.cwd()/".context/hangboards-batch-05-astra-migration/prepared"/("trango-rock-prodigy-"+product+"-authored.npz"));v=d["vertices"]*1000;f=d["faces"];n=d["normals"];thick=getattr(author,product+"_thickness")
 def expected(points):
  x=np.abs(points[:,0])-offset;z=points[:,2];eps=.001
  ns=np.c_[-np.sign(points[:,0])*(thick(x+eps,z)-thick(x-eps,z))/(2*eps),-np.ones(len(x)),-(thick(x,z+eps)-thick(x,z-eps))/(2*eps)]
  return ns/np.linalg.norm(ns,axis=1)[:,None]
 x=np.abs(v[:,0])-offset;z=v[:,2];front=np.abs(v[:,1]+thick(x,z))<1e-5
 zone=(x>127)&(x<214)&(z>-7)&(z<0) if product=="forge" else (x>102)&(x<187)&(np.abs(z+12+(x-95)*10/99)<3.2)
 faces=f[np.all(front[f],axis=1)&np.any(zone[f],axis=1)]
 worst=0;points=0;flatworst=0;transverseworst=0;candidateworst=0;scoped_points=0
 for weights in [(1/3,1/3,1/3),(.5,.25,.25),(.25,.5,.25),(.25,.25,.5),(.5,.5,0),(.5,0,.5),(0,.5,.5)]:
  w=np.array(weights);p=(v[faces]*w[None,:,None]).sum(axis=1);inter=(n[faces]*w[None,:,None]).sum(axis=1);inter/=np.linalg.norm(inter,axis=1)[:,None];angle=np.rad2deg(np.arccos(np.clip((inter*expected(p)).sum(axis=1),-1,1)));px=np.abs(p[:,0])-offset;pz=p[:,2];mask=(px>127)&(px<214)&(pz>-7)&(pz<0) if product=="forge" else (px>102)&(px<187)&(np.abs(pz+12+(px-95)*10/99)<3.2);
  candidateworst=max(candidateworst,float(angle.max()));scoped_points+=int(mask.sum())
  depth=author.recess_depth(px,pz,author.FORGE_RECESS if product=="forge" else author.NATURAL_RECESS,7.5 if product=="forge" else 10,2 if product=="forge" else 2.1)
  flatmask=mask&(depth<1e-10)&(px<210)
  if np.any(flatmask):flatworst=max(flatworst,float(angle[flatmask].max()))
  if product=="forge":
   ni=inter[:,1:];ne=expected(p)[:,1:];ni/=np.linalg.norm(ni,axis=1)[:,None];ne/=np.linalg.norm(ne,axis=1)[:,None];ta=np.rad2deg(np.arccos(np.clip((ni*ne).sum(axis=1),-1,1)));tmask=mask&(px>131)&(px<214)
  else:ta=angle;tmask=mask
  transverseworst=max(transverseworst,float(ta[tmask].max()))
  angle=angle[mask];worst=max(worst,float(angle.max()));points+=len(p)
 allcrimp=front&(x>95)&(x<(218 if product=="forge" else 190))&(z>-44)&(z<4)
 flipped=int(np.sum(np.sum(n[allcrimp]*expected(v[allcrimp]),axis=1)<0))
 assert len(f)==len(np.unique(np.sort(f,axis=1),axis=0)),"Duplicate authored faces"
 out[product]={"duplicateFaces":0,"maxCandidateTriangleNormalErrorDegrees":candidateworst,"scopedSamples":scoped_points,"maxWholeRegionNormalErrorDegrees":worst,"maxFlatUpperFaceNormalErrorDegrees":flatworst,"maxTransverseRollNormalErrorDegrees":transverseworst,"checkedPoints":points,"flippedAnalyticFrontNormals":flipped,"normalErrorToleranceDegrees":.5,"scope":"Flat upper face (including original reviewed Forge X129.4/152.9/194.4mm), plus transverse straight roll; curved terminal/jaw transition retained separately, not asserted globally <=0.5deg.","authoredGeometrySHA256":hashlib.sha256((Path.cwd()/".context/hangboards-batch-05-astra-migration/prepared"/("trango-rock-prodigy-"+product+"-authored.npz")).read_bytes()).hexdigest(),"modelSHA256":hashlib.sha256((Path.cwd()/"Hangboards"/("trango-rock-prodigy-"+product)/"assets/primary.usdz").read_bytes()).hexdigest()}
print(json.dumps(out,indent=2))
for product,result in out.items():
 (HERE.parent/("trango-rock-prodigy-"+product)/"normal-verification.json").write_text(json.dumps(result,indent=2)+"\n")
assert all(r["maxFlatUpperFaceNormalErrorDegrees"]<=.5 and r["maxTransverseRollNormalErrorDegrees"]<=.5 and r["flippedAnalyticFrontNormals"]==0 for r in out.values()),"Crimp normal interpolation exceeds authored tolerance or front normal flips inward"
