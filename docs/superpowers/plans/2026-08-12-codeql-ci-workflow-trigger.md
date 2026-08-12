# CodeQL CI Workflow Trigger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Schedule CodeQL when `.github/workflows/ci.yml` changes.

**Architecture:** Keep CodeQL's existing path-filtered workflow model. Add the CI workflow path symmetrically to its pull-request and main-branch push filters; CodeQL jobs and permissions remain unchanged.

**Tech Stack:** GitHub Actions YAML; Python with PyYAML for static validation.

## Global Constraints

- Modify only `.github/workflows/codeql.yml` for the functional change.
- Add `.github/workflows/ci.yml` exactly once under each existing `pull_request.paths` and `push.paths` list.
- Preserve all existing trigger paths, jobs, permissions, and schedules.

---

### Task 1: Cover CI workflow changes with CodeQL

**Files:**
- Modify: `.github/workflows/codeql.yml`

**Interfaces:**
- Consumes: GitHub Actions `on.pull_request.paths` and `on.push.paths` filters.
- Produces: CodeQL runs for pull requests and pushes that modify `.github/workflows/ci.yml`.

- [ ] **Step 1: Establish the failing regression check**

Run:

```bash
python3 - <<'PY'
import pathlib
import yaml

workflow = yaml.safe_load(pathlib.Path('.github/workflows/codeql.yml').read_text())
triggers = workflow[True]
for event in ('pull_request', 'push'):
    assert '.github/workflows/ci.yml' in triggers[event]['paths'], event
PY
```

Expected: assertion failure because the CI workflow path is absent.

- [ ] **Step 2: Add the CI workflow path to both filters**

Add this exact list item after `.github/workflows/codeql.yml` in both trigger lists:

```yaml
      - .github/workflows/ci.yml
```

- [ ] **Step 3: Verify the regression check passes**

Run the Step 1 Python command again. Expected: exit code 0.

- [ ] **Step 4: Verify scope and commit**

Run:

```bash
git diff --check
git diff -- .github/workflows/codeql.yml
```

Expected: no whitespace errors and exactly two added CI workflow path entries. Commit the functional change with:

```bash
git add .github/workflows/codeql.yml
git commit -m "ci: run CodeQL for CI workflow changes"
```
