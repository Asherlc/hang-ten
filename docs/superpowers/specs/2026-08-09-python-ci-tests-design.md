# Python Test CI Design

## Goal

Run the existing Hangboard Onboarding Python test suite as a required part of the repository's existing GitHub Actions `CI` workflow.

## Scope

The change covers only CI wiring for the existing Python package. It does not add new Python tests, coverage enforcement, linting, type checking, or a Python-version matrix.

## Design

Add a `python` job to `.github/workflows/ci.yml` with the following behavior:

1. Run on `ubuntu-latest`.
2. Check out the repository with the same pinned checkout action already used by the workflow.
3. Install Python 3.11 with the repository's pinned GitHub Action convention.
4. Enable pip caching, keyed by `Tools/HangboardOnboarding/pyproject.toml`.
5. From `Tools/HangboardOnboarding`, install the package and development extra with `python -m pip install -e ".[dev]"`.
6. From the same directory, run `python -m pytest -q --junitxml=pytest-results.xml`.
7. Upload `pytest-results.xml` as a diagnostic artifact when the job fails.

The job is independent of the macOS build and XCTest jobs, so Python failures are reported as their own required CI check without changing Apple-platform test behavior.

## Acceptance Criteria

- Pull requests, pushes to `main`, and merge queue runs execute the Python job through the existing `CI` workflow triggers.
- The job uses Python 3.11 and installs the package's declared development dependency set.
- The complete test suite under `Tools/HangboardOnboarding/tests` runs from the package directory.
- A failing test fails the job and preserves the JUnit report for diagnosis.
- Existing iOS CI jobs and unrelated files are unchanged.
