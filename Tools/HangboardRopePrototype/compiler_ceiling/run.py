import pathlib,sys,argparse,json,hashlib,os,signal,statistics,math
sys.dont_write_bytecode=True
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from run_native_contact_screen import REPO,OwnedCommands
ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);args=ap.parse_args()
assert REPO.name=='strong-owl-live-physics' and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
root=REPO/'.context'/f'{REPO.name}-compiler-ceiling-{args.label}';root.mkdir();sources=root/'sources';sources.mkdir()
prior=REPO/'.context/strong-owl-live-physics-stationary-residual-e09fc8a-loaded-full-540'
tool=pathlib.Path(__file__).resolve().parent
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((REPO/'docs/source-audits/2026-10-03-live-loaded-start-screen.json').read_text())
assert audit['evidenceSHA256'][str((prior/'result.json').relative_to(REPO))]==h(prior/'result.json')
hashes=json.loads((prior/'provenance.json').read_text())['hashes']
for p in (prior/'sources').glob('*.swift'):
 assert hashes[str(p.relative_to(REPO))]==h(p)
 if p.name!='main.swift':(sources/p.name).write_bytes(p.read_bytes())
(sources/'main.swift').write_bytes((tool/'Main.swift.txt').read_bytes())
commands={mode:['xcrun','swiftc','-O' if mode=='checked' else '-Ounchecked','-D','DEBUG','-whole-module-optimization',
 '-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(root/'module-cache'),
 *[str(p) for p in sorted(sources.glob('*.swift'))],'-o',str(root/(REPO.name+'-'+mode))] for mode in ['checked','unchecked']}
(root/'provenance.json').write_text(json.dumps({'owner':REPO.name,'commands':commands,'loadedInputSHA256':h(prior/'loaded-input.json'),
 'sourceSHA256':{str(p.relative_to(REPO)):h(p) for p in sources.glob('*.swift')}},indent=2))
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
status=0;result={'owner':REPO.name,'adopted':False,'uncheckedDeployable':False,'pass':False}
try:
 for mode,command in commands.items():
  status=c.run('compile-'+mode,['perl','-e','alarm 180;exec @ARGV',*command],root/('compile-'+mode+'.log'),dict(os.environ))
  if status:break
 if not status:
  ratios=[];times={'checked':[],'unchecked':[]};anchor=None
  for pair in range(7):
   total={}
   for mode in (['checked','unchecked'] if pair%2==0 else ['unchecked','checked']):
    label=f'{pair}-{mode}'
    status=c.run('run-'+label,['perl','-e','alarm 60;exec @ARGV',str(root/(REPO.name+'-'+mode)),str(root),str(prior/'loaded-input.json'),label],root/(label+'.log'),dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1'))
    if status:raise RuntimeError(label+' failed')
    records=json.loads((root/(label+'.json')).read_text())
    signatures=[{k:v for k,v in row.items() if k!='seconds'} for row in records]
    if anchor is None:anchor=signatures
    assert signatures==anchor,'complete checkpoint/decision/metric mismatch: '+label
    total[mode]=sum(row['seconds'] for row in records)
    times[mode].extend(row['seconds'] for row in records)
   ratios.append(total['unchecked']/total['checked'])
  p95={mode:sorted(v)[math.ceil(.95*(len(v)-1))] for mode,v in times.items()}
  result.update(checkpointAndDecisionIdentity=True,pairRatios=ratios,medianRatio=statistics.median(ratios),p95Seconds=p95,
    pass_=p95['unchecked']<.004 and statistics.median(ratios)<=4/6.888)
  result['pass']=result.pop('pass_')
  if not result['pass']:status=3
except Exception as e:result['failure']=str(e);status=3
finally:
 c.cleanup()
 (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(status)
