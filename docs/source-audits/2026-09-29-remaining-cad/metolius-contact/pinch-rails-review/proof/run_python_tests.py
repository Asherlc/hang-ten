from pathlib import Path
import hashlib,json,os,subprocess,time
root=Path.cwd();scratch=root/'.context/placid-badger/metolius-contact-pinch-rails/ios'
command=[str(root/'.context/placid-badger/venv/bin/python'),'-m','pytest','Tools/HangboardCAD/tests','Tools/HangboardModels/tests','Tools/HangboardPackages/tests','-q','--basetemp',str(scratch/'placid-badger-full-pytest-tmp')]
meshopt=root/'.context/placid-badger/deps/meshoptimizer-build/libmeshoptimizer.dylib'
assert meshopt.is_file()
env=dict(os.environ,TMPDIR=str(root/'.context/placid-badger/tmp')+'/',MESHOPT_LIBRARY=str(meshopt))
report={'owner':root.name,'command':command,'timeoutSeconds':900,'meshoptimizerSHA256':hashlib.sha256(meshopt.read_bytes()).hexdigest()}
started=time.monotonic()
with (scratch/'python-tests.log').open('w') as log:
    result=subprocess.run(['rtk','proxy',*command],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
report.update(exitCode=result.returncode,elapsedSeconds=time.monotonic()-started,summary=(scratch/'python-tests.log').read_text().splitlines()[-1])
(scratch/'python-test-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(result.returncode)
