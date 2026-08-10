# Task 2 Report

Date: 2026-08-10

Status: DONE

## Summary

Took over Task 2 in `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit` and preserved the existing uncommitted Task 2 work. The stalled implementer had already added the new linting and acceptance production modules plus the expected fixture and CLI/test updates, but had not written the report or committed the task.

I audited the existing implementation against the Task 2 brief instead of discarding it:

- `review_lint.py` defines `LintIssue`, `LintReport`, `lint_review`, `write_lint_report`, stable issue ordering, canonical correction-entry reconciliation, confined Stage 2 writes, and atomic JSON persistence through a temporary file plus `Path.replace`.
- `review_acceptance.py` defines `AcceptanceRecord`, `write_acceptance`, `validate_acceptance`, UTC timestamps, hash-bound source validation, accepted-vs-rejected behavior, and atomic persistence.
- `review_cli.py` exposes `lint --run PATH --json` and `accept --run PATH --decision accepted|rejected --reviewer NAME --notes TEXT`, writes lint reports on every lint run, and forces a current lint pass before accepted decisions.
- `tests/review_fixtures.py` routes acceptance fixture setup through public `write_acceptance`, not hand-written JSON.

No additional production-code edits were required during takeover because the required implementation was already present and the focused Task 2 suite was green when verified with the required worktree-local interpreter.

## Commands and outputs

### 1. Inspect takeover state

Command:

```bash
rtk git -C /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit status --short
```

Output:

```text
 M Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py
 M Tools/HangboardOnboarding/tests/review_fixtures.py
 M Tools/HangboardOnboarding/tests/test_review_cli.py
?? Tools/HangboardOnboarding/src/hangboard_vectorizer/review_acceptance.py
?? Tools/HangboardOnboarding/src/hangboard_vectorizer/review_lint.py
?? Tools/HangboardOnboarding/tests/test_review_acceptance.py
?? Tools/HangboardOnboarding/tests/test_review_lint.py
```

Interpretation: the expected Task 2 files were present as uncommitted local work at takeover time.

### 2. Focused Task 2 verification

Command:

```bash
rtk /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_lint.py /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_acceptance.py /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_cli.py -q
```

Output:

```text
..............                                                           [100%]
14 passed in 0.21s
```

Interpretation: the required focused Task 2 suite was already green in the worktree, so the red step described in the brief was no longer reproducible at takeover time.

## Requirement audit notes

- Generated Stage 1/2 artifacts remain inputs only; Task 2 writes only `lint-report.json` and `stage-2-review-acceptance.json` in the confined Stage 2 directory.
- Acceptance is hash-bound via `sha256_file` for present source artifacts and invalidates on edited-artifact drift.
- Acceptance fixture uses public `write_acceptance`.
- No Tasks 3–6 changes were introduced.
- No network or model calls were used in the implementation worktree.

## Concern

The brief expected missing production files and a red focused run, but by takeover time on 2026-08-10 the worktree already contained uncommitted `review_lint.py` and `review_acceptance.py`, and the focused Task 2 suite was already passing. I preserved and verified that work rather than rewriting it.

---

## Fix Round 1 — 2026-08-10

Status: DONE

### Reviewer findings addressed

1. Accepted decisions no longer reuse a stale passing lint report after `stage-2-human-corrections.json` changes. `write_acceptance(..., "accepted", ...)` now always runs `lint_review()` and rewrites `lint-report.json` from the public acceptance path before allowing an accepted decision.
2. `validate_acceptance()` now requires mandatory `stage1ImageSha256` and `baselineSha256` keys and rejects malformed hashes unless they are 64 lowercase hexadecimal characters.

### Files changed

- `Tools/HangboardOnboarding/tests/test_review_acceptance.py`
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_acceptance.py`

### TDD evidence

#### 1. Added regression tests first

Added acceptance regressions for:

- stale passing lint report after corrections drift
- missing `stage1ImageSha256`
- missing `baselineSha256`
- malformed `stage1ImageSha256`
- malformed `baselineSha256`

#### 2. Verified the new tests failed before implementation

Command:

```bash
rtk /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_acceptance.py -q
```

Output:

```text
..FFFFF                                                                  [100%]
=================================== FAILURES ===================================
_____ test_acceptance_rejects_stale_passing_lint_after_corrections_change ______

tmp_path = PosixPath('/private/var/folders/b4/95kqjtzd7zlc75ndbg2_svpr0000gp/T/pytest-of-asherlc/pytest-240/test_acceptance_rejects_stale_0')

    def test_acceptance_rejects_stale_passing_lint_after_corrections_change(
        tmp_path: Path,
    ) -> None:
        run = make_review_run_with_edit(tmp_path)
        review_run = discover_review_run(run)
        write_lint_report(review_run, lint_review(review_run))

        corrections_path = run / "stages/02/attempt-0001/stage-2-human-corrections.json"
        corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
        corrections["modified"][0]["notes"] = "stale-lint"
        corrections_path.write_text(
            json.dumps(corrections, sort_keys=True) + "\n", encoding="utf-8"
        )

>       with pytest.raises(ValueError, match="lint must pass before acceptance"):
E       Failed: DID NOT RAISE ValueError

tests/test_review_acceptance.py:56: Failed
_ test_validate_acceptance_requires_mandatory_source_hashes[stage1ImageSha256] _

