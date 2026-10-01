#!/bin/bash
set -eu
cd "${BASH_SOURCE[0]%/*}/../.."
task_workspace="${PASEO_WORKTREE_PATH:-$PWD}"
task_owner="${task_workspace##*/}"
task_root="$PWD/.context/$task_owner-channel-geometry"
task_python="${HANGTEN_CHANNEL_GEOMETRY_PYTHON:-python3}"
for task_path in "$PWD/.context" "$task_root" "$task_root/resources-driver.log" "$task_root/pycache"; do
  if [ -L "$task_path" ]; then echo 'Owned output cannot be a symlink' >&2; exit 2; fi
done
mkdir -p "$task_root"
task_child=
task_launching=1
task_pending=
cleanup() {
  task_result=$?
  trap - EXIT INT TERM
  if [ -n "$task_child" ]; then
    for task_job in $(jobs -pr); do
      if [ "$task_job" = "$task_child" ]; then kill -TERM "$task_child" 2>/dev/null || true; fi
    done
    wait "$task_child" 2>/dev/null || true
    printf '%s %s deleted-and-verified\n' "$task_owner" "$task_child" >> "$task_root/resources-driver.log"
  fi
  exit "$task_result"
}
trap cleanup EXIT
trap 'if [ "$task_launching" = 1 ]; then task_pending=130; else exit 130; fi' INT
trap 'if [ "$task_launching" = 1 ]; then task_pending=143; else exit 143; fi' TERM
HANGTEN_CHANNEL_GEOMETRY_OWNER="$task_owner" PYTHONPYCACHEPREFIX="$task_root/pycache" \
  "$task_python" Tools/HangboardRopePrototype/run_channel_geometry_screen.py "$@" &
task_child=$!
printf '%s %s owned %s\n' "$task_owner" "$task_child" "$task_owner-channel-geometry-driver" >> "$task_root/resources-driver.log"
task_launching=0
if [ -n "$task_pending" ]; then exit "$task_pending"; fi
task_status=0
wait "$task_child" || task_status=$?
printf '%s %s deleted-and-verified\n' "$task_owner" "$task_child" >> "$task_root/resources-driver.log"
task_child=
exit "$task_status"
