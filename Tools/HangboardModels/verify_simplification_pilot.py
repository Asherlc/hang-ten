"""Independent point-to-triangle readback and descriptor verification."""
import argparse, hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
sys.path.insert(0,str(Path(__file__).resolve().parent))
from usdz_readback import read_scene, validate_archive, vertical_hits
from remove_mounting_bores import package_board_bytes
from simplify_display_models import boundary_edge_positions,_geometric_edges
from contact_model_descriptor import NodeBinding,compile_descriptor

def sample(mesh,n,rng):
    t=mesh.triangles;area=mesh.area_faces
    ix=rng.choice(len(t),size=n,p=area/area.sum())
    u=rng.random((n,2));mask=u.sum(1)>1;u[mask]=1-u[mask]
    return t[ix,0]+u[:,0,None]*(t[ix,1]-t[ix,0])+u[:,1,None]*(t[ix,2]-t[ix,0])

def distance(source,target,n,seed):
    pts=sample(source,n,np.random.default_rng(seed));chunks=[]
    for offset in range(0,n,250):
        _,d,_=trimesh.proximity.closest_point(target,pts[offset:offset+250]);chunks.extend(d)
    a=np.asarray(chunks)*1000
    return {'samples':len(a),'maxMM':float(a.max()),'p99MM':float(np.percentile(a,99)),'rmsMM':float(np.sqrt(np.mean(a*a)))}

def topology(v,f):
    p,inv,e,c=_geometric_edges(v,f);q=inv[f];used=np.unique(q)
    matrix=coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(p),len(p))).tocsr()[used][:,used]
    return {'components':int(connected_components(matrix,directed=False,return_labels=False)),
      'boundaryEdges':int(np.sum(c==1)),'nonmanifoldEdges':int(np.sum(c>2)),
      'euler':int(len(used)-len(e)+len(f)),
      'degenerateFaces':int(np.sum((q[:,0]==q[:,1])|(q[:,0]==q[:,2])|(q[:,1]==q[:,2])))}

def verify(baseline,out,slug):
    a=baseline/'Hangboards'/slug/'assets/primary.usdz';b=out/'Hangboards'/slug/'assets/primary.usdz'
    sa,ams=read_scene(a);sb,bms=read_scene(b)
    am={m['prim'].GetName():m for m in ams};bm={m['prim'].GetName():m for m in bms};assert am.keys()==bm.keys()
    da=json.loads(a.with_suffix('.model.json').read_text());db=json.loads(b.with_suffix('.model.json').read_text())
    assert da['nodes']==db['nodes'];assert da['contacts']==db['contacts'];assert da['modelBounds']==db['modelBounds']
    verts={n:m['world'][np.unique(m['f'])].tolist() for n,m in bm.items()}
    desc=compile_descriptor(b.read_bytes(),[NodeBinding(n['nodeID'],n['role'],n.get('contactID')) for n in db['nodes']],verts,frozenset(db['contacts']))
    assert desc.to_json()==db;validate_archive(b)
    assert package_board_bytes(a.parents[1])==package_board_bytes(b.parents[1])
    with zipfile.ZipFile(a) as za,zipfile.ZipFile(b) as zb:
        assert za.namelist()==zb.namelist()
        for n in za.namelist()[1:]:assert za.read(n)==zb.read(n)
    if 'reviewedLayerSHA256' in json.loads((baseline/'Tools/HangboardModels/simplification_pilot.json').read_text())['models'][slug]:
        expected=json.loads((baseline/'Tools/HangboardModels/simplification_pilot.json').read_text())['models'][slug]['reviewedLayerSHA256']
        assert hashlib.sha256(sb.GetRootLayer().ExportToString().encode()).hexdigest()==expected, 'reviewed layer changed'
    report={'board':slug,'sourceSHA256':hashlib.sha256(a.read_bytes()).hexdigest(),'modelSHA256':hashlib.sha256(b.read_bytes()).hexdigest(),
      'descriptorRecompiledMatch':True,'contactsBoundsAndIDsUnchanged':True,'materialsAndTexturesUnchanged':True,'meshResults':[]}
    for i,(name,m) in enumerate(am.items()):
        other=bm[name]
        assert boundary_edge_positions(m['world'],m['f'])==boundary_edge_positions(other['world'],other['f'])
        ta=topology(m['world'],m['f']);tb=topology(other['world'],other['f'])
        assert ta==tb,(slug,name,ta,tb)
        # Geometry is sampled against the same logical node in each direction,
        # preventing a neighboring/back surface from hiding a missing contact.
        ma=trimesh.Trimesh(m['world'],m['f'],process=False);mb=trimesh.Trimesh(other['world'],other['f'],process=False)
        r={'node':name,'sourceTopology':ta,'outputTopology':tb,
           'sourceToOutput':distance(ma,mb,1800,i+717),'outputToSource':distance(mb,ma,1800,i+1717)}
        report['meshResults'].append(r)
    # Read from the pinned baseline checkout (simplification_pilot.json
    # sourceCommit), where the bore record still lived at this path; at later
    # commits it is docs/source-audits/2026-09-22-mounting-bore-repairs.json.
    boremanifest=json.loads((baseline/'Tools/HangboardModels/mounting_bore_repairs.json').read_text())
    if slug in boremanifest['models']:
        checks=[]
        for hole in boremanifest['models'][slug]['holes']:
            xy=np.asarray(hole['center']);
            for offset in ([0,0],[.00035,0],[-.00035,0],[0,.00035],[0,-.00035]):
                h=vertical_hits(bms,xy+offset);assert len(h)>=2,(slug,xy,offset)
                checks.append({'xy':(xy+offset).tolist(),'hitCount':len(h),'depthMM':1000*(h[-1][0]-h[0][0])})
        report['closedBoreRays']=checks
    report['maxSampledDistanceMM']=max(max(r['sourceToOutput']['maxMM'],r['outputToSource']['maxMM']) for r in report['meshResults'])
    if report['maxSampledDistanceMM']>.5:raise ValueError('sampled surface deviation exceeds 0.5 mm')
    report['sampleCount']=sum(r[d]['samples'] for r in report['meshResults'] for d in ('sourceToOutput','outputToSource'))
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--board',required=True);args=ap.parse_args()
    r=verify(args.root,args.output,args.board)
    dest=args.output/'Verification';dest.mkdir(exist_ok=True)
    (dest/(args.board+'.json')).write_text(json.dumps(r,indent=2)+'\n')
    print(args.board,'max sampled distance mm',r['maxSampledDistanceMM'],'samples',r['sampleCount'],flush=True)
