#!/bin/zsh
set -euo pipefail

repo_root=${0:A:h:h:h}
cleanup_script="$repo_root/scripts/conductor-resource-cleanup.sh"
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

fake_bin="$temp_dir/bin"
call_log="$temp_dir/xcrun-calls"
mkdir -p "$fake_bin"

cat > "$fake_bin/xcrun" <<'EOF'
#!/bin/zsh
set -euo pipefail

if [[ "$1" != simctl ]]; then
  print -u2 -- "unexpected xcrun invocation: $*"
  exit 64
fi

case "$2" in
  list)
    [[ "${3:-}" == devices ]] || exit 64
    cat <<'DEVICES'
== Devices ==
-- iOS 26.5 --
    Hang Ten Conductor alpha Review (11111111-1111-1111-1111-111111111111) (Shutdown)
    Hang Ten Conductor alpha Running (22222222-2222-2222-2222-222222222222) (Booted)
    Hang Ten Conductor beta Review (33333333-3333-3333-3333-333333333333) (Shutdown)
    iPhone 17 Pro (44444444-4444-4444-4444-444444444444) (Shutdown)
    Hang Ten Conductor alphabet Review (55555555-5555-5555-5555-555555555555) (Shutdown)
    Hang Ten Conductor alpha Scratch (66666666-6666-6666-6666-666666666666) (Shutdown)
    Hang Ten Conductor alpha Review 263 (88888888-8888-8888-8888-888888888888) (Shutdown)
    Hang Ten Conductor alpha Review 20260803 (99999999-9999-9999-9999-999999999999) (Shutdown)
DEVICES
    print -r -- '    Hang Ten Conductor alpha Review 2 (77777777-7777-7777-7777-777777777777) (Shutdown)   '
    ;;
  shutdown)
    print -r -- "$2 $3" >> "$XCRUN_CALL_LOG"
    [[ "${SHUTDOWN_FAIL_UUID:-}" != "$3" ]] || exit 1
    ;;
  delete)
    print -r -- "$2 $3" >> "$XCRUN_CALL_LOG"
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

run_cleanup() {
  PATH="$fake_bin:$PATH" XCRUN_CALL_LOG="$call_log" "$cleanup_script" "$@"
}

workspace="$temp_dir/workspace"
manifest="$workspace/.context/conductor-owned-simulators"
mkdir -p "${manifest:h}"

print -r -- '11111111-1111-1111-1111-111111111111
22222222-2222-2222-2222-222222222222
aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' > "$manifest"
: > "$call_log"
CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive
archive_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$archive_calls"
assert_contains 'shutdown 22222222-2222-2222-2222-222222222222' "$archive_calls"
assert_contains 'delete 22222222-2222-2222-2222-222222222222' "$archive_calls"
assert_not_contains '33333333-3333-3333-3333-333333333333' "$archive_calls"
assert_not_contains '44444444-4444-4444-4444-444444444444' "$archive_calls"

print -r -- 'not-a-uuid' > "$manifest"
: > "$call_log"
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
if CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive accepted another workspace device'
  exit 1
fi
mismatched_calls=$(<"$call_log")
assert_not_contains 'delete 33333333-3333-3333-3333-333333333333' "$mismatched_calls"

print -r -- '55555555-5555-5555-5555-555555555555' > "$manifest"
: > "$call_log"
if CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive accepted a workspace name with alpha as a substring'
  exit 1
fi
alphabet_calls=$(<"$call_log")
assert_not_contains 'delete 55555555-5555-5555-5555-555555555555' "$alphabet_calls"

print -r -- '22222222-2222-2222-2222-222222222222' > "$manifest"
: > "$call_log"
if SHUTDOWN_FAIL_UUID=22222222-2222-2222-2222-222222222222 CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive returned success after a shutdown failure'
  exit 1
fi
shutdown_failure_calls=$(<"$call_log")
assert_contains 'shutdown 22222222-2222-2222-2222-222222222222' "$shutdown_failure_calls"
assert_not_contains 'delete 22222222-2222-2222-2222-222222222222' "$shutdown_failure_calls"

print -r -- '11111111-1111-1111-1111-111111111111' > "$manifest"
: > "$call_log"
if DELETE_FAIL_UUID=11111111-1111-1111-1111-111111111111 CONDUCTOR_WORKSPACE_PATH="$workspace" CONDUCTOR_WORKSPACE_NAME=alpha run_cleanup archive; then
  print -u2 -- 'archive returned success after a delete failure'
  exit 1
fi
archive_delete_failure_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$archive_delete_failure_calls"

: > "$call_log"
dry_run=$(run_cleanup prune)
assert_contains 'Would delete Hang Ten Conductor alpha Review (11111111-1111-1111-1111-111111111111)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor beta Review (33333333-3333-3333-3333-333333333333)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor alpha Review 2 (77777777-7777-7777-7777-777777777777)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor alpha Review 263 (88888888-8888-8888-8888-888888888888)' "$dry_run"
assert_contains 'Would delete Hang Ten Conductor alpha Review 20260803 (99999999-9999-9999-9999-999999999999)' "$dry_run"
assert_not_contains '66666666-6666-6666-6666-666666666666' "$dry_run"
[[ ! -s "$call_log" ]] || {
  print -u2 -- 'prune dry run invoked xcrun delete or shutdown'
  exit 1
}

: > "$call_log"
run_cleanup prune --delete
prune_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$prune_calls"
assert_contains 'delete 33333333-3333-3333-3333-333333333333' "$prune_calls"
assert_contains 'delete 77777777-7777-7777-7777-777777777777' "$prune_calls"
assert_contains 'delete 88888888-8888-8888-8888-888888888888' "$prune_calls"
assert_contains 'delete 99999999-9999-9999-9999-999999999999' "$prune_calls"
assert_not_contains '22222222-2222-2222-2222-222222222222' "$prune_calls"
assert_not_contains '44444444-4444-4444-4444-444444444444' "$prune_calls"
assert_not_contains '66666666-6666-6666-6666-666666666666' "$prune_calls"

: > "$call_log"
if DELETE_FAIL_UUID=11111111-1111-1111-1111-111111111111 run_cleanup prune --delete; then
  print -u2 -- 'prune returned success after a delete failure'
  exit 1
fi
prune_delete_failure_calls=$(<"$call_log")
assert_contains 'delete 11111111-1111-1111-1111-111111111111' "$prune_delete_failure_calls"

print -- 'conductor resource cleanup tests passed'
