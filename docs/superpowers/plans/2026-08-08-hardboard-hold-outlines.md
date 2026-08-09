# Generated Hardboard Hold Outlines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate hand-editable normalized vector hold outlines as JSON for the 32 individual PNGs in `docs/hangboard-generative-catalog/`.

**Architecture:** Add a focused catalog-outline module to the existing Python vectorizer. It will load each raster, propose board/hold regions with deterministic local OpenCV processing, simplify contours into explicit `M`/`L`/`C` command objects, validate the JSON contract, and optionally render review overlays. Keep the generated files separate from the accepted onboarding fixtures and do not connect them to Swift runtime geometry.

**Tech Stack:** Python 3.11, NumPy, OpenCV, Pillow, dataclasses, JSON, pytest.

## Global Constraints

- Process the 32 individual catalog PNGs and exclude `contact-sheet-primary.png`.
- Produce one JSON outline document per source image in `docs/hangboard-generative-catalog/outlines/`.
- Use normalized `0...1` coordinates and preserve source pixel dimensions.
- Use explicit `M`, `L`, and cubic `C` path commands; do not emit dense pixel point clouds.
- Keep labels, kinds, confidence, and notes as visual estimates; do not claim manufacturer-verified semantics.
- Use advisory manufacturer/source hints where available, preserving source URLs in each document’s `references` array.
- Generated outlines are editable calibration artifacts, not Swift runtime hit-testing geometry.
- Generation must be deterministic and write outputs transactionally.
- Generated review artifacts belong under `.context/hardboard-outlines/`.

---

### Task 1: Add the editable outline schema and validator

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outlines.py`
- Create: `Tools/HangboardOnboarding/tests/test_catalog_outlines.py`
- Modify: `Tools/HangboardOnboarding/pyproject.toml`

**Interfaces:**
- `OutlineCommand`, `OutlinePath`, `HoldOutline`, and `CatalogOutlineDocument` are immutable dataclasses with `to_json()`/`from_json()` helpers.
- `validate_catalog_document(document: CatalogOutlineDocument, source_path: Path | None = None) -> None` raises `ValueError` for invalid schema, coordinate ranges, command sequences, bounds, or source dimensions.
- `write_catalog_document(document: CatalogOutlineDocument, output_path: Path) -> None` writes stable, indented JSON through a sibling temporary file and atomic replace.
- `path_bounds(path: OutlinePath) -> tuple[float, float, float, float]` returns normalized `x, y, width, height` from all endpoints and cubic controls.
- `normalize_contour(contour: np.ndarray, width: int, height: int) -> OutlinePath` converts a closed pixel contour to an editable normalized path using line segments and cubic smoothing while retaining the first point as the closing endpoint.

- [ ] **Step 1: Write failing schema tests**

Add tests covering:

```python
def test_round_trip_preserves_explicit_commands_and_bounds():
    document = sample_document()
    restored = CatalogOutlineDocument.from_json(document.to_json())
    assert restored == document
    validate_catalog_document(restored)


def test_validator_rejects_coordinates_outside_normalized_canvas():
    document = sample_document().replace_first_coordinate(1.01, 0.4)
    with pytest.raises(ValueError, match="normalized"):
        validate_catalog_document(document)


def test_validator_rejects_open_or_degenerate_path():
    document = sample_document().with_commands((OutlineCommand("M", (0.1, 0.1)),))
    with pytest.raises(ValueError, match="closed"):
        validate_catalog_document(document)


def test_normalize_contour_emits_lines_and_curves_in_range():
    contour = np.array([[10, 10], [90, 10], [100, 50], [90, 90], [10, 90]], dtype=float)
    path = normalize_contour(contour, 100, 100)
    assert path.closed
    assert {command.command for command in path.commands} <= {"M", "L", "C"}
    assert any(command.command == "C" for command in path.commands)
    assert all(0 <= value <= 1 for value in path.all_coordinates())
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_outlines.py -q`

Expected: collection or assertion failures because the schema module and helpers do not exist yet.

- [ ] **Step 3: Implement the schema and path conversion**

Use explicit command objects shaped as follows:

```python
{"command": "M", "to": [x, y]}
{"command": "L", "to": [x, y]}
{"command": "C", "controls": [[c1x, c1y], [c2x, c2y]], "to": [x, y]}
```

Require exactly one `M`, at least two drawing segments, and `closed: true`. Include only finite normalized coordinates. For contour conversion, preserve persistent corners as `L` commands and fit smooth cubic spans between them; use a deterministic point ordering and fixed tolerance derived from the contour’s smaller pixel extent.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_outlines.py -q`

