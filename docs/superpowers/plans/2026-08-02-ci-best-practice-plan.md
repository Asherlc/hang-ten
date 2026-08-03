# CI Best-Practice Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pull-request CI validate compilation and the existing XCTest suite, then require all resulting checks for merges to `main`.

**Architecture:** Extend the existing GitHub Actions `CI` workflow with a separate Debug iOS Simulator test job and a `merge_group` trigger. Keep the two existing build matrix jobs unchanged, then extend the active GitHub `Main` ruleset with the new test check while preserving all existing rules.

**Tech Stack:** GitHub Actions, GitHub rulesets/API, Xcode `xcodebuild`, XCTest, macOS hosted runner `macos-26`.

## Global Constraints

- Keep the existing build matrix unchanged: `Build (Debug simulator)` and `Build (Release device)`.
- Add one independent check named exactly `Test (iOS Simulator)`.
- Use runner `macos-26`, configuration `Debug`, scheme `HangTen`, and an available iPhone 17 iOS Simulator without a runner-specific UDID or patch-level OS version.
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

Add this job to `.github/workflows/ci.yml` without altering the existing `build` matrix:

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

      - name: Run XCTest suite
        run: |
          set -o pipefail
          mkdir -p "$RUNNER_TEMP/hang-ten-test-logs" "$RUNNER_TEMP/hang-ten-test-derived-data"
          xcodebuild \
            -project HangTen.xcodeproj \
            -scheme HangTen \
            -configuration Debug \
            -destination "platform=iOS Simulator,name=iPhone 17" \
            -derivedDataPath "$RUNNER_TEMP/hang-ten-test-derived-data" \
            -resultBundlePath "$RUNNER_TEMP/HangTenTests.xcresult" \
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
```

If the runner exposes multiple iPhone 17 OS versions, leave the OS component unspecified as shown so Xcode selects an available version. Do not hard-code a simulator UDID.

- [ ] **Step 3: Run the exact test command locally**

Run the same test action with temporary paths:

```bash
tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT
xcodebuild \
  -project HangTen.xcodeproj \
  -scheme HangTen \
  -configuration Debug \
  -destination "platform=iOS Simulator,name=iPhone 17" \
  -derivedDataPath "$tmp_root/derived-data" \
  -resultBundlePath "$tmp_root/HangTenTests.xcresult" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  test
```

Expected result: `xcodebuild` exits 0 and the existing `WorkoutTimelineTests` XCTest cases pass.

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

- [ ] Local `xcodebuild test` passes for the shared `HangTen` scheme on an iPhone 17 simulator.
- [ ] The workflow parses and retains the existing build matrix.
- [ ] `Test (iOS Simulator)` is emitted by CI and has failure diagnostics.
- [ ] The active `Main` ruleset requires all three exact CI contexts.
- [ ] The release workflow remains unchanged.
- [ ] No unrelated source files changed.
