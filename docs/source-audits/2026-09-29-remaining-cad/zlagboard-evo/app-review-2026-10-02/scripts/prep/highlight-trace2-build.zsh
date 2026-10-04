#!/bin/zsh
set -euo pipefail
base="$PWD/.context/placid-badger-cad-second-half/zlagboard-evo/ios-resume-2026-10-02"
scratch="$base/highlight-regression/trace2-build"
result="$scratch/build-placid-badger-cad-second-half.xcresult"
cleanup() {
 rtk proxy rm -rf "$result"
 rtk proxy python3 - "$result" "$scratch/cleanup.json" <<'VERIFY'
from pathlib import Path
import sys,json
p,out=sys.argv[1:];Path(out).write_text(json.dumps({'exactResultBundle':p,'deleted':not Path(p).exists()},indent=2)+'\n');assert not Path(p).exists()
VERIFY
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rtk proxy mkdir -p "$scratch"
rtk proxy python3 - "$result" "$scratch/ownership.json" <<'OWN'
from pathlib import Path
import sys,json
p,out=sys.argv[1:];Path(out).write_text(json.dumps({'owner':'placid-badger-cad-second-half','exactResultBundle':p,'cleanup':'EXIT INT TERM trap before creation'},indent=2)+'\n')
OWN
uuid=1684856E-FC2D-4407-8063-9B343B99CAD6
derived="$base/DerivedData-placid-badger-cad-second-half"
build_status=0
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$uuid" -derivedDataPath "$derived" -resultBundlePath "$result" build > "$scratch/build.log" 2>&1 || build_status=$?
rtk proxy python3 - "$build_status" "$scratch/exit-status.json" <<'STATUS'
import sys,json
from pathlib import Path
Path(sys.argv[2]).write_text(json.dumps({'exitStatus':int(sys.argv[1])},indent=2)+'\n')
STATUS
rtk proxy xcrun xcresulttool get build-results --path "$result" > "$scratch/build-summary.json" 2> "$scratch/build-summary-stderr.txt" || true
(( build_status == 0 )) || exit "$build_status"
rtk proxy xcrun simctl install "$uuid" "$derived/Build/Products/Debug-iphonesimulator/HangTen.app" > "$scratch/install.log" 2>&1
rtk proxy xcrun simctl get_app_container "$uuid" com.hangten.training app > "$scratch/installed-container.txt"
