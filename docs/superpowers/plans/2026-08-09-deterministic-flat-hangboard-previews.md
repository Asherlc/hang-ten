# Deterministic Flat Hangboard Previews Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 32 generated flat-preview PNGs with deterministic warm illustrations built from each source board mask and its existing normalized hold-outline JSON.

**Architecture:** Add one focused Python renderer/CLI inside `hangboard_vectorizer`. It extracts all significant board components from the source PNG, paints a fixed flat palette, clips the existing outline paths into the board mask as dark cavities, writes stable PNGs, and rebuilds the labeled contact sheet.

**Tech Stack:** Python 3.11, NumPy, OpenCV, Pillow, pytest.

## Global Constraints

- Exactly 32 source stems map to exactly 32 `*-flat.png` outputs.
- Source PNGs, outline JSON, Swift code, and runtime artwork remain unchanged.
- Use no generated pixels, photographic texture, gradients, branding, hardware, or scene details.
- Preserve significant disconnected board pieces instead of keeping only the largest component.
- Use a fixed parchment, warm board, contour, and cavity palette.
- Rendering the same inputs twice must produce byte-identical PNGs.
- Outputs remain preview references, not interaction or highlight geometry.

---

### Task 1: Deterministic flat catalog renderer

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_flat_illustrations.py`
- Modify: `Tools/HangboardOnboarding/pyproject.toml`
- Create: `Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py`
- Replace: `docs/hangboard-generative-catalog/flat-illustrations/*-flat.png`
- Replace: `docs/hangboard-generative-catalog/flat-illustrations-contact-sheet.png`
- Modify: `.context/flat-hangboard-illustrations/batch-review.md`

**Interfaces:**
- Consumes: source PNGs in `docs/hangboard-generative-catalog/` and `CatalogOutlineDocument` JSON files in `docs/hangboard-generative-catalog/outlines/`.
- Produces: `render_flat_illustration(source_path: Path, document: CatalogOutlineDocument, output_path: Path) -> None`, `render_flat_catalog(source_dir: Path, outline_dir: Path, output_dir: Path, contact_sheet_path: Path) -> tuple[Path, ...]`, and CLI entry point `hangboard-catalog-flat`.

- [ ] **Step 1: Write failing renderer tests.**

  Add a synthetic two-piece board fixture with one normalized hold path. Assert that `render_flat_illustration` keeps both board pieces, leaves the center gap parchment-colored, paints the hold darker than the board plane, and writes the source canvas dimensions. Add a catalog test that renders two fixtures twice and asserts identical PNG/contact-sheet bytes and exact `<stem>-flat.png` naming.

  The central assertions should follow this shape:

  ```python
  render_flat_illustration(source_path, document, output_path)
  rendered = np.array(Image.open(output_path).convert("RGB"))
  assert tuple(rendered[40, 35]) == BOARD_COLOR
  assert tuple(rendered[40, 165]) == BOARD_COLOR
  assert tuple(rendered[40, 100]) == PARCHMENT_COLOR
  assert tuple(rendered[40, 45]) == CAVITY_COLOR
  ```

- [ ] **Step 2: Run the focused tests and confirm RED.**

  Run:

  ```sh
  rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py -q
  ```

  Expected: collection/import failure because `catalog_flat_illustrations` does not exist.

- [ ] **Step 3: Implement the minimal deterministic renderer.**

  In `catalog_flat_illustrations.py`:

  - define fixed RGB constants `PARCHMENT_COLOR`, `BOARD_COLOR`, `CONTOUR_COLOR`, and `CAVITY_COLOR`;
  - estimate the border background from source pixels and keep every foreground connected component whose area is at least 5% of the largest component, with a 64-pixel minimum;
  - close/open the mask deterministically, fill the board plane, and draw a one-pixel contour derived from the mask boundary;
  - parse each outline path using the existing deterministic path flattener, fill it with `CAVITY_COLOR`, and clip it to the board mask;
  - save RGB PNGs without metadata;
  - render a four-column labeled contact sheet using Pillow's default font;
  - expose a CLI accepting `--source-dir`, `--outline-dir`, `--output-dir`, and `--contact-sheet`;
  - register `hangboard-catalog-flat = "hangboard_vectorizer.catalog_flat_illustrations:main"` in `pyproject.toml`.

- [ ] **Step 4: Run focused tests and confirm GREEN.**

  Run the focused pytest command from Step 2. Expected: all tests pass with pristine output.

- [ ] **Step 5: Render the complete catalog twice.**

  Run the new CLI against `docs/hangboard-generative-catalog`, its `outlines` directory, the existing `flat-illustrations` directory, and `flat-illustrations-contact-sheet.png`. Hash all 33 PNGs, run the CLI again, and assert the hashes are unchanged.

- [ ] **Step 6: Run catalog and outline verification.**

  Run:

  ```sh
  rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_flat_illustrations.py Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py -q
  rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli --source-dir docs/hangboard-generative-catalog --output-dir docs/hangboard-generative-catalog/outlines --check
  ```

  Expected: all tests pass and the outline CLI reports 32 verified documents.

- [ ] **Step 7: Review the contact sheet and record the verdict.**

  Inspect the complete contact sheet for visible board bodies, split-board component retention, readable cavity paths, fixed warm palette, and absence of texture/lighting. Update `.context/flat-hangboard-illustrations/batch-review.md` with the deterministic method, 32/32 inventory, visual findings, and `PASS` only if the sheet is traceable.

- [ ] **Step 8: Commit the scoped change.**

  Stage only the renderer, CLI registration, focused tests, 32 replaced preview PNGs, rebuilt contact sheet, and review note. Preserve all unrelated Swift and outline-JSON worktree modifications.

  ```sh
  rtk git commit -m "feat: render deterministic flat hangboard previews"
  ```
