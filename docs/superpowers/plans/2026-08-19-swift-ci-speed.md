# Swift and macOS CI Speed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce iOS XCTest feedback time and macOS runner consumption while preserving the repository's required validation gates.

**Architecture:** Consolidate duplicate iOS work into the XCTest job, reuse hosted-runner simulator and SwiftPM assets, and move portable Workbench validation to Linux. Preserve stable branch-protection check names and all release/security behavior.

**Tech Stack:** GitHub Actions YAML, Xcode 26 `xcodebuild`, XCTest, Swift Package Manager, Bash, Ruby YAML parsing

**Spec:** `docs/superpowers/specs/2026-08-19-swift-ci-speed-design.md`

## Global Constraints

- Preserve the exact required check name `Build (Debug simulator)`.
- Preserve iOS Debug simulator testing, main-branch Release device building, HealthKit entitlement verification, and failure artifact uploads.
- Preserve metadata validation for metadata-only pull requests and run it exactly once when the iOS test job already covers the change.
- Use an installed `iPhone 17 Pro` with `OS=latest`; do not create or delete a simulator in CI.
- Enable XCTest parallelization with at most two workers.
- Cache only dependency/source or SwiftPM build artifacts with keys scoped by OS, architecture, and resolved dependencies; do not cache simulator state.
- Preserve Swift CodeQL cadence and tracing behavior.
- Apply the repository's configuration-only exception: add no source-text regression tests; validate with existing parsers, linters, build tools, and diff checks.
- Prefix every shell command with `rtk`.

---

### Task 1: Consolidate and cache iOS CI

**Files:**
- Create: `docs/superpowers/specs/2026-08-19-swift-ci-speed-design.md`
- Create: `docs/superpowers/plans/2026-08-19-swift-ci-speed.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/codeql.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `scripts/validate-app-store-metadata.sh`

**Interfaces:**
- Consumes: existing `changes` outputs and stable required-build job name.
- Produces: one iOS test/build path per PR, optional metadata-only job, explicit SwiftPM source cache directory, and timing summaries.

- [ ] **Step 1: Remove redundant workflow triggers and jobs**

Remove the `pull_request.edited` trigger and its concurrency suffix. Delete the standalone Debug simulator `build-ios` job. Change `build-required` to depend on and report the existing `test` job while preserving its exact displayed name and path-based required/skipped logic.

- [ ] **Step 2: Consolidate metadata validation**

Restrict the standalone metadata job to metadata-only pull requests. Add a conditional metadata-validation step to the iOS test job for pushes and for metadata, workflow, or shared-board changes. Ensure no event that previously required metadata validation loses it.

- [ ] **Step 3: Reuse the hosted simulator and remove duplicate tests**

Delete explicit simulator creation, boot polling, output plumbing, and deletion. Set the XCTest destination to `platform=iOS Simulator,name=iPhone 17 Pro,OS=latest`. Enable parallel testing and cap it at two workers. Delete the second `BoardPackageStoreTests` invocation because the full suite already contains it.

- [ ] **Step 4: Add SwiftPM source caching and build timings**

Use pinned `actions/cache` v4 in macOS jobs that resolve the iOS project's Swift packages. Cache a runner-temporary cloned-source-packages directory using OS, architecture, and `HangTen.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`. Pass the directory through `-clonedSourcePackagesDirPath`, including via optional `SWIFT_PACKAGE_CACHE_PATH` handling in `scripts/validate-app-store-metadata.sh`. Add `-showBuildTimingSummary` to optimized Xcode build/test invocations and disable the compiler index store only for normal CI compilation, not CodeQL tracing.

- [ ] **Step 5: Validate and commit**

Run Ruby YAML parsing across `.github/workflows/*.yml`, `rtk bash -n scripts/validate-app-store-metadata.sh`, and targeted `rtk rg` checks proving the old edited trigger, explicit simulator lifecycle, standalone Debug build, and duplicate focused test command are absent while the stable gate remains. Review `rtk git diff --check`, then commit the task.

---

### Task 2: Optimize native Workbench macOS jobs

**Files:**
- Create: `Tools/HangboardWorkbench/macos/Package.resolved`
- Modify: `.github/workflows/hangboard-workbench-pr.yml`
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `.github/actions/build-hangboard-workbench/action.yml`

**Interfaces:**
- Consumes: the existing composite action and Workbench change filter.
- Produces: Ubuntu portable-test gates, deterministic native dependencies, Debug-mode native tests, and matching PR/release SwiftPM caches.

- [ ] **Step 1: Pin native Swift dependencies**

Run SwiftPM resolution for `Tools/HangboardWorkbench/macos` and add the resulting `Package.resolved`. Use it as the dependency hash input for native cache keys.

- [ ] **Step 2: Move portable tests to Ubuntu**

Keep the existing JavaScript check on Ubuntu and add a Python Workbench test job there with Python 3.12, pip caching, an isolated workspace-owned virtual environment, installation of `Tools/HangboardWorkbench[dev]`, and `pytest Tools/HangboardWorkbench/tests -q`. Make the macOS build depend on both portable checks. Remove the Python and Node test executions from the macOS composite action, retaining dependency installation required by packaging.

- [ ] **Step 3: Run native tests in proven Debug mode and cache SwiftPM artifacts**

Run the proven Debug-mode `swift test --package-path Tools/HangboardWorkbench/macos` command. Retain the existing native test coverage and Release app verification. Add pinned `actions/cache` v4 steps for `Tools/HangboardWorkbench/macos/.build` in both PR and release build jobs, keyed by OS, architecture, and the native `Package.resolved` hash; do not promise Release test/build product reuse.

- [ ] **Step 4: Validate and commit**

Run Ruby YAML parsing across `.github/workflows/*.yml`, `rtk swift package describe --package-path Tools/HangboardWorkbench/macos`, targeted `rtk rg` checks proving portable tests no longer execute in the macOS composite and that the Debug test command and Release build flags remain intentional, and `rtk git diff --check`. Commit the task.
