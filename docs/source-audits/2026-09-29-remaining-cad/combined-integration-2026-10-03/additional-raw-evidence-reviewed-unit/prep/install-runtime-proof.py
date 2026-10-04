from pathlib import Path
import argparse,json,subprocess,shutil,re
from common import ROOT,WORKSPACE,OWNER,IOS,sha,write_new,ownership,run,verify_controller
p=argparse.ArgumentParser();p.add_argument('--build-proof',required=True);p.add_argument('--name',required=True);a=p.parse_args()
assert re.fullmatch(r'[a-zA-Z0-9_-]+',a.name) and re.fullmatch(r'[a-zA-Z0-9_-]+',a.build_proof)
b=ROOT/a.build_proof;out=ROOT/a.name;out.mkdir(exist_ok=False)
d=ownership();verify_controller(d,out)
source=json.loads((b/'source-reference.json').read_text());old=json.loads((b/'parity.json').read_text());assert old['allEqual'] and old['sourceUnchanged']
for x in source['files']:assert sha(WORKSPACE/x['path'])==x['sha256'],x['path']
for x in old['checks']:
 assert sha(x['builtPath'])==x['builtSHA256']
 if 'sourcePath' in x:assert sha(x['sourcePath'])==x['sourceSHA256']
assert not subprocess.check_output(['rtk','proxy','git','status','--porcelain','--untracked-files=no'],cwd=WORKSPACE,text=True).strip(),'Bind only committed clean source'
head=subprocess.check_output(['rtk','proxy','git','rev-parse','HEAD'],cwd=WORKSPACE,text=True).strip()
for name in ['build.command.json','build.exit.json','build.stdout','build.stderr','source-reference.json']:
 shutil.copyfile(b/name,out/name)
write_new(out/'build-proof-reuse.json',dict(originalDirectory=str(b),originalFiles={name:sha(b/name) for name in ['build.command.json','build.exit.json','build.stdout','build.stderr','source-reference.json']},rawBytesUnchanged=True))
write_new(out/'published-source-binding.json',dict(publishedCommit=head,frozenSourceRecord=str(b/'source-reference.json'),frozenSourceRecordSHA256=sha(b/'source-reference.json'),frozenHEADAtBuildStart=source['commit'],allFrozenFilesMatchCurrentCommittedWorktree=True,trackedWorktreeClean=True,qualification='Original build reference records its then-HEAD, including its separately frozen working-source hashes. No raw reference or proof is rewritten; this additional binding identifies the committed tree containing those exact source bytes.'))
app=Path(d['derivedData'])/'Build/Products/Debug-iphonesimulator/HangTen.app'
run(out,'install',['xcrun','simctl','install',d['simulatorUUID'],app],60)
run(out,'container',['xcrun','simctl','get_app_container',d['simulatorUUID'],'com.hangten.training','app'],30)
installed=Path((out/'container.stdout').read_text().strip());assert '/Devices/'+d['simulatorUUID']+'/' in str(installed)
checks=[]
for x in old['checks']:
 row=dict(x);live=installed/row['relativePath'];row['installedPath']=str(live);row['installedSHA256']=sha(live);row['equal']=row['builtSHA256']==row['installedSHA256']
 if 'sourceSHA256' in row:row['equal'] &= row['sourceSHA256']==row['builtSHA256']
 checks.append(row)
write_new(out/'parity.json',dict(nativePackageCount=old['nativePackageCount'],nativePackages=old['nativePackages'],selectedCanonicalFileCount=old['selectedCanonicalFileCount'],assignedNativeSourceCount=old['assignedNativeSourceCount'],allEqual=all(x['equal'] for x in checks),sourceUnchanged=True,checks=checks,originalBuildProof=str(b),publishedSourceCommit=head))
assert all(x['equal'] for x in checks)
d['installedApp']=str(installed);tmp=IOS/'ownership.json.tmp';tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(IOS/'ownership.json')
print('REINSTALLED_SAME_BUILT_BYTES_AND_CURRENT_PUBLISHED_SOURCE_PARITY_PASS',flush=True)
