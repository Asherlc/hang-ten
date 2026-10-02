from pathlib import Path
import json,sys,hashlib,shutil
w=Path(__file__).resolve().parent;f=w/'final-code-freeze'
sys.path.insert(0,str(f/'Tools/HangboardPackages/src'))
from hangboard_packages.board_catalog import load_board_package,read_board_json
p=w/'final-package/nature-stone-hanger';p.mkdir(parents=True,exist_ok=False)
for src,dest in ((w/'native-author/nature-stone-hanger.FCStd',p/'nature-stone-hanger.FCStd'),(w/'assets/primary.usdz',p/'assets/primary.usdz'),(w/'assets/primary.model.json',p/'assets/primary.model.json'),(w/'final-apply/suspension.json',p/'suspension.json')):
 dest.parent.mkdir(exist_ok=True);shutil.copy2(src,dest)
board=load_board_package(p);generated=read_board_json(p)
out=w/'final-package-validation.json';out.write_text(json.dumps({'status':'pass','validatedPackage':str(p),'fileSHA256':{str(v):hashlib.sha256(v.read_bytes()).hexdigest() for v in p.rglob('*') if v.is_file()},'generatedBoardSHA256':hashlib.sha256(generated).hexdigest(),'generatedBoardBytes':len(generated),'canonicalMutation':False},indent=2)+'\n')
print(str(out))
