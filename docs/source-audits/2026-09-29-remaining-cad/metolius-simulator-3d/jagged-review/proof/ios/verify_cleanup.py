from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
ios = root / '.context/placid-badger/metolius-simulator-3d-jagged/ios'
uid = (ios / 'simulator-ready').read_text().strip()
assert uid == '5DBF7406-93EC-474A-9320-931FC57FA394'
cleanup = json.loads((ios / 'ios-cleanup.json').read_text())
assert cleanup['simulator'] == uid and cleanup['cleanupStatus'] == 0
command = ['rtk', 'proxy', 'xcrun', 'simctl', 'list', 'devices', '--json']
raw = subprocess.check_output(command, timeout=30)
(ios / 'devices-fresh-deletion-verification.json').write_bytes(raw)
devices = json.loads(raw)
assert not any(d['udid'] == uid for group in devices['devices'].values() for d in group)
assert not (root / '.context/DerivedData').exists()
assert not (ios / 'placid-badger-simulator-jagged-tests.xcresult').exists()
record = {
    'verifiedAtUTC': datetime.now(timezone.utc).isoformat(), 'owner': root.name,
    'simulator': uid, 'exactSimulatorAbsent': True, 'derivedDataRemoved': True,
    'xcresultRemoved': True, 'cleanupStatus': 0,
    'command': command,
    'devicesJSONSHA256': hashlib.sha256(raw).hexdigest(),
    'lifecycle': 'The registered EXIT trap performed teardown before this independent read-only verification.',
}
(ios / 'verified-cleanup.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
