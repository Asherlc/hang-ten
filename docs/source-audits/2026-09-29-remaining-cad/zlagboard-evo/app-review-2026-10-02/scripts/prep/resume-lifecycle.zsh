#!/bin/zsh
set -euo pipefail
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
scratch="$workspace_path/.context/$workspace_name/zlagboard-evo/ios-resume-2026-10-02"
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
rtk proxy python3 - "$workspace_path/.context/$workspace_name/zlagboard-evo/final-ready.json" <<'GATE'
import hashlib,json,sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
assert record.get('authorizedByParent') is True
for name,expected in record['packageSHA256'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
GATE
uuid="$(rtk proxy xcrun simctl create "Hang Ten Paseo $workspace_name Review Zlagboard Evo Resume20261002" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)"
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
rtk proxy xcrun simctl boot "$uuid"
ready=0
for attempt in {1..40}; do
  if rtk proxy perl -e 'alarm 4; exec @ARGV' xcrun simctl spawn "$uuid" launchctl print system > "$scratch/launch-services.log" 2>&1; then
    ready=1
    break
  fi
  rtk proxy sleep 3
done
(( ready == 1 ))
rtk proxy python3 "$workspace_path/.context/$workspace_name/zlagboard-evo/prep/resume-boot.py" "$uuid" "$scratch"
rtk proxy python3 - "$scratch/source-package-sha256-before-build.json" <<'HASH'
import hashlib,json,sys
from pathlib import Path
package=Path('Hangboards/zlagboard-evo')
paths=[package/'zlagboard-evo.FCStd',package/'assets/primary.usdz',package/'assets/primary.model.json']
assert paths[0].read_bytes()[:2]==b'PK','FCStd must be real archive, not LFS pointer'
Path(sys.argv[1]).write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
HASH
rtk proxy python3 Tools/HangboardCAD/board_manifest.py --package zlagboard-evo --output "$scratch/generated-board-at-build.json"
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$uuid" -derivedDataPath "$derived" -resultBundlePath "$result" build > "$scratch/build.log" 2>&1
test_status=0
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$uuid" -derivedDataPath "$derived" -resultBundlePath "$test_result" -parallel-testing-enabled NO -only-testing:HangTenTests/BoardPackageStoreTests/testModelBoardFinishDecodesWithoutPerMeshSelections -only-testing:HangTenTests/BoardModelRealityTests/testWoodFinishHighlightsAndRestoresEveryContactWithoutChangingPicking test > "$scratch/tests.log" 2>&1 || test_status=$?
print "$test_status" > "$scratch/tests-exit-status.txt"
rtk proxy xcrun xcresulttool get test-results summary --path "$test_result" > "$scratch/test-results-summary.json" 2> "$scratch/test-results-summary-stderr.txt" || true
if (( test_status != 0 )); then
  print "Targeted tests failed; raw status/summary retained. Keeping exact owned simulator for visual diagnosis."
fi
rtk proxy xcrun simctl install "$uuid" "$derived/Build/Products/Debug-iphonesimulator/HangTen.app" > "$scratch/install.log" 2>&1
rtk proxy xcrun simctl get_app_container "$uuid" com.hangten.training app > "$scratch/installed-container.txt"
print -r -- "$uuid" > "$scratch/simulator-ready"
print "Build ready: $uuid"
while [[ ! -f "$scratch/cleanup-requested" ]]; do
  rtk proxy sleep 3
done
