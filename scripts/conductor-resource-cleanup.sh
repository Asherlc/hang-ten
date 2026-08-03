#!/bin/zsh
set -euo pipefail

usage() {
  print -- "Usage: ${0:t} archive | prune [--delete]"
}

is_uuid() {
  [[ "$1" =~ '^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$' ]]
}

is_review_device_name() {
  [[ "$1" =~ '^(HangTen|Hang Ten)([[:space:]]|$)' ]] || return 1
  [[ "$1" =~ '(^|[[:space:]])(Task[0-9]*|Validation|Scratch)($|[[:space:]])' ]] && return 1
  [[ "$1" =~ '(^|[[:space:]])Review[0-9]*($|[[:space:]])' ]]
}

device_record_for_uuid() {
  local devices=$1 uuid=$2

  print -r -- "$devices" | awk -v uuid="$uuid" '
    {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      state = line
      if (state !~ / \([^()]*\)$/) next
      sub(/^.* \(/, "", state)
      sub(/\)$/, "", state)

      fields = line
      sub(/ \([^()]*\)$/, "", fields)
      if (fields !~ / \([^()]*\)$/) next
      actual_uuid = fields
      sub(/^.* \(/, "", actual_uuid)
      sub(/\)$/, "", actual_uuid)
      if (actual_uuid != uuid) next

      name = fields
      sub(/ \([^()]*\)$/, "", name)
      print name "\t" state
      exit
    }
  '
}

run_archive_cleanup() {
  local workspace_path=${CONDUCTOR_WORKSPACE_PATH:-}
  local workspace_name=${CONDUCTOR_WORKSPACE_NAME:-}
  local owned_manifest pending_manifest manifest devices uuid record device_name device_state workspace_prefix
  local manifests=()
  local result_status=0
  typeset -A seen

  if [[ -z "$workspace_path" || -z "$workspace_name" ]]; then
    print -u2 -- 'archive requires CONDUCTOR_WORKSPACE_PATH and CONDUCTOR_WORKSPACE_NAME'
    return 1
  fi

  owned_manifest="$workspace_path/.context/conductor-owned-simulators"
  pending_manifest="$workspace_path/.context/conductor-pending-simulators"
  workspace_prefix="Hang Ten Conductor ${workspace_name} "

  [[ -f "$owned_manifest" ]] && manifests+=("$owned_manifest")
  [[ -f "$pending_manifest" ]] && manifests+=("$pending_manifest")
  [[ "${#manifests[@]}" -gt 0 ]] || return 0

  devices=$(xcrun simctl list devices)

  for manifest in "${manifests[@]}"; do
    while IFS= read -r uuid || [[ -n "$uuid" ]]; do
      if ! is_uuid "$uuid"; then
        print -u2 -- "Skipping malformed simulator UUID: $uuid"
        result_status=1
        continue
      fi

      [[ -n "${seen[$uuid]:-}" ]] && continue
      seen[$uuid]=1

      record=$(device_record_for_uuid "$devices" "$uuid")
      [[ -n "$record" ]] || continue
      device_name=${record%%$'\t'*}
      device_state=${record#*$'\t'}

      if [[ "$device_name" != "$workspace_prefix"* ]]; then
        print -u2 -- "Skipping simulator not owned by workspace $workspace_name: $uuid"
        result_status=1
        continue
      fi

      if [[ "$device_state" == Booted ]] && ! xcrun simctl shutdown "$uuid"; then
        print -u2 -- "Failed to shut down simulator: $uuid"
        result_status=1
        continue
      fi

      if ! xcrun simctl delete "$uuid"; then
        print -u2 -- "Failed to delete simulator: $uuid"
        result_status=1
      fi
    done < "$manifest"
  done

  return "$result_status"
}

run_prune() {
  local option=${1:-}
  local devices current_devices record device_name current_device_name device_state uuid
  local result_status=0

  if [[ -n "$option" && "$option" != --delete ]]; then
    usage >&2
    return 2
  fi

  devices=$(xcrun simctl list devices)
  while IFS=$'\t' read -r device_name uuid device_state; do
    [[ "$device_state" == Shutdown ]] || continue
    is_review_device_name "$device_name" || continue

    if [[ "$option" == --delete ]]; then
      current_devices=$(xcrun simctl list devices "$uuid")
      record=$(device_record_for_uuid "$current_devices" "$uuid")
      if [[ -z "$record" ]]; then
        print -u2 -- "Skipping simulator no longer available: $device_name ($uuid)"
        result_status=1
        continue
      fi
      current_device_name=${record%%$'\t'*}
      device_state=${record#*$'\t'}
      if ! is_review_device_name "$current_device_name"; then
        print -u2 -- "Skipping simulator no longer has a review name: $current_device_name ($uuid)"
        result_status=1
        continue
      fi
      if [[ "$device_state" != Shutdown ]]; then
        print -u2 -- "Skipping simulator no longer Shutdown: $device_name ($uuid) is $device_state"
        result_status=1
        continue
      fi
      if ! xcrun simctl delete "$uuid"; then
        print -u2 -- "Failed to delete simulator: $uuid"
        result_status=1
      fi
    else
      print -- "Would delete $device_name ($uuid)"
    fi
  done < <(
    print -r -- "$devices" | awk '
      {
        line = $0
        sub(/^[[:space:]]+/, "", line)
        sub(/[[:space:]]+$/, "", line)
        if (line !~ / \([^)]*\) \([^)]*\)$/) next

        name = line
        sub(/ \([^)]*\) \([^)]*\)$/, "", name)
        uuid = line
        sub(/ \([^)]*\)$/, "", uuid)
        sub(/^.* \(/, "", uuid)
        sub(/\)$/, "", uuid)
        state = line
        sub(/^.* \(/, "", state)
        sub(/\)$/, "", state)
        print name "\t" uuid "\t" state
      }
    '
  )

  return "$result_status"
}

case "${1:-}" in
  archive)
    [[ "$#" -eq 1 ]] || { usage >&2; exit 2; }
    run_archive_cleanup
    ;;
  prune)
    [[ "$#" -eq 1 || ( "$#" -eq 2 && "$2" == --delete ) ]] || { usage >&2; exit 2; }
    run_prune "${2:-}"
    ;;
  *) usage >&2; exit 2 ;;
esac
