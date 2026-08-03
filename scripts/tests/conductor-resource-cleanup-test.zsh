#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h:h}
cleanup_script="$repo_root/scripts/conductor-resource-cleanup.sh"
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

fake_bin="$temp_dir/bin"
call_log="$temp_dir/xcrun-calls"
all_call_log="$temp_dir/xcrun-all-calls"
mkdir -p "$fake_bin"

cat > "$fake_bin/xcrun" <<'EOF'
#!/bin/zsh
set -euo pipefail

if [[ "$1" != simctl ]]; then
  print -r -- "$*" >> "$XCRUN_ALL_CALL_LOG"
  print -u2 -- "unexpected xcrun invocation: $*"
  exit 64
fi

print -r -- "$*" >> "$XCRUN_ALL_CALL_LOG"

case "$2" in
  list)
    [[ "${3:-}" == devices ]] || exit 64
    if [[ -n "${4:-}" && -n "${PRUNE_TRANSITION_UUID:-}" && "$4" == "$PRUNE_TRANSITION_UUID" ]]; then
      print -- '== Devices =='
      print -- '-- iOS 26.5 --'
      print -r -- "    Hang Ten Conductor alpha Review Transition ($PRUNE_TRANSITION_UUID) (Booted)"
      exit 0
    fi
    if [[ -n "${4:-}" && -n "${PRUNE_RENAME_UUID:-}" && "$4" == "$PRUNE_RENAME_UUID" ]]; then
      print -- '== Devices =='
      print -- '-- iOS 26.5 --'
      print -r -- "    iPhone 17 Pro ($PRUNE_RENAME_UUID) (Shutdown)"
      exit 0
    fi
    if [[ -n "${4:-}" && -n "${PRUNE_NAME_UUID:-}" && "$4" == "$PRUNE_NAME_UUID" ]]; then
      print -- '== Devices =='
      print -- '-- iOS 26.5 --'
      print -r -- "    Hang Ten Conductor alpha Review named $PRUNE_NAME_UUID (77777777-7777-7777-7777-777777777777) (Shutdown)"
      exit 0
    fi
    cat <<'DEVICES'
== Devices ==
-- iOS 26.5 --
    Hang Ten Conductor alpha Review (11111111-1111-1111-1111-111111111111) (Shutdown)
    Hang Ten Conductor alpha Review Lowercase (ABABABAB-ABAB-ABAB-ABAB-ABABABABABAB) (Shutdown)
    Hang Ten Conductor alpha Lowercase Device (cdcdcdcd-cdcd-cdcd-cdcd-cdcdcdcdcdcd) (Shutdown)
    Hang Ten Conductor alpha Review Booted (74747474-7474-7474-7474-747474747474) (Booted)
    Hang Ten Conductor alpha Running (22222222-2222-2222-2222-222222222222) (Booted)
    Hang Ten Conductor beta Review (33333333-3333-3333-3333-333333333333) (Shutdown)
    iPhone 17 Pro (44444444-4444-4444-4444-444444444444) (Shutdown)
    Hang Ten Conductor alphabet Review (55555555-5555-5555-5555-555555555555) (Shutdown)
    Hang Ten Conductor alpha Scratch (66666666-6666-6666-6666-666666666666) (Shutdown)
    iPhone Review (abababab-abab-abab-abab-abababababab) (Shutdown)
    Hang Ten Conductor alpha Review 263 (88888888-8888-8888-8888-888888888888) (Shutdown)
    Hang Ten Conductor alpha Review 20260803 (99999999-9999-9999-9999-999999999999) (Shutdown)
    Hang Ten Conductor alpha Review Transition (12121212-1212-1212-1212-121212121212) (Shutdown)
    HangTen bariloche Task5 Review1 20260802 (10101010-1010-1010-1010-101010101010) (Shutdown)
    Hang Ten Worcester Review ff8fa93 (20202020-2020-2020-2020-202020202020) (Shutdown)
    Hang Ten Worcester Validation (30303030-3030-3030-3030-303030303030) (Shutdown)
    Hang Ten Worcester Preview (40404040-4040-4040-4040-404040404040) (Shutdown)
    Hang Ten Worcester Reviewing (50505050-5050-5050-5050-505050505050) (Shutdown)
    HangTen bariloche Task5 (60606060-6060-6060-6060-606060606060) (Shutdown)
    HangTen bariloche Task Review (73737373-7373-7373-7373-737373737373) (Shutdown)
    Hang Ten Worcester Validation Review (71717171-7171-7171-7171-717171717171) (Shutdown)
    Hang Ten Worcester Scratch Review (72727272-7272-7272-7272-727272727272) (Shutdown)
    Hang Ten Shared Review (73737370-7373-7373-7373-737373737370) (Shutdown)
    Hang Ten Team Task-5 Review (73737371-7373-7373-7373-737373737371) (Shutdown)
    Hang Ten Team Validation2 Review (73737372-7373-7373-7373-737373737372) (Shutdown)
    HangTennis Review (31313131-3131-3131-3131-313131313131) (Shutdown)
    Hang Tenacious Review (32323232-3232-3232-3232-323232323232) (Shutdown)