Expected: all schema, validation, normalization, and atomic-write tests pass.

- [ ] **Step 5: Commit the schema implementation**

Run: `rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outlines.py Tools/HangboardOnboarding/tests/test_catalog_outlines.py Tools/HangboardOnboarding/pyproject.toml && rtk git commit -m "feat: add editable catalog outline schema"`

### Task 2: Add deterministic catalog raster detection and CLI

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outlines.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outline_cli.py`
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outline_sources.json`
- Modify: `Tools/HangboardOnboarding/pyproject.toml`
- Modify: `Tools/HangboardOnboarding/tests/test_catalog_outlines.py`

**Interfaces:**
- `detect_board_mask(image: np.ndarray) -> np.ndarray` returns one binary board mask for an RGB/RGBA image.
- `detect_hold_candidates(image: np.ndarray, board_mask: np.ndarray) -> tuple[tuple[np.ndarray, str, str], ...]` returns ordered `(closed_pixel_contour, kind, note)` candidates.
- `vectorize_catalog_image(source_path: Path) -> CatalogOutlineDocument` produces a validated document without reading external state.
- `load_catalog_source_hints(path: Path | None = None) -> Mapping[str, object]` loads the checked-in advisory product/source table.
- CLI entry point `hangboard-catalog-outlines` supports `--source-dir`, `--output-dir`, `--review-dir`, `--limit`, and `--check`; `--check` validates existing JSONs without rewriting them.

The checked-in source-hint table must use this shape and these authoritative hints where a matching product is known; unmatched stems remain valid with an empty reference list:

```json
{
  "beastmaker-1000": {
    "references": [{
      "title": "Beastmaker Fingerboards",
      "url": "https://www.beastmaker.co.uk/collections/fingerboards",
      "hints": ["2 jugs", "35-degree and 20-degree slopers", "two- through four-finger pockets"]
    }]
  },
  "beastmaker-2000": {
    "references": [{
      "title": "Beastmaker Fingerboards",
      "url": "https://www.beastmaker.co.uk/collections/fingerboards",
      "hints": ["advanced pocket and sloper layout", "no beginner jugs claimed without visual confirmation"]
    }]
  },
  "tension-whetstone": {
    "references": [{
      "title": "Tension Hangboards",
      "url": "https://tensionclimbing.com/pages/hangboards",
      "hints": ["top jug with ergo bumps", "40mm center edge", "40mm two-finger pockets", "40/30/25/20mm edges"]
    }]
  },
  "tension-grindstone": {
    "references": [{
      "title": "Tension Hangboards",
      "url": "https://tensionclimbing.com/pages/hangboards",
      "hints": ["full-width bar jug", "50mm center edge", "30/25/20/15/10/8mm edges"]
    }]
  },
  "tension-honestone": {
    "references": [{
      "title": "Tension Hangboards",
      "url": "https://tensionclimbing.com/pages/hangboards",
      "hints": ["35- and 45-degree top slopers", "25mm center edge", "one-finger pockets", "20/15/10/8mm edges"]
    }]
  },
  "metolius-project": {
    "references": [{
      "title": "Project Training Board",
      "url": "https://www.metoliusclimbing.com/products/project-training-board",
      "hints": ["broad arc", "outward and downward taper", "perfectly symmetric CAD/CAM layout"]
    }]
  },
  "metolius-climbers-edge": {
    "references": [{
      "title": "Climbers Edge Board",
      "url": "https://www.metoliusclimbing.com/products/climbers-edge-board",
      "hints": ["7.5/10/12.5/15/17.5/20mm edges", "40mm radius round sloper", "20-degree flat sloper", "jugs"]
    }]
  },
  "metolius-simulator-3d": {
    "references": [{
      "title": "Simulator 3D Training Guide",
      "url": "https://www.metoliusclimbing.com/pages/simulator-3d-training-guide",
      "hints": ["outer jugs", "flat and round slopers", "deep/medium/shallow edges", "numbered pocket rows"]
    }]
  },
  "metolius-contact": {
    "references": [{
      "title": "Metolius Climbing Hold Catalog",
      "url": "https://www.metoliusclimbing.com/pdf/Climbing-Hold-Catalog.pdf",
      "hints": ["11 pockets", "four central edges", "top pull-up jugs", "rounded and flat slopers"]
    }]
  },
  "trango-rock-prodigy-natural": {
    "references": [{
      "title": "Rock Prodigy Natural",
      "url": "https://trango.com/products/rock-prodigy-natural",
      "hints": ["two variable-depth rails", "three pockets", "closed crimp", "small and large pinches"]
    }]
  },
  "trango-rock-prodigy-forge": {
    "references": [{
      "title": "Rock Prodigy Forge",
      "url": "https://trango.com/products/rock-prodigy-forge",
      "hints": ["closed-crimp grip with thumb support", "drafted pockets", "steeper slopers", "different holds from Training Center"]
    }]
  },
  "trango-rock-prodigy-pivot": {
    "references": [{
      "title": "Rock Prodigy Pivot",
      "url": "https://trango.com/products/rock-prodigy-pivot",
      "hints": ["22 distinct grip positions", "rotatable four-orientation system", "adjustable shoulder width"]
    }]
  },
  "trango-rock-prodigy-training-center": {
    "references": [{
      "title": "Rock Prodigy Training Center",
      "url": "https://trango.com/products/rock-prodigy-training-center",
      "hints": ["two-piece adjustable layout", "index bumps along variable edge rails", "symmetric hold design"]
    }]
  },
  "lattice-triple-rung": {
    "references": [{
      "title": "Triple Rung",
      "url": "https://latticetraining.com/product/triple-rung-wooden-hangboard/",
      "hints": ["continuous 45mm, 20mm, and 10mm edges", "no pockets", "wide-radius extruded design"]
    }]
  },
  "frictitious-megalith": {
    "references": [{
      "title": "The Megalith",
      "url": "https://frictitiousclimbing.com/products/megalith",
      "hints": ["full-width pull-up jug", "pockets", "flat and unlevel shoulder-width edges", "8mm to 40mm edges"]
    }]
  },
  "soill-split-palm": {
    "references": [{
      "title": "Split Palm",
      "url": "https://soillholds.com/products/split-palm",
      "hints": ["two slopers", "pinch", "multiple crimp sizes and angles"]
    }]
  }
}
```

