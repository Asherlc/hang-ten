from pathlib import Path
import subprocess,json,time,signal
s=Path('.context/placid-badger-cad-second-half/zlagboard-evo/ios-resume-2026-10-02');uid=(s/'simulator-ready').read_text().strip();derived=s/('DerivedData-'+Path.cwd().name);result=s/('tests-after-reboot-'+Path.cwd().name+'.xcresult')
assert not result.exists()
cmd=['rtk','proxy','xcodebuild','-project','HangTen.xcodeproj','-scheme','HangTen','-configuration','Debug','-destination','platform=iOS Simulator,id='+uid,'-derivedDataPath',str(derived),'-resultBundlePath',str(result),'-parallel-testing-enabled','NO','-only-testing:HangTenTests/BoardPackageStoreTests/testModelBoardFinishDecodesWithoutPerMeshSelections','-only-testing:HangTenTests/BoardModelRealityTests/testWoodFinishHighlightsAndRestoresEveryContactWithoutChangingPicking','test-without-building']
(s/'tests-retry-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (s/'tests-retry.log').open('wb') as log:
 proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:status=proc.wait(timeout=180)
 except subprocess.TimeoutExpired:
  (s/'tests-retry-timeout.json').write_text(json.dumps({'timeoutSeconds':180,'action':'SIGINT exact owned subprocess group','pid':proc.pid},indent=2)+'\n');__import__('os').killpg(proc.pid,signal.SIGINT)
  try:status=proc.wait(timeout=60)
  except subprocess.TimeoutExpired:__import__('os').killpg(proc.pid,signal.SIGTERM);status=proc.wait(timeout=30)
(s/'tests-retry-exit-status.txt').write_text(str(status)+'\n')
r=subprocess.run(['rtk','proxy','xcrun','xcresulttool','get','test-results','summary','--path',str(result)],capture_output=True)
(s/'tests-retry-summary.json').write_bytes(r.stdout);(s/'tests-retry-summary-stderr.txt').write_bytes(r.stderr)
print('Retry status',status)
