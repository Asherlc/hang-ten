from pathlib import Path
import json,sys,hashlib,logging,copy,re
w=Path(__file__).resolve().parent
f=w/'final-code-freeze'
sys.path.insert(0,str(f/'Tools/HangboardCAD'))
sys.path.insert(0,str(f/'Tools/HangboardPackages/src'))
import trimesh
from native_cord_routes import solve_native_routes
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(mode):
    freeze=json.loads((f/'freeze.json').read_text())
    for path,digest in freeze['inputSHA256'].items():
        if sha(Path(path))!=digest:raise ValueError('frozen input changed: '+path)
    for path,digest in freeze['codeSHA256'].items():
        if sha(f/path)!=digest:raise ValueError('frozen helper changed: '+path)
    data=json.loads((w/'vertical-input-final-metadata.json').read_text())
    # Remove all prior route caches; solver must generate from native features.
    for pose in data['suspension']['canonicalPoses'].values():pose.pop('wrappedRoutes',None)
    source=json.loads((w/'native-collision-vertical.json').read_text())
    descriptor=json.loads((w/'assets/primary.model.json').read_text())
    mesh=trimesh.Trimesh(source['vertices'],source['triangles'],process=False)
    solved=solve_native_routes(mesh,data,descriptor,source_metadata=source)
    for key,result in solved.items():
        data['suspension']['canonicalPoses'][key]['translation'][1]=result['height']
        data['suspension']['canonicalPoses'][key]['wrappedRoutes']=result['routes']
    report={'package':'nature-stone-hanger','presentationID':data['presentationID'],'sourceSHA256':source['sourceSHA256'],'modelSHA256':descriptor['modelSHA256'],'collisionSolidSHA256':sha(w/'native-collision-vertical.json'),'codeFreezeSHA256':sha(f/'freeze.json'),'helperSHA256':freeze['codeSHA256']['Tools/HangboardCAD/native_cord_guides.py'],'poses':solved}
    out=w/('final-'+mode);out.mkdir(exist_ok=False)
    (out/'native-route-report.json').write_text(json.dumps(report,indent=2)+'\n')
    formatted=json.dumps(data,indent=2)
    number=r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?'
    triplet=re.compile(rf'\[\n\s+({number}),\n\s+({number}),\n\s+({number})\n\s+\]')
    formatted=triplet.sub(lambda m:f'[{m[1]}, {m[2]}, {m[3]}]',formatted)
    assert json.loads(formatted)==data
    (out/'suspension.json').write_text(formatted+'\n')
    for path,digest in freeze['inputSHA256'].items():assert sha(Path(path))==digest
    for path,digest in freeze['codeSHA256'].items():assert sha(f/path)==digest
    loaded={name:{'path':str(Path(module.__file__).resolve()),'sha256':sha(Path(module.__file__))} for name,module in list(sys.modules.items()) if getattr(module,'__file__',None) and str(f) in str(module.__file__) and str(module.__file__).endswith('.py')}
    counts={'outputPoses':len(solved),'branches':sum(len(p['routes']) for p in solved.values()),'presentationFrames':len({tuple(p['rotation']) for p in data['suspension']['canonicalPoses'].values()}),'freshPhysicsFrames':sum('freshComputationReuse' not in p['nativeGrooveGuidance'] for p in solved.values())}
    if mode=='check':
        for name in ('native-route-report.json','suspension.json'):
            assert (out/name).read_bytes()==(w/'final-apply'/name).read_bytes(),name+' does not reproduce'
    (out/'completion.json').write_text(json.dumps({'status':'pass','mode':mode,'counts':counts,'loadedModules':loaded,'reportSHA256':sha(out/'native-route-report.json'),'sidecarSHA256':sha(out/'suspension.json'),'freshIndependentRegenerationMatches':mode=='check'},indent=2)+'\n')
    print(json.dumps({'status':'pass','mode':mode,'counts':counts,'report':str(out/'native-route-report.json')}),flush=True)
if __name__=='__main__':main(sys.argv[1])
