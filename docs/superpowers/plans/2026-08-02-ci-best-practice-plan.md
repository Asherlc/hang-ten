# CI Best-Practice Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pull-request CI validate compilation and the existing XCTest suite, then require all resulting checks for merges to `main`.

**Architecture:** Extend the existing GitHub Actions `CI` workflow with a separate Debug iOS Simulator test job and a `merge_group` trigger. Keep the two existing build matrix jobs unchanged, then extend the active GitHub `Main` ruleset with the new test check while preserving all existing rules.

**Tech Stack:** GitHub Actions, GitHub rulesets/API, Xcode `xcodebuild`, XCTest, macOS hosted runner `macos-26`.

## Global Constraints

- Keep the existing build matrix unchanged: `Build (Debug simulator)` and `Build (Release device)`.
- Add one independent check named exactly `Test (iOS Simulator)`.
- Use runner `macos-26`, configuration `Debug`, scheme `HangTen`, and provision an owned iPhone 17 iOS Simulator by discovering its device type from the complete `simctl list devicetypes` output and selecting the newest available iOS runtime.
- Disable signing with `CODE_SIGNING_ALLOWED=NO` and `CODE_SIGNING_REQUIRED=NO`.
- Keep read-only contents permissions, cancellation for superseded CI runs, timeouts, full-SHA-pinned actions, and failure diagnostics.
- Add the `merge_group` workflow trigger.
- Preserve all existing `Main` ruleset settings and required checks.
- The final required contexts are exactly `Build (Debug simulator)`, `Build (Release device)`, and `Test (iOS Simulator)`.
- Do not add a multi-device or physical-device test matrix, code-coverage threshold, or third-party test-reporting dependency.
- Do not change the release signing/archive workflow.

---

### Task 1: Add the simulator XCTest CI job

**Files:**
- Modify: `.github/workflows/ci.yml`
- Test: `HangTenTests/WorkoutTimelineTests.swift` through the shared `HangTen` scheme

**Interfaces:**
- Consumes: Existing `CI` workflow triggers, checkout action SHA, build matrix, runner, permissions, concurrency, and artifact-upload conventions.
- Produces: A GitHub Actions check named exactly `Test (iOS Simulator)` emitted for pull requests, pushes to `main`, and merge-queue groups.

- [ ] **Step 1: Add the merge-queue trigger without changing existing triggers**

Add this event alongside the existing `pull_request` and `push` events:

```yaml
  merge_group:
```

- [ ] **Step 2: Add the independent test job**

Add this job to `.github/workflows/ci.yml` without altering the existing `build` matrix. Its simulator setup must:

- discover the `iPhone 17` device type from the complete `xcrun simctl list devicetypes` output;
- select the newest available iOS runtime from `xcrun simctl list runtimes available`;
- create a uniquely named simulator and publish its UUID as the setup step output before booting;
- boot that UUID and wait for readiness with `xcrun simctl bootstatus <uuid> -b`.

The test step must use the created UUID and retain serial XCTest execution:

