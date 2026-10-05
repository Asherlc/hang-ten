from pathlib import Path
import subprocess,json,time,signal,sys,os
phase=sys.argv[1];tests=sys.argv[2:];assert phase in ['red','red-timeline','normal-monotonic','green','candidate2','candidate3','candidate4'];assert tests
base=Path('.context/placid-badger-cad-second-half/zlagboard-evo/ios-resume-2026-10-02');s=base/'highlight-regression'/phase
uid=(base/'simulator-ready').read_text().strip();assert uid=='1684856E-FC2D-4407-8063-9B343B99CAD6'
derived=base/('DerivedData-'+Path.cwd().name);result=s/('tests-'+Path.cwd().name+'.xcresult');assert not result.exists()
cmd=['rtk','proxy','xcodebuild','-project','HangTen.xcodeproj','-scheme','HangTen','-configuration','Debug','-destination','platform=iOS Simulator,id='+uid,'-derivedDataPath',str(derived),'-resultBundlePath',str(result),'-parallel-testing-enabled','NO']+['-only-testing:HangTenTests/'+x for x in tests]+['test']
(s/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
start=time.time()
with (s/'tests.log').open('wb') as log:
 proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 (s/'process.json').write_text(json.dumps({'pid':proc.pid,'startedAtEpoch':start},indent=2)+'\n')
 try:status=proc.wait(timeout=300)
 except subprocess.TimeoutExpired:
  (s/'timeout.json').write_text(json.dumps({'timeoutSeconds':300,'action':'SIGINT exact owned subprocess group','pid':proc.pid},indent=2)+'\n');os.killpg(proc.pid,signal.SIGINT)
  try:status=proc.wait(timeout=60)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGTERM);status=proc.wait(timeout=30)
(s/'exit-status.json').write_text(json.dumps({'exitStatus':status,'elapsedSeconds':time.time()-start},indent=2)+'\n')
r=subprocess.run(['rtk','proxy','xcrun','xcresulttool','get','test-results','summary','--path',str(result)],capture_output=True)
(s/'summary.json').write_bytes(r.stdout);(s/'summary-stderr.txt').write_bytes(r.stderr)
print(phase,'test status',status)
