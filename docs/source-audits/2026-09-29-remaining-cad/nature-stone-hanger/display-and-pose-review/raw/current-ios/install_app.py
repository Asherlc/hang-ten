from pathlib import Path
import hashlib
import json
import subprocess
import sys
sys.path.insert(0, str(Path.cwd()/'Tools/HangboardPackages/src'))
from hangboard_packages.board_catalog import read_board_json

root = Path.cwd()
scratch = root / '.context/placid-badger/nature-stone-review9/vertical-groove-ios'
uid = (scratch / 'simulator-ready').read_text().strip()
app = root / '.context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app'
assert json.loads((scratch / 'ios-build-command.json').read_text())['exitCode'] == 0
subprocess.run(['rtk', 'proxy', 'xcrun', 'simctl', 'install', uid, str(app)], check=True, timeout=120)
installed = Path(subprocess.check_output([
    'rtk', 'proxy', 'xcrun', 'simctl', 'get_app_container', uid,
    'com.hangten.training', 'app'], text=True, timeout=30).strip())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert (app / 'HangTen').read_bytes() == (installed / 'HangTen').read_bytes()
record = {'owner': root.name, 'simulator': uid, 'builtApp': str(app),
          'installedApp': str(installed), 'builtBinarySHA256': sha(app / 'HangTen'),
          'installedBinarySHA256': sha(installed / 'HangTen'), 'binaryBytesMatch': True,
          'nativeSourceSHA256': sha(root / 'Hangboards/nature-stone-hanger/nature-stone-hanger.FCStd')}
package=root/'Hangboards/nature-stone-hanger'
inputs=json.loads((scratch/'final-inputs.json').read_text())
for rel,expected in inputs['packageSHA256'].items(): assert sha(root/rel)==expected
canonical=read_board_json(package)
bundled=installed/'Hangboards/nature-stone-hanger/board.json'
assert canonical==bundled.read_bytes()==(app/'Hangboards/nature-stone-hanger/board.json').read_bytes()
manifest=json.loads(canonical)
record.update(generatedManifestSHA256=sha(bundled), generatedManifestBytesMatchSource=True,
    sidecarSHA256=sha(package/'suspension.json'), packageSHA256=inputs['packageSHA256'],
    contactIDs=[x['id'] for x in manifest['contacts']],positions=manifest['positions'])
models=[]
for presentation in manifest['presentations']:
    media=presentation['media']
    if media['type']!='model': continue
    desc=installed/'Hangboards/nature-stone-hanger'/media['descriptorPath']
    assert desc.read_bytes()==(package/media['descriptorPath']).read_bytes()
    expected=sha(package/media['assetPath'])
    candidates=list(installed.rglob(Path(media['assetPath']).name))
    candidates=[p for p in candidates if sha(p)==expected]
    # Embedded ODR packs must contain the current model before launch.
    assert candidates, 'Current USDZ missing from installed app/embedded ODR packs'
    models.append({'presentationID':presentation['id'],'descriptorSHA256':sha(desc),'modelSHA256':expected,'installedModelPaths':[str(p) for p in candidates]})
record['models']=models
record['commit']=subprocess.check_output(['rtk','proxy','git','rev-parse','HEAD'],text=True).strip()
diff=subprocess.check_output(['rtk','proxy','git','diff','--binary','HEAD'])
(scratch/'build-dirty-diff.patch').write_bytes(diff)
record['dirtyDiffSHA256']=hashlib.sha256(diff).hexdigest()
(scratch/'git-status.txt').write_text(subprocess.check_output(['rtk','proxy','git','status','--porcelain=v1'],text=True))
(scratch / 'installed-app-provenance.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
