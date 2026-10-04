from pathlib import Path
import subprocess,json,hashlib,zipfile,datetime,re
root=Path.cwd();out=Path(__file__).parent;base='0a4c2cfe2';slug='zlagboard-pro';sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['rtk','proxy','git',*args])
def baseline(path):return git('show',base+':'+path)
def expected(data):
 if data.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
  return re.search(rb'oid sha256:([0-9a-f]{64})',data).group(1).decode()
 return sha(data)
paths=git('ls-tree','-r','--name-only',base,'--','Hangboards','HangTen','HangTenTests').decode().splitlines()
records=[]
for name in paths:
 if name.startswith('Hangboards/'+slug+'/'):continue
 p=root/name;wanted=expected(baseline(name));actual=sha(p.read_bytes()) if p.is_file() else None
 records.append({'path':name,'expectedSHA256':wanted,'actualSHA256':actual,'unchanged':wanted==actual})
assert all(x['unchanged'] for x in records)
qpath='docs/source-audits/2026-09-29-remaining-cad/review-queue.json';oldq=json.loads(baseline(qpath));newq=json.loads((root/qpath).read_bytes());oldrows={b['package']:b for b in oldq['boards']};newrows={b['package']:b for b in newq['boards']};queue={k:oldrows[k]==newrows[k] for k in oldrows if k!=slug};assert all(queue.values()) and oldrows.keys()==newrows.keys();assert {k:v for k,v in oldq.items() if k!='boards'}=={k:v for k,v in newq.items() if k!='boards'}
lpath='docs/model-delivery-lock.json';oldl=json.loads(baseline(lpath));newl=json.loads((root/lpath).read_bytes());allowed={'sha256Manifest','sha256ManifestHistory','supersededSha256Manifest','migratedPackages'};assert all(oldl.get(k)==newl.get(k) for k in set(oldl)|set(newl) if k not in allowed);locks={k:oldl['migratedPackages'][k]==newl['migratedPackages'][k] for k in oldl['migratedPackages'] if k!=slug};assert all(locks.values());assert oldl['migratedPackages'].keys()==newl['migratedPackages'].keys();assert newl['sha256ManifestHistory']==oldl['sha256ManifestHistory']+[oldl['sha256Manifest']];assert newl['supersededSha256Manifest']==oldl['sha256Manifest']
docroot='docs/source-audits/2026-09-29-remaining-cad/zlagboard-pro';historical=[]
for name in git('ls-tree','-r','--name-only',base,'--',docroot).decode().splitlines():
 a=baseline(name);b=(root/name).read_bytes();ok=b.startswith(a) if name.endswith('/source-audit.md') else expected(a)==sha(b);historical.append({'path':name,'unchangedOrAuditPrefixPreserved':ok});assert ok,name
source=root/'Hangboards/zlagboard-pro/zlagboard-pro.FCStd';digest=sha(source.read_bytes());common=Path(git('rev-parse','--git-common-dir').decode().strip());common=common if common.is_absolute() else root/common;obj=common/'lfs/objects'/digest[:2]/digest[2:4]/digest;assert zipfile.is_zipfile(source) and obj.is_file() and sha(obj.read_bytes())==digest
index=git('show',':Hangboards/zlagboard-pro/zlagboard-pro.FCStd');index_matches=expected(index)==digest
cleanup={stage:json.loads((out.parents[1]/'compiler-final'/f'{stage}-resources.json').read_bytes()) for stage in ['check','publish']};assert all(r['verifiedTemporaryDirectoryDeleted'] and r['childExited'] and not Path(r['exactTemporaryDirectory']).exists() for r in cleanup.values())
report={'timestampUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':git('rev-parse',base).decode().strip(),'passed':True,'outOfScopeByteChecks':records,'outOfScopeFileCount':len(records),'otherQueueRowsUnchanged':queue,'otherLockRecordsUnchanged':locks,'queueWrapperUnchanged':True,'lockWrapperChangesOnlyDigestAndHistory':True,'historicalProofs':historical,'nativeSource':{'sha256':digest,'bytes':source.stat().st_size,'realZIP':True,'realLFSObject':str(obj),'realLFSObjectExact':True,'indexCurrentlyMatches':index_matches,'indexNote':'Parent stages final files; actual native LFS object verified independently.'},'compilerOwnedTemporaryResourcesDeleted':True,'compilerCleanupRecords':cleanup,'limitations':'Canonical review document/packet assembly and runtime validation are ongoing. This proves package/source/global-row preservation at the recorded time, not human acceptance or completed app validation.'}
p=out/'scope-native-freeze.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'outOfScopeFileCount':len(records),'otherQueueRows':len(queue),'otherLockRecords':len(locks),'historicalFiles':len(historical),'sourceRealLFS':True,'sourceIndexMatches':index_matches,'report':str(p)},indent=2))
