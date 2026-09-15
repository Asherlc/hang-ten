"""Execute the DELIVERED authoring sources, without the working-tree build scripts."""
from pathlib import Path
import json, tempfile, subprocess,shutil,sys,os,hashlib,time
ROOT=Path(__file__).resolve().parents[1]
results=[]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for statuspath in sorted((ROOT/'models').glob('*/model-status.json')):
    st=json.loads(statuspath.read_text());d=statuspath.parent
    if not st.get('usableExport'):continue
    if len(sys.argv)>1 and d.name not in sys.argv[1:]:continue
    start=time.time()
    with tempfile.TemporaryDirectory(prefix='hangboard-source-rebuild-') as temp:
        td=Path(temp);src=td/'source';shutil.copytree(d/'source',src,ignore=shutil.ignore_patterns('__pycache__'))
        assert not list(td.rglob('*.glb')), 'Original GLB must not be present at rebuild start'
        used={p.relative_to(src).as_posix():h(p) for p in src.rglob('*') if p.is_file()}
        env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='2',PYTHONHASHSEED='0',TERM='dumb')
        proc=subprocess.run([sys.executable,str(src/'rebuild.py'),'--output',str(td/'rebuilt')],cwd=td,env=env,text=True,capture_output=True,timeout=80)
        (d/'validation/rebuild-stdout.txt').write_text(proc.stdout)
        (d/'validation/rebuild-stderr.txt').write_text(proc.stderr)
        asset=td/'rebuilt'/(d.name+'.glb');actual=h(asset) if asset.is_file() else None
        r={'schemaVersion':1,'slug':d.name,'assetSha256':st['sha256'],'method':'Executed delivered source/rebuild.py in a fresh temporary directory with only delivered source/ files, no original export and no working-tree build scripts.','command':'python source/rebuild.py --output rebuilt','exitCode':proc.returncode,'rebuiltSha256':actual,'byteIdentical':actual==st['sha256'],'sourceFilesSha256':used,'elapsedSeconds':round(time.time()-start,3),'stdout':'validation/rebuild-stdout.txt','stderr':'validation/rebuild-stderr.txt'}
        (d/'validation/rebuild-results.json').write_text(json.dumps(r,indent=2))
        results.append(r);print(d.name,proc.returncode,'BYTE IDENTICAL' if r['byteIdentical'] else 'FAIL',flush=True)
        if proc.returncode or not r['byteIdentical']:
            raise RuntimeError('Reproduction failed: '+d.name+'\n'+proc.stderr)
results=[json.loads(p.read_text()) for p in sorted((ROOT/'models').glob('*/validation/rebuild-results.json'))]
assert all(r['assetSha256']==json.loads((ROOT/'models'/r['slug']/'model-status.json').read_text())['sha256'] for r in results)
(ROOT/'rebuild-verification.json').write_text(json.dumps({'models':results,'allDeliveredModelsReproduceByteIdentically':all(r['byteIdentical'] for r in results),'nativeBlenderUsed':False},indent=2))
