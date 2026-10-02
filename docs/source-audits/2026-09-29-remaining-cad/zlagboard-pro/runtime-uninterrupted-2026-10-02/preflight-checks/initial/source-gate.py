from pathlib import Path
import subprocess,json,sys,hashlib
s=Path(sys.argv[1]);r=json.loads((s/'home-visual-approved.json').read_text());assert r['actualHomeConfirmed'] is True and r['responsiveAXConfirmed'] is True
head=subprocess.check_output(['rtk','proxy','git','rev-parse','HEAD']).decode().strip();status=subprocess.check_output(['rtk','proxy','git','status','--porcelain']);(s/'git-status-before-build.txt').write_bytes(status);assert not status.strip(),'Current HEAD must be clean before fresh build'
paths=['HangTen/Views/BoardModelView.swift','HangTen/Models/BoardModelRealityTypes.swift','HangTen/Views/RootView.swift'];record={'head':head,'cleanWorktree':True,'sourceSHA256':{n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in paths}};(s/'source-head-before-build.json').write_text(json.dumps(record,indent=2)+'\n')
