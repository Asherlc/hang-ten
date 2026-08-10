# Task 3 Report — deterministic previews and read-only comparison viewer

Status: DONE

## Scope completed

- Added `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/src/hangboard_vectorizer/review_preview.py` with:
  - `render_preview_bundle(run: ReviewRun, output: Path) -> dict[str, object]`
  - `build_comparison_document(run: ReviewRun) -> str`
  - atomic bundle/document writing helpers
  - deterministic Pillow PNG rendering using the existing hold-type colors
  - read-only comparison HTML generation with embedded Stage 1 image data and inert JSON payloads
- Added `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/compare-model.js`
  - `buildSummary(baseline, edited, corrections)`
  - `visibleLayers(mode)`
- Added `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/compare.html`
  - read-only viewer template
  - image / automatic / edited / difference modes
  - opacity control
  - side-by-side toggle
  - fit / zoom controls
  - selected-region focus
  - correction summary + metadata panel
  - no Save/Add/Delete/editor mutation controls
- Added `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/compare.css`
- Added `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_preview.py`
- Added `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/tests/compare_model.test.js`
- Extended `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_cli.py`
- Updated `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/src/hangboard_vectorizer/review_cli.py`
  - `preview --run PATH --output PATH`
  - `compare --run PATH --output PATH`
  - `compare` returns exit code `2` without an edited artifact and does not write output
  - invalid preview inputs still surface as exit code `3` through existing CLI error handling

## TDD record

Red:

- `python -m pytest .../test_review_preview.py -q` failed with `ModuleNotFoundError: No module named 'hangboard_vectorizer.review_preview'`
- `node --test .../compare_model.test.js` failed with `Cannot find module '../compare-model.js'`

Green:

- Implemented the minimal preview/comparison code to satisfy the new tests
- Kept existing Task 1/2 contracts intact (`ReviewRun`, artifact discovery/hashes, lint report, review CLI JSON behavior)

## Verification

Executed with the worktree-local interpreter:

- `/Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest tests/test_review_preview.py tests/test_review_cli.py -q`
  - Result: `13 passed in 0.24s`
- `node --test /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/tests/compare_model.test.js`
  - Result: `2 passed`

## Constraints checked

- No Task 1/2 contract changes
- No Stage 1/2 source artifact mutation
- Preview bundle writes only to explicit output under `review-preview/`
- Comparison document is self-contained and embeds the source image as a data URL
- No network/model calls added
- No product-specific logic added
- No Save/Add/Delete controls added to the comparison viewer
- No git push or external upload performed

## Notes / concerns

- The comparison viewer is covered by contract tests and generated as self-contained HTML, but it was not manually browser-smoke-tested in this task.
