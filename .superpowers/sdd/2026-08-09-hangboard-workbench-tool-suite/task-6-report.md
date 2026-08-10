# Task 6 report

## Coverage and documentation

- Corrected the canonical-promotion E2E fixture so its temporary repository
  copies the real `scripts/export-plan-library.sh`, `ExportPlanLibrary.swift`,
  and every HangTen Swift source compiled by that script. It no longer stubs a
  successful plan-library validation.
- The E2E result now requires package-readiness and hold-ID parity to pass. In
  this checkout its real plan-library check fails at the known
  `WorkoutStep.fingerConfiguration` incompatibility in
  `WorkoutStepNormalization.swift:69`; the test asserts that failure's source
  excerpt. If the real script succeeds in another environment, the same test
  instead requires the overall report and plan-library check to pass.
- Added an actual temporary-checkout flow for canonical Compact II:
  open → inspect its active revision → preview the four grouped native targets
  with a token → save locally → validate. The test asserts that promotion has
  no commit or remote side effect.
- Added a dirty-target conflict test that proves every target remains at its
  pre-existing content and no staged promotion directory is left behind.
- Added HTTP and browser boundary checks for missing preview tokens, local-only
  save, and caller-owned simulator handoff.
- Documented the single-board Onboard / Inspect / Promote to iOS / Validate
  workflow, grouped-diff review, conflict/no-write behavior, local-save
  boundary, and explicit simulator handoff in both operator READMEs and the
  simulator-validation guide.

## Verification commands and results

- `rtk .context/hangboard-suite-venv/bin/python -m pytest Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests -q`
  completed with an empty `.pytest_cache/v/cache/lastfailed` file. The focused
  rerun below also completed with no failures.
- `rtk .context/hangboard-suite-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py Tools/hold-highlight-editor/tests/test_server.py -q`
  passed: `129` tests, `0` failures, with `28` pre-existing Pillow deprecation
  warnings from `generic_stage2.py` about the deprecated
  `Image.fromarray(..., mode="I;16")` parameter.
- `rtk node --test Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/workbench_client.test.js Tools/hold-highlight-editor/tests/promotion_view.test.js Tools/hold-highlight-editor/tests/validation_view.test.js`
  passed: `39` tests, `0` failures.
- `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`
  ran all Node tests: `153` passed and `10` failed. The failures are the
  pre-existing assertions in `tests/editor_ui.test.js` that require the old
  Hold Editor title/static-mode wording; they conflict with the already
  committed Hangboard Workbench suite shell and do not involve Task 6 files.
- `rtk scripts/export-plan-library.sh --check` failed before validation because
  `HangTen/Models/WorkoutStepNormalization.swift:69` references the absent
  `WorkoutStep.fingerConfiguration` member and passes an unsupported argument.
  The same baseline incompatibility prevented the main-derived clean-worktree
  check; no unrelated Swift files were changed.
- Local server verification used
  `rtk .context/hangboard-suite-venv/bin/python Tools/hold-highlight-editor/server.py --repository-root /Users/asherlc/src/hang-ten/.worktrees/hangboard-workbench-tool-suite --workspace-root /Users/asherlc/src/hang-ten/.worktrees/hangboard-workbench-tool-suite/.context/hangboard-workbench-suite-verification`.
  It opened `metolius-wood-grips-compact-ii` as `board-0001`/
  `revision-0001`, produced the expected four-file promotion preview and a
  preview token without saving, and returned package-readiness and hold-ID
  parity as passed. Its plan-library check failed only for the same baseline
  Swift incompatibility. No simulator lifecycle command was run: browser
  handoff requires a caller-supplied owned UUID and never uses `booted`.

## Resource cleanup

- The main-derived temporary worktree
  `/Users/asherlc/src/hang-ten/.worktrees/hangboard-workbench-task-6-main-20260809`
  was deleted after its unrelated merge conflict and baseline check failure.
- The exact server process was stopped and its owned
  `.context/hangboard-workbench-suite-verification` workspace was deleted and
  verified absent.

## Commit

- `743f13ac8c89474ac080c673e7e0a63fad871b38`
  (`test: verify hangboard workbench tool suite end to end`)

## Final-review fixes

- Suite promotion and validation results now require both the active board ID
  and revision ID; the already context-scoped controllers remain unchanged.
- Both promotion-profile entry points reject `NaN`, positive infinity, and
  negative infinity aspect ratios while preserving the existing schema,
  identity, and token guards.
- Validation now runs deterministic semantic-routine resolution after hold-ID
  parity. It derives semantic groups with the approved Stage 2–4 artifacts and
  `ios_promotion` helpers, fails closed before the plan-library check, and
  requires every resolved hold ID to be an approved Stage 4 hold ID.
- The release workflow retains pull-request and manual build coverage, removes
  the automatic `push` trigger, and only permits publication on an explicit
  `workflow_dispatch` event.

Verification: focused Python (`26 passed`), focused Node (`13 passed`), and
workflow configuration (`7 passed`) suites all passed. The real
`scripts/export-plan-library.sh --check` remains blocked by the pre-existing
`WorkoutStep.fingerConfiguration` Swift incompatibility; no unrelated Swift
files were changed. The broad legacy Node suite likewise retains ten existing
Hold Editor wording failures unrelated to this final-fix scope.
