from pathlib import Path
import sys,json,subprocess,shutil
uid,products,folder=sys.argv[1:];s=Path(folder);s.mkdir(parents=True,exist_ok=True);records=[]
def run(args):
 cmd=['rtk','proxy',*args];r=subprocess.run(cmd,capture_output=True);records.append({'command':cmd,'exitStatus':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')});return r
rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))['devices'];matched=[d for ds in rows.values() for d in ds if d['udid']==uid]
if matched:
 assert len(matched)==1 and matched[0]['name'].startswith('Hang Ten Paseo placid-badger-cad-second-half ')
 if matched[0]['state']=='Booted':run(['xcrun','simctl','shutdown',uid])
 run(['xcrun','simctl','delete',uid])
p=Path(products);assert p.name=='Products-placid-badger-cad-second-half' and 'ios-26-4' in p.parts
shutil.rmtree(p,ignore_errors=True)
rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))['devices'];deleted=not any(d['udid']==uid for ds in rows.values() for d in ds)
if deleted and uid:
 for name in ['paseo-owned-simulators','paseo-pending-simulators']:
  p=Path('.context')/name
  if p.exists():p.write_text(''.join(x+'\n' for x in p.read_text().splitlines() if x.upper()!=uid.upper()))
r={'uuid':uid,'simulatorDeleted':deleted,'preservedProductsDeleted':not Path(products).exists(),'derivedDataCreated':False,'resultBundleCreated':False,'commands':records};(s/'cleanup-verification.json').write_text(json.dumps(r,indent=2)+'\n');assert r['simulatorDeleted'] and r['preservedProductsDeleted']
