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

## Hardening follow-up: protected diagnostics and opening-screen boundary

### Scope and audit

The hardening review found one additional visible external-diagnostic path:
`openingBoardController.refresh()` returned repository diagnostics whose
messages were stored unchanged in `state.libraryDiagnostics`, passed through
`openingScreenState()`, and rendered by the source-neutral
`renderRepositoryDiagnostics()` aria-live warning. The controller remains
unchanged. All other focused-editor external message paths continue to use
`formatFocusedEditorError()` or `focusedEditorErrorMessage()`; geometry focus
continues to parse the original backend message before any display formatting.

Backend/data/API contracts, Stage 2/Stage 3 documents, CLI behavior,
save/autosave, approval, and history were not changed.

### Files and changes

- `Tools/HangboardWorkbench/editor-ui-model.js`
  - Protects filenames, slash-prefixed routes/URLs, camelCase fields, and
    snake_case fields with temporary spans before applying the existing
    human-language workflow translations, then restores every protected value
    exactly.
  - Adds `formatFocusedEditorDiagnostic()`, which returns a new diagnostic with
    only `message` formatted and preserves path, code, severity, hold ID,
    reason, and any other properties.
- `Tools/HangboardWorkbench/app.js`
  - Formats every opening repository diagnostic before assigning
    `state.libraryDiagnostics`, closing the remaining visible bypass at the app
    boundary without making the controller source-specific.
- `Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js`
  - Proves workflow prose is translated while `stage-2-regions.json`,
    `/promotion`, and `checkpointToken` remain exact.
  - Proves repository diagnostic metadata, hold ID, and reason remain exact
    while only its visible message changes.
- `Tools/HangboardWorkbench/tests/workbench_app.test.js`
  - Executes the real `refreshBoards()` body with a repository diagnostic and
    then renders it through the real controller renderer, proving Stage wording
    cannot reach the visible warning.

### TDD evidence

- RED, UI model: the new tests failed because the old formatter changed
  `checkpointToken`, `stage-2-regions.json`, and `/promotion`, and because
  `formatFocusedEditorDiagnostic` did not exist.
- RED, opening-screen behavior: after correcting the test harness to preserve
  the source function's `async` modifier, the renderer visibly received
  `Stage 2 region 17 failed validation: contour overlaps itself` unchanged.
- GREEN:
  `node --test Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js Tools/HangboardWorkbench/tests/workbench_app.test.js`
  — 21 passed, 0 failed.

### Verification

- Focused Node suite above — 21 passed, 0 failed.
- Full Node suite:
  `node --test Tools/HangboardWorkbench/tests/*.test.js`
  — 249 passed, 0 failed.
- Python Workbench suite in a fresh isolated uv environment:
  `python -m pytest Tools/HangboardWorkbench/tests -q`
  — 180 passed in 54.32 seconds.
- `git diff --check` — clean before report generation.

### Cleanup

The successful Python run used
`.context/pipeline-error-translation-hardening.8zKp8I`; its exact-path cleanup
trap removed the environment and the command verified it absent. An earlier
verification-harness attempt accidentally overlapped two pytest processes;
its exact temporary environment
`.context/pipeline-error-translation-hardening.6fM2ZR` was also removed before
the clean single-process rerun. No persistent `.venv` or `uv.lock` was
created, and shared `.context` resources were left untouched.

### Self-review and concerns

- Removing the opening diagnostic mapping makes the end-to-end visible-render
  test fail; removing any protected-span category makes the literal identifier
  test fail; changing or dropping diagnostic metadata makes the diagnostic
  equality test fail.
- The production diff is limited to the focused-editor app/UI-model boundary;
  `workbench-controller.js`, backend code, payloads, and documents are
  unchanged.
- No known functional concerns remain. Future technical identifier syntaxes
  outside filenames, routes/URLs, camelCase, and snake_case should receive a
  focused regression before expanding the protected-span recognizer.
