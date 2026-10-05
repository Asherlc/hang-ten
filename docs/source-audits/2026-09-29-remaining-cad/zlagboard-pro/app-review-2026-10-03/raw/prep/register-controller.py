from pathlib import Path
import sys,json,re
out,pid,name,*rest=sys.argv[1:];out=Path(out);owner='placid-badger-cad-second-half'
assert owner in name and out.resolve().is_relative_to((Path('.context')/owner/'pro-app-review-2026-10-03').resolve())
record={'owner':owner,'controllerPID':int(pid),'simulatorName':name,'simulatorUUID':rest[0] if rest else None,'derivedData':str(out/('DerivedData-'+owner)),'resultBundle':str(out/('build-'+owner+'.xcresult')),'testResultBundle':str(out/('tests-'+owner+'.xcresult')),'lifecyclePath':str((out.parent/'prep/lifecycle.zsh').resolve())}
if rest:
 assert re.fullmatch(r'[0-9A-Fa-f-]{36}',rest[0])
 for n in ['paseo-pending-simulators','paseo-owned-simulators']:
  with (Path('.context')/n).open('a') as f:f.write(rest[0]+'\n')
 (out/'simulator-uuid').write_text(rest[0]+'\n')
(out/'ownership.json').write_text(json.dumps(record,indent=2)+'\n')
