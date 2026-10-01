#!/bin/bash
set -eu
cd "${BASH_SOURCE[0]%/*}/../.."
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
owner="${workspace_path##*/}"
resource_dir="$PWD/.context/$owner-affine-geometry"
python="${HANGTEN_NATIVE_SCREEN_PYTHON:-python3}"
for path in "$PWD/.context" "$resource_dir" "$resource_dir/resources-driver.log"; do
  if [ -L "$path" ]; then echo "Owned output must not be a symlink: $path" >&2; exit 2; fi
done
mkdir -p "$resource_dir"
child_pid=
launching=1
pending_status=
cleanup() {
  result=$?
  trap - EXIT INT TERM
  if [ -n "$child_pid" ]; then
    # Signal only a still-running job owned by this shell, never a stale PID
    # that a completed wait has already reaped.
    for job_pid in $(jobs -pr); do
      if [ "$job_pid" = "$child_pid" ]; then kill -TERM "$child_pid" 2>/dev/null || true; fi
    done
    wait "$child_pid" 2>/dev/null || true
    printf '%s %s deleted-and-verified\n' "$owner" "$child_pid" >> "$resource_dir/resources-driver.log"
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'if [ "$launching" = 1 ]; then pending_status=130; else exit 130; fi' INT
trap 'if [ "$launching" = 1 ]; then pending_status=143; else exit 143; fi' TERM
HANGTEN_AFFINE_GEOMETRY_OWNER="$owner" PYTHONPYCACHEPREFIX="$resource_dir/pycache" \
  "$python" Tools/HangboardRopePrototype/run_affine_geometry_screen.py "$@" &
child_pid=$!
printf '%s %s owned %s\n' "$owner" "$child_pid" "$owner-affine-geometry-driver" >> "$resource_dir/resources-driver.log"
launching=0
if [ -n "$pending_status" ]; then exit "$pending_status"; fi
status=0
wait "$child_pid" || status=$?
printf '%s %s deleted-and-verified\n' "$owner" "$child_pid" >> "$resource_dir/resources-driver.log"
child_pid=
exit "$status"
