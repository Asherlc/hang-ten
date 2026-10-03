"""One owned offline render, with exact process/config/cache/TMP cleanup."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
REPO=Path.cwd()
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def stamp():return datetime.now(timezone.utc).isoformat()


def main():
    assert OUT==REPO/'.context/placid-badger/mini-review10-resume/preview-worker'
    identity=json.loads((OUT/'input-identity.json').read_text())
    package=Path(identity['package'])
    assert all(H(package/n)==digest for n,digest in identity['canonical4'].items())
    resources=[OUT/('placid-badger-'+kind) for kind in ('config','cache','tmp')]
    owner=json.loads((OUT/'ownership.json').read_text())
    assert not owner['processGroups'] and not owner['temporaryResources']
    owner['temporaryResources']=[str(p) for p in resources]
    owner['resourceName']='placid-badger-mini10-offline-preview'
    owner['inputs']=identity
    write(OUT/'ownership.json',owner)
    child=None
    receipt={'owner':'placid-badger','task':'mini10-offline-preview','exitCode':1,'processGroups':[],'temporaryPaths':[],'externalResources':[]}
    def interrupted(sig,frame):raise KeyboardInterrupt(f'exact owned preview signal {sig}')
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    try:
        for p in resources:p.mkdir()
        env=dict(os.environ);env.update({'PYTHONDONTWRITEBYTECODE':'1','XDG_CONFIG_HOME':str(resources[0]),
            'XDG_CACHE_HOME':str(resources[1]),'TMPDIR':str(resources[2])})
        script=OUT/'render-mini-current.py'
        argv=['rtk','proxy',str(REPO/'.context/placid-badger/venv/bin/python'),str(script)]
        command={'argv':argv,'cwd':str(REPO),'startedAt':stamp(),'scriptSHA256':H(script),'runnerSHA256':H(Path(__file__)),
            'environment':{k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','XDG_CONFIG_HOME','XDG_CACHE_HOME','TMPDIR')},
            'canonical4Before':identity['canonical4'],'generatedManifestSHA256':identity['generatedManifestSHA256']}
        write(OUT/'render-command.json',command)
        with (OUT/'render.stdout.log').open('wb') as stdout,(OUT/'render.stderr.log').open('wb') as stderr:
            child=subprocess.Popen(argv,cwd=REPO,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            owner['processGroups']=[{'pid':child.pid,'pgid':child.pid,'argv':argv}]
            write(OUT/'ownership.json',owner)
            print(json.dumps({'output':str(OUT),'phase':'read-only current CAD/cache preview running','pgid':child.pid}),flush=True)
            code=child.wait()
        command.update({'exitCode':code,'completedAt':stamp(),'stdoutSHA256':H(OUT/'render.stdout.log'),'stderrSHA256':H(OUT/'render.stderr.log')})
        write(OUT/'render-command.json',command)
        assert code==0
        after={n:H(package/n) for n in identity['canonical4']}
        assert after==identity['canonical4']
        receipt['canonical4After']=after;receipt['canonicalFourBytesUnchanged']=True;receipt['exitCode']=0
        print(json.dumps({'output':str(OUT),'phase':'two whole current previews ready','canonical4Unchanged':True}),flush=True)
    finally:
        if child is not None:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            try:os.killpg(child.pid,0)
            except ProcessLookupError:absent=True
            else:
                absent=False;os.killpg(child.pid,signal.SIGTERM)
                for _ in range(50):
                    try:os.killpg(child.pid,0)
                    except ProcessLookupError:absent=True;break
                    time.sleep(.1)
                if not absent:
                    os.killpg(child.pid,signal.SIGKILL)
                    for _ in range(50):
                        try:os.killpg(child.pid,0)
                        except ProcessLookupError:absent=True;break
                        time.sleep(.1)
            receipt['processGroups'].append({'pid':child.pid,'pgid':child.pid,'absent':absent})
            if not absent:receipt['cleanupFailure']='exact owned process group survived'
        for p in resources:
            assert p.parent==OUT and p.name.startswith('placid-badger-') and not p.is_symlink()
            if p.exists():shutil.rmtree(p)
            receipt['temporaryPaths'].append({'path':str(p),'absent':not p.exists()})
        receipt['completedAt']=stamp();receipt['unknownOrSharedResourcesModified']=False
        write(OUT/'cleanup-receipt.json',receipt)
        if receipt.get('cleanupFailure'):raise RuntimeError(receipt['cleanupFailure'])


if __name__=='__main__':main()
