#!/usr/bin/env bash
# Run Hang Ten XCTest with build-for-testing, soft retry, and reused DerivedData.
#
# Soft retry (attempt 2+): re-run only tests that failed in the previous
# attempt's .xcresult (via xcresulttool), and only when that attempt finished
# a normal test-phase failure. Watchdog timeouts (exit 124) and incomplete
# runs keep a full-shard retry so never-run tests are not skipped. If no
# failed-test IDs can be extracted (infra flake / empty bundle), also fall
# back to one full-shard retry.
#
# Required environment:
#   XCTEST_LABEL                 Artifact/log label (e.g. HangTenTests)
#   XCTEST_DERIVED_DATA          Shared derived-data path (reused across attempts)
#   XCTEST_LOG_ROOT              Per-attempt log directory root
#   XCTEST_RESULT_ROOT           Directory for *.xcresult bundles (usually $RUNNER_TEMP)
#   XCTEST_XCCONFIG              Analytics/signing xcconfig path
#   XCTEST_ONLY_TESTING          Whitespace-separated -only-testing identifiers
#   XCTEST_PARALLEL_WORKERS      maximum-parallel-testing-workers value;
#                                parallel testing enabled only when > 1
#   XCTEST_ATTEMPT_TIMEOUT_SECONDS
#
# Optional:
#   SWIFT_PACKAGE_CACHE_PATH     -clonedSourcePackagesDirPath
#   XCTEST_DESTINATION           xcodebuild -destination (default: iPhone 17 Pro)
#   XCTEST_MAX_ATTEMPTS          Soft retries including the first run (default: 2)
#   GITHUB_OUTPUT                When set, records attempt_N_failed=true
#
# Self-check (no other env required):
#   scripts/ci-run-xctest.sh --self-check

set -euo pipefail

