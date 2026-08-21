# Task 3 report — presentation-aware Workbench editing

## Status

Complete.

## Implementation

- `board_package.py`
  - Loads both schema v1 and schema v2 packages. V1 accepts the optional
    `presentation` field or synthesizes the implicit `primary` surface when it
    is omitted.
  - Validates ordered v2 presentation metadata, exact declared PNG assets,
    per-presentation aspect ratios, and each hold's presentation ownership.
  - Exposes a focused editor document for one selected presentation. Its canvas,
    regions, and region metadata all identify the same presentation.
  - Saves only the focused presentation's holds while preserving every
    unselected hold and presentation asset. New v2 holds receive the selected
    `presentationID`.
- `server.py` and `github_board_store.py`
  - Board responses list every presentation and its image URL, expose the
    selected presentation ID, and return only that presentation's regions.
  - `?presentationID=` selects both the board document and image route.
  - Local and GitHub-backed saves retain the selected presentation in the
    response and merge only its holds. Hosted presentation image reads and
    cache-safe package copies support all declared assets.
  - Board responses include the complete hold-ID inventory so a new hold on one
    surface cannot collide with an unselected surface's hold.
- React/TypeScript Workbench
  - Adds an accessible `Board surface` selector beside the canvas controls when
    more than one surface exists.
  - Surface changes atomically load the matching image and canvas, clear hold
    selection and guides, and display only focused regions.
  - Document cloning, client validation, save state, and new-hold creation
    preserve presentation ownership.
  - Surface switching refuses to discard dirty edits; the operator must save or
    undo the current surface before switching.

## Test-driven development

- RED (Python): new focused package/server tests failed because the v1-only
  loader rejected `assets/back.png` and schema v2 documents.
- GREEN (Python): focused v2 load, region filtering, server surface listing,
  image routing, local scoped save, and hosted scoped save tests pass.
- RED (TypeScript): the presentation protocol tests initially failed typecheck
  because board/document/region presentation fields and the selected-surface
  request signature did not exist.
- GREEN (TypeScript): the module and React tests pass with the surface selector,
  image/canvas switching, filtered regions, cleared selection/guides, and a new
  back-surface hold.
- Regression RED/GREEN: the React test found that `cloneEditorDocument` dropped
  `presentationID`; preserving it made the saved focused document pass.
- Regression RED/GREEN: the global-ID test failed because `nextHoldId` only saw
  focused regions; reserving the board's complete hold inventory prevents a
  hidden-surface collision.
- Compatibility RED/GREEN: a v1 package without the optional on-disk
  `presentation` object was rejected, then passed after synthesizing `primary`.

## Verification

- Python: `Tools/HangboardWorkbench/.venv/bin/python -m pytest Tools/HangboardWorkbench/tests -q --junitxml=.context/task3-pytest-final.xml`
  - JUnit result: 318 tests, 0 failures, 0 errors, 0 skipped.
- TypeScript/React: `npm test` in `Tools/HangboardWorkbench`
  - Typecheck passed; 84 module tests and 92 React tests passed.
- Browser bundle: `npm run build` in `Tools/HangboardWorkbench`
  - esbuild completed successfully.
- Hygiene: `git diff --check` passed.

## Concerns

- One existing server-shutdown race test can print a handled `BrokenPipeError`
  traceback while its loopback request is intentionally torn down. The final
  JUnit report confirms that the suite still completed with zero failures and
  zero errors.
- No functional Task 3 concerns remain.
