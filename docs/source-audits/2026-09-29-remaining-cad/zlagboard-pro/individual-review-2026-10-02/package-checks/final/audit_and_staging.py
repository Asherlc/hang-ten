from pathlib import Path
import sys,json,hashlib,zipfile,importlib.util,shutil,os,datetime
root=Path.cwd();out=root/'.context/placid-badger-cad-second-half/zlagboard-pro/package-checks/final';sys.path.insert(0,str(root/'Tools/HangboardPackages/src'))
from hangboard_packages import cad_source
from hangboard_packages.board_catalog import load_board_package
from pxr import Usd,UsdGeom,UsdShade
p=root/'Hangboards/zlagboard-pro';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'timestampUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'package':'zlagboard-pro','filesBefore':{str(x.relative_to(root)):sha(x) for x in p.rglob('*') if x.is_file()}}
loaded=load_board_package(p);r['schemaPassed']=True;r['boardID']=loaded.board.id
manifest=cad_source.generate_board_json(p/'zlagboard-pro.FCStd');(out/'published-generated-board.json').write_bytes(manifest)
b=json.loads(manifest);desc=json.loads((p/'assets/primary.model.json').read_text());stage=Usd.Stage.Open(str(p/'assets/primary.usdz'));meshes=[];material=[];bindings=[]
for prim in stage.Traverse():
 if prim.IsA(UsdGeom.Mesh):meshes.append({'name':prim.GetName(),'faces':len(UsdGeom.Mesh(prim).GetFaceVertexCountsAttr().Get())})
 if prim.IsA(UsdShade.Material) or prim.IsA(UsdShade.Shader):material.append(str(prim.GetPath()))
 for rel in prim.GetRelationships():
  if rel.GetName().startswith('material:binding'):bindings.append(str(rel.GetPath()))
r['usd']={'version':Usd.GetVersion(),'meshes':meshes,'materialsOrShaders':material,'materialBindings':bindings,'members':zipfile.ZipFile(p/'assets/primary.usdz').namelist(),'exactDescriptorNodes':sorted(m['name'] for m in meshes)==sorted(n['nodeID'] for n in desc['nodes']),'modelHashMatches':sha(p/'assets/primary.usdz')==desc['modelSHA256'],'unbound':not(material or bindings)}
r['manifest']={'woodFinish':b['presentations'][0]['media']['display'].get('surfaceFinish')=='wood','suspensionPresent':'suspension' in b['presentations'][0]['media'],'contactIDs':sorted(c['id'] for c in b['contacts'])}
mini=out/'staging-input';shutil.copytree(p,mini/'Hangboards/zlagboard-pro');shutil.copytree(root/'Tools/HangboardPackages/src/hangboard_packages',mini/'Tools/HangboardPackages/src/hangboard_packages',ignore=shutil.ignore_patterns('__pycache__'))
spec=importlib.util.spec_from_file_location('actual_staging',root/'scripts/stage-board-packages.py');staging=importlib.util.module_from_spec(spec);spec.loader.exec_module(staging)
ios=out/'ios/HangTen.app/Hangboards';android=out/'android/Hangboards';derived=out/'ios/derived'
os.environ.update(TARGET_BUILD_DIR=str(out/'ios'),UNLOCALIZED_RESOURCES_FOLDER_PATH='HangTen.app',DERIVED_FILE_DIR=str(derived))
staging.stage_board_packages(mini,ios,target='xcode',debug_simulator_model_slugs=frozenset())
staging.stage_board_packages(mini,android,target='android')
r['staging']={}
for target,dest in [('ios',ios),('android',android)]:
 package=dest/'zlagboard-pro';model=(derived/'HangTenModelODR/zlagboard-pro/Hangboards/zlagboard-pro/assets/primary.usdz') if target=='ios' else package/'assets/primary.usdz'
 r['staging'][target]={'generatedBoardMatchesSource':(package/'board.json').read_bytes()==manifest,'descriptorBytesMatch':(package/'assets/primary.model.json').read_bytes()==(p/'assets/primary.model.json').read_bytes(),'modelBytesMatch':model.read_bytes()==(p/'assets/primary.usdz').read_bytes(),'authoringFilesOmitted':not(package/'suspension.json').exists() and not(package/'zlagboard-pro.FCStd').exists(),'usdzDeliveryLocationCorrect':(package/'assets/primary.usdz').exists()==(target=='android'),'stagedFiles':sorted(str(x.relative_to(package)) for x in package.rglob('*') if x.is_file())}
r['sourceFilesUnchanged']=r['filesBefore']=={str(x.relative_to(root)):sha(x) for x in p.rglob('*') if x.is_file()}
r['passed']=r['schemaPassed'] and r['sourceFilesUnchanged'] and all(r['usd'][k] for k in ['exactDescriptorNodes','modelHashMatches','unbound']) and all(all(v for k,v in row.items() if k!='stagedFiles') for row in r['staging'].values())
(out/'published-package-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
