# Conditional CodeQL Merge Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require a stable CodeQL gate while running expensive language scans only for relevant changes.

**Architecture:** Run the CodeQL workflow on every protected-branch event. Detect changed language inputs in one job, always analyze GitHub Actions, conditionally analyze Swift/Python/JavaScript, and aggregate all results in one required `CodeQL gate`; retain GitHub's native CodeQL alert-threshold rule.

**Tech Stack:** GitHub Actions YAML, `dorny/paths-filter` v4.0.3 pinned at `ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d`, CodeQL Action v4.37.6 pinned at `5595ccaf912efad79be6eef63a5619ff05969be3`, pytest, GitHub repository rulesets API.

## Global Constraints

- Preserve the native CodeQL ruleset thresholds: `alerts_threshold: errors` and `security_alerts_threshold: high_or_higher`.
- The stable required status context is exactly `CodeQL gate` and is produced by GitHub Actions integration ID `15368`.
- Pull requests and pushes must not use workflow-level path filters.
- GitHub Actions analysis runs on every CodeQL workflow invocation.
- Swift, Python, and JavaScript/TypeScript analyses run only for matching changes, except schedules, manual dispatches, and CodeQL workflow changes force all source analyses.
- Every third-party or GitHub Action reference remains pinned to a full commit SHA.
- Failed or cancelled selected analyses must fail `CodeQL gate`; skipped source-language analyses must not fail it.

---

### Task 1: Implement and test the conditional CodeQL workflow

**Files:**
- Modify: `Tools/HangboardPipeline/tests/test_ci_workflow.py`
- Modify: `.github/workflows/codeql.yml`

**Interfaces:**
- Consumes: changed paths from pull requests, pushes, and merge groups; full-scan events from `schedule` and `workflow_dispatch`.
- Produces: detector outputs `swift`, `python`, and `javascript`; analysis jobs `analyze-actions`, `analyze-swift`, `analyze-python`, and `analyze-javascript`; required job name `CodeQL gate`.

- [ ] **Step 1: Add failing workflow-contract tests**

Extend `Tools/HangboardPipeline/tests/test_ci_workflow.py` with tests that read `.github/workflows/codeql.yml` and assert all of the following exact contracts:

```python
CODEQL_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "codeql.yml"


def test_codeql_workflow_uses_conditional_language_gate() -> None:
    workflow = CODEQL_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d" in workflow
    assert "languages: actions" in workflow
    assert "needs.changes.outputs.swift == 'true'" in workflow
    assert "needs.changes.outputs.python == 'true'" in workflow
    assert "needs.changes.outputs.javascript == 'true'" in workflow
    assert "name: CodeQL gate" in workflow
    assert "if: ${{ always() }}" in workflow
    assert "needs: [changes, analyze-actions, analyze-swift, analyze-python, analyze-javascript]" in workflow


def test_codeql_workflow_is_not_filtered_before_it_can_report_its_gate() -> None:
    workflow = CODEQL_WORKFLOW_PATH.read_text(encoding="utf-8")
    trigger_section = workflow.split("permissions:", 1)[0]

    assert "paths:" not in trigger_section
    assert "paths-ignore:" not in trigger_section
```

- [ ] **Step 2: Run the focused tests and observe the expected failure**

Run:

```bash
cd Tools/HangboardPipeline
python -m pytest tests/test_ci_workflow.py -q
```

Expected: the existing CI contract passes and the two new CodeQL contracts fail because the detector, `actions` analysis, and stable gate do not exist and trigger path filters are present.

- [ ] **Step 3: Implement change detection and conditional analyses**

Update `.github/workflows/codeql.yml` as follows:

