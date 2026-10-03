#!/usr/bin/env python3
"""Exact owned subprocesses for one bounded geometry-proxy census."""
import argparse,hashlib,json,os,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
from run_native_contact_screen import OwnedCommands,REPO

parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--fixtures-only',action='store_true');args=parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert Path(os.environ.get('PASEO_WORKTREE_PATH',REPO)).resolve()==REPO and REPO.name=='strong-owl-live-physics'
tool=Path(__file__).resolve().parent/'certified_proxy'
root=REPO/'.context'/f'{REPO.name}-certified-proxy-{args.label}';root.mkdir()
red=root/'red_geometry.py'
red.write_text((tool/'geometry.py').read_text().replace('def proposal(vertices,faces,errors,center,ids):','def proposal(vertices,faces,errors,center,ids):\n    return None # absent geometric replacement negative control'))
files=[*tool.glob('*.py'),Path(__file__),red,REPO/'.context/strong-owl-live-physics-certified-proxy-proposal/PLAN.md']
(root/'provenance.json').write_text(json.dumps({'owner':REPO.name,'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},indent=2)+'\n')
owner=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,owner.interrupted)
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
try:
    command=[sys.executable,'-c',"import importlib.util,sys;spec=importlib.util.spec_from_file_location('red',sys.argv[1]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.fixtures()",str(red)]
    rc=owner.run('proxy-red',command,root/'red.log',env)
    assert rc==1 and 'shallow curved fan must certify' in (root/'red.log').read_text(),'RED must fail for absent replacement'
    rc=owner.run('proxy-green',[sys.executable,str(tool/'census.py'),'--output',str(root/'fixture'),'--fixtures-only'],root/'green.log',env)
    print((root/'green.log').read_text(),end='',flush=True)
    if rc:sys.exit(rc)
    if args.fixtures_only:sys.exit(0)
    rc=owner.run('proxy-census',['perl','-e','alarm 600;exec @ARGV',sys.executable,str(tool/'census.py'),'--output',str(root/'census')],root/'census.log',env)
    print((root/'census.log').read_text(),end='',flush=True)
    sys.exit(rc)
finally:
    owner.cleanup()
