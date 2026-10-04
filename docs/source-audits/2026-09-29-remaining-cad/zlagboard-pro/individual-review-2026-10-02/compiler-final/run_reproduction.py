import sys,os,json,subprocess,tempfile,hashlib
from pathlib import Path
root=Path.cwd();out=Path(__file__).resolve().parent
sys.path.insert(0,str(root/"Tools/HangboardCAD"))
import verify_reproducible as verifier
work=Path(sys.argv[1]);report=Path(sys.argv[2]);tempfile.tempdir=str(work)
actual_run=subprocess.run;count=0
def retained_run(*args,**kwargs):
 global count
 count+=1;text_mode=kwargs.pop("text",False)
 result=actual_run(*args,**kwargs)
 (out/f"reproduction-freecad-{count}.stdout.log").write_bytes(result.stdout)
 (out/f"reproduction-freecad-{count}.stderr.log").write_bytes(result.stderr)
 if text_mode:
  result.stdout=result.stdout.decode("utf-8",errors="replace")
  result.stderr=result.stderr.decode("utf-8",errors="replace")
 return result
verifier.subprocess.run=retained_run
result=verifier.verify("zlagboard-pro",Path("/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"),os.environ["HANGTEN_CAD_PYTHONPATH"],out/"rebuild")
asset=root/"Hangboards/zlagboard-pro/assets/primary.model.json";rebuilt=out/"rebuild/zlagboard-pro/assets/primary.model.json"
result["descriptorBytesExact"]=asset.read_bytes()==rebuilt.read_bytes()
result["descriptorSHA256"]=hashlib.sha256(asset.read_bytes()).hexdigest()
result["rebuiltDescriptorSHA256"]=hashlib.sha256(rebuilt.read_bytes()).hexdigest()
result["sourceSHA256"]=hashlib.sha256((root/"Hangboards/zlagboard-pro/zlagboard-pro.FCStd").read_bytes()).hexdigest()
report.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result,indent=2))
raise SystemExit(0 if result["assetMatches"] and result["descriptorMatches"] and result["descriptorBindsCommittedAsset"] and result["descriptorBytesExact"] else 1)