```yaml
  test:
    name: Test (iOS Simulator)
    runs-on: macos-26
    timeout-minutes: 30

    steps:
      # actions/checkout v4.2.2
      - name: Check out source
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          persist-credentials: false

      - name: Show Apple toolchain
        run: |
          set -euo pipefail
          sw_vers
          xcodebuild -version
          xcodebuild -showsdks

      - name: Create test simulator
        id: create-simulator
        run: |
          set -euo pipefail
          device_type_id="$(xcrun simctl list devicetypes | sed -nE 's/^[[:space:]]*iPhone 17 \((com\.apple\.CoreSimulator\.SimDeviceType\.[^)]+)\).*$/\1/p' | head -n 1)"
          if [[ -z "$device_type_id" ]]; then
            echo "Required iPhone 17 simulator device type is unavailable." >&2
            exit 1
          fi
          runtime_id="$(xcrun simctl list runtimes available | awk '/^[[:space:]]*iOS [0-9]/ { version = $2; runtime = $NF; if (runtime ~ /^com\.apple\.CoreSimulator\.SimRuntime\.iOS-/) print version "|" runtime }' | awk -F'|' '{ split($1, version, /\./); printf "%03d%03d%03d|%s\n", version[1], version[2], version[3], $2 }' | sort | tail -n 1 | cut -d'|' -f 2-)"
          if [[ -z "$runtime_id" ]]; then
            echo "No available iOS simulator runtime was found." >&2
            exit 1
          fi
          simulator_name="Hang Ten CI iPhone 17 $(uuidgen)"
          simulator_udid="$(xcrun simctl create "$simulator_name" "$device_type_id" "$runtime_id")"
          if [[ -z "$simulator_udid" ]]; then
            echo "Failed to create the owned iPhone 17 simulator." >&2
            exit 1
          fi
          echo "udid=$simulator_udid" >> "$GITHUB_OUTPUT"
          xcrun simctl boot "$simulator_udid"
          xcrun simctl bootstatus "$simulator_udid" -b

      - name: Run XCTest suite
        run: |
          set -o pipefail
          mkdir -p "$RUNNER_TEMP/hang-ten-test-logs" "$RUNNER_TEMP/hang-ten-test-derived-data"
          xcodebuild \
            -project HangTen.xcodeproj \
            -scheme HangTen \
            -configuration Debug \
            -destination "platform=iOS Simulator,id=${{ steps.create-simulator.outputs.udid }}" \
            -derivedDataPath "$RUNNER_TEMP/hang-ten-test-derived-data" \
            -resultBundlePath "$RUNNER_TEMP/HangTenTests.xcresult" \
            -parallel-testing-enabled NO \
            -maximum-parallel-testing-workers 1 \
            CODE_SIGNING_ALLOWED=NO \
            CODE_SIGNING_REQUIRED=NO \
            test 2>&1 | tee "$RUNNER_TEMP/hang-ten-test-logs/test.log"

      # actions/upload-artifact v4.6.2
      - name: Upload test diagnostics on failure
        if: failure()
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
        with:
          name: ci-test-results-${{ github.run_id }}
          path: |
            ${{ runner.temp }}/HangTenTests.xcresult
            ${{ runner.temp }}/hang-ten-test-logs/
          if-no-files-found: ignore

      - name: Delete test simulator
        if: always()
        env:
          SIMULATOR_UDID: ${{ steps.create-simulator.outputs.udid }}
        run: |
          set -euo pipefail
          if [[ -n "$SIMULATOR_UDID" ]]; then
            xcrun simctl delete "$SIMULATOR_UDID"
          fi
```

The failure artifact step remains conditional on failure. Cleanup must run with `if: always()` and delete only the UUID published by the create step.

- [ ] **Step 3: Run the exact test command locally**

Exercise the same discovery, creation, UUID-based test, diagnostics, and cleanup lifecycle locally with workspace-owned paths:

```bash
set -euo pipefail

workspace_path="$PWD"
workspace_name="${CONDUCTOR_WORKSPACE_NAME:?Set CONDUCTOR_WORKSPACE_NAME}"
context_path="$workspace_path/.context"
manifest="$context_path/conductor-owned-simulators"
logs_path="$context_path/ci-test-logs"
derived_data_path="$context_path/ci-test-derived-data"
result_bundle_path="$context_path/HangTenTests.xcresult"
mkdir -p "$logs_path" "$derived_data_path"
touch "$manifest"
simulator_name="Hang Ten Conductor ${workspace_name} iPhone 17 Review"

cleanup() {
  CONDUCTOR_WORKSPACE_PATH="$workspace_path" \
  CONDUCTOR_WORKSPACE_NAME="$workspace_name" \
  "$workspace_path/scripts/conductor-resource-cleanup.sh" archive
}
cleanup_on_exit() {
  original_status=$?
  trap - EXIT INT TERM
  cleanup_status=0
  cleanup || cleanup_status=$?
  if (( original_status != 0 )); then
    exit "$original_status"
  fi
  exit "$cleanup_status"
}
signal_exit() {
  trap - INT TERM
  exit "$1"
}
trap cleanup_on_exit EXIT
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM

device_type_id="$(xcrun simctl list devicetypes | sed -nE 's/^[[:space:]]*iPhone 17 \((com\.apple\.CoreSimulator\.SimDeviceType\.[^)]+)\).*$/\1/p' | head -n 1)"
runtime_id="$(xcrun simctl list runtimes available | awk '/^[[:space:]]*iOS [0-9]/ { version = $2; runtime = $NF; if (runtime ~ /^com\.apple\.CoreSimulator\.SimRuntime\.iOS-/) print version "|" runtime }' | awk -F'|' '{ split($1, version, /\./); printf "%03d%03d%03d|%s\n", version[1], version[2], version[3], $2 }' | sort | tail -n 1 | cut -d'|' -f 2-)"
simulator_udid="$(xcrun simctl create "$simulator_name" "$device_type_id" "$runtime_id")"
if [[ -z "$simulator_udid" ]]; then
  echo "Failed to create the owned iPhone 17 simulator." >&2
  exit 1
fi
if ! printf '%s\n' "$simulator_udid" >> "$manifest"; then
  if ! xcrun simctl delete "$simulator_udid"; then
    printf 'failed to write simulator manifest and failed to delete simulator %s\n' "$simulator_udid" >&2
    exit 1
  fi
  printf 'failed to write simulator manifest for %s\n' "$simulator_udid" >&2
  exit 1
fi
xcrun simctl boot "$simulator_udid"
xcrun simctl bootstatus "$simulator_udid" -b
xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination "platform=iOS Simulator,id=$simulator_udid" -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -derivedDataPath "$derived_data_path" -resultBundlePath "$result_bundle_path" CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO test 2>&1 | tee "$logs_path/test.log"
```

