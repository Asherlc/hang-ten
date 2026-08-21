# Source-only Hangboard Workbench Bundling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development with a fresh subagent for every implementation task and review checkpoints after each task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the Workbench browser bundle only in build workspaces, never commit it, while preserving server and macOS package behavior.

**Architecture:** `app.js` remains the server and PyInstaller input path, but becomes an ignored artifact produced by `npm run check:bundle`. Every isolated CI job that runs Python static-asset tests or creates a macOS runtime builds it first. The packaged runtime still embeds `/app.js`; only its source-control ownership changes.

**Tech Stack:** npm/esbuild, TypeScript/React, Python/pytest, GitHub Actions, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-08-20-source-only-workbench-bundling-design.md`

## Global Constraints

- `Tools/HangboardWorkbench/app.js` must not be tracked by Git and must be ignored at that exact path.
- Keep the public `/app.js` route and current packaged static asset manifest unchanged.
- Never invoke npm dynamically from the Python HTTP server.
- Build the UI explicitly before each independent Python test or macOS packaging workspace that needs static assets.
- CI/release automation must not commit or push generated browser artifacts.

---

### Task 1: Make the browser bundle a local build artifact

**Files:**
- Modify: `.gitignore`
- Delete: `Tools/HangboardWorkbench/app.js`
- Modify: `Tools/HangboardWorkbench/package.json`
- Modify: `Tools/HangboardWorkbench/README.md`
- Modify: `Tools/HangboardWorkbench/tests/test_workbench_packaging.py`

**Interfaces:**
- Consumes: `npm run build`, which writes `Tools/HangboardWorkbench/app.js`.
- Produces: `npm run check:bundle`, a successful source-build verification with no Git-diff assertion; a generated ignored `app.js` that `workbench_assets.STATIC_ASSETS` and PyInstaller can continue to consume.

- [ ] **Step 1: Write the failing source-ownership regression test**

  Add a test to `test_workbench_packaging.py` that invokes Git from
  `REPOSITORY_ROOT` and proves the bundle is no longer in the index while
  `.gitignore` contains the exact repository-relative path:

  ```python
  def test_browser_bundle_is_an_ignored_build_artifact() -> None:
      tracked = subprocess.run(
          ["git", "ls-files", "--error-unmatch", "Tools/HangboardWorkbench/app.js"],
          cwd=REPOSITORY_ROOT,
          capture_output=True,
          text=True,
          check=False,
      )
      assert tracked.returncode != 0
      assert "/Tools/HangboardWorkbench/app.js" in (
          REPOSITORY_ROOT / ".gitignore"
      ).read_text(encoding="utf-8")
  ```

  Import `subprocess` at the top of the test module. This test must only check
  source-control ownership; it must not assert that a locally generated bundle
  is absent.

- [ ] **Step 2: Run the regression test and observe the expected failure**

  Run:

  ```bash
  rtk pytest Tools/HangboardWorkbench/tests/test_workbench_packaging.py::test_browser_bundle_is_an_ignored_build_artifact -q
  ```

  Expected: FAIL because `app.js` is currently tracked and not ignored.

- [ ] **Step 3: Apply the minimal source-only contract**

  - Add `/Tools/HangboardWorkbench/app.js` to the root `.gitignore` near the
    other Workbench build outputs.
  - Remove the tracked generated `app.js` file with
    `git rm Tools/HangboardWorkbench/app.js` (do not replace it with a
    hand-authored stub).
  - Change `check:bundle` in `package.json` to `npm run build`; remove only the
    `git diff --exit-code -- app.js` assertion.
  - Update the README verification command so `npm run check:bundle` appears
    before the Python suite and explain that local server/package operations
    need the generated UI bundle.

- [ ] **Step 4: Verify the source-only contract**

  Run:

  ```bash
  rtk npm run --prefix Tools/HangboardWorkbench check:bundle
  rtk pytest Tools/HangboardWorkbench/tests/test_workbench_packaging.py -q
  rtk git status --short
  ```

  Expected: the new regression test passes, `app.js` is regenerated but absent
  from `git status` because it is ignored, and the package test suite passes.

- [ ] **Step 5: Commit the task**

  ```bash
  rtk git add .gitignore Tools/HangboardWorkbench/package.json Tools/HangboardWorkbench/README.md Tools/HangboardWorkbench/tests/test_workbench_packaging.py
  rtk git commit -m "Stop tracking Workbench browser bundle"
  ```

### Task 2: Build the ignored bundle before Python CI tests

**Files:**
- Modify: `.github/workflows/hangboard-workbench-pr.yml`
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py`

