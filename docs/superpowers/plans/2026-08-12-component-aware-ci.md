# Component-Aware CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run only the CI checks a pull request can affect, while forcing complete validation for `main` pushes and merge-queue entries.

**Architecture:** Put all component ownership globs in `.github/ci-paths.yml`; a lightweight `dorny/paths-filter` job exposes its Boolean outputs to workflow jobs. The primary CI workflow gates its existing jobs, while the Workbench release workflow uses small PR-only Node/Python/native jobs and retains its current full unsigned-app/release path for `main` and manual releases.

**Tech Stack:** GitHub Actions YAML, `dorny/paths-filter` pinned at `ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d`, Python `pytest`, existing Ruby YAML parser, Node built-in test runner.

## Global Constraints

- Editor-only pull requests run Workbench Node tests and skip Python and iOS/Xcode work.
- Python-only pull requests skip iOS/Xcode unless a declared shared board/export path changes.
- iOS and shared board/export changes run the iOS build and simulator suite.
- Workflow/taxonomy edits run the full relevant pull-request suite.
- `push` to `main`, `merge_group`, and Workbench `workflow_dispatch` always run complete validation regardless of filters.
- Preserve current release-artifact, signing, notarization, App Store release, Stage 2/3 data, and local-save behavior.
- Use only Boolean `paths-filter` outputs in `if:` expressions; never interpolate changed-file lists into shell commands.
- Keep existing required main-CI job names stable; a non-applicable job must be visibly skipped, not removed by a workflow-level path trigger.
- Every commit is pushed to `origin simplify-board-editor`.

---

### Task 1: Add the shared CI path taxonomy and configuration contract tests

**Files:**
- Create: `.github/ci-paths.yml`
- Create: `Tools/HangboardPipeline/tests/test_ci_path_taxonomy.py`
- Modify: `Tools/HangboardPipeline/tests/test_ci_workflow.py`

**Interfaces:**
- Produces: `dorny/paths-filter` YAML filters named `ios`, `python`, `workbench_web`, `workbench_native`, `shared_board_content`, `metadata`, and `workflow`.
- Consumed by: the `changes` jobs added to both GitHub workflows in Tasks 2 and 3.
- Test interface: `load_yaml(path: Path) -> dict[str, object]`, implemented with the repository’s existing `ruby -ryaml -rjson` approach so no Python YAML dependency is introduced.

- [ ] **Step 1: Write the failing taxonomy tests**

Create `test_ci_path_taxonomy.py` with a Ruby-backed YAML loader and explicit ownership assertions. Keep the test structural: inspect the filter pattern arrays rather than attempting to reimplement picomatch in Python.

```python
def test_taxonomy_has_each_required_component_filter() -> None:
    filters = load_yaml(PATHS_PATH)
    assert set(filters) == {
        "ios", "python", "workbench_web", "workbench_native",
        "shared_board_content", "metadata", "workflow",
    }

def test_taxonomy_assigns_editor_python_ios_and_shared_paths_conservatively() -> None:
    filters = load_yaml(PATHS_PATH)
    assert "Tools/HangboardWorkbench/*.js" in filters["workbench_web"]
    assert "Tools/HangboardPipeline/**" in filters["python"]
    assert "HangTen/**" in filters["ios"]
    assert "Hangboards/**" in filters["shared_board_content"]
    assert "scripts/export-board-library.py" in filters["shared_board_content"]
    assert ".github/workflows/**" in filters["workflow"]
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest Tools/HangboardPipeline/tests/test_ci_path_taxonomy.py -q
```

Expected: FAIL because the taxonomy file does not exist.

- [ ] **Step 3: Create the taxonomy**

Create `.github/ci-paths.yml` using this filter shape. Include every listed path; where a category needs extra paths already established in a workflow, add those exact paths rather than weakening an existing category.

```yaml
ios:
  - 'HangTen/**'
  - 'HangTenTests/**'
  - 'HangTen.xcodeproj/**'
  - '.github/ExportOptions.plist'
python:
  - 'Tools/HangboardPipeline/**'
  - 'Tools/HangboardWorkbench/**/*.py'
  - 'Tools/HangboardWorkbench/tests/**/*.py'
workbench_web:
  - 'Tools/HangboardWorkbench/**/*.html'
  - 'Tools/HangboardWorkbench/**/*.css'
  - 'Tools/HangboardWorkbench/**/*.js'
  - 'Tools/HangboardWorkbench/tests/**/*.test.js'
workbench_native:
  - 'Tools/HangboardWorkbench/macos/**'
  - 'Tools/HangboardWorkbench/packaging/**'
shared_board_content:
  - 'Hangboards/**'
  - 'Tools/HangboardPipeline/boards/**'
  - 'HangTen/Resources/BoardLibrary.json'
  - 'scripts/export-board-library.py'
  - 'scripts/export-board-catalog.py'
  - 'docs/hangboard-generative-catalog/**'
metadata:
  - 'metadata/**'
  - 'scripts/validate-app-store-metadata.sh'
workflow:
  - '.github/workflows/**'
  - '.github/ci-paths.yml'
  - '.github/actions/**'
  - 'Tools/HangboardPipeline/pyproject.toml'
```