Local XCTest may be inconclusive on the shared host when the required device type or runtime is unavailable; the hosted `macos-26` CI run is authoritative. Record the observed local result rather than assuming a pass.

- [ ] **Step 4: Validate the workflow file**

Run:

```bash
git diff --check
ruby -e 'require "yaml"; YAML.load_file(".github/workflows/ci.yml")'
```

Expected result: both commands exit 0. Also inspect the diff to confirm only the `merge_group` trigger and the new test job were added.

- [ ] **Step 5: Commit the workflow change**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run XCTest suite on pull requests"
```

### Task 2: Require the simulator test in the Main ruleset

**Files:**
- Modify: GitHub ruleset `Asherlc/hang-ten` / `Main` (ID `20264425`)
- Test: GitHub ruleset read-back via `gh api`

**Interfaces:**
- Consumes: The exact check context produced by Task 1: `Test (iOS Simulator)`.
- Produces: The active `Main` ruleset requiring exactly the two existing build contexts plus `Test (iOS Simulator)`.

- [ ] **Step 1: Read and snapshot the current ruleset**

```bash
ruleset_before="$(mktemp -t hang-ten-main-ruleset)"
gh api repos/Asherlc/hang-ten/rulesets/20264425 > "$ruleset_before"
echo "Ruleset snapshot: $ruleset_before"
```

Confirm the ruleset is active, targets `~DEFAULT_BRANCH`, and currently contains the two build contexts before changing it.

- [ ] **Step 2: Update only the required-status-check rule**

Build the update payload from the read-back ruleset, preserving `name`, `target`, `enforcement`, `conditions`, `bypass_actors`, and every unrelated rule. Set the required status check list to exactly:

```json
[
  { "context": "Build (Debug simulator)", "integration_id": 15368 },
  { "context": "Build (Release device)", "integration_id": 15368 },
  { "context": "Test (iOS Simulator)", "integration_id": 15368 }
]
```

Use the GitHub ruleset update endpoint for `repos/Asherlc/hang-ten/rulesets/20264425`. Do not delete or recreate the ruleset.

- [ ] **Step 3: Verify the effective ruleset**

```bash
gh api repos/Asherlc/hang-ten/rulesets/20264425 --jq '{name, enforcement, target, required_status_checks: [.rules[] | select(.type == "required_status_checks") | .parameters.required_status_checks]}'
```

Expected result: the `Main` ruleset is active, targets the default branch, and returns exactly the three required contexts above.

- [ ] **Step 4: Confirm repository cleanliness and final scope**

```bash
git status --short
git diff origin/main...HEAD --stat
git diff --check origin/main...HEAD
```

Expected result: only the approved design/plan documentation and `.github/workflows/ci.yml` are changed locally; the ruleset mutation is visible in the API read-back and no source code changed.

---

## Final verification checklist

- [ ] The local simulator lifecycle is exercised when the shared host permits it; hosted CI remains the authoritative XCTest verification.
- [ ] The workflow parses and retains the existing build matrix.
- [ ] `Test (iOS Simulator)` is emitted by CI and has failure diagnostics.
- [ ] The active `Main` ruleset requires all three exact CI contexts.
- [ ] The release workflow remains unchanged.
- [ ] No unrelated source files changed.
