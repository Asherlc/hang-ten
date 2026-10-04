#!/bin/zsh
set -euo pipefail
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
scratch="$workspace_path/.context/$workspace_name/pr-readiness-repair-2026-10-02/ios-diagnosis"
rtk proxy mkdir -p "$scratch"
manifest="$workspace_path/.context/paseo-owned-simulators"
pending_manifest="$workspace_path/.context/paseo-pending-simulators"
derived="$scratch/DerivedData-$workspace_name"
result="$scratch/build-$workspace_name.xcresult"
test_result="$scratch/tests-$workspace_name.xcresult"
simulator_name="Hang Ten Paseo $workspace_name Review Pro MigrationDiagnosis20261002 $$"
uuid=""
pending_registered=0
bounded="$workspace_path/.context/$workspace_name/pr-readiness-repair-2026-10-02/prep/bounded-command.py"
cleanup() {
  original_status=$?
  trap - EXIT INT TERM
  set +e
  cleanup_status=0
  create_recovery_error=0
  if [[ -z "$uuid" && -f "$scratch/create-command.json" ]]; then
    uuid="$(rtk proxy python3 - "$simulator_name" <<'RECOVER'
import json,subprocess,sys
rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json'],timeout=20))['devices']
match=[d for ds in rows.values() for d in ds if d['name']==sys.argv[1]]
assert len(match)<=1,'Exact unique creation name unexpectedly matched multiple devices'
if match:print(match[0]['udid'])
RECOVER
)"
    create_recovery_error=$?
    (( create_recovery_error == 0 )) || cleanup_status=$create_recovery_error
    if [[ -n "$uuid" ]]; then
      print -r -- "$uuid" >> "$pending_manifest"
      pending_registered=1
      print -r -- "$uuid" >> "$manifest"
      print -r -- "$uuid" > "$scratch/recovered-create-uuid"
    fi
  fi
  PASEO_WORKTREE_PATH="$workspace_path" rtk proxy python3 "$bounded" 120 "$scratch/archive-cleanup-command.json" "$workspace_path/scripts/paseo-resource-cleanup.sh" archive >> "$scratch/cleanup.log" 2>&1 || cleanup_status=$?
  if [[ -n "$uuid" && "$pending_registered" == 0 ]]; then
    rtk proxy python3 - "$uuid" "$workspace_name" >> "$scratch/cleanup.log" 2>&1 <<'FALLBACK'
import json,subprocess,sys
uid,owner=sys.argv[1:]
rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json'],timeout=20))['devices']
match=[d for ds in rows.values() for d in ds if d['udid'].upper()==uid.upper()]
if match:
 assert len(match)==1 and match[0]['name'].startswith('Hang Ten Paseo '+owner+' ')
 subprocess.run(['rtk','proxy','xcrun','simctl','delete',uid],check=True,timeout=30)
FALLBACK
    fallback_status=$?
    (( fallback_status == 0 )) || cleanup_status=$fallback_status
  fi
  rtk proxy python3 "$bounded" 120 "$scratch/artifact-cleanup-command.json" rm -rf "$derived" "$result" "$test_result" || cleanup_status=$?
  rtk proxy python3 - "$uuid" "$derived" "$result" "$test_result" "$scratch/cleanup-verification.json" "$create_recovery_error" <<'VERIFY'
import json,subprocess,sys
from pathlib import Path
uid,derived,result,test_result,out,recovery_error=sys.argv[1:]
query_error=None
try:
 rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json'],timeout=20))['devices']
 found=[d for ds in rows.values() for d in ds if d['udid'].upper()==uid.upper()]
except Exception as exc:
 query_error=repr(exc);found=None
record={'uuid':uid,'simulatorQueryError':query_error,'createRecoveryError':int(recovery_error),'simulatorDeleted':int(recovery_error)==0 and query_error is None and not found,'derivedDataDeleted':not Path(derived).exists(),'resultBundleDeleted':not Path(result).exists(),'testResultBundleDeleted':not Path(test_result).exists()}
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
uuid="$(rtk proxy python3 "$bounded" 30 "$scratch/create-command.json" xcrun simctl create "$simulator_name" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)"
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
rtk proxy python3 "$bounded" 40 "$scratch/boot-command.json" xcrun simctl boot "$uuid" > "$scratch/boot-command.log" 2>&1
rtk proxy python3 "$bounded" 15 "$scratch/frontend-command.json" open -a Simulator --args -CurrentDeviceUDID "$uuid" > "$scratch/frontend-open.log" 2>&1
print -r -- "$uuid" > "$scratch/diagnostic-device-created"
print "Exact owned diagnostic device created: $uuid; no Home or app readiness implied."
while [[ ! -f "$scratch/cleanup-requested" ]]; do
  rtk proxy sleep 3
done