DEVICES
    print -r -- '    Hang Ten Conductor alpha Review 2 (77777777-7777-7777-7777-777777777777) (Shutdown)   '
    ;;
  shutdown)
    print -r -- "$2 $3" >> "$XCRUN_CALL_LOG"
    [[ "${SHUTDOWN_FAIL_UUID:-}" != "$3" ]] || exit 1
    ;;
  delete)
    print -r -- "$2 $3" >> "$XCRUN_CALL_LOG"
    if [[ -n "${SECOND_DELETE_FAIL_UUID:-}" && "$3" == "$SECOND_DELETE_FAIL_UUID" ]]; then
      count_file=${SECOND_DELETE_COUNT_FILE:?}
      count=0
      [[ ! -f "$count_file" ]] || count=$(<"$count_file")
      count=$((count + 1))
      print -r -- "$count" > "$count_file"
      [[ "$count" -lt 2 ]] || exit 1
    fi
    [[ "${DELETE_FAIL_UUID:-}" != "$3" ]] || exit 1
    ;;
  *)
    exit 64
    ;;
esac
EOF
chmod +x "$fake_bin/xcrun"

assert_contains() {
  local expected=$1 actual=$2
  [[ "$actual" == *"$expected"* ]] || {
    print -u2 -- "expected output to contain: $expected"
    print -u2 -- "actual: $actual"
    exit 1
  }
}

assert_not_contains() {
  local unexpected=$1 actual=$2
  [[ "$actual" != *"$unexpected"* ]] || {
    print -u2 -- "did not expect output to contain: $unexpected"
    print -u2 -- "actual: $actual"
    exit 1
  }
}

assert_all_call_log_contains_list_devices() {
  local all_calls
  all_calls=$(<"$all_call_log")
  assert_contains 'simctl list devices' "$all_calls"
}

run_cleanup() {
  PATH="$fake_bin:$PATH" XCRUN_CALL_LOG="$call_log" XCRUN_ALL_CALL_LOG="$all_call_log" "$cleanup_script" "$@"
}

workspace="$temp_dir/workspace"
manifest="$workspace/.context/conductor-owned-simulators"
pending_manifest="$workspace/.context/conductor-pending-simulators"
mkdir -p "${manifest:h}"

print -r -- '11111111-1111-1111-1111-111111111111
22222222-2222-2222-2222-222222222222
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' > "$manifest"
: > "$call_log"
: > "$all_call_log"
CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive
archive_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$archive_calls"
assert_contains 'shutdown 22222222-2222-2222-2222-222222222222' "$archive_calls"
assert_contains 'delete 22222222-2222-2222-2222-222222222222' "$archive_calls"
assert_not_contains '33333333-3333-3333-3333-333333333333' "$archive_calls"
assert_not_contains '44444444-4444-4444-4444-444444444444' "$archive_calls"
assert_all_call_log_contains_list_devices

print -r -- 'abababab-abab-abab-abab-abababababab' > "$manifest"
: > "$call_log"
: > "$all_call_log"
CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive
lowercase_uuid_calls=$(<"$call_log")
assert_contains 'delete ABABABAB-ABAB-ABAB-ABAB-ABABABABABAB' "$lowercase_uuid_calls"
assert_not_contains 'delete abababab-abab-abab-abab-abababababab' "$lowercase_uuid_calls"
[[ ! -s "$manifest" ]] || {
  print -u2 -- 'lowercase manifest UUID was not consumed after successful delete'
  exit 1
}

