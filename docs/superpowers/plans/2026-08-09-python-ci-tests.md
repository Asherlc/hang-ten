# Python CI Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for every implementation task, with a fresh subagent and a review checkpoint before commit. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the existing Hangboard Onboarding pytest suite to the repository's required GitHub Actions CI workflow.

**Architecture:** Extend `.github/workflows/ci.yml` with one independent `python` job. A fresh implementation subagent performs the workflow change, followed by a separate review checkpoint before commit. The job uses Ubuntu, Python 3.11, the package's editable development install, and the full pytest suite; it uploads a JUnit report only when the test job fails.

**Tech Stack:** GitHub Actions, `actions/checkout` v4.2.2, `actions/setup-python` v5.6.0, `actions/upload-artifact` v4.6.2, Python 3.11, pytest.

## Global Constraints

- The Python package requires Python `>=3.11`.
- Install CI-only wheel-build prerequisites with `python -m pip install 'setuptools>=68' wheel` because an existing test invokes `pip wheel --no-build-isolation`.
- Install the package from `Tools/HangboardOnboarding` with `python -m pip install -e ".[dev]"`.
- Run tests from `Tools/HangboardOnboarding` with `python -m pytest -q --junitxml=pytest-results.xml`.
- Preserve the existing checkout and upload-artifact action pins already used in `.github/workflows/ci.yml`.
- Do not modify iOS jobs or unrelated working-tree files.

---

### Task 1: Add the Python test job to CI

**Files:**
- Modify: `.github/workflows/ci.yml` by adding a new top-level `python` job after `metadata`.
- Test: `.github/workflows/ci.yml` through YAML parsing and the package's full local pytest command.

**Interfaces:**
- Consumes: the existing `CI` workflow triggers and repository action pins.
- Produces: a required `python` job that installs and tests `Tools/HangboardOnboarding`.

- [ ] **Step 1: Record the existing workflow baseline**

Run:

```bash
git status --short
sed -n '1,230p' .github/workflows/ci.yml
```

Expected: only the plan/spec commits are present in this isolated worktree, and the workflow contains the existing `metadata`, `build`, and `test` jobs without a Python job.

- [ ] **Step 2: Add the Python job**

Add this job beneath `metadata` in `.github/workflows/ci.yml`:

```yaml
  python:
    name: Test (Python)
    runs-on: ubuntu-latest
    timeout-minutes: 15

    defaults:
      run:
        working-directory: Tools/HangboardOnboarding

    steps:
      # actions/checkout v4.2.2
      - name: Check out source
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          persist-credentials: false

      # actions/setup-python v5.6.0
      - name: Set up Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: '3.11'
          cache: pip
          cache-dependency-path: Tools/HangboardOnboarding/pyproject.toml

      - name: Install wheel-build prerequisites
        run: python -m pip install 'setuptools>=68' wheel

      - name: Install Python package and test dependencies
        run: python -m pip install -e ".[dev]"

      - name: Run pytest suite
        run: python -m pytest -q --junitxml=pytest-results.xml

      # actions/upload-artifact v4.6.2
      - name: Upload pytest report on failure
        if: failure()
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
        with:
          name: python-test-results-${{ github.run_id }}
          path: Tools/HangboardOnboarding/pytest-results.xml
          if-no-files-found: ignore
```

- [ ] **Step 3: Validate the workflow structure**

Run:

```bash
ruby -e 'require "yaml"; YAML.load_file(".github/workflows/ci.yml"); puts "ci.yml parses"'
git diff --check
```

Expected: the YAML parser exits 0 and `git diff --check` reports no whitespace errors.

- [ ] **Step 4: Run the complete Python test suite**

Run:

```bash
python3 -m venv .context/python-ci-test-venv
.context/python-ci-test-venv/bin/python -m pip install 'setuptools>=68' wheel
.context/python-ci-test-venv/bin/python -m pip install -e 'Tools/HangboardOnboarding[dev]'
.context/python-ci-test-venv/bin/python -m pytest -q --junitxml=.context/python-ci-pytest-results.xml
```

Expected: pytest exits 0 with zero failures and writes `.context/python-ci-pytest-results.xml`.

- [ ] **Step 5: Review the focused diff**

Run:

```bash
git diff -- .github/workflows/ci.yml
git status --short
```

Expected: only `.github/workflows/ci.yml` is modified for the implementation; the generated virtual environment and report remain under `.context` and are ignored.

- [ ] **Step 6: Commit the implementation**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run Python tests"
```
