from pathlib import Path
import json,hashlib,shutil,sys,os,datetime
w=Path(__file__).resolve().parent;root=Path.cwd();audit=Path(sys.argv[1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
independent=json.loads(audit.read_text());assert independent['status']=='pass-independent-new-geometry-rounded-candidate-only' and not independent['blockingFindings']
assert independent['routeCount']==16 and independent['poseCount']==8
apply=w/'final-apply';check=w/'final-check'
for mode in ('apply','check'):
 complete=json.loads((w/('final-'+mode)/'completion.json').read_text());assert complete['status']=='pass'
 receipt=json.loads((w/('placid-badger-final-'+mode+'-v2-ownership.json')).read_text())
 assert receipt['exitCode']==0 and receipt['ownedProcessGroupAbsent'] and receipt['ownedTmpAbsent']
assert json.loads((check/'completion.json').read_text())['freshIndependentRegenerationMatches']
for name in ('native-route-report.json','suspension.json'):assert (apply/name).read_bytes()==(check/name).read_bytes()
assert sha(apply/'suspension.json')==independent['scratchCandidateSidecarSHA256']
validation=json.loads((w/'final-package-validation.json').read_text());assert validation['status']=='pass'
for path,digest in validation['fileSHA256'].items():assert sha(Path(path))==digest
baseline=json.loads((w/'takeover-package-baseline.json').read_text())['files'];current={str(p):sha(p) for p in Path('Hangboards').rglob('*') if p.is_file()}
assert current==baseline,'package files changed during isolated solve; recheck explicitly before any promotion'
package=Path('Hangboards/nature-stone-hanger');pairs=[(w/'native-author/nature-stone-hanger.FCStd',package/'nature-stone-hanger.FCStd'),(w/'assets/primary.usdz',package/'assets/primary.usdz'),(w/'assets/primary.model.json',package/'assets/primary.model.json'),(apply/'suspension.json',package/'suspension.json')]
expected={independent['sourceSHA256'],independent['modelSHA256'],independent['descriptorSHA256'],independent['scratchCandidateSidecarSHA256']}
assert {sha(a) for a,b in pairs}==expected
for src,dest in pairs:shutil.copyfile(src,dest)
now={str(p):sha(p) for p in Path('Hangboards').rglob('*') if p.is_file()}
changed=[p for p in baseline if baseline[p]!=now[p]]
assert set(now)==set(baseline) and set(changed)=={str(b) for a,b in pairs}
report={'status':'pass','timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'packageSHA256':{str(b):sha(b) for a,b in pairs},'changedFiles':changed,'unchangedOtherPackageFiles':len(now)-len(changed),'allOtherPackageFilesUnchanged':True,'independentAuditPath':str(audit),'independentAuditSHA256':sha(audit),'codeFreezeSHA256':sha(w/'final-code-freeze/freeze.json'),'colliderSHA256':sha(w/'native-collision-vertical.json'),'applyReportSHA256':sha(apply/'native-route-report.json'),'checkReportSHA256':sha(check/'native-route-report.json'),'twoReportsAndSidecarsByteIdentical':True,'humanAcceptance':'pending','rootRuntimeReview':'pending','noGitMutation':True}
(w/'final-promotion.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
