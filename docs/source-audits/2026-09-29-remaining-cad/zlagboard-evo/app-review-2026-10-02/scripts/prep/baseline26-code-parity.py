from pathlib import Path
import hashlib,json,subprocess,sys
s=Path('.context/placid-badger-cad-second-half/zlagboard-evo/ios-26-4');out=s/sys.argv[1];out.mkdir(exist_ok=False)
built=s/'Products-placid-badger-cad-second-half/HangTen.app';raw=subprocess.check_output(['rtk','proxy','xcrun','simctl','get_app_container',(s/'simulator-ready').read_text().strip(),'com.hangten.training','app']);(out/'installed-container.txt').write_bytes(raw);installed=Path(raw.decode().strip());magic={bytes.fromhex(x) for x in ['feedface','cefaedfe','feedfacf','cffaedfe','cafebabe','bebafeca','cafebabf','bfbafeca']}
def codes(base):
 result={}
 for p in base.rglob('*'):
  if p.is_file():
   with p.open('rb') as f:m=f.read(4)
   if m in magic:result[str(p.relative_to(base))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
 return result
b,i=codes(built),codes(installed);r={'builtApp':str(built.resolve()),'installedApp':str(installed),'builtMachO':b,'installedMachO':i,'allCodeEqual':b==i,'different':[x for x in sorted(set(b)|set(i)) if b.get(x)!=i.get(x)]};(out/'mach-o-parity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'allCodeEqual':b==i,'count':len(b),'different':r['different'],'debugDylibSHA256':b.get('HangTen.debug.dylib',{})},indent=2));assert b==i