**Interfaces:**
- Consumes: Task 1's `npm run check:bundle` command.
- Produces: every independent `test-python` job has Node 22.14.0, installs the
  lockfile-resolved dependencies, and creates `app.js` before pytest starts.

- [ ] **Step 1: Write failing workflow-contract tests**

  Add a pytest case that parses both workflow files with the existing
  `_workflow` helper. For each `test-python` job, assert that:

  ```python
  setup = _step(job, "Set up Node")
  assert setup["uses"] == "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020"
  assert setup["with"]["node-version"] == "22.14.0"
  bundle = _step(job, "Build generated Workbench bundle")
  assert bundle["working-directory"] == "Tools/HangboardWorkbench"
  assert "npm ci" in bundle["run"]
  assert "npm run check:bundle" in bundle["run"]
  ```

  Also assert `cache-dependency-path` names the Workbench `package-lock.json`.

- [ ] **Step 2: Run the new workflow test and observe the expected failure**

  Run:

  ```bash
  rtk pytest Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q -k generated_bundle
  ```

  Expected: FAIL because neither Python job has the Node/bundle preparation
  step.

- [ ] **Step 3: Prepare static assets in both Python jobs**

  In each `test-python` job, add the pinned `actions/setup-node` step with the
  same cache configuration used by that workflow's JavaScript job. Add a
  `Build generated Workbench bundle` step immediately before the Python setup:

  ```yaml
  - name: Build generated Workbench bundle
    working-directory: Tools/HangboardWorkbench
    run: |
      set -euo pipefail
      npm ci
      npm run check:bundle
  ```

  Do not change the Python virtualenv paths, test command, or release behavior.

- [ ] **Step 4: Verify workflow tests and syntax**

  Run:

  ```bash
  rtk pytest Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q
  rtk git diff --check
  ```

  Expected: workflow contract tests and existing shell-syntax coverage pass.

- [ ] **Step 5: Commit the task**

  ```bash
  rtk git add .github/workflows/hangboard-workbench-pr.yml .github/workflows/hangboard-workbench-release.yml Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py
  rtk git commit -m "Build Workbench bundle before Python CI tests"
  ```

### Task 3: Build the ignored bundle before native packaging

**Files:**
- Modify: `.github/actions/build-hangboard-workbench/action.yml`
- Modify: `Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py`

**Interfaces:**
- Consumes: Task 1's source-only `check:bundle` script.
- Produces: the composite native-build action creates `app.js` before
  `packaging/build.py` validates and embeds `workbench_assets.STATIC_ASSETS`.

- [ ] **Step 1: Write the failing composite-action contract test**

  Add a pytest test that uses the existing `_build_action()` helper and asserts
  the composite action contains a pinned Node setup step and a named bundle
  preparation step before `Build unsigned native app`:

  ```python
  steps = _build_action()["steps"]
  bundle_index = next(i for i, step in enumerate(steps) if step["name"] == "Build generated Workbench bundle")
  native_index = next(i for i, step in enumerate(steps) if step["name"] == "Build unsigned native app")
  assert bundle_index < native_index
  assert "npm ci" in steps[bundle_index]["run"]
  assert "npm run check:bundle" in steps[bundle_index]["run"]
  ```

  Assert the setup step pins Node 22.14.0 and uses the Workbench lockfile for
  cache invalidation.

- [ ] **Step 2: Run the test and observe the expected failure**

  Run:

  ```bash
  rtk pytest Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q -k native_bundle
  ```

  Expected: FAIL because the composite action currently has no Node or UI
  bundle preparation.

- [ ] **Step 3: Add native-build bundle preparation**

  In `.github/actions/build-hangboard-workbench/action.yml`, add the same
  pinned `actions/setup-node` configuration used by the workflows. Add this
  step after dependency setup and before any native build consumes static
  assets:

  ```yaml
  - name: Build generated Workbench bundle
    shell: bash
    working-directory: Tools/HangboardWorkbench
    run: |
      set -euo pipefail
      npm ci
      npm run check:bundle
  ```

  Leave PyInstaller's static asset manifest and `packaging/build.py` validation
  unchanged: they must continue to reject a missing generated asset.

- [ ] **Step 4: Verify release workflow coverage**

  Run:

  ```bash
  rtk npm run --prefix Tools/HangboardWorkbench check:bundle
  rtk pytest Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q
  rtk pytest Tools/HangboardWorkbench/tests -q
  rtk git diff --check
  ```

  Expected: the browser bundle is generated but ignored, all workflow and
  Workbench Python tests pass, and no generated file is staged.

- [ ] **Step 5: Commit and push the task**

  ```bash
  rtk git add .github/actions/build-hangboard-workbench/action.yml Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py
  rtk git commit -m "Build Workbench bundle for native packaging"
  rtk git push
  ```
