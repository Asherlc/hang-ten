#!/bin/zsh
set -euo pipefail
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
scratch="$workspace_path/.context/$workspace_name"
review_scratch="$scratch/nature-stone-review9/granite-seat-correction/ios"
manifest="$workspace_path/.context/paseo-owned-simulators"
pending_manifest="$workspace_path/.context/paseo-pending-simulators"
simulator_uuid=""
pending_registered=0
rtk proxy python3 "$review_scratch/preflight.py"
[[ ! -e "$workspace_path/.context/DerivedData" ]] || exit 1
[[ ! -s "$manifest" && ! -s "$pending_manifest" ]] || exit 1
uuid_regex='^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$'
cleanup_on_exit() {
  original_status=$?
  trap - EXIT INT TERM
  cleanup_status=0
  rtk proxy env PASEO_WORKTREE_PATH="$workspace_path" "$workspace_path/scripts/paseo-resource-cleanup.sh" archive || cleanup_status=$?
  if [[ -n "$simulator_uuid" ]]; then
    rtk proxy xcrun simctl list devices --json > "$review_scratch/devices-after-cleanup.json"
    rtk proxy python3 - "$simulator_uuid" "$workspace_name" "$review_scratch/devices-after-cleanup.json" "$pending_registered" <<'PY' || cleanup_status=$?
import json,subprocess,sys
uid,owner,path,registered=sys.argv[1:]
devices=[d for group in json.load(open(path))['devices'].values() for d in group if d['udid']==uid]
if devices:
    assert registered == "0", "registered simulator still exists after archive; retain manifests for retry"
    assert len(devices)==1 and devices[0]['name'].startswith('Hang Ten Paseo '+owner+' '), 'ownership check failed'
    subprocess.run(['rtk','proxy','xcrun','simctl','shutdown',uid],capture_output=True)
    subprocess.run(['rtk','proxy','xcrun','simctl','delete',uid],check=True)
    remaining=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))
    assert not any(d['udid']==uid for group in remaining['devices'].values() for d in group), 'simulator deletion failed'
PY
  fi
  rtk proxy rm -rf "$workspace_path/.context/DerivedData" "$workspace_path/.context/workout-raw.png" "$workspace_path/.context/workout-landscape.png" "$review_scratch/placid-badger-stone-granite-seat-tests.xcresult" "$review_scratch/tmp" || cleanup_status=$?
  rtk proxy python3 - "$workspace_path" "$review_scratch" "$simulator_uuid" "$cleanup_status" <<'PY' || cleanup_status=$?
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);p=Path(sys.argv[2]);status=int(sys.argv[4])
assert not(p/'tmp').exists()
assert not(root/'.context/DerivedData').exists()
assert not(p/'placid-badger-stone-granite-seat-tests.xcresult').exists()
for manifest in ('paseo-owned-simulators','paseo-pending-simulators'):
    q=root/'.context'/manifest
    assert not q.exists() or sys.argv[3] not in q.read_text().splitlines()
(p/'ios-cleanup.json').write_text(json.dumps({'owner':root.name,'simulator':sys.argv[3],'cleanupStatus':status,'derivedDataRemoved':not(root/'.context/DerivedData').exists(),'xcresultRemoved':not(p/'placid-badger-stone-granite-seat-tests.xcresult').exists(),'ownedTmpRemoved':not(p/'tmp').exists(),'pendingAndOwnedRecordsConsumed':True},indent=2)+'\n')
PY
  (( original_status != 0 )) && exit "$original_status"
  exit "$cleanup_status"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
simulator_uuid="$(rtk proxy xcrun simctl create "Hang Ten Paseo $workspace_name Review Granite Seat" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)"
[[ "$simulator_uuid" =~ $uuid_regex ]] || exit 1
print -r -- "$simulator_uuid" >> "$pending_manifest"
pending_registered=1
print -r -- "$simulator_uuid" >> "$manifest"
rtk proxy python3 - "$review_scratch/ownership.json" "$simulator_uuid" "$workspace_name" <<'PYOWN'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'owner':sys.argv[3],'simulatorUUID':sys.argv[2],'simulatorName':'Hang Ten Paseo '+sys.argv[3]+' Review Granite Seat','pendingAndOwnedRegistered':True,'cleanupTrap':'ios-session.zsh'},indent=2)+'\n')
PYOWN
rtk proxy xcrun simctl boot "$simulator_uuid"
simulator_ready=0
for attempt in {1..40}; do
  if rtk proxy perl -e 'alarm 4; exec @ARGV' xcrun simctl spawn "$simulator_uuid" launchctl print system >/dev/null 2>&1; then
    simulator_ready=1
    break
  fi
  rtk proxy sleep 3
done
(( simulator_ready == 1 )) || exit 1
print -r -- "$simulator_uuid" > "$review_scratch/simulator-ready"
for attempt in {1..720}; do
  [[ -f "$review_scratch/finish-ios-session" ]] && exit 0
  rtk proxy sleep 5
done
exit 124
