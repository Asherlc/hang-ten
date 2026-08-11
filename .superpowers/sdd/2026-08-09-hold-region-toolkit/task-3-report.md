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

---

# Fix Round 1 Report — August 10, 2026

Status: DONE

## Review findings addressed

1. Removed output-location-specific content from `review-gallery.html` so identical inputs now produce identical gallery bytes across different output directories.
2. Added pure fit-to-viewport math in `compare-model.js` and wired the comparison viewer’s Fit control to compute real viewport-based zoom instead of forcing `1`.
3. Reworked preview bundle publishing so a failed final publish preserves the previous `review-preview/` directory and restores it before re-raising.

## TDD record

### Red — regression tests added first

Python:

- `test_preview_bundle_is_deterministic_and_records_edited_hash`
  - now asserts `review-gallery.html` bytes are identical across two output roots
  - now asserts the absolute output root does not appear in the gallery HTML
- `test_preview_bundle_preserves_previous_output_when_publish_fails`
  - simulates a failing final directory publish and asserts the previous bundle remains intact

Node:

- `computeFitZoom scales oversized images to the viewport without enlarging smaller ones`

### Red command outputs

Command:

```bash
rtk /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_preview.py -q
```

Output:

```text
FF..
2 failed, 2 passed in 0.21s
```

Failures:

- gallery HTML bytes differed between two output directories
- previous preview bundle disappeared after simulated publish failure

Command:

```bash
rtk node --test /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/tests/compare_model.test.js
```

Output:

```text
2 pass, 1 fail
TypeError: computeFitZoom is not a function
```

## Minimal implementation

- `review_preview.py`
  - removed absolute output-root text from gallery generation
  - added failure-safe preview bundle publication with backup/restore around final replace
- `compare-model.js`
  - added `computeFitZoom({ imageWidth, imageHeight, viewportWidth, viewportHeight, maxZoom })`
- `compare.html`
  - wired Fit to compute zoom from the visible shell dimensions
  - set initial rendered zoom from the same fit calculation after image load

## Green verification

Command:

```bash
rtk /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/HangboardOnboarding/tests/test_review_preview.py -q
```

Output:

```text
....
4 passed in 0.17s
```

Command:

```bash
rtk node --test /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/tests/compare_model.test.js
```

Output:

```text
3 tests passed
```

Command:

```bash
rtk /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/.context/hangboard-onboarding-venv/bin/python -m pytest tests/test_review_preview.py tests/test_review_cli.py -q
```

Output:

```text
..............
14 passed in 0.22s
```

Command:

```bash
rtk node --test /Users/asherlc/src/hang-ten/.worktrees/hold-region-toolkit/Tools/hold-highlight-editor/tests/compare_model.test.js
```

Output:

```text
3 tests passed
```

## Notes / concerns

- The fit behavior is now test-backed through a pure helper and wired to the browser viewer, but it was not visually smoke-tested in a live browser during this fix round.