- [ ] **Step 1: Write failing detector and CLI tests**

Add a synthetic-board fixture and tests:

```python
def test_detector_returns_stable_candidates_for_synthetic_board(tmp_path):
    source = write_synthetic_board(tmp_path / "synthetic.png")
    first = vectorize_catalog_image(source)
    second = vectorize_catalog_image(source)
    assert first.to_json() == second.to_json()
    assert len(first.outlines) >= 2
    assert all(outline.confidence == "approximate" for outline in first.outlines)


def test_cli_check_rejects_missing_or_malformed_catalog_output(tmp_path):
    result = runner.invoke(main, ["--source-dir", str(tmp_path), "--output-dir", str(tmp_path / "out"), "--check"])
    assert result.exit_code != 0


def test_cli_excludes_contact_sheet_and_writes_review_overlay(tmp_path):
    write_synthetic_board(tmp_path / "board.png")
    write_synthetic_board(tmp_path / "contact-sheet-primary.png")
    result = runner.invoke(main, ["--source-dir", str(tmp_path), "--output-dir", str(tmp_path / "out"), "--review-dir", str(tmp_path / "review")])
    assert result.exit_code == 0
    assert (tmp_path / "out" / "board.json").exists()
    assert not (tmp_path / "out" / "contact-sheet-primary.json").exists()
    assert (tmp_path / "review" / "board.png").exists()
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_outlines.py -q`

Expected: failures for missing detector, CLI, and entry-point behavior.

- [ ] **Step 3: Implement board and hold candidate extraction**

Use Pillow for decoding and OpenCV for masks, connected components, edge extraction, morphology, contour simplification, and overlay drawing. Keep the algorithm local and deterministic: remove the dominant background, select the largest plausible board component, derive internal hold candidates from persistent local contrast/edge regions constrained to the board mask, reject tiny/noisy components, order candidates top-to-bottom then left-to-right, and assign `confidence: "approximate"` with non-authoritative notes. Load matching entries from `catalog_outline_sources.json` to attach URLs and broad hold/layout hints, but do not use those hints to move a contour or claim depth/finger count that is not visible. Do not use a model call.

Use the schema’s `normalize_contour()` for all emitted candidates. Ensure candidate contours are clipped to the board mask, contain at least three unique points, and have nonzero area. Render review overlays with source pixels plus a contrasting outline and ID label; review images are diagnostic only.

