from pathlib import Path
import sys,json,hashlib,shutil,subprocess,datetime
root=Path.cwd();work=Path(__file__).resolve().parent;source=root/'.context/placid-badger-cad-second-half/runtime-resume-2026-10-02';mode=sys.argv[1];assert mode in ('copy','finalize');stamp=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
packetroot=root/'docs/source-audits/2026-09-29-remaining-cad'
destinations={'pro':packetroot/'zlagboard-pro/runtime-uninterrupted-2026-10-02','evo':packetroot/'zlagboard-evo/diagnostic-preparation-2026-10-02'}
baseline=json.loads((source/'packaging-preparation/baseline.json').read_bytes())
def preserved():
 groups={'canonical':baseline['canonicalPackageAppTestFiles'],'queueLock':baseline['sharedQueueLock'],'acceptance':baseline['humanAcceptanceRecords']}
 for key,val in baseline['existingProofTrees'].items():groups[key]=val['allExistingPackageProofFiles']
 counts={}
 for kind,files in groups.items():
  for name,expected in files.items():assert sha(root/name)==expected,(kind,name)
  counts[kind]=len(files)
 return counts

def cleanup():
 run=source/'ios-uninterrupted';r=json.loads((run/'final-runtime-validation.json').read_bytes());assert r['buildAttempted'] is False and r['installAttempted'] is False and r['boot']['readyForVisualApproval'] is False and r['contactCoverage']=={'required':28,'captured':0}
 own=json.loads((run/'ownership.json').read_bytes());proof=json.loads((run/'cleanup-verification.json').read_bytes());assert own['owner']=='placid-badger-cad-second-half' and own['simulator']==proof['uuid'];assert all(proof.get(k) is True for k in ['simulatorDeleted','derivedDataDeleted','resultBundleDeleted','testResultBundleDeleted'])
 cmd=['rtk','proxy','xcrun','simctl','list','devices','--json'];devices=json.loads(subprocess.check_output(cmd,timeout=20))['devices'];assert not any(d['udid']==own['simulator'] for rows in devices.values() for d in rows)
 for k in ['derivedData','resultBundle','testResultBundle']:
  p=Path(own[k]);assert p.resolve().is_relative_to(run.resolve()) and not p.exists(),p
 for name in ['paseo-owned-simulators','paseo-pending-simulators']:
  p=root/'.context'/name
  if p.exists():assert own['simulator'].upper() not in p.read_text().upper().splitlines()
 helper=json.loads((run/'helper-cleanup-verification.json').read_bytes());pids=[]
 for record in helper:
  cmd=['rtk','proxy','ps','-p',str(record['pid']),'-o','pid=,ppid=,comm='];result=subprocess.run(cmd,capture_output=True,timeout=10);assert not result.stdout.strip(),result.stdout
  pids.append({'pid':record['pid'],'absent':True,'queryExit':result.returncode})
 return {'uuid':own['simulator'],'exactUUIDAbsent':True,'resourcePathsAbsent':{k:own[k] for k in ['derivedData','resultBundle','testResultBundle']},'helperPIDs':pids,'rawValidationSHA256':sha(run/'final-runtime-validation.json'),'rawValidationUnmodified':True,'interpretation':'No Home/build/install;0/28. Raw fresh-app humanAccepted:false does not revoke prior native geometry acceptance.'}

def inventory(directory):return {str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
status=cleanup();scope=preserved();external=json.loads((source/'ios-uninterrupted.sha256.json').read_bytes());assert external==inventory(source/'ios-uninterrupted')
if mode=='copy':
 for d in destinations.values():
  assert not d.exists() or set(inventory(d)).issubset({'review.md','validation.json'}),d
 mappings={'pro':[],'evo':[]}
 for tree in ['ios-uninterrupted','independent','prep','preflight-checks','packaging-preparation']:
  for p in sorted((source/tree).rglob('*')):
   if p.is_file():mappings['pro'].append((p,tree+'/'+str(p.relative_to(source/tree))))
 for p in sorted(source.iterdir()):
  if p.is_file():mappings['pro'].append((p,p.name if p.name=='ios-uninterrupted.sha256.json' else 'diagnosis/'+p.name))
 for p in sorted((source/'renderer-review').rglob('*')):
  if p.is_file():mappings['evo'].append((p,str(p.relative_to(source/'renderer-review'))))
 for kind,mapping in mappings.items():
  mapping.append((Path(__file__).resolve(),'packaging-copy-recipe.py'))
  records=[]
  for origin,relative in mapping:
   expected=sha(origin);dest=destinations[kind]/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin,dest);assert sha(origin)==sha(dest)==expected
   records.append({'source':str(origin.relative_to(root)),'relativePath':relative,'sha256':expected,'bytes':dest.stat().st_size})
  for item in records:assert sha(root/item['source'])==item['sha256'],'Source changed while copying'
  result={'timestampUTC':stamp(),'scope':kind,'copied':records,'copyExact':True,'sourceStable':True,'fileCount':len(records),'excludedDuplicateTree':'lifecycle-review is identically retained under preflight-checks' if kind=='pro' else None,'noOriginalEvidenceRewritten':True}
  (destinations[kind]/'copy-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
  (work/(kind+'-copy-report.json')).write_text(json.dumps(result,indent=2)+'\n')
 report={'timestampUTC':stamp(),'passedCopyGate':True,'preservationCounts':scope,'cleanup':status,'groups':{k:{'destination':str(v.relative_to(root)),'copiedFileCount':len(mappings[k]),'copyInventorySHA256':sha(v/'copy-inventory.json')} for k,v in destinations.items()},'finalProofManifestPendingRootNotes':True}
 (work/'copy-gate-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
else:
 for kind,dest in destinations.items():
  copies=json.loads((dest/'copy-inventory.json').read_bytes())
  for item in copies['copied']:assert sha(dest/item['relativePath'])==sha(root/item['source'])==item['sha256'],item['relativePath']
  assert (dest/'review.md').exists() and (dest/'validation.json').exists(),'Wait for root notes'
  manifest=dest/'proof-sha256.json';assert not manifest.exists(),'Never overwrite final manifest without separate explicit refresh'
  files=inventory(dest);manifest.write_text(json.dumps({'algorithm':'sha256','files':files},indent=2)+'\n');assert {k:v for k,v in inventory(dest).items() if k!='proof-sha256.json'}==files
  result={'timestampUTC':stamp(),'passed':True,'packet':str(dest.relative_to(root)),'proofEntries':len(files),'manifestSHA256':sha(manifest),'copiedRawFilesExact':len(copies['copied']),'preservationCounts':scope,'cleanup':status,'acceptanceRecordsUnchanged':True,'queueLockUnchanged':True,'canonicalAppAndPackageBytesUnchanged':True,'noBuildNoInstallThisAttempt':True,'humanGeometryApprovalPreserved':True,'sourcePatchApplied':False,'limitations':'Checks copy/hash/scope/resource facts only; not a new app validation or geometry judgment. New root notes are included in manifest; raw failure evidence remains unchanged.'}
  output=work/(kind+'-final-audit.json');assert not output.exists();output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'kind':kind,'packet':str(dest.relative_to(root)),'proofEntries':len(files),'manifestSHA256':sha(manifest),'audit':str(output.relative_to(root)),'auditSHA256':sha(output)},indent=2))
