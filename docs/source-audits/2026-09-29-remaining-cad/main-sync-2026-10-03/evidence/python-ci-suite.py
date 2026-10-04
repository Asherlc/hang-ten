import subprocess,json,pathlib,time,os,hashlib
p=pathlib.Path(__file__).resolve().parent
root=p.parents[2]
python=root/'.context/placid-badger-cad-second-half/yy-baguette/venv/bin/python'
owned=p/'python-deps'
assert not owned.exists()
def run(label,cmd,env=None):
 start=time.time();r=subprocess.run(cmd,capture_output=True,text=True,env=env)
 (p/(label+'.stdout')).write_text(r.stdout);(p/(label+'.stderr')).write_text(r.stderr)
 (p/(label+'.json')).write_text(json.dumps({'command':cmd,'exitCode':r.returncode,'duration':time.time()-start},indent=2)+'\n')
 print(label,r.returncode,r.stdout[-7000:],r.stderr[-1000:],flush=True)
 return r.returncode
code=run('pyyaml-install',[str(python),'-m','pip','install','--no-deps','--target',str(owned),'--report',str(p/'pyyaml-install-report.json'),'PyYAML'])
if code:raise SystemExit(code)
env=dict(os.environ,PYTHONPATH=str(owned))
code=run('merged-ci-contract-tests',[str(python),'-m','pytest','Tools/HangboardPackages/tests/test_ci_xctest_contract.py','-q','--basetemp',str(p/'pytest-placid-badger-cad-second-half-ci')],env)
if code:raise SystemExit(code)
code=run('merged-complete-package-suite',[str(python),'-m','pytest','Tools/HangboardPackages/tests','-q','--basetemp',str(p/'pytest-placid-badger-cad-second-half-complete')],env)
raise SystemExit(code)