# Emit one Target/Class/method per line suitable for xcodebuild -only-testing.
# Prefers xcresulttool summary / tests tree; falls back to xcodebuild log lines.
collect_failed_only_testing_ids() {
  local result_bundle="$1"
  local attempt_log_dir="${2:-}"
  python3 - "$result_bundle" "$attempt_log_dir" <<'PY'
import json
import os
import re
import subprocess
import sys

result_bundle = sys.argv[1]
attempt_log_dir = sys.argv[2] if len(sys.argv) > 2 else ""


def normalize_id(target, ident, url=""):
    target = (target or "").strip()
    ident = (ident or "").strip()
    url = (url or "").strip()
    if url.startswith("test://"):
        # test://com.apple.xcode/Project/Target/Class/method
        path = url.split("://", 1)[1]
        parts = [p for p in path.split("/") if p]
        # host, project, target, class, method, ...
        if len(parts) >= 5:
            return "/".join(parts[2:])
    if not ident:
        return None
    if ident.endswith("()"):
        ident = ident[:-2]
    if target and not ident.startswith(target + "/"):
        return f"{target}/{ident}"
    return ident or None


def ids_from_summary(data):
    out = []
    for failure in data.get("testFailures") or []:
        nid = normalize_id(
            failure.get("targetName") or "",
            failure.get("testIdentifierString") or "",
            failure.get("testIdentifierURL") or "",
        )
        if nid:
            out.append(nid)
    return out


def ids_from_tests_tree(data):
    out = []

    def walk(nodes, bundle=None):
        for node in nodes or []:
            node_type = node.get("nodeType") or ""
            name = node.get("name") or ""
            next_bundle = bundle
            if node_type in ("Unit test bundle", "UI test bundle"):
                next_bundle = name
            if node_type == "Test Case" and node.get("result") == "Failed":
                nid = normalize_id(
                    next_bundle or "",
                    node.get("nodeIdentifier") or name,
                    node.get("nodeIdentifierURL") or "",
                )
                if nid:
                    out.append(nid)
            walk(node.get("children"), next_bundle)

    walk(data.get("testNodes"))
    return out


def xcresulttool_json(*args):
    try:
        raw = subprocess.check_output(
            ["xcrun", "xcresulttool", *args],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def ids_from_xcodebuild_logs(log_dir):
    if not log_dir or not os.path.isdir(log_dir):
        return []
    # Test Case '-[Target.ClassName testMethod]' failed
    pattern = re.compile(
        r"Test Case '-\[([^.]+)\.([^ ]+) ([^\]]+)\]' (?:failed|crashed)"
    )
    out = []
    for root, _dirs, files in os.walk(log_dir):
        for name in files:
            if not name.endswith(".log"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        match = pattern.search(line)
                        if match:
                            out.append(f"{match.group(1)}/{match.group(2)}/{match.group(3)}")
            except OSError:
                continue
    return out


ids = []
if result_bundle and os.path.isdir(result_bundle):
    summary = xcresulttool_json(
        "get", "test-results", "summary", "--path", result_bundle, "--compact"
    )
    if summary:
        ids = ids_from_summary(summary)
    if not ids:
        tests = xcresulttool_json(
            "get", "test-results", "tests", "--path", result_bundle, "--compact"
        )
        if tests:
            ids = ids_from_tests_tree(tests)

if not ids:
    ids = ids_from_xcodebuild_logs(attempt_log_dir)

# Stable unique order
seen = set()
for item in ids:
    if item and item not in seen:
        seen.add(item)
        print(item)
PY
}

if [[ "${1:-}" == "--self-check" ]]; then
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/ci-run-xctest-self-check.XXXXXX")"
  trap 'rm -rf "$tmpdir"' EXIT
  mkdir -p "$tmpdir/logs"
  cat > "$tmpdir/summary.json" <<'JSON'
{
  "testFailures": [
    {
      "targetName": "HangTenUITests",
      "testIdentifierString": "GripCueDiagnosticScreenshotUITests/testFoo()",
      "testIdentifierURL": "test://com.apple.xcode/HangTen/HangTenUITests/GripCueDiagnosticScreenshotUITests/testFoo",
      "testName": "testFoo()",
      "failureText": "XCTAssert"
    },
    {
      "targetName": "HangTenTests",
      "testIdentifierString": "WorkoutAudioCoachTests/testBar()",
      "testIdentifierURL": "",
      "testName": "testBar()",
      "failureText": "XCTAssert"
    }
  ]
}
JSON
  python3 - "$tmpdir/summary.json" <<'PY' > "$tmpdir/from-summary.txt"
import json, sys
path = sys.argv[1]
data = json.load(open(path))

def normalize_id(target, ident, url=""):
    target = (target or "").strip()
    ident = (ident or "").strip()
    url = (url or "").strip()
    if url.startswith("test://"):
        parts = [p for p in url.split("://", 1)[1].split("/") if p]
        if len(parts) >= 5:
            return "/".join(parts[2:])
    if not ident:
        return None
    if ident.endswith("()"):
        ident = ident[:-2]
    if target and not ident.startswith(target + "/"):
        return f"{target}/{ident}"
    return ident or None

for failure in data["testFailures"]:
    print(normalize_id(failure["targetName"], failure["testIdentifierString"], failure.get("testIdentifierURL") or ""))
PY
  printf "%s\n" \
    "Test Case '-[HangTenTests.WorkoutAudioCoachTests testBar]' failed (0.100 seconds)." \
    > "$tmpdir/logs/test-without-building.log"
  # Exercise log fallback with a missing xcresult path.
  log_ids=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && log_ids+=("$line")
  done < <(collect_failed_only_testing_ids "$tmpdir/missing.xcresult" "$tmpdir/logs")
  summary_ids=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && summary_ids+=("$line")
  done < "$tmpdir/from-summary.txt"
  expected_summary=(
    "HangTenUITests/GripCueDiagnosticScreenshotUITests/testFoo"
    "HangTenTests/WorkoutAudioCoachTests/testBar"
  )
  expected_log=("HangTenTests/WorkoutAudioCoachTests/testBar")
  if [[ "${summary_ids[*]}" != "${expected_summary[*]}" ]]; then
    echo "self-check failed: summary normalize got: ${summary_ids[*]}" >&2
    exit 1
  fi
  if [[ "${log_ids[*]}" != "${expected_log[*]}" ]]; then
    echo "self-check failed: log parse got: ${log_ids[*]}" >&2
    exit 1
  fi
  echo "ci-run-xctest self-check ok (failed-only id normalize + log fallback)"
  exit 0
fi

: "${XCTEST_LABEL:?XCTEST_LABEL is required}"
: "${XCTEST_DERIVED_DATA:?XCTEST_DERIVED_DATA is required}"
: "${XCTEST_LOG_ROOT:?XCTEST_LOG_ROOT is required}"
: "${XCTEST_RESULT_ROOT:?XCTEST_RESULT_ROOT is required}"
: "${XCTEST_XCCONFIG:?XCTEST_XCCONFIG is required}"
: "${XCTEST_ONLY_TESTING:?XCTEST_ONLY_TESTING is required}"
: "${XCTEST_PARALLEL_WORKERS:?XCTEST_PARALLEL_WORKERS is required}"
: "${XCTEST_ATTEMPT_TIMEOUT_SECONDS:?XCTEST_ATTEMPT_TIMEOUT_SECONDS is required}"

XCTEST_MAX_ATTEMPTS="${XCTEST_MAX_ATTEMPTS:-2}"
if ! [[ "$XCTEST_MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ ]]; then
  echo "XCTEST_MAX_ATTEMPTS must be a positive integer; got: $XCTEST_MAX_ATTEMPTS" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

destination="${XCTEST_DESTINATION:-platform=iOS Simulator,name=iPhone 17 Pro,OS=latest}"

mkdir -p "$XCTEST_DERIVED_DATA" "$XCTEST_LOG_ROOT" "$XCTEST_RESULT_ROOT"

# shellcheck disable=SC2206
shard_only_testing_targets=(${XCTEST_ONLY_TESTING})
if [[ "${#shard_only_testing_targets[@]}" -eq 0 ]]; then
  echo "XCTEST_ONLY_TESTING must list at least one identifier." >&2
  exit 1
fi
only_testing_targets=("${shard_only_testing_targets[@]}")

# Set when attempt 1's build-for-testing succeeds. Retry reuse must not trust
# stale products restored from the DerivedData cache after a failed build.
built_for_testing_ok=0

mark_attempt_failed() {
  local attempt="$1"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "attempt_${attempt}_failed=true" >> "$GITHUB_OUTPUT"
  fi
}

products_exist() {
  local hit
  hit="$(
    find "$XCTEST_DERIVED_DATA" \
      -path '*/Build/Products/*' \
      \( -name 'HangTen.app' -o -name '*.xctest' \) \
      -print \
      -quit 2>/dev/null || true
  )"
  [[ -n "$hit" ]]
}

run_xcodebuild_with_watchdog() {
  local attempt="$1"
  local phase="$2"
  local action="$3"
  local result_bundle="${4:-}"
  local attempt_log_dir="$XCTEST_LOG_ROOT/attempt-$attempt"
  local attempt_log="$attempt_log_dir/${phase}.log"
  local timeout_seconds=$((attempt_deadline - SECONDS))
  local attempt_started
  local xcodebuild_pid
  local xcodebuild_status=0
  local target
  local -a cmd

  mkdir -p "$attempt_log_dir"

  if (( timeout_seconds <= 0 )); then
    echo "XCTest attempt $attempt out of time before ${phase}." | tee -a "$attempt_log"
    return 124
  fi

  : > "$attempt_log"

  # Parallel clones (even with 1 worker) leave the simulator unhealthy for UI
  # shards. Enable parallel testing only when workers > 1 (unit tests).
  local parallel_enabled=NO
  if [[ "$XCTEST_PARALLEL_WORKERS" -gt 1 ]]; then
    parallel_enabled=YES
  fi

  cmd=(
    xcodebuild
    -project HangTen.xcodeproj
    -scheme HangTen
    -configuration Debug
    -destination "$destination"
    -parallel-testing-enabled "$parallel_enabled"
    -maximum-parallel-testing-workers "$XCTEST_PARALLEL_WORKERS"
  )
  for target in "${only_testing_targets[@]}"; do
    cmd+=("-only-testing:${target}")
  done
  cmd+=(-derivedDataPath "$XCTEST_DERIVED_DATA")
  if [[ -n "${SWIFT_PACKAGE_CACHE_PATH:-}" ]]; then
    cmd+=(-clonedSourcePackagesDirPath "$SWIFT_PACKAGE_CACHE_PATH")
  fi
  cmd+=(
    -showBuildTimingSummary
    -xcconfig "$XCTEST_XCCONFIG"
    COMPILER_INDEX_STORE_ENABLE=NO
    CODE_SIGNING_ALLOWED=YES
    CODE_SIGNING_REQUIRED=YES
    CODE_SIGN_IDENTITY="-"
  )
  if [[ -n "$result_bundle" ]]; then
    rm -rf "$result_bundle"
    cmd+=(-resultBundlePath "$result_bundle")
  fi
  cmd+=("$action")

  echo "XCTest attempt $attempt phase=${phase} action=${action} timeout=${timeout_seconds}s derivedData=${XCTEST_DERIVED_DATA}"
  attempt_started=$SECONDS

  # Give xcodebuild and its XCTest/simulator descendants their own process
  # group. A background command normally inherits this script's group, so
  # signalling that inherited group could kill the Actions shell itself.
  python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
    "${cmd[@]}" > "$attempt_log" 2>&1 &
  xcodebuild_pid=$!

  while kill -0 "$xcodebuild_pid" 2>/dev/null; do
    if (( SECONDS - attempt_started >= timeout_seconds )); then
      echo "XCTest attempt $attempt (${phase}) exceeded ${timeout_seconds}s; collecting diagnostics before retrying." | tee -a "$attempt_log"
      sample "$xcodebuild_pid" 10 -file "$attempt_log_dir/xcodebuild-${phase}.sample.txt" || true
      xcrun simctl list devices >> "$attempt_log_dir/simctl-devices.txt" 2>&1 || true
      kill -TERM -- "-$xcodebuild_pid" 2>/dev/null || true
      for _ in $(seq 1 30); do
        kill -0 -- "-$xcodebuild_pid" 2>/dev/null || break
        sleep 1
      done
      if kill -0 -- "-$xcodebuild_pid" 2>/dev/null; then
        echo "XCTest attempt $attempt (${phase}) ignored SIGTERM; sending SIGKILL." | tee -a "$attempt_log"
        kill -KILL -- "-$xcodebuild_pid" 2>/dev/null || true
      fi
      wait "$xcodebuild_pid" || true
      cat "$attempt_log"
      return 124
    fi
    sleep 5
  done

  wait "$xcodebuild_pid" || xcodebuild_status=$?
  cat "$attempt_log"
  return "$xcodebuild_status"
}

run_xctest_attempt() {
  local attempt="$1"
  local result_bundle="$XCTEST_RESULT_ROOT/${XCTEST_LABEL}-attempt-${attempt}.xcresult"
  attempt_deadline=$((SECONDS + XCTEST_ATTEMPT_TIMEOUT_SECONDS))

  if [[ "$attempt" -eq 1 ]]; then
    run_xcodebuild_with_watchdog "$attempt" "build-for-testing" "build-for-testing" \
      || return $?
    built_for_testing_ok=1
    run_xcodebuild_with_watchdog "$attempt" "test-without-building" "test-without-building" "$result_bundle" \
      || return $?
    return 0
  fi

  # Prefer test-without-building only when this run already built successfully.
  # products_exist alone is insufficient: a DerivedData cache restore can leave
  # stale .app/.xctest trees after build-for-testing failed.
  if [[ "$built_for_testing_ok" -eq 1 ]] && products_exist; then
    echo "XCTest attempt $attempt reusing DerivedData products at $XCTEST_DERIVED_DATA"
    run_xcodebuild_with_watchdog "$attempt" "test-without-building" "test-without-building" "$result_bundle" \
      || return $?
    return 0
  fi

  echo "XCTest attempt $attempt: no trusted DerivedData products; falling back to full test."
  run_xcodebuild_with_watchdog "$attempt" "test" "test" "$result_bundle" \
    || return $?
}

# True when the attempt's test phase appears to have finished (not cut off).
# Used to avoid failed-only narrowing after partial runs that leave early
# failures in the xcresult while later tests never executed.
test_phase_completed_normally() {
  local attempt="$1"
  local result_bundle="$XCTEST_RESULT_ROOT/${XCTEST_LABEL}-attempt-${attempt}.xcresult"
  local attempt_log_dir="$XCTEST_LOG_ROOT/attempt-$attempt"
  local summary_result=""

  if [[ -d "$attempt_log_dir" ]] && \
    grep -R -q -E "Test Suite 'Selected tests' (passed|failed)" "$attempt_log_dir" --include='*.log' 2>/dev/null; then
    return 0
  fi

  if [[ -d "$result_bundle" ]]; then
    summary_result="$(
      xcrun xcresulttool get test-results summary --path "$result_bundle" --compact 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("result") or "")' \
        2>/dev/null || true
    )"
    case "$summary_result" in
      Failed|Passed)
        return 0
        ;;
    esac
  fi

  return 1
}

