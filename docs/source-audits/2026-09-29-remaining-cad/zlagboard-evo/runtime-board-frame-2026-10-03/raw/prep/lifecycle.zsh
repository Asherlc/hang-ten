#!/bin/zsh
set -euo pipefail
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
workspace_name="${workspace_path:t}"
root="$workspace_path/.context/$workspace_name/board-frame-fix-2026-10-03"
prep="$root/prep"
scratch="$root/ios"
[[ ! -e "$scratch" ]]
rtk proxy mkdir -p "$scratch"
simulator_name="Hang Ten Paseo $workspace_name BoardFrame20261003 $$"
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
uuid="$(rtk proxy python3 "$prep/bounded-command.py" 30 "$scratch/create-command.json" xcrun simctl create "$simulator_name" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro com.apple.CoreSimulator.SimRuntime.iOS-26-5)"
[[ "$uuid" =~ '^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$' ]]
rtk proxy python3 "$prep/register-controller.py" "$scratch" "$$" "$simulator_name" "$uuid"
boot_deadline="$(rtk proxy python3 -c 'import time; print(time.monotonic()+900)')"
rtk proxy python3 "$prep/bounded-command.py" 40 "$scratch/boot-command.json" xcrun simctl boot "$uuid"
rtk proxy python3 "$prep/bounded-command.py" 15 "$scratch/frontend-command.json" open -a Simulator --args -CurrentDeviceUDID "$uuid"
rtk proxy python3 "$prep/boot-uninterrupted.py" "$uuid" "$scratch" "$boot_deadline"
print 'Home candidate retained. Root must visually approve before any build or install.'
while [[ ! -f "$scratch/cleanup-requested" ]]; do
  rtk proxy sleep 3
done
