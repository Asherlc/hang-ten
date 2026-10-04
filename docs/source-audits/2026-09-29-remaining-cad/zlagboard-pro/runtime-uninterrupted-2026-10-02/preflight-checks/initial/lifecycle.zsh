#!/bin/zsh
set -euo pipefail
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
scratch="$workspace_path/.context/$workspace_name/runtime-resume-2026-10-02/ios-uninterrupted"
rtk proxy mkdir -p "$scratch"
manifest="$workspace_path/.context/paseo-owned-simulators"
pending_manifest="$workspace_path/.context/paseo-pending-simulators"
derived="$scratch/DerivedData-$workspace_name"
result="$scratch/build-$workspace_name.xcresult"
test_result="$scratch/tests-$workspace_name.xcresult"
uuid=""
pending_registered=0
cleanup() {
  original_status=$?
  trap - EXIT INT TERM
  cleanup_status=0
  PASEO_WORKTREE_PATH="$workspace_path" rtk proxy "$workspace_path/scripts/paseo-resource-cleanup.sh" archive >> "$scratch/cleanup.log" 2>&1 || cleanup_status=$?
  if [[ -n "$uuid" && "$pending_registered" == 0 ]]; then
    rtk proxy python3 - "$uuid" "$workspace_name" >> "$scratch/cleanup.log" 2>&1 <<'FALLBACK'
import json,subprocess,sys
uid,owner=sys.argv[1:]
rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))['devices']
match=[d for ds in rows.values() for d in ds if d['udid'].upper()==uid.upper()]
if match:
 assert len(match)==1 and match[0]['name'].startswith('Hang Ten Paseo '+owner+' ')
 subprocess.run(['rtk','proxy','xcrun','simctl','delete',uid],check=True)
FALLBACK
    fallback_status=$?
    (( fallback_status == 0 )) || cleanup_status=$fallback_status
  fi
  rtk proxy rm -rf "$derived" "$result" "$test_result" || cleanup_status=$?
  rtk proxy python3 - "$uuid" "$derived" "$result" "$test_result" "$scratch/cleanup-verification.json" <<'VERIFY'
import json,subprocess,sys
from pathlib import Path
uid,derived,result,test_result,out=sys.argv[1:]
rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))['devices']
found=[d for ds in rows.values() for d in ds if d['udid'].upper()==uid.upper()]
record={'uuid':uid,'simulatorDeleted':not found,'derivedDataDeleted':not Path(derived).exists(),'resultBundleDeleted':not Path(result).exists(),'testResultBundleDeleted':not Path(test_result).exists()}
Path(out).write_text(json.dumps(record,indent=2)+'\n')
assert all(record[k] for k in ('simulatorDeleted','derivedDataDeleted','resultBundleDeleted','testResultBundleDeleted'))
VERIFY
  verify_status=$?
  (( verify_status == 0 )) || cleanup_status=$verify_status
  (( original_status == 0 )) || exit "$original_status"
  exit "$cleanup_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
uuid="$(rtk proxy xcrun simctl create "Hang Ten Paseo $workspace_name Review Pro iOS26.5 Uninterrupted20261002" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)"
[[ "$uuid" =~ '^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$' ]]
print -r -- "$uuid" >> "$pending_manifest"
pending_registered=1
print -r -- "$uuid" >> "$manifest"
print -r -- "$uuid" > "$scratch/simulator-uuid"
rtk proxy python3 - "$scratch/ownership.json" "$uuid" "$workspace_name" "$derived" "$result" "$test_result" <<'OWNER'
import json,sys
from pathlib import Path
out,uid,owner,derived,result,test_result=sys.argv[1:]
Path(out).write_text(json.dumps({'owner':owner,'simulator':uid,'derivedData':derived,'resultBundle':result,'testResultBundle':test_result,'lifetime':'temporary validation; cleanup trap removes exact owned resources'},indent=2)+'\n')
OWNER
rtk proxy perl -e 'alarm 40; exec @ARGV' xcrun simctl boot "$uuid" > "$scratch/boot-command.log" 2>&1
rtk proxy open -a Simulator --args -CurrentDeviceUDID "$uuid" > "$scratch/frontend-open.log" 2>&1
rtk proxy python3 "$workspace_path/.context/$workspace_name/runtime-resume-2026-10-02/prep/boot-uninterrupted.py" "$uuid" "$scratch"
print 'Responsive Home AX and screenshot candidate captured; waiting independent visual approval before build.'
while [[ ! -f "$scratch/home-visual-approved.json" ]]; do
  rtk proxy sleep 3
done
rtk proxy python3 "$workspace_path/.context/$workspace_name/runtime-resume-2026-10-02/prep/source-gate.py" "$scratch"
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
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "generic/platform=iOS Simulator" -derivedDataPath "$derived" -resultBundlePath "$result" build > "$scratch/build.log" 2>&1 || build_status=$?
print "$build_status" > "$scratch/build-exit-status.txt"
rtk proxy xcrun xcresulttool get build-results --path "$result" > "$scratch/build-results-summary.json" 2> "$scratch/build-results-summary-stderr.txt" || true
(( build_status == 0 )) || exit "$build_status"
rtk proxy python3 "$workspace_path/.context/$workspace_name/runtime-resume-2026-10-02/prep/build-parity.py"
rtk proxy perl -e 'alarm 40; exec @ARGV' xcrun simctl install "$uuid" "$derived/Build/Products/Debug-iphonesimulator/HangTen.app" > "$scratch/install.log" 2>&1
rtk proxy perl -e 'alarm 20; exec @ARGV' xcrun simctl get_app_container "$uuid" com.hangten.training app > "$scratch/installed-container.txt"
print -r -- "$uuid" > "$scratch/simulator-ready"
print "Build ready: $uuid"
while [[ ! -f "$scratch/cleanup-requested" ]]; do
  rtk proxy sleep 3
done
