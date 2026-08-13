# Opening diagnostic callback fix

## Scope

Fixed only the focused editor's opening-diagnostic mapping callback. No backend, data, API, save, autosave, history, or geometry behavior changed.

## Root cause

`Array.prototype.map` calls its callback with `(value, index, array)`. Passing `formatFocusedEditorDiagnostic` directly therefore supplied the second diagnostic's index (`1`) as the formatter fallback. A malformed message was consequently stored and rendered as `1`.

## TDD evidence

1. Extended `Tools/HangboardWorkbench/tests/workbench_app.test.js` with two repository diagnostics: a valid translated diagnostic followed by one whose `message` is a non-string object.
2. Ran `rtk node --test Tools/HangboardWorkbench/tests/workbench_app.test.js` before the production change. The regression failed as intended with `actual: 1`, expected `Repository package is invalid`.
3. Changed only the `.map` callback in `Tools/HangboardWorkbench/app.js` to pass the diagnostic explicitly.
4. Re-ran the focused test: 12 passing, 0 failing.

## Behavioral coverage

The regression verifies that refresh stores the default fallback for the second malformed diagnostic and that repository-diagnostic rendering shows that fallback. It also retains the first diagnostic assertion, preserving user-facing translation. Existing identifiers (`path`, `holdId`, and `reason`) remain unchanged.

## Verification

- `rtk node --test Tools/HangboardWorkbench/tests/workbench_app.test.js` — 12 passing, 0 failing.
- `rtk node --test Tools/HangboardWorkbench/tests/*.test.js` — 249 passing, 0 failing.
- `rtk git diff --check` — clean.

## Self-review

- The wrapper prevents map's index and array arguments from reaching the formatter.
- The default fallback remains `Repository package is invalid`; no wording or translation rules changed.
- Only the requested callback, its behavioral regression, and this report changed.
