from pathlib import Path
import json,os,subprocess,time
root=Path.cwd();scratch=root/'.context/placid-badger/metolius-simulator-3d-plastic-review/ios'
uuid=(scratch/'simulator-ready').read_text().strip()
command=['xcodebuild','-project','HangTen.xcodeproj','-scheme','HangTen','-configuration','Debug','-destination','platform=iOS Simulator,id='+uuid,'-derivedDataPath','.context/DerivedData','build-for-testing']
identity={'owner':root.name,'simulator':uuid,'command':command,'timeoutSeconds':900}
(scratch/'ios-build-command.json').write_text(json.dumps(identity,indent=2)+'\n')
started=time.monotonic()
with (scratch/'ios-build.log').open('w') as log:
    completed=subprocess.run(['rtk','proxy',*command],cwd=root,env=dict(os.environ,TMPDIR=str(root/'.context/placid-badger/tmp')+'/'),stdout=log,stderr=subprocess.STDOUT,timeout=900)
identity.update(exitCode=completed.returncode,elapsedSeconds=time.monotonic()-started)
(scratch/'ios-build-command.json').write_text(json.dumps(identity,indent=2)+'\n')
print(json.dumps(identity,indent=2));raise SystemExit(completed.returncode)
