#!/usr/bin/env bash
# Run Hang Ten XCTest with build-for-testing, soft retry, and reused DerivedData.
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

set -euo pipefail

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
only_testing_targets=(${XCTEST_ONLY_TESTING})
if [[ "${#only_testing_targets[@]}" -eq 0 ]]; then
  echo "XCTEST_ONLY_TESTING must list at least one identifier." >&2
  exit 1
fi

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

attempt=1
while (( attempt <= XCTEST_MAX_ATTEMPTS )); do
  if run_xctest_attempt "$attempt"; then
    exit 0
  fi
  mark_attempt_failed "$attempt"
  if (( attempt == XCTEST_MAX_ATTEMPTS )); then
    echo "XCTest attempt $attempt failed." >&2
    exit 1
  fi
  echo "XCTest attempt $attempt failed; retrying while reusing DerivedData."
  attempt=$((attempt + 1))
done
