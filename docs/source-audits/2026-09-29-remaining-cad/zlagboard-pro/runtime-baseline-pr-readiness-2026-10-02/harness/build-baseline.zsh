#!/bin/zsh
set -euo pipefail
workspace_path="$PWD"
workspace_name="${workspace_path:t}"
scratch="$workspace_path/.context/$workspace_name/pr-readiness-repair-2026-10-02/ios-diagnosis"
bounded="$workspace_path/.context/$workspace_name/pr-readiness-repair-2026-10-02/prep/bounded-command.py"
derived="$scratch/DerivedData-$workspace_name"
result="$scratch/build-$workspace_name.xcresult"
uuid="$(rtk proxy cat "$scratch/diagnostic-device-created")"
rtk proxy python3 - "$scratch" "$uuid" <<'OWNED'
from pathlib import Path
import json,sys
s=Path(sys.argv[1]);uid=sys.argv[2];r=json.loads((s/'ownership.json').read_text());assert r['simulator']==uid and r['owner']==Path.cwd().name
assert uid in Path('.context/paseo-owned-simulators').read_text().splitlines()
assert not (s/'cleanup-verification.json').exists(),'Owner lifecycle must still be active'
OWNED
rtk proxy python3 "$workspace_path/.context/$workspace_name/pr-readiness-repair-2026-10-02/prep/source-gate.py" "$scratch"
while [[ ! -f "$workspace_path/.context/$workspace_name/zlagboard-pro/final-ready.json" ]]; do
  rtk proxy sleep 3
done
rtk proxy python3 - "$workspace_path/.context/$workspace_name/zlagboard-pro/final-ready.json" <<'GATE'
import hashlib,json,sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
assert record.get('authorizedByParent') is True
for name,expected in record['packageSHA256'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
GATE
rtk proxy python3 - "$scratch/source-package-sha256-before-build.json" <<'HASH'
import hashlib,json,sys
from pathlib import Path
package=Path('Hangboards/zlagboard-pro')
paths=[package/'zlagboard-pro.FCStd',package/'assets/primary.usdz',package/'assets/primary.model.json']
assert paths[0].read_bytes()[:2]==b'PK','FCStd must be real archive, not LFS pointer'
Path(sys.argv[1]).write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
HASH
rtk proxy python3 Tools/HangboardCAD/board_manifest.py --package zlagboard-pro --output "$scratch/generated-board-at-build.json"
build_status=0
rtk proxy python3 "$bounded" 600 "$scratch/build-command.json" xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "generic/platform=iOS Simulator" -derivedDataPath "$derived" -resultBundlePath "$result" build > "$scratch/build.log" 2>&1 || build_status=$?
print "$build_status" > "$scratch/build-exit-status.txt"
rtk proxy python3 "$bounded" 30 "$scratch/build-summary-command.json" xcrun xcresulttool get build-results --path "$result" > "$scratch/build-results-summary.json" 2> "$scratch/build-results-summary-stderr.txt" || true
(( build_status == 0 )) || exit "$build_status"
rtk proxy python3 "$workspace_path/.context/$workspace_name/pr-readiness-repair-2026-10-02/prep/build-parity.py"
rtk proxy python3 "$bounded" 40 "$scratch/install-command.json" xcrun simctl install "$uuid" "$derived/Build/Products/Debug-iphonesimulator/HangTen.app" > "$scratch/install.log" 2>&1
rtk proxy python3 "$bounded" 20 "$scratch/container-command.json" xcrun simctl get_app_container "$uuid" com.hangten.training app > "$scratch/installed-container.txt"
print -r -- "$uuid" > "$scratch/simulator-ready"
print "Build ready: $uuid"
