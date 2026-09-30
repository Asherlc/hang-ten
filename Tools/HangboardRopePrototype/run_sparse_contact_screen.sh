#!/bin/bash
# Own only this finite screen process; never execute copied ownership scripts.
set -eu
cd "${BASH_SOURCE[0]%/*}/../.."
workspace_path="${PASEO_WORKTREE_PATH:-$PWD}"
owner="${workspace_path##*/}"
resource_dir="$PWD/.context/$owner-sparse-contact"
python="$resource_dir/venv/bin/python"
[ -x "$python" ] || { echo "Missing screen environment: $python" >&2; exit 2; }
mkdir -p "$resource_dir"
child_pid=
cleanup() {
  result=$?
  trap - EXIT INT TERM
  if [ -n "$child_pid" ]; then
    if kill -0 "$child_pid" 2>/dev/null; then
      kill -TERM "$child_pid" 2>/dev/null || true
    fi
    wait "$child_pid" 2>/dev/null || true
    if kill -0 "$child_pid" 2>/dev/null; then
      echo "Owned screen process still exists: $child_pid" >&2
      exit 99
    fi
    printf '%s %s deleted-and-verified\n' "$owner" "$child_pid" >> "$resource_dir/resources.log"
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
PYTHONPYCACHEPREFIX="$resource_dir/pycache" "$python" Tools/HangboardRopePrototype/sparse_contact_screen.py "$@" &
child_pid=$!
printf '%s %s owned %s\n' "$owner" "$child_pid" "$python" >> "$resource_dir/resources.log"
wait "$child_pid"