print -r -- 'CDCDCDCD-CDCD-CDCD-CDCD-CDCDCDCDCDCD' > "$manifest"
: > "$call_log"
: > "$all_call_log"
CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive
lowercase_device_record_calls=$(<"$call_log")
assert_contains 'delete CDCDCDCD-CDCD-CDCD-CDCD-CDCDCDCDCDCD' "$lowercase_device_record_calls"
[[ ! -s "$manifest" ]] || {
  print -u2 -- 'uppercase manifest UUID did not match lowercase simctl device record'
  exit 1
}

: > "$manifest"
print -r -- '74747474-7474-7474-7474-747474747474
33333333-3333-3333-3333-333333333333
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' > "$pending_manifest"
: > "$call_log"
: > "$all_call_log"
if CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive accepted a pending simulator owned by another workspace'
  exit 1
fi
pending_archive_calls=$(<"$call_log")
assert_contains 'shutdown 74747474-7474-7474-7474-747474747474' "$pending_archive_calls"
assert_contains 'delete 74747474-7474-7474-7474-747474747474' "$pending_archive_calls"
assert_not_contains 'shutdown 33333333-3333-3333-3333-333333333333' "$pending_archive_calls"
assert_not_contains 'delete 33333333-3333-3333-3333-333333333333' "$pending_archive_calls"
assert_not_contains 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' "$pending_archive_calls"
assert_all_call_log_contains_list_devices
: > "$pending_manifest"

print -r -- 'not-a-uuid' > "$manifest"
: > "$call_log"
: > "$all_call_log"
if CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive accepted a malformed manifest entry'
  exit 1
fi
[[ ! -s "$call_log" ]] || {
  print -u2 -- 'archive invoked simctl for a malformed manifest entry'
  exit 1
}

print -r -- '33333333-3333-3333-3333-333333333333' > "$manifest"
: > "$call_log"
: > "$all_call_log"
if CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive accepted another workspace device'
  exit 1
fi
mismatched_calls=$(<"$call_log")
assert_not_contains 'delete 33333333-3333-3333-3333-333333333333' "$mismatched_calls"

print -r -- '55555555-5555-5555-5555-555555555555' > "$manifest"
: > "$call_log"
: > "$all_call_log"
if CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive accepted a workspace name with alpha as a substring'
  exit 1
fi
alphabet_calls=$(<"$call_log")
assert_not_contains 'delete 55555555-5555-5555-5555-555555555555' "$alphabet_calls"

print -r -- '22222222-2222-2222-2222-222222222222' > "$manifest"
: > "$call_log"
: > "$all_call_log"
if SHUTDOWN_FAIL_UUID=22222222-2222-2222-2222-222222222222 CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive returned success after a shutdown failure'
  exit 1
fi
shutdown_failure_calls=$(<"$call_log")
assert_contains 'shutdown 22222222-2222-2222-2222-222222222222' "$shutdown_failure_calls"
assert_not_contains 'delete 22222222-2222-2222-2222-222222222222' "$shutdown_failure_calls"

print -r -- '11111111-1111-1111-1111-111111111111' > "$manifest"
: > "$call_log"
: > "$all_call_log"
if DELETE_FAIL_UUID=11111111-1111-1111-1111-111111111111 CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive returned success after a delete failure'
  exit 1
fi
archive_delete_failure_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$archive_delete_failure_calls"

print -r -- '11111111-1111-1111-1111-111111111111' > "$manifest"
print -r -- '11111111-1111-1111-1111-111111111111' > "$pending_manifest"
duplicate_delete_count_file="$temp_dir/duplicate-delete-count"
: > "$call_log"
: > "$all_call_log"
CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha SECOND_DELETE_FAIL_UUID=11111111-1111-1111-1111-111111111111 SECOND_DELETE_COUNT_FILE="$duplicate_delete_count_file" run_cleanup archive
duplicate_archive_calls=$(<"$call_log")
duplicate_archive_delete_count=$(grep -c '^delete 11111111-1111-1111-1111-111111111111$' "$call_log" || true)
[[ "$duplicate_archive_delete_count" -eq 1 ]] || {
  print -u2 -- "expected archive to delete duplicate manifest UUID once, got $duplicate_archive_delete_count"
  print -u2 -- "actual: $duplicate_archive_calls"
  exit 1
}
[[ "$(<"$duplicate_delete_count_file")" -eq 1 ]] || {
  print -u2 -- "expected fake xcrun to observe one delete for duplicate UUID"
  exit 1
}
assert_all_call_log_contains_list_devices
: > "$pending_manifest"