- [ ] **Step 4: Run the taxonomy tests**

Run the Step 2 command again. Expected: PASS.

- [ ] **Step 5: Commit and push**

```bash
git add .github/ci-paths.yml Tools/HangboardPipeline/tests/test_ci_path_taxonomy.py Tools/HangboardPipeline/tests/test_ci_workflow.py
git commit -m "test: define component-aware CI paths"
git push origin simplify-board-editor
```

### Task 2: Gate existing main CI jobs from the shared taxonomy

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `Tools/HangboardPipeline/tests/test_ci_workflow.py`

**Interfaces:**
- Consumes: `.github/ci-paths.yml` from Task 1.
- Produces: `changes` job outputs named after every taxonomy filter, and conditions on the existing `metadata`, `python`, `build`, `build-release-device`, and `test` jobs.
- Preserves: existing job IDs/names, commands, artifacts, simulator lifecycle, and `release.yml` dependency on a successful CI workflow.

- [ ] **Step 1: Write failing workflow-contract tests**

Extend the Ruby YAML loader in `test_ci_workflow.py` and assert the actual configuration contract:

```python
def test_ci_classifies_changes_with_the_pinned_shared_taxonomy() -> None:
    workflow = load_yaml(CI_WORKFLOW_PATH)
    changes = workflow["jobs"]["changes"]
    assert changes["runs-on"] == "ubuntu-latest"
    assert changes["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert changes["outputs"]["ios"] == "${{ steps.filter.outputs.ios }}"
    filter_step = next(step for step in changes["steps"] if step["id"] == "filter")
    assert filter_step["uses"] == "dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d"
    assert filter_step["with"]["filters"] == ".github/ci-paths.yml"

def test_ci_keeps_existing_jobs_but_gates_pr_work_by_component() -> None:
    jobs = load_yaml(CI_WORKFLOW_PATH)["jobs"]
    assert jobs["python"]["needs"] == ["changes"]
    assert "github.event_name != 'pull_request'" in jobs["python"]["if"]
    assert "needs.changes.outputs.python == 'true'" in jobs["python"]["if"]
    assert "needs.changes.outputs.ios == 'true'" in jobs["build"]["if"]
    assert "needs.changes.outputs.shared_board_content == 'true'" in jobs["test"]["if"]
```

Add an assertion that `merge_group` remains a trigger and conditions use the
non-PR branch as their force-full path.

- [ ] **Step 2: Run the focused CI workflow tests to verify they fail**

Run:

```bash
python -m pytest Tools/HangboardPipeline/tests/test_ci_workflow.py -q
```

Expected: FAIL because `changes`, outputs, and conditions do not exist.

- [ ] **Step 3: Add `changes` and job conditions to `ci.yml`**

1. Keep workflow-level `permissions: { contents: read }`.
2. Insert `changes` before `metadata`:

```yaml
  changes:
    name: Classify changed components
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
    outputs:
      ios: ${{ steps.filter.outputs.ios }}
      python: ${{ steps.filter.outputs.python }}
      shared_board_content: ${{ steps.filter.outputs.shared_board_content }}
      metadata: ${{ steps.filter.outputs.metadata }}
      workflow: ${{ steps.filter.outputs.workflow }}
    steps:
      - id: filter
        uses: dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d
        with:
          filters: .github/ci-paths.yml
```

3. Give `metadata`, `python`, `build`, and `test` `needs: changes` and an
`if: >-` condition that starts with
`github.event_name != 'pull_request' ||`. Add each job’s relevant Boolean
filters from the design. This forces all jobs for `push` and `merge_group`.
4. Keep `build-release-device` push-only; give it `needs: changes` but retain
its existing non-PR condition so it still runs on every main push.
5. Do not change checkout pins, Xcode commands, Python commands, artifact
uploads, simulator ownership/cleanup, or job display names.

- [ ] **Step 4: Run configuration and syntax verification**

Run:

```bash
python -m pytest Tools/HangboardPipeline/tests/test_ci_path_taxonomy.py Tools/HangboardPipeline/tests/test_ci_workflow.py -q
ruby -ryaml -e 'YAML.load_file(".github/workflows/ci.yml")'
```

Expected: PASS with valid YAML and configuration assertions.

- [ ] **Step 5: Commit and push**

```bash
git add .github/workflows/ci.yml Tools/HangboardPipeline/tests/test_ci_workflow.py
git commit -m "ci: gate iOS checks by changed component"
git push origin simplify-board-editor
```

### Task 3: Separate Workbench pull-request checks from full release builds

