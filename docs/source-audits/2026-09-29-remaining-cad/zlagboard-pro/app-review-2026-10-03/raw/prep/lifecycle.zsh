#!/bin/zsh
set -euo pipefail
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
root="$workspace_path/.context/$workspace_name/pro-app-review-2026-10-03"
prep="$root/prep"
scratch="$root/ios"
[[ ! -e "$scratch" ]]
rtk proxy mkdir -p "$scratch"
simulator_name="Hang Ten Paseo $workspace_name ProContacts20261003 $$"
uuid=""
cleanup() {
 original_status=$?
 trap - EXIT INT TERM
 set +e
 rtk proxy python3 "$prep/cleanup.py" "$scratch" "$simulator_name" "$uuid"
 cleanup_status=$?
 (( original_status == 0 )) || exit "$original_status"
 exit "$cleanup_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rtk proxy python3 "$prep/register-controller.py" "$scratch" "$$" "$simulator_name"
uuid="$(rtk proxy xcrun simctl create "$simulator_name" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)"
[[ "$uuid" =~ '^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$' ]]
rtk proxy python3 "$prep/register-controller.py" "$scratch" "$$" "$simulator_name" "$uuid"
rtk proxy xcrun simctl boot "$uuid" > "$scratch/boot.stdout" 2> "$scratch/boot.stderr"
rtk proxy perl -e 'alarm 120; exec @ARGV' xcrun simctl bootstatus "$uuid" -b > "$scratch/bootstatus.stdout" 2> "$scratch/bootstatus.stderr"
print 'Owned post-Main render device ready.'
while [[ ! -f "$scratch/cleanup-requested" ]]; do
 rtk proxy sleep 3
done