print -r -- '11111111-1111-1111-1111-111111111111
11111111-1111-1111-1111-111111111111
22222222-2222-2222-2222-222222222222
not-a-uuid' > "$manifest"
print -r -- '11111111-1111-1111-1111-111111111111
33333333-3333-3333-3333-333333333333
bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' > "$pending_manifest"
: > "$call_log"
: > "$all_call_log"
if DELETE_FAIL_UUID=22222222-2222-2222-2222-222222222222 CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive accepted a delete failure in mixed manifest test'
  exit 1
fi
[[ "$(<"$manifest")" == *'22222222-2222-2222-2222-222222222222'* ]] || exit 1
[[ "$(<"$manifest")" == *'not-a-uuid'* ]] || exit 1
[[ "$(<"$pending_manifest")" == *'33333333-3333-3333-3333-333333333333'* ]] || exit 1
assert_not_contains '11111111-1111-1111-1111-111111111111' "$(<"$manifest")$(<"$pending_manifest")"
assert_not_contains 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb' "$(<"$pending_manifest")"

: > "$call_log"
: > "$all_call_log"
dry_run=$(run_cleanup prune)
assert_contains 'Would delete Hang Ten Conductor alpha Review (11111111-1111-1111-1111-111111111111)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor beta Review (33333333-3333-3333-3333-333333333333)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor alpha Review 2 (77777777-7777-7777-7777-777777777777)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor alpha Review 263 (88888888-8888-8888-8888-888888888888)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor alpha Review 20260803 (99999999-9999-9999-9999-999999999999)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor alpha Review Transition (12121212-1212-1212-1212-121212121212)' "$dry_run"
assert_contains 'Would delete Hang Ten Worcester Review ff8fa93 (20202020-2020-2020-2020-202020202020)' "$dry_run"
assert_not_contains '74747474-7474-7474-7474-747474747474' "$dry_run"
assert_not_contains '10101010-1010-1010-1010-101010101010' "$dry_run"
assert_not_contains '66666666-6666-6666-6666-666666666666' "$dry_run"
assert_not_contains 'iPhone Review' "$dry_run"
assert_not_contains 'abababab-abab-abab-abab-abababababab' "$dry_run"
assert_not_contains '30303030-3030-3030-3030-303030303030' "$dry_run"
assert_not_contains '40404040-4040-4040-4040-404040404040' "$dry_run"
assert_not_contains '50505050-5050-5050-5050-505050505050' "$dry_run"
assert_not_contains '60606060-6060-6060-6060-606060606060' "$dry_run"
assert_not_contains '73737373-7373-7373-7373-737373737373' "$dry_run"
assert_not_contains '31313131-3131-3131-3131-313131313131' "$dry_run"
assert_not_contains '32323232-3232-3232-3232-323232323232' "$dry_run"
assert_not_contains '71717171-7171-7171-7171-717171717171' "$dry_run"
assert_not_contains '72727272-7272-7272-7272-727272727272' "$dry_run"
assert_not_contains '73737370-7373-7373-7373-737373737370' "$dry_run"
assert_not_contains '73737371-7373-7373-7373-737373737371' "$dry_run"
assert_not_contains '73737372-7373-7373-7373-737373737372' "$dry_run"
[[ ! -s "$call_log" ]] || {
  print -u2 -- 'prune dry run invoked xcrun delete or shutdown'
  exit 1
}
assert_all_call_log_contains_list_devices

