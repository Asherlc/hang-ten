#!/bin/zsh
set -euo pipefail
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
scratch="$workspace_path/.context/$workspace_name"
review_scratch="$scratch/metolius-simulator-3d-plastic-review/ios"
manifest="$workspace_path/.context/paseo-owned-simulators"
pending_manifest="$workspace_path/.context/paseo-pending-simulators"
simulator_uuid=""
uuid_regex='^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$'
cleanup_on_exit() {
  original_status=$?
  trap - EXIT INT TERM
  cleanup_status=0
  PASEO_WORKTREE_PATH="$workspace_path" rtk proxy "$workspace_path/scripts/paseo-resource-cleanup.sh" archive || cleanup_status=$?
  if [[ -n "$simulator_uuid" ]]; then
    rtk proxy xcrun simctl list devices --json > "$review_scratch/devices-after-cleanup.json"
    rtk proxy python3 - "$simulator_uuid" "$workspace_name" "$review_scratch/devices-after-cleanup.json" <<'PY' || cleanup_status=$?
import json,subprocess,sys
uid,owner,path=sys.argv[1:]
devices=[d for group in json.load(open(path))['devices'].values() for d in group if d['udid']==uid]
if devices:
    assert len(devices)==1 and devices[0]['name'].startswith('Hang Ten Paseo '+owner+' '), 'ownership check failed'
    subprocess.run(['rtk','proxy','xcrun','simctl','shutdown',uid],capture_output=True)
    subprocess.run(['rtk','proxy','xcrun','simctl','delete',uid],check=True)
    remaining=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))
    assert not any(d['udid']==uid for group in remaining['devices'].values() for d in group), 'simulator deletion failed'
PY
  fi
  rtk proxy rm -rf "$workspace_path/.context/DerivedData" "$workspace_path/.context/workout-raw.png" "$workspace_path/.context/workout-landscape.png" "$review_scratch/placid-badger-simulator-plastic-tests.xcresult"
  rtk proxy python3 - "$review_scratch" "$simulator_uuid" "$cleanup_status" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);status=int(sys.argv[3]);(p/'ios-cleanup.json').write_text(json.dumps({'simulator':sys.argv[2],'cleanupStatus':status,'derivedDataRemoved':not(Path(sys.argv[1]).parents[2]/'DerivedData').exists(),'xcresultRemoved':not(p/'placid-badger-simulator-plastic-tests.xcresult').exists()},indent=2)+'\n')
PY
  (( original_status != 0 )) && exit "$original_status"
  exit "$cleanup_status"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
simulator_uuid="$(rtk proxy xcrun simctl create "Hang Ten Paseo $workspace_name Simulator Opus Plastic Review" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)"
[[ "$simulator_uuid" =~ $uuid_regex ]] || exit 1
print -r -- "$simulator_uuid" >> "$pending_manifest"
print -r -- "$simulator_uuid" >> "$manifest"
print -r -- "$simulator_uuid" > "$scratch/simulator-uuid"
rtk proxy python3 - "$scratch/ownership.json" "$simulator_uuid" "$workspace_name" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);d=json.loads(p.read_text());d['externalResources'].append({'kind':'iOSSimulator','uuid':sys.argv[2],'name':'Hang Ten Paseo '+sys.argv[3]+' Simulator Opus Plastic Review','cleanupTrap':'metolius-simulator-3d-plastic-review/ios/ios-session.zsh'});p.write_text(json.dumps(d,indent=2)+'\n')
PY
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
while [[ ! -f "$review_scratch/finish-ios-session" ]]; do
  rtk proxy sleep 5
done
