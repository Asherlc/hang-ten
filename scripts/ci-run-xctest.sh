#!/usr/bin/env bash
# Run Hang Ten XCTest once with build-for-testing and test-without-building.
#
# Required environment:
#   XCTEST_LABEL                 Artifact/log label (e.g. HangTenTests)
#   XCTEST_DERIVED_DATA          Derived-data path
#   XCTEST_LOG_ROOT              Build and test log directory root
#   XCTEST_RESULT_ROOT           Directory for *.xcresult bundles (usually $RUNNER_TEMP)
#   XCTEST_XCCONFIG              Analytics/signing xcconfig path
#   XCTEST_ONLY_TESTING          Whitespace-separated -only-testing identifiers
#   XCTEST_PARALLEL_WORKERS      maximum-parallel-testing-workers value;
#                                parallel testing enabled only when > 1
#   XCTEST_RUN_TIMEOUT_SECONDS
#
# Optional:
#   SWIFT_PACKAGE_CACHE_PATH     -clonedSourcePackagesDirPath
#   XCTEST_DESTINATION           xcodebuild -destination (default: iPhone 17 Pro)
set -euo pipefail

: "${XCTEST_LABEL:?XCTEST_LABEL is required}"
: "${XCTEST_DERIVED_DATA:?XCTEST_DERIVED_DATA is required}"
: "${XCTEST_LOG_ROOT:?XCTEST_LOG_ROOT is required}"
: "${XCTEST_RESULT_ROOT:?XCTEST_RESULT_ROOT is required}"
: "${XCTEST_XCCONFIG:?XCTEST_XCCONFIG is required}"
: "${XCTEST_ONLY_TESTING:?XCTEST_ONLY_TESTING is required}"
: "${XCTEST_PARALLEL_WORKERS:?XCTEST_PARALLEL_WORKERS is required}"
: "${XCTEST_RUN_TIMEOUT_SECONDS:?XCTEST_RUN_TIMEOUT_SECONDS is required}"

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

run_xcodebuild_with_watchdog() {
  local phase="$1"
  local action="$2"
  local result_bundle="${3:-}"
  local log_dir="$XCTEST_LOG_ROOT/run"
  local phase_log="$log_dir/${phase}.log"
  local timeout_seconds=$((deadline - SECONDS))
  local phase_started
  local xcodebuild_pid
  local xcodebuild_status=0
  local target
  local -a cmd

  mkdir -p "$log_dir"

  if (( timeout_seconds <= 0 )); then
    echo "XCTest run out of time before ${phase}." | tee -a "$phase_log"
    return 124
  fi

  : > "$phase_log"

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

  echo "XCTest run phase=${phase} action=${action} timeout=${timeout_seconds}s derivedData=${XCTEST_DERIVED_DATA}"
  phase_started=$SECONDS

  # Give xcodebuild and its XCTest/simulator descendants their own process
  # group. A background command normally inherits this script's group, so
  # signalling that inherited group could kill the Actions shell itself.
  python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' \
    "${cmd[@]}" > "$phase_log" 2>&1 &
  xcodebuild_pid=$!
  # xcodebuild runs in a detached process group. Forward Actions cancellation
  # before the shell exits so it cannot keep writing to a result bundle.
  trap 'trap - INT TERM; kill -TERM -- "-$xcodebuild_pid" 2>/dev/null || true; wait "$xcodebuild_pid" 2>/dev/null || true; exit 143' INT TERM

  while kill -0 "$xcodebuild_pid" 2>/dev/null; do
    if (( SECONDS - phase_started >= timeout_seconds )); then
      echo "XCTest run (${phase}) exceeded ${timeout_seconds}s; collecting diagnostics." | tee -a "$phase_log"
      sample "$xcodebuild_pid" 10 -file "$log_dir/xcodebuild-${phase}.sample.txt" || true
      xcrun simctl list devices >> "$log_dir/simctl-devices.txt" 2>&1 || true
      kill -TERM -- "-$xcodebuild_pid" 2>/dev/null || true
      for _ in $(seq 1 30); do
        kill -0 -- "-$xcodebuild_pid" 2>/dev/null || break
        sleep 1
      done
      if kill -0 -- "-$xcodebuild_pid" 2>/dev/null; then
        echo "XCTest run (${phase}) ignored SIGTERM; sending SIGKILL." | tee -a "$phase_log"
        kill -KILL -- "-$xcodebuild_pid" 2>/dev/null || true
      fi
      wait "$xcodebuild_pid" || true
      trap - INT TERM
      cat "$phase_log"
      return 124
    fi
    sleep 5
  done

  wait "$xcodebuild_pid" || xcodebuild_status=$?
  trap - INT TERM
  cat "$phase_log"
  return "$xcodebuild_status"
}

deadline=$((SECONDS + XCTEST_RUN_TIMEOUT_SECONDS))
result_bundle="$XCTEST_RESULT_ROOT/${XCTEST_LABEL}-run.xcresult"

run_xcodebuild_with_watchdog "build-for-testing" "build-for-testing"
run_xcodebuild_with_watchdog "test-without-building" "test-without-building" "$result_bundle"