- [ ] **Step 4: Add the CLI and stable output policy**

The CLI must discover only `*.png` files directly in `--source-dir`, skip the exact basename `contact-sheet-primary.png`, map each source stem to `<stem>.json`, sort inputs lexicographically, and write outputs transactionally. `--limit N` is a deterministic development subset. `--check` must verify the expected one-to-one source/output set, JSON schema, normalized bounds, and source canvas dimensions without modifying files. `--review-dir` is optional and, when present, writes one overlay PNG per processed board.

- [ ] **Step 5: Run focused tests and the package type/syntax checks**

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_outlines.py -q`

Expected: all focused tests pass.

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m compileall -q Tools/HangboardOnboarding/src`

Expected: exit 0 with no syntax errors.

- [ ] **Step 6: Commit the catalog detector and CLI**

Run: `rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outlines.py Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outline_cli.py Tools/HangboardOnboarding/tests/test_catalog_outlines.py Tools/HangboardOnboarding/pyproject.toml && rtk git commit -m "feat: add catalog outline vectorization"`

### Task 3: Generate and validate all catalog outline JSON artifacts

**Files:**
- Create: `docs/hangboard-generative-catalog/outlines/*.json` for all 32 individual board images.
- Create: `Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/catalog_outline_sources.json`
- Modify: `Tools/HangboardOnboarding/README.md`
- Modify: `Tools/HangboardOnboarding/TESTING.md`

**Interfaces:**
- The CLI from Task 2 is the sole generator for committed artifacts.
- The catalog test derives the expected source set from `docs/hangboard-generative-catalog/*.png`, excludes `contact-sheet-primary.png`, and validates every committed JSON against its source.

- [ ] **Step 1: Add the full-catalog validation test**

Add a test that asserts the source and output stems are exactly equal, each document’s `sourceImage` resolves to the matching PNG, each canvas matches the PNG dimensions, every outline path is valid and normalized, each document’s `references` entries match the source-hint table, and no output is generated for the contact sheet.

- [ ] **Step 2: Run the validation test before generation and verify the expected failure**

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py -q`

Expected: failure because the 32 outline JSON files do not exist yet.

- [ ] **Step 3: Generate all 32 JSON documents and review overlays**

Run:

```bash
rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli \
  --source-dir docs/hangboard-generative-catalog \
  --output-dir docs/hangboard-generative-catalog/outlines \
  --review-dir .context/hardboard-outlines/reviews
```

Review representative overlay PNGs from wide, square, and portrait source ratios under `.context/hardboard-outlines/reviews/`. If the detector emits obvious background or board-silhouette false positives, adjust deterministic thresholds or contour filtering in Task 2, regenerate, and preserve the explicit approximate confidence notes.

- [ ] **Step 4: Run the full catalog and package test suites**

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests -q`

Expected: all tests pass, including the new 32-file catalog validation.

Run: `rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli --source-dir docs/hangboard-generative-catalog --output-dir docs/hangboard-generative-catalog/outlines --check`

Expected: exit 0 and report 32 valid outline documents with no contact-sheet output.

- [ ] **Step 5: Document the generator and hand-editing contract**

Add README/TESTING documentation showing the full `hangboard_vectorizer.catalog_outline_cli` command, the JSON command shape, normalized coordinate convention, the purpose of `bounds`, the advisory source-hint policy, and the fact that generated semantics are approximate and must be reviewed before runtime use.

- [ ] **Step 6: Commit the generated artifacts and docs**

Run: `rtk git add docs/hangboard-generative-catalog/outlines Tools/HangboardOnboarding/tests/test_catalog_outline_catalog.py Tools/HangboardOnboarding/README.md Tools/HangboardOnboarding/TESTING.md && rtk git commit -m "feat: add generated hardboard hold outlines"`

## Final verification

After all task reviews are clean, run:

```bash
rtk .context/hangboard-onboarding-venv/bin/python -m pytest Tools/HangboardOnboarding/tests -q
rtk .context/hangboard-onboarding-venv/bin/python -m hangboard_vectorizer.catalog_outline_cli --source-dir docs/hangboard-generative-catalog --output-dir docs/hangboard-generative-catalog/outlines --check
rtk git status --short
```

Expected: the full suite passes, the check reports 32 valid documents, and only the intended spec, tool, test, documentation, and outline JSON files are present in the worktree.
