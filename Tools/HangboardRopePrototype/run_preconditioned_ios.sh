#!/bin/zsh
set -euo pipefail
repo="${PASEO_WORKTREE_PATH:-$PWD}"
label="${1:?Pass a fresh staged experiment label}"
[[ "${repo:t}" == strong-owl-live-physics ]] || exit 1
[[ "$label" != *[^a-z0-9-]* ]] || exit 1
root="$repo/.context/strong-owl-live-physics-preconditioned-ios-$label"
workspace_path="$root/strong-owl-live-physics"
[[ -f "$root/stage-ownership.json" ]] || exit 1
cleanup_on_exit() {
  original_status=$?
  trap - EXIT INT TERM
  cleanup_status=0
  rtk proxy env PASEO_WORKTREE_PATH="$workspace_path" "$repo/scripts/paseo-resource-cleanup.sh" archive || cleanup_status=$?
  rtk proxy rm -rf "$workspace_path/.context/DerivedData" "$workspace_path/.context/workout-raw.png" "$workspace_path/.context/workout-landscape.png" || cleanup_status=$?
  rtk proxy python3 "$repo/Tools/HangboardRopePrototype/verify_preconditioned_ios_cleanup.py" "$root" || cleanup_status=$?
  if (( original_status != 0 )); then
    exit "$original_status"
  fi
  exit "$cleanup_status"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rtk proxy env PYTHONDONTWRITEBYTECODE=1 HANGTEN_PRECONDITIONED_IOS_EXIT_TRAP=strong-owl-live-physics python3 "$repo/Tools/HangboardRopePrototype/run_preconditioned_ios.py" record --label "$label"