- Remove `paths` from the `pull_request` and `push` triggers while preserving their `main` branch filters.
- Add `pull-requests: read` to workflow permissions.
- Add job `changes` on `ubuntu-latest`, expose `swift`, `python`, and `javascript` outputs, and use `dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d` with inline filters.
- Make each output true for `schedule` and `workflow_dispatch`, or when the matching filter output is `true`.
- Include `.github/workflows/codeql.yml` in all three filters so a CodeQL workflow edit exercises all source analyses.
- Add an unconditional Ubuntu `analyze-actions` job using CodeQL language `actions` and build mode `none`.
- Keep the existing Swift build steps in `analyze-swift`, add `needs: changes`, and condition it on the `swift` output.
- Replace the interpreted-language matrix with separate conditional `analyze-python` and `analyze-javascript` jobs using build mode `none`.
- Add a final job with `name: CodeQL gate`, `if: ${{ always() }}`, and the exact compact dependency list asserted by the test. Its shell step must require `changes` and `analyze-actions` to be `success`, accept `success` or `skipped` for each source analysis, and reject every other result including `failure` and `cancelled`.

Use these detector patterns:

```yaml
swift:
  - '**/*.swift'
  - '**/Package.swift'
  - '**/Package.resolved'
  - 'HangTen.xcodeproj/**'
  - '.github/workflows/codeql.yml'
python:
  - '**/*.py'
  - '**/pyproject.toml'
  - '**/requirements*.txt'
  - '**/poetry.lock'
  - '**/Pipfile.lock'
  - '.github/workflows/codeql.yml'
javascript:
  - '**/*.js'
  - '**/*.jsx'
  - '**/*.mjs'
  - '**/*.cjs'
  - '**/*.ts'
  - '**/*.tsx'
  - '**/package.json'
  - '**/package-lock.json'
  - '**/yarn.lock'
  - '**/pnpm-lock.yaml'
  - '.github/workflows/codeql.yml'
```

- [ ] **Step 4: Run focused and full Python verification**

Run:

```bash
cd Tools/HangboardPipeline
python -m pytest tests/test_ci_workflow.py -q
python -m pytest -q
```

Expected: all focused and full Python tests pass.

- [ ] **Step 5: Validate syntax, scope, commit, and push**

Run:

```bash
ruby -e 'require "yaml"; YAML.load_file(".github/workflows/codeql.yml"); puts "codeql.yml parses"'
git diff --check
git diff -- .github/workflows/codeql.yml Tools/HangboardPipeline/tests/test_ci_workflow.py
```

Expected: YAML parses, no whitespace errors, and the diff is limited to the workflow and its contract tests. Commit and push:

```bash
git add .github/workflows/codeql.yml Tools/HangboardPipeline/tests/test_ci_workflow.py
git commit -m "ci: gate CodeQL by changed language"
git push origin HEAD
```

### Task 2: Require the stable gate in the Main ruleset

**Files:**
- Create local backup only: `.context/${CONDUCTOR_WORKSPACE_NAME}-main-ruleset-before-codeql-gate.json`
- Modify external repository setting: GitHub ruleset `Main` (`20264425`)

**Interfaces:**
- Consumes: a successful `CodeQL gate` check for the pushed PR head.
- Produces: the existing native CodeQL rule plus required status context `CodeQL gate` from integration `15368`.

- [ ] **Step 1: Wait for and verify the live gate**

Run `gh pr checks 115` until `CodeQL gate` completes successfully for the current `HEAD`. Stop without changing repository settings if the gate fails, is cancelled, or does not belong to the current PR head SHA.

- [ ] **Step 2: Back up and update the exact ruleset**

Fetch ruleset `20264425` into the workspace-owned `.context` backup path. Build a PUT body preserving `name`, `target`, `enforcement`, `bypass_actors`, `conditions`, and every existing rule. In the existing `required_status_checks` rule, append this entry only when absent:

```json
{"context":"CodeQL gate","integration_id":15368}
```

Keep the existing `code_scanning` rule and its thresholds unchanged. Apply the body with:

```bash
gh api --method PUT repos/Asherlc/hang-ten/rulesets/20264425 --input <update-body-path>
```

- [ ] **Step 3: Read back and verify repository policy**

Fetch the ruleset again and assert:

- enforcement is `active`;
- required checks are `Build (Debug simulator)`, `Test (iOS Simulator)`, and `CodeQL gate`, each with integration ID `15368`;
- the CodeQL rule still has `alerts_threshold: errors` and `security_alerts_threshold: high_or_higher`;
- no other rule changed relative to the backup.

Record the API response and verification in the task report. Do not create a commit for the repository-settings-only task.
