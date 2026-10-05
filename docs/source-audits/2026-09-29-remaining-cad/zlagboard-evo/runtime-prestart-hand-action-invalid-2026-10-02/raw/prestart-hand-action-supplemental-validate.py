from pathlib import Path
import subprocess,json
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=E/'prestart-hand-action-landscape';records=[]
def run(name,cmd):
 out=p/(name+'.stdout');err=p/(name+'.stderr');assert not out.exists() and not err.exists();r=subprocess.run(['rtk','proxy','python3',*map(str,cmd)],capture_output=True);out.write_bytes(r.stdout);err.write_bytes(r.stderr);records.append(dict(name=name,command=cmd,exitStatus=r.returncode));print(name,r.returncode,flush=True);return r.returncode
status=run('original-validator-wrapper',[str(E/'prestart-hand-action-validate.py')]);prior=json.loads((p/'validator-command-results.json').read_text());unexpected=[x for x in prior if x['exitStatus']!=0 and x['helper']!='check-prestart-hands.py'];assert not unexpected,unexpected
assert len(prior) in [9,10] and all(x['exitStatus']==0 for x in prior[:8])
original=json.loads((p/'prestart-hand-validation.json').read_text());supp=run('supplemental-timing-check',[str(E/'prestart-hand-action-supplemental-helpers/check-supplemental-timing.py'),'action']);assert supp==0
if len(prior)==9:assert run('supplemental-downstream-comparison',[str(E/'prestart-hand-applied/runtime-helpers/action/compare.py')])==0
report=dict(originalWrapperExitStatus=status,originalProspectiveCheckPassed=all(original['checks'].values()),originalErrors=original['errors'],records=records,supplementalTimingCheckPassed=True,remainingEvidencePassed=True)
(p/'supplemental-validator-command-results.json').write_text(json.dumps(report,indent=2)+'\n')
