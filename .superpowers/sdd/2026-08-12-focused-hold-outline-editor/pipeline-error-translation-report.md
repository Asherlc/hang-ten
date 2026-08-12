# Pipeline Error Translation Report

## Scope

Implemented the approved narrow UI-boundary follow-up. Backend error strings,
Python contracts, Stage 2/Stage 3 documents, APIs, save/autosave behavior,
geometry, history, and command-line workflows were not changed.

## Exact changes

- Added `formatFocusedEditorError(message, fallback)` to the existing
  dependency-free `editor-ui-model.js` browser/CommonJS model.
- The formatter keeps the original diagnostic content unless a focused-editor
  pipeline term needs translation. It maps Stage 2/Stage 3 region prefixes to
  `Hold <id>`, contour/region wording to outline/hold wording, and translates
  checkpoint, promotion, approval, and validation terms to saved-version,
  repository-update, outline-save, and outline-check language.
- Preserved concrete diagnostic details, including hold numbers, free-form
  reasons, field identifiers such as `displayPath`, command identifiers, and
  other backend-provided text.
- Routed all audited external-error sinks in `app.js` through the formatter:
  validation-list rendering, autosave, repository/runtime board selection,
  board creation, explicit save/approval, retry/revise/final-save mutations,
  active-job reconciliation/recovery, static-session load, and static save.
- Kept geometry-error parsing on the original backend message so its existing
  Stage 2/Stage 3 contract can still identify and focus the correct region;
  only the message stored/rendered by the editor is translated.
- Formatted opening-list transport errors at the app boundary as defense in
  depth. The controller and backend error objects remain unchanged.
- Added behavioral formatter tests for representative Stage 2 and Stage 3
  errors, additional pipeline terms, action-specific fallback behavior, and
  retention of identifiers/reasons.
- Added a focused app regression test that audits the known visible error
  functions for formatter use and rejects direct assignment of external
  `error.message`/`failure.message` to visible editor state. This is not a
  source-wide banned-word regex and does not block internal artifact names or
  backend contracts.

## TDD evidence

### RED: formatter behavior

Command:

```text
node --test Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js
```

Observed: 5 tests, 3 passed, 2 failed. Both new Stage 2/Stage 3 tests failed
with `TypeError: formatFocusedEditorError is not a function`, proving the new
behavior was absent.

### GREEN: formatter behavior

Same command after the minimal model implementation:

```text
7 tests, 7 passed, 0 failed
```

### RED: app boundary wiring

Command:

```text
node --test --test-name-pattern="focused editor error sinks" Tools/HangboardWorkbench/tests/workbench_app.test.js
```

Observed: 1 test, 1 failed because `renderValidation()` still assigned raw
`error.message` to visible text.

### GREEN: app boundary wiring

Same command after routing the audited sinks through the formatter:

```text
1 test, 1 passed, 0 failed
```

## Verification

- Focused Node tests:
  `node --test Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js Tools/HangboardWorkbench/tests/workbench_app.test.js Tools/HangboardWorkbench/tests/editor_ui.test.js`
  — 59 passed, 0 failed.
- Full Node suite:
  `node --test Tools/HangboardWorkbench/tests/*.test.js`
  — 246 passed, 0 failed.
- Python Workbench suite in a temporary isolated uv environment:
  `.context/shrewd-wolf.pipeline-error-tests.kPUeId/bin/python -m pytest Tools/HangboardWorkbench/tests -q`
  — 180 passed in 55.82 seconds.
- `git diff --check` — clean.

The first isolated Python attempt installed only pytest and stopped during
collection because NumPy was absent. That exact environment
`.context/shrewd-wolf.pipeline-error-tests.Q3jjCh` was deleted and verified
absent. The successful rerun installed the declared
`Tools/HangboardPipeline[dev]` dependencies into a fresh isolated environment.

## Cleanup

- The exit trap deleted and verified removal of both exact temporary uv
  environments named above.
- No persistent project virtual environment or `uv.lock` was created.
- Existing shared `.context` resources were left untouched.

## Self-review

- Confirmed only the four intended JavaScript/test files and this report are
  changed.
- Confirmed no Python/backend files or data-contract strings were modified.
- Confirmed the formatter passes unknown diagnostic text through rather than
  replacing it with a generic error; fallback text is used only for an empty or
  non-string message.
- Confirmed representative translated output contains none of the prohibited
  focused-editor words while retaining the hold ID and specific reason.
- Confirmed raw messages are still supplied to existing geometry-error parsing,
  so region focus behavior is preserved.
- Mutation check: removing the formatter export fails the behavioral tests;
  bypassing the formatter at an audited UI sink fails the app-boundary test;
  dropping the ID/reason or leaving a prohibited term fails the literal output
  and retention assertions.

## Concerns

The translation is intentionally lexical and narrow. A future backend error
that introduces a new pipeline synonym will pass through unchanged until that
term is added to the focused formatter and its behavioral table. Existing
diagnostic details are otherwise preserved verbatim.
