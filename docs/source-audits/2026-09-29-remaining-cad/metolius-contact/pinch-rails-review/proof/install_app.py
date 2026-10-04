from pathlib import Path
import hashlib
import json
import subprocess

root = Path.cwd()
scratch = root / '.context/placid-badger/metolius-contact-pinch-rails/ios'
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
          'nativeSourceSHA256': sha(root / 'Hangboards/metolius-contact/metolius-contact.FCStd')}
(scratch / 'installed-app-provenance.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