restore_full_shard_targets() {
  only_testing_targets=("${shard_only_testing_targets[@]}")
}

narrow_only_testing_for_retry() {
  local attempt="$1"
  local result_bundle="$XCTEST_RESULT_ROOT/${XCTEST_LABEL}-attempt-${attempt}.xcresult"
  local attempt_log_dir="$XCTEST_LOG_ROOT/attempt-$attempt"
  local -a failed_targets=()
  local line

  while IFS= read -r line; do
    [[ -n "$line" ]] && failed_targets+=("$line")
  done < <(collect_failed_only_testing_ids "$result_bundle" "$attempt_log_dir")
  if [[ "${#failed_targets[@]}" -gt 0 ]]; then
    echo "XCTest attempt $attempt failed; retrying only failed tests (${#failed_targets[@]}): ${failed_targets[*]}"
    only_testing_targets=("${failed_targets[@]}")
  else
    echo "XCTest attempt $attempt failed; no failed-test IDs found (infra/empty result); retrying full shard."
    restore_full_shard_targets
  fi
}

attempt=1
while (( attempt <= XCTEST_MAX_ATTEMPTS )); do
  attempt_status=0
  run_xctest_attempt "$attempt" || attempt_status=$?
  if [[ "$attempt_status" -eq 0 ]]; then
    exit 0
  fi
  mark_attempt_failed "$attempt"
  if (( attempt == XCTEST_MAX_ATTEMPTS )); then
    echo "XCTest attempt $attempt failed." >&2
    exit 1
  fi
  # Never narrow after watchdog timeout or an incomplete test phase: early
  # failures in a partial xcresult would skip never-run tests on retry.
  if [[ "$attempt_status" -eq 124 ]]; then
    echo "XCTest attempt $attempt timed out (status 124); retrying full shard."
    restore_full_shard_targets
  elif ! test_phase_completed_normally "$attempt"; then
    echo "XCTest attempt $attempt incomplete/infra failure (status ${attempt_status}); retrying full shard."
    restore_full_shard_targets
  else
    narrow_only_testing_for_retry "$attempt"
  fi
  attempt=$((attempt + 1))
done
