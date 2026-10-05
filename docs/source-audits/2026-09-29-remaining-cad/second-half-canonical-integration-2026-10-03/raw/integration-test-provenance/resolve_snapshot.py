import subprocess,json,hashlib,re,difflib,sys,importlib.util
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description="Create a scratch-only integration preview; never applies, stages, merges, or modifies refs")
parser.add_argument('--own',required=True,help='Explicit committed own revision; use a fresh commit after runtime edits')
parser.add_argument('--parent',default='40c16ae850bf5de26c1ebc2e167de4ef2958941c')
parser.add_argument('--output',type=Path,required=True,help='New nonexistent directory under workspace-owned .context')
args=parser.parse_args()
P=args.output.absolute()
owned=(Path.cwd()/'.context/placid-badger-cad-second-half').absolute()
assert P.is_relative_to(owned), 'output must be workspace owned'
assert not P.exists(), 'output must be new; preserve prior reports'
resolve=lambda ref:subprocess.check_output(['git','rev-parse',ref+'^{commit}'],text=True).strip()
refs={'base':'9399160729fcc418cedf47344b41163d244b5d96','own':resolve(args.own),'parent':resolve(args.parent)}
assert subprocess.check_output(['git','merge-base',refs['own'],refs['parent']],text=True).strip()==refs['base'], 'unexpected ancestry requires fresh review'
P.mkdir(parents=True)
files=['Tools/HangboardCAD/native_cord_routes.py','Tools/HangboardPackages/src/hangboard_packages/cad_source.py','docs/HANGBOARD_CORD_AUTHORING.md','docs/model-delivery-lock.json','docs/source-audits/2026-09-29-remaining-cad/review-queue.json']
preview=[]
for path in files:
    prefix=P/path.replace('/','__')
    for side,ref in refs.items(): Path(str(prefix)+'.'+side).write_bytes(subprocess.check_output(['git','show',ref+':'+path]))
    result=subprocess.run(['git','merge-file','-p','-L','own','-L','base','-L','parent',str(prefix)+'.own',str(prefix)+'.base',str(prefix)+'.parent'],capture_output=True)
    Path(str(prefix)+'.merge-preview.txt').write_bytes(result.stdout)
    Path(str(prefix)+'.merge-stderr.txt').write_bytes(result.stderr)
    assert result.returncode in (0,1,2), 'merge-file error'
    if path not in (files[0],files[3]): assert result.returncode==0, 'new conflict requires manual review: '+path
    preview.append({'file':path,'mergeFileExitStatus':result.returncode})
(P/'overlap-merge-preview.json').write_text(json.dumps({'refs':refs,'files':preview,'previewOnly':True},indent=2)+'\n')
def git(*args): return subprocess.check_output(['git',*args])
def blob(side,path): return git('show',refs[side]+':'+path)
def paths(side): return set(git('ls-tree','-r','--name-only',refs[side]).decode().splitlines())
allpaths={s:paths(s) for s in refs}
changed={s:set(git('diff','--name-only',refs['base'],refs[s]).decode().splitlines()) for s in ('own','parent')}
R=P/'resolved';R.mkdir(exist_ok=True)
route='Tools/HangboardCAD/native_cord_routes.py'
t=(P/(route.replace('/','__')+'.merge-preview.txt')).read_text()
pattern=r'<<<<<<< own\n(.*?)=======\n(.*?)>>>>>>> parent\n'
m=re.search(pattern,t,re.S);assert m and len(re.findall(pattern,t,re.S))==1, 'unreviewed solver conflict structure'
own=m[1].replace('solve_native_routes(mesh, one, descriptor)', 'solve_native_routes(mesh, one, descriptor, source_metadata=source_metadata)')
t=t[:m.start()]+own+m[2]+t[m.end():]
assert 'source_metadata=None' in t
assert '<<<<<<<' not in t and '>>>>>>>' not in t
for path in [route,'Tools/HangboardPackages/src/hangboard_packages/cad_source.py','docs/HANGBOARD_CORD_AUTHORING.md','docs/source-audits/2026-09-29-remaining-cad/review-queue.json']:
 out=R/path;out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(t if path==route else (P/(path.replace('/','__')+'.merge-preview.txt')).read_text())
lockpath='docs/model-delivery-lock.json'
locks={s:json.loads(blob(s,lockpath)) for s in refs}
def merge_json(base, own, parent, path=''):
    if own == parent: return own
    if own == base: return parent
    if parent == base: return own
    if path == '/sha256Manifest': return None  # rebuilt below from exact Git objects
    if isinstance(base,dict) and isinstance(own,dict) and isinstance(parent,dict):
        keys=list(dict.fromkeys([*base,*own,*parent]))
        missing=object(); result={}
        for key in keys:
            value=merge_json(base.get(key,missing),own.get(key,missing),parent.get(key,missing),path+'/'+key)
            if value is not missing: result[key]=value
        return result
    if path in ('/sha256ManifestHistory','/individualReviewRevisions'):
        result=[]
        for value in [*base,*own,*parent]:
            if value not in result: result.append(value)
        return result
    raise ValueError('unreviewed semantic JSON conflict: '+path)
merged=merge_json(locks['base'],locks['own'],locks['parent'])
hist=[]
for side in ('base','own','parent'):
 for item in locks[side]['sha256ManifestHistory']:
  if item not in hist:hist.append(item)