**Files:**
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py`
- Modify: `Tools/HangboardPipeline/tests/test_ci_path_taxonomy.py`

**Interfaces:**
- Consumes: the shared taxonomy filters from Task 1 and the `changes` job convention from Task 2.
- Produces: PR-only `workbench-node`, `workbench-python`, and `workbench-native` jobs, plus the existing full `build` job restricted to `push`/`workflow_dispatch` on `main`.
- Preserves: the release job’s `needs: build`, artifact names, signing/notarization behavior, release criteria, and current full `build` commands for non-PR events.

- [ ] **Step 1: Write failing release-workflow contract tests**

Extend `test_workbench_release_workflow.py` using its existing `_workflow()` Ruby parser:

```python
def test_pr_workbench_jobs_are_component_gated_but_main_build_stays_full():
    jobs = _workflow()["jobs"]
    assert jobs["changes"]["outputs"]["workbench_web"] == "${{ steps.filter.outputs.workbench_web }}"
    assert "needs.changes.outputs.workbench_web == 'true'" in jobs["workbench-node"]["if"]
    assert "needs.changes.outputs.python == 'true'" in jobs["workbench-python"]["if"]
    assert "needs.changes.outputs.workbench_native == 'true'" in jobs["workbench-native"]["if"]
    assert jobs["build"]["if"] == "github.event_name != 'pull_request'"
    assert jobs["release"]["needs"] == "build"
```

Also assert `workbench-node` runs the Node suite on `ubuntu-latest`,
`workbench-python` installs `Tools/HangboardPipeline[dev]` and runs the Python
Workbench/Pipeline tests on `ubuntu-latest`, and `workbench-native` runs
`swift test --package-path Tools/HangboardWorkbench/macos` on macOS.

- [ ] **Step 2: Run the focused release-workflow test to verify it fails**

Run:

```bash
python -m pytest Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py -q
```

Expected: FAIL because the PR component jobs and gating do not exist.

- [ ] **Step 3: Refactor the Workbench workflow**

1. Add the same Ubuntu `changes` job, with `contents: read`,
`pull-requests: read`, the immutable paths-filter pin, and outputs for
`python`, `workbench_web`, `workbench_native`, `shared_board_content`, and
`workflow`.
2. Add `workbench-node` with `needs: changes`, `runs-on: ubuntu-latest`, and
a PR-only condition requiring `workbench_web`, `shared_board_content`, or
`workflow`. Its only test command is:

```yaml
run: node --test Tools/HangboardWorkbench/tests/workbench*.test.js
```

3. Add `workbench-python` with `needs: changes`, `runs-on: ubuntu-latest`,
and a PR-only condition requiring `python`, `shared_board_content`, or
`workflow`. Reuse the current Python 3.12 setup/install approach and run:

```yaml
run: python -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
```

4. Add `workbench-native` with `needs: changes`, `runs-on: macos-latest`,
and a PR-only condition requiring `workbench_native` or `workflow`. Run the
existing SwiftPM native shell test command.
5. Keep the existing `build` body intact, but add:

```yaml
needs: changes
if: github.event_name != 'pull_request'
```

This retains complete unsigned-app assembly and smoke validation on every main
push and manual dispatch, while browser-only PRs allocate no macOS release
runner.
6. Keep `release` depending only on `build`; it already has the main-only
release condition. Do not alter signing secrets, artifact names, or publishing
commands.

- [ ] **Step 4: Run workflow contract and shell-syntax tests**

Run:

```bash
python -m pytest Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py Tools/HangboardPipeline/tests/test_ci_path_taxonomy.py -q
```

Expected: PASS, including existing bash syntax checks for every workflow step.

- [ ] **Step 5: Run focused product suites**

Run:

```bash
node --test Tools/HangboardWorkbench/tests/workbench*.test.js
python -m pytest Tools/HangboardPipeline/tests Tools/HangboardWorkbench/tests -q
```

Expected: PASS. If the local Python environment lacks dependencies, use the
existing isolated `.context`/`uv` procedure and record the exact command and
cleanup evidence; do not add a committed virtual environment or lockfile.

- [ ] **Step 6: Commit and push**

```bash
git add .github/workflows/hangboard-workbench-release.yml Tools/HangboardWorkbench/tests/test_workbench_release_workflow.py Tools/HangboardPipeline/tests/test_ci_path_taxonomy.py
git commit -m "ci: split workbench PR checks by component"
git push origin simplify-board-editor
```

## Plan Self-Review

### Spec coverage

- One taxonomy and immutable filter action pin: Task 1.
- Main CI stable job IDs, PR gating, and force-full main/merge queue: Task 2.
- Workbench browser-only PR avoids Python/native build; main releases stay full: Task 3.
- Python-only/iOS/shared/workflow change matrix and force-full event rules:
  Tasks 1–3 configuration tests.
- Runner, simulator, artifact, signing, and release behavior preservation:
  Tasks 2–3 exact preservation constraints and existing workflow tests.

### Placeholder and consistency check

Every taxonomy name used in Tasks 2–3 is defined in Task 1. The action pin,
workflow paths, job IDs, commands, and testing commands are explicit. No
requirements are deferred beyond the three implementation tasks.