: > "$call_log"
: > "$all_call_log"
run_cleanup prune --delete
prune_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$prune_calls"
assert_contains 'delete 33333333-3333-3333-3333-333333333333' "$prune_calls"
assert_contains 'delete 77777777-7777-7777-7777-777777777777' "$prune_calls"
assert_contains 'delete 88888888-8888-8888-8888-888888888888' "$prune_calls"
assert_contains 'delete 99999999-9999-9999-9999-999999999999' "$prune_calls"
assert_contains 'delete 12121212-1212-1212-1212-121212121212' "$prune_calls"
assert_contains 'delete 20202020-2020-2020-2020-202020202020' "$prune_calls"
assert_not_contains 'delete 74747474-7474-7474-7474-747474747474' "$prune_calls"
assert_not_contains 'delete 10101010-1010-1010-1010-101010101010' "$prune_calls"
assert_not_contains '22222222-2222-2222-2222-222222222222' "$prune_calls"
assert_not_contains '44444444-4444-4444-4444-444444444444' "$prune_calls"
assert_not_contains '66666666-6666-6666-6666-666666666666' "$prune_calls"
assert_not_contains 'abababab-abab-abab-abab-abababababab' "$prune_calls"
assert_not_contains '30303030-3030-3030-3030-303030303030' "$prune_calls"
assert_not_contains '40404040-4040-4040-4040-404040404040' "$prune_calls"
assert_not_contains '50505050-5050-5050-5050-505050505050' "$prune_calls"
assert_not_contains '60606060-6060-6060-6060-606060606060' "$prune_calls"
assert_not_contains '73737373-7373-7373-7373-737373737373' "$prune_calls"
assert_not_contains '31313131-3131-3131-3131-313131313131' "$prune_calls"
assert_not_contains '32323232-3232-3232-3232-323232323232' "$prune_calls"
assert_not_contains '71717171-7171-7171-7171-717171717171' "$prune_calls"
assert_not_contains '72727272-7272-7272-7272-727272727272' "$prune_calls"
assert_not_contains 'delete 73737370-7373-7373-7373-737373737370' "$prune_calls"
assert_not_contains 'delete 73737371-7373-7373-7373-737373737371' "$prune_calls"
assert_not_contains 'delete 73737372-7373-7373-7373-737373737372' "$prune_calls"
assert_all_call_log_contains_list_devices

assert_rejects_malformed_args_without_xcrun() {
  local description=$1
  shift
  local exit_status=0

  : > "$call_log"
  : > "$all_call_log"
  run_cleanup "$@" >/dev/null 2>&1 || exit_status=$?
  [[ "$exit_status" -ne 0 ]] || {
    print -u2 -- "$description accepted malformed arguments"
    exit 1
  }
  [[ ! -s "$all_call_log" ]] || {
    print -u2 -- "$description invoked xcrun"
    exit 1
  }
  [[ ! -s "$call_log" ]] || {
    print -u2 -- "$description invoked simctl delete or shutdown"
    exit 1
  }
}

assert_rejects_malformed_args_without_xcrun 'prune typo' prune typo
assert_rejects_malformed_args_without_xcrun 'prune --delete typo' prune --delete typo
assert_rejects_malformed_args_without_xcrun 'prune empty option' prune ''
assert_rejects_malformed_args_without_xcrun 'archive extra argument' archive extra

: > "$call_log"
: > "$all_call_log"
if DELETE_FAIL_UUID=11111111-1111-1111-1111-111111111111 run_cleanup prune --delete; then
  print -u2 -- 'prune returned success after a delete failure'
  exit 1
fi
prune_delete_failure_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$prune_delete_failure_calls"

: > "$call_log"
: > "$all_call_log"
if transition_output=$(PRUNE_TRANSITION_UUID=12121212-1212-1212-1212-121212121212 run_cleanup prune --delete 2>&1); then
  print -u2 -- 'prune accepted a simulator that changed from Shutdown to Booted'
  exit 1
fi
transition_calls=$(<"$call_log")
assert_not_contains 'delete 12121212-1212-1212-1212-121212121212' "$transition_calls"
assert_contains 'Skipping simulator no longer Shutdown: Hang Ten Conductor alpha Review Transition (12121212-1212-1212-1212-121212121212) is Booted' "$transition_output"

: > "$call_log"
: > "$all_call_log"
if rename_output=$(PRUNE_RENAME_UUID=12121212-1212-1212-1212-121212121212 run_cleanup prune --delete 2>&1); then
  print -u2 -- 'prune accepted a simulator renamed to a standard device'
  exit 1
fi
rename_calls=$(<"$call_log")
assert_not_contains 'delete 12121212-1212-1212-1212-121212121212' "$rename_calls"
assert_contains 'Skipping simulator no longer has a review name: iPhone 17 Pro (12121212-1212-1212-1212-121212121212)' "$rename_output"

: > "$call_log"
: > "$all_call_log"
if name_output=$(PRUNE_NAME_UUID=12121212-1212-1212-1212-121212121212 run_cleanup prune --delete 2>&1); then
  print -u2 -- 'prune matched a UUID appearing only in a device name'
  exit 1
fi
name_calls=$(<"$call_log")
assert_not_contains 'delete 12121212-1212-1212-1212-121212121212' "$name_calls"
assert_contains 'Skipping simulator no longer available: Hang Ten Conductor alpha Review Transition (12121212-1212-1212-1212-121212121212)' "$name_output"

print -- 'conductor resource cleanup tests passed'