for side in ('own','parent'):
 item={'sha256Manifest':locks[side]['sha256Manifest'],'reason':'Exact snapshot before combined integration preview','commit':refs[side]}
 if item not in hist:hist.append(item)
merged['sha256ManifestHistory']=hist
# Exact checksum identity uses LFS payload OID; no need to fetch/read another worktree.
def digest(b):
 m=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize [0-9]+\n',b)
 return m[1].decode() if m else hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('delivery',Path.cwd()/'scripts/verify-model-delivery.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
suffixes={pkg:mod.package_suffixes(Path.cwd(),pkg) for pkg in merged['modelPackages']}
manifests={}
for side in ('own','parent','combined'):
 rows=[]
 for pkg in merged['modelPackages']:
  for suffix in suffixes[pkg]:
   path=f'Hangboards/{pkg}/{suffix}'
   src=('parent' if path in changed['parent'] else 'own') if side=='combined' else side
   rows.append((path,digest(blob(src,path))))
 text=''.join(f'{h}  {p}\n' for p,h in sorted(rows)); manifests[side]=hashlib.sha256(text.encode()).hexdigest();(P/f'{side}-delivery-checksums.txt').write_text(text)
 if side!='combined':assert manifests[side]==locks[side]['sha256Manifest'],(side,manifests[side],locks[side]['sha256Manifest'])
merged['sha256Manifest']=manifests['combined'];(R/lockpath).write_text(json.dumps(merged,indent=2)+'\n')
# Metadata acceptance preservation follows package owners; no record loss.
queuepath='docs/source-audits/2026-09-29-remaining-cad/review-queue.json'
qs={s:json.loads(blob(s,queuepath)) for s in refs};qm=json.loads((R/queuepath).read_text())
for i,row in enumerate(qm['boards']):
 expected=qs['own' if row['number']>=16 else 'parent']['boards'][i];assert row==expected
 if row['number']<=8:assert row==qs['base']['boards'][i]
for pkg,rec in merged['migratedPackages'].items():
 b=locks['base']['migratedPackages'][pkg];o=locks['own']['migratedPackages'][pkg];par=locks['parent']['migratedPackages'][pkg]
 assert not(o!=b and par!=b),pkg
 assert rec==(par if par!=b else o),pkg
for side in ('own','parent'):
 assert all(r in merged['individualReviewRevisions'] for r in locks[side]['individualReviewRevisions'])
owned={'yy-baguette','yy-baguette-evo','yy-penta-evo','yy-travelboard','zlagboard-evo','zlagboard-pro'}
assert all(x.split('/')[1] in owned for x in changed['own'] if x.startswith('Hangboards/'))
assert all(x.split('/')[1] not in owned for x in changed['parent'] if x.startswith('Hangboards/'))
# Minimal Python-only overlay uses Git objects and exact resolved blobs; no checkout mutation.
overlay=P/'test-overlay'
pythonpaths={x for x in allpaths['own']|allpaths['parent'] if (x.startswith('Tools/HangboardCAD/') or x.startswith('Tools/HangboardPackages/')) and x.endswith(('.py','.json'))}
for path in pythonpaths:
 target=overlay/path;target.parent.mkdir(parents=True,exist_ok=True)
 data=(R/path).read_bytes() if (R/path).exists() else blob('parent' if path in changed['parent'] else 'own',path)
 target.write_bytes(data)
patches=[]
for path in [route,'Tools/HangboardPackages/src/hangboard_packages/cad_source.py','docs/HANGBOARD_CORD_AUTHORING.md',lockpath,queuepath]:
 patches.extend(difflib.unified_diff(blob('own',path).decode().splitlines(True),(R/path).read_text().splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(P/'resolved-shared-files.patch').write_text(''.join(patches))
report={'refs':refs,'previewOnly':True,'worktreeOrRefMutation':False,'otherParentSnapshotChangesMustAlsoBeIntegrated':sorted(changed['parent']-changed['own']),'ownChangedPaths':len(changed['own']),'parentChangedPaths':len(changed['parent']),'sharedOverlaps':sorted(changed['own']&changed['parent']),'checks':{'all21QueueRowsPreservedFromOwner':True,'accepted1Through8RowsExact':True,'all57MigrationRecordsPreservedFromOwner':True,'allRevisionRecordsRetained':True,'bothManifestHistoriesRetained':True,'bothPriorManifestDigestsIndependentlyReconstructed':True,'ownPackageScopeOnly16Through21':True,'parentPackagesDisjoint':True},'manifestSHA256':manifests,'resolvedFiles':{str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in R.rglob('*') if x.is_file()},'checksumMethod':'Git blob SHA256; Git LFS pointer OID represents payload SHA256. Full inherited descriptor path list independently reconstructs both snapshot aggregate hashes exactly; no runtime package validation claimed.'}
(P/'resolved-preview-report.json').write_text(json.dumps(report,indent=2)+'\n')
test_source=Path(__file__).with_name('test_integration_dispatch.py')
(overlay/'Tools/HangboardCAD/tests/test_integration_dispatch.py').write_bytes(test_source.read_bytes())
print(json.dumps({k:v for k,v in report.items() if k!='otherParentSnapshotChangesMustAlsoBeIntegrated'},indent=2))