tmp_path = PosixPath('/private/var/folders/b4/95kqjtzd7zlc75ndbg2_svpr0000gp/T/pytest-of-asherlc/pytest-240/test_validate_acceptance_requi0')
missing_key = 'stage1ImageSha256'

    @pytest.mark.parametrize("missing_key", ["stage1ImageSha256", "baselineSha256"])
    def test_validate_acceptance_requires_mandatory_source_hashes(
        tmp_path: Path, missing_key: str
    ) -> None:
        run = make_review_run_with_edit(tmp_path)
        acceptance_path = write_acceptance(
            discover_review_run(run), "accepted", "asher", "Reviewed all regions"
        )
        document = json.loads(acceptance_path.read_text(encoding="utf-8"))
        del document["source"][missing_key]
        acceptance_path.write_text(
            json.dumps(document, sort_keys=True) + "\n", encoding="utf-8"
        )

>       with pytest.raises(ValueError, match=missing_key):
E       Failed: DID NOT RAISE ValueError

tests/test_review_acceptance.py:74: Failed
__ test_validate_acceptance_requires_mandatory_source_hashes[baselineSha256] ___

tmp_path = PosixPath('/private/var/folders/b4/95kqjtzd7zlc75ndbg2_svpr0000gp/T/pytest-of-asherlc/pytest-240/test_validate_acceptance_requi1')
missing_key = 'baselineSha256'

    @pytest.mark.parametrize("missing_key", ["stage1ImageSha256", "baselineSha256"])
    def test_validate_acceptance_requires_mandatory_source_hashes(
        tmp_path: Path, missing_key: str
    ) -> None:
        run = make_review_run_with_edit(tmp_path)
        acceptance_path = write_acceptance(
            discover_review_run(run), "accepted", "asher", "Reviewed all regions"
        )
        document = json.loads(acceptance_path.read_text(encoding="utf-8"))
        del document["source"][missing_key]
        acceptance_path.write_text(
            json.dumps(document, sort_keys=True) + "\n", encoding="utf-8"
        )

>       with pytest.raises(ValueError, match=missing_key):
E       Failed: DID NOT RAISE ValueError

tests/test_review_acceptance.py:74: Failed
_ test_validate_acceptance_rejects_invalid_mandatory_hash_format[stage1ImageSha256] _

tmp_path = PosixPath('/private/var/folders/b4/95kqjtzd7zlc75ndbg2_svpr0000gp/T/pytest-of-asherlc/pytest-240/test_validate_acceptance_rejec1')
invalid_key = 'stage1ImageSha256'

    @pytest.mark.parametrize("invalid_key", ["stage1ImageSha256", "baselineSha256"])
    def test_validate_acceptance_rejects_invalid_mandatory_hash_format(
        tmp_path: Path, invalid_key: str
    ) -> None:
        run = make_review_run_with_edit(tmp_path)
        acceptance_path = write_acceptance(
            discover_review_run(run), "accepted", "asher", "Reviewed all regions"
        )
        document = json.loads(acceptance_path.read_text(encoding="utf-8"))
        document["source"][invalid_key] = "abc123"
        acceptance_path.write_text(
            json.dumps(document, sort_keys=True) + "\n", encoding="utf-8"
        )

>       with pytest.raises(ValueError, match=invalid_key):
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'stage1ImageSha256'
E         Actual message: 'stage 1 image hash changed'

tests/test_review_acceptance.py:92: AssertionError
_ test_validate_acceptance_rejects_invalid_mandatory_hash_format[baselineSha256] _

tmp_path = PosixPath('/private/var/folders/b4/95kqjtzd7zlc75ndbg2_svpr0000gp/T/pytest-of-asherlc/pytest-240/test_validate_acceptance_rejec2')
invalid_key = 'baselineSha256'

    @pytest.mark.parametrize("invalid_key", ["stage1ImageSha256", "baselineSha256"])
    def test_validate_acceptance_rejects_invalid_mandatory_hash_format(
        tmp_path: Path, invalid_key: str
    ) -> None:
        run = make_review_run_with_edit(tmp_path)
        acceptance_path = write_acceptance(
            discover_review_run(run), "accepted", "asher", "Reviewed all regions"
        )
        document = json.loads(acceptance_path.read_text(encoding="utf-8"))
        document["source"][invalid_key] = "abc123"
        acceptance_path.write_text(
            json.dumps(document, sort_keys=True) + "\n", encoding="utf-8"
        )

>       with pytest.raises(ValueError, match=invalid_key):
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'baselineSha256'
E         Actual message: 'baseline artifact hash changed'

tests/test_review_acceptance.py:92: AssertionError
=========================== short test summary info ============================
FAILED tests/test_review_acceptance.py::test_acceptance_rejects_stale_passing_lint_after_corrections_change
FAILED tests/test_review_acceptance.py::test_validate_acceptance_requires_mandatory_source_hashes[stage1ImageSha256]
FAILED tests/test_review_acceptance.py::test_validate_acceptance_requires_mandatory_source_hashes[baselineSha256]
FAILED tests/test_review_acceptance.py::test_validate_acceptance_rejects_invalid_mandatory_hash_format[stage1ImageSha256]
FAILED tests/test_review_acceptance.py::test_validate_acceptance_rejects_invalid_mandatory_hash_format[baselineSha256]
5 failed, 2 passed in 0.24s
```

#### 3. Implemented the minimal acceptance fix

Changes made:

- removed the stale lint-report cache reuse from the accepted decision path by making `_ensure_current_lint_pass()` always recompute lint and rewrite `lint-report.json`
- tightened hash validation so `_require_hash_match()` requires a present 64-character lowercase hexadecimal hash before comparing bytes
- added key-specific failures:
  - `missing required source hash: <key>`
  - `invalid source hash format: <key>`

#### 4. Re-ran the regression tests green

Command:

```bash
rtk /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_acceptance.py -q
```

Output:

```text
.......                                                                  [100%]
7 passed in 0.19s
```

#### 5. Re-ran the focused Task 2 suite green

Command:

```bash
rtk /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_lint.py /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_acceptance.py /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_cli.py -q
```

Output:

```text
...................                                                      [100%]
19 passed in 0.27s
```
