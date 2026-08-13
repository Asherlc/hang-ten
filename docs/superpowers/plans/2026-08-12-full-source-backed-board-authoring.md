# Full Source-Backed Hangboard Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn every current image-only `Hangboards/` directory into a complete, source-backed runtime package when—and only when—official manufacturer material supports every factual field, semantic target, and artwork element.

**Architecture:** `Hangboards/catalog.json` remains the sole runtime registry and lists only complete packages. Each complete package has four JSON sidecars, exactly one generated presentation image at `assets/primary.png`, and optional untouched source photography; its `evidence.json` maps every runtime fact and package asset to declared HTTPS sources. Research happens on Git branches and is recorded as durable source audits and package evidence, never as a lifecycle, confidence, review, or approximation field in the app.

**Tech Stack:** JSON, Python 3.11+, pytest, Swift 5, XCTest, SwiftUI, Xcode, GitHub Actions.

## Global Constraints

- `Hangboards/catalog.json` has schema version `1` and entries containing exactly `id` and `path`; it contains no `status`, draft, review, confidence, onboarding, or shipping state.
- Every registered package is a single direct child of `Hangboards/` and contains exactly `board.json`, `evidence.json`, `semantics.json`, and `artwork.json` as JSON sidecars.
- A completed package contains `assets/primary.png` as its sole generated raster. An optional unmodified manufacturer source photo may remain only as an evidence-covered asset; no alternate generated PNG, preview, flat rendering, outline, `review/` directory, or board README is permitted.
- `artwork.json` is the sole normalized geometry representation. Do not create `outline.json`, `outline.approx.json`, SVG duplicates, or a second hold map.
- Official manufacturer evidence is required for product identity, dimensions, hold count, hold depth/size, finger capacity, grip classification, and any factual cue or feature. A current generated PNG, a retailer listing, a user photo, third-party prose, old app code, or another package may not establish a factual hold field.
- A board with an incomplete official source set remains unregistered and has no partial sidecars. Record the precise source gap in its batch source audit and the batch PR; do not fill it with an estimate, `null`, a provisional semantic, or review state.
- `evidence.json` uses nonempty HTTPS `sources`, an ISO `checkedAt` date, and exact coverage maps for `fieldEvidence`, `holdEvidence`, `semanticEvidence`, `artworkEvidence`, and `assetEvidence`. An adaptation method describes representation only; `external-generative-adaptation` may support `assets/primary.png` but never a physical or semantic fact.
- `board.json`, `semantics.json`, and `artwork.json` share the same board ID. Physical hold IDs and artwork hold IDs match exactly; semantic mappings reference existing hold IDs and only name source-supported concepts.
- Board-specific facts, semantic mappings, and geometry stay in package JSON. The iOS app only loads staged package JSON and package PNGs; do not add board-specific Swift, imagesets, generated runtime catalogs, or runtime image generation.
- `scripts/stage-approved-board-packages.py` stages only registered package directories and `catalog.json` into the app bundle. Preserve its path/symlink protections.
- Existing training-plan text may be changed only when traceable to a real plan source. Do not create routines, counts, grip prescriptions, accessory copy, or coaching claims while authoring a board.

---

## File structure after completion

```text
Hangboards/
  catalog.json
  beastmaker-1000/
    board.json
    evidence.json
    semantics.json
    artwork.json
    assets/
      primary.png
      WoodGripsCompactII.jpg                 # optional, unchanged source photo
  zlagboard-pro/
    board.json
    evidence.json
    semantics.json
    artwork.json
    assets/
      primary.png

docs/source-audits/
  2026-08-12-beastmaker-board-packages.md
  2026-08-12-dewoodstok-escape-board-packages.md
  2026-08-12-evolv-frictitious-board-packages.md
  2026-08-12-single-board-documentation-packages.md
  2026-08-12-metolius-board-packages.md
  2026-08-12-soill-tension-board-packages.md
  2026-08-12-trango-board-packages.md
  2026-08-12-yy-vertical-board-packages.md
  2026-08-12-zlagboard-board-packages.md

Tools/HangboardPipeline/tests/
  test_approved_board_packages.py
  test_board_catalog.py
  test_generated_catalog_import.py

HangTenTests/
  BoardSourceBoundaryTests.swift
```

`docs/source-audits/` is documentation, not a package sidecar or runtime input. It must identify sources and source gaps but must not apply a lifecycle label to package data.

## Canonical package authoring interface

Every completed package must conform to the existing validator interface:

```python
def load_board_package(package_root: Path) -> BoardPackage: ...
def validate_catalog(catalog_path: Path) -> CatalogDocument: ...
```

The source-audit document for each batch uses this fixed factual table, once per candidate, so a reviewer can compare the prose audit with its committed `evidence.json` without introducing another package representation:

```markdown
| slug | catalog id | official product URL | official front image URL |
| --- | --- | --- | --- |

| hold field or artwork element | official source URL | package evidence key | representation method |
| --- | --- | --- | --- |
```

For a blocked candidate the source audit has this exact record instead of a partial package:

```markdown
### `manufacturer-model`

Missing official evidence: no manufacturer hold guide or measurement supports
`fingerCapacity`, `gripType`, and each physical hold boundary. The product page
and front image establish identity and silhouette only. No `board.json`,
`semantics.json`, `artwork.json`, `evidence.json`, or catalog entry was added.
```

## Stable catalog identifiers and authoring batches

Use the following IDs; do not derive runtime identifiers from image filenames during implementation:

| Batch | package slug → catalog ID |
| --- | --- |
| Beastmaker | `beastmaker-1000` → `beastmaker.1000`; `beastmaker-2000` → `beastmaker.2000` |
| DeWoodstok | `dewoodstok-woodbord` → `dewoodstok.woodbord` |
| Escape | `escape-beta` → `escape.beta`; `escape-unlimited` → `escape.unlimited` |
| Evolv / Frictitious | `evolv-kilter-basic-long` → `evolv.kilter-basic-long`; `frictitious-doormount-pro-7` → `frictitious.doormount-pro-7`; `frictitious-megalith` → `frictitious.megalith` |
| Single-board documentation set | `lattice-triple-rung` → `lattice.triple-rung`; `moon-armstrong` → `moon.armstrong`; `nature-stoak-board-iii` → `nature.stoak-board-iii`; `target10a-linebreaker-base` → `target10a.linebreaker-base` |
| Metolius | `metolius-climbers-edge` → `metolius.climbers-edge`; `metolius-contact` → `metolius.contact`; `metolius-project` → `metolius.project`; `metolius-simulator-3d` → `metolius.simulator-3d` |
| So iLL | `soill-iron-palm-2` → `soill.iron-palm-2`; `soill-split-palm` → `soill.split-palm`; `soill-training-tiles` → `soill.training-tiles` |
| Tension | `tension-grindstone` → `tension.grindstone`; `tension-honestone` → `tension.honestone`; `tension-whetstone` → `tension.whetstone` |
| Trango | `trango-rock-prodigy-forge` → `trango.rock-prodigy-forge`; `trango-rock-prodigy-natural` → `trango.rock-prodigy-natural`; `trango-rock-prodigy-pivot` → `trango.rock-prodigy-pivot` |
| YY Vertical | `yy-verticalboard-evo` → `yy.verticalboard-evo`; `yy-verticalboard-first` → `yy.verticalboard-first`; `yy-verticalboard-light` → `yy.verticalboard-light`; `yy-verticalboard-one` → `yy.verticalboard-one` |
| Zlagboard | `zlagboard-evo` → `zlagboard.evo`; `zlagboard-pro` → `zlagboard.pro` |

The 31 candidates above plus the two existing packages make 33 catalog entries only if all 31 pass the evidence gate. A completed batch may register only its ready candidates. A blocked candidate must remain as its current primary-image-only directory, outside the catalog, until primary evidence is found on a later branch.

### Task 1: Make the published authoring contract state-free and regression-tested

**Files:**
- Modify: `docs/ADDING_A_BOARD.md`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`
- Modify: `Tools/HangboardPipeline/tests/test_generated_catalog_import.py`

**Interfaces:**
- Consumes: `load_board_package(package_root: Path) -> BoardPackage` and `validate_catalog(catalog_path: Path) -> CatalogDocument`.
- Produces: a documented and tested package boundary: only registered, complete packages are runtime content; unregistered candidates have one `assets/primary.png` and no state/parallel geometry files.

- [ ] **Step 1: Write the failing state-free and one-generated-image tests.**

  Add repository tests that reject a catalog entry with `status`, a registered package with `README.md`, `review/`, `outline.json`, `outline.approx.json`, or a second generated PNG, and an unregistered candidate containing a JSON sidecar. Keep the source-photo exception explicit: a source image is allowed only when `evidence.assetEvidence` contains its exact package-relative path.

  ```python
  package.joinpath("README.md").write_text("review state")
  with pytest.raises(ValueError, match="unknown package file"):
      load_board_package(package)

  assert not (candidate / "outline.approx.json").exists()
  assert sorted(path.name for path in (candidate / "assets").iterdir()) == ["primary.png"]
  ```

- [ ] **Step 2: Run the focused tests and confirm RED.**

  Run: `python3 -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_generated_catalog_import.py -q`

  Expected: the new assertions fail until the validator/documentation boundary is tightened.

- [ ] **Step 3: Update the guide and the package validation tests.**

  Replace the obsolete `draft`/`approved` instructions in `docs/ADDING_A_BOARD.md` with the state-free structure and exact sidecar/evidence contract in this plan. In the Python tests, enumerate only the four JSON sidecars and `assets/primary.png` for an unregistered image-only directory. Add the source-photo fixture by copying `WoodGripsCompactII.jpg` and asserting the existing `assetEvidence` key is required.

- [ ] **Step 4: Implement the closed on-disk package shape.**

  In `board_catalog.py`, make `load_board_package` reject every root child other than the four canonical JSON sidecars and the `assets/` directory. Make `_package_assets` reject nested asset paths and permit only `assets/primary.png` plus zero or one regular non-PNG source image with a `.jpg`, `.jpeg`, `.webp`, or `.heic` extension. Retain exact `assetEvidence` equality, so the optional original photo cannot silently bypass evidence. Do not rename `WoodGripsCompactII.jpg` or synthesize a second raster.

- [ ] **Step 5: Run focused GREEN and the full package suite.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_generated_catalog_import.py -q
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  ```

  Expected: the two existing packages validate and every remaining candidate is primary-only and unregistered.

- [ ] **Step 6: Commit and push the contract.**

  ```sh
  git add docs/ADDING_A_BOARD.md Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py Tools/HangboardPipeline/tests/test_board_catalog.py Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_generated_catalog_import.py
  git commit -m "docs: define state-free source-backed board authoring"
  git push origin HEAD
  ```

### Task 2: Add the reusable evidence-gated batch harness

**Files:**
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Create: `docs/source-audits/2026-08-12-hangboard-batch-template.md`

**Interfaces:**
- Consumes: the package parser's exact `fieldEvidence`, `holdEvidence`, `semanticEvidence`, `artworkEvidence`, and `assetEvidence` key checks.
- Produces: a reproducible PR checklist and tests that make each batch prove the same cross-document and asset invariants.

- [ ] **Step 1: Write a failing catalog-wide completeness assertion.**

  Add a test that walks every registered package, loads it through `load_board_package`, and asserts its presentation is exactly `assets/primary.png`, its sidecar names are exactly the canonical four, and its assets are `primary.png` plus at most one evidence-covered non-PNG source photo.

  ```python
  package = module.load_board_package(root / entry.path)
  assert package.board.presentation_asset_path == "assets/primary.png"
  assert {path.name for path in (root / entry.path).glob("*.json")} == {
      "board.json", "evidence.json", "semantics.json", "artwork.json"
  }
  ```

- [ ] **Step 2: Run the assertion to establish RED.**

  Run: `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py -q`

  Expected: RED until the test and currently complete package expectations agree on the `primary.png` convention.

- [ ] **Step 3: Create the committed audit template.**

  Create `docs/source-audits/2026-08-12-hangboard-batch-template.md` with the exact candidate table and exact evidence-key table shown above, a `checkedAt` rule, source URL capture requirements, and the exact blocker record. It must state that the template itself is not runtime/package state and must not prescribe values unsupported by a source.

- [ ] **Step 4: Run GREEN and inspect catalog output.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q
  scripts/hangboard-tools.sh catalog status --catalog Hangboards/catalog.json
  ```

  Expected: every registered entry has complete canonical sidecars; the status command returns no lifecycle/status field.

- [ ] **Step 5: Commit and push the batch harness.**

  ```sh
  git add Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py docs/source-audits/2026-08-12-hangboard-batch-template.md
  git commit -m "test: gate board packages on source-backed evidence"
  git push origin HEAD
  ```

### Task 3: Audit and author the Beastmaker batch

**Files:**
- Create: `docs/source-audits/2026-08-12-beastmaker-board-packages.md`
- Create: `Hangboards/beastmaker-1000/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/beastmaker-2000/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: the `beastmaker.1000` and `beastmaker.2000` IDs, official Beastmaker product/measurement/front/oblique material, and the package validator.
- Produces: zero, one, or two complete registered packages; a candidate without official per-hold support remains unregistered with an exact source-gap record.

- [ ] **Step 1: Collect official sources and write the audit before package JSON.**

  Add the two candidate rows to the Beastmaker audit. For each candidate, record an HTTPS manufacturer product URL, official front-image URL, official oblique-image URL when depth is visually ambiguous, and official numbered guide/manual/measurement URL. Add the checked calendar date and map each anticipated factual field, physical hold field, semantic target, silhouette, layer, hold piece, `assets/primary.png`, and retained source photo to those URLs.

- [ ] **Step 2: Apply the evidence readiness gate.**

  Mark a candidate ready only if the official material supports each physical hold's count, size/depth, finger capacity, and grip classification. Otherwise write the exact blocker record from the canonical template and leave its directory with only `assets/primary.png`; do not create a catalog entry or any sidecar.

- [ ] **Step 3: Author every ready package from its official source set.**

  For each ready candidate, create the four canonical JSON sidecars. Set `presentation.assetPath` to `assets/primary.png`; use the exact catalog ID above; draw one normalized silhouette/layer/hold-piece representation in `artwork.json`; and construct `evidence.json` with exact keys matching the validator's factual, hold, semantic, artwork, and asset maps. Retain a manufacturer source photo only if it is unmodified and has an `assetEvidence` entry.

- [ ] **Step 4: Register only validated ready packages and write regression expectations.**

  Insert each ready entry into `Hangboards/catalog.json` in deterministic ID order. Extend `test_approved_board_packages.py` with the exact resulting Beastmaker ID set and its physical/artwork hold-ID equality assertions; do not assert an ID for a blocked candidate.

- [ ] **Step 5: Validate and commit the atomic batch.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  git add Hangboards/beastmaker-1000 Hangboards/beastmaker-2000 Hangboards/catalog.json docs/source-audits/2026-08-12-beastmaker-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author Beastmaker board packages"
  git push origin HEAD
  ```

### Task 4: Audit and author the DeWoodstok and Escape batch

**Files:**
- Create: `docs/source-audits/2026-08-12-dewoodstok-escape-board-packages.md`
- Create: `Hangboards/dewoodstok-woodbord/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/escape-beta/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/escape-unlimited/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: official DeWoodstok and Escape product, front/oblique, and hold-measurement sources.
- Produces: only evidence-complete `dewoodstok.woodbord`, `escape.beta`, and `escape.unlimited` packages.

- [ ] **Step 1: Write the manufacturer-source audit.**

  Record each candidate's official product, front, oblique where required, and hold-guide/measurement URLs with the date checked. Use exact evidence-key rows for board facts, every hold field, all semantic IDs, all artwork elements, and all retained assets.

- [ ] **Step 2: Block unsupported candidates before creating JSON.**

  For every product without an official per-hold depth/count/finger/grip source, write its exact missing fields in the audit and retain only the existing primary image. Do not substitute a dealer specification or image reading for the missing source.

- [ ] **Step 3: Create the four sidecars for each ready candidate.**

  Create `board.json`, `semantics.json`, `artwork.json`, and `evidence.json` only for ready candidates; use the stable IDs, source-backed hold frames and semantic mappings, `assets/primary.png`, and exact evidence coverage.

- [ ] **Step 4: Register/test/validate the batch.**

  Update the catalog and exact package tests only for ready IDs, then run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q` and `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 5: Commit and push.**

  ```sh
  git add Hangboards/dewoodstok-woodbord Hangboards/escape-beta Hangboards/escape-unlimited Hangboards/catalog.json docs/source-audits/2026-08-12-dewoodstok-escape-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author DeWoodstok and Escape board packages"
  git push origin HEAD
  ```

### Task 5: Audit and author the Evolv and Frictitious batch

**Files:**
- Create: `docs/source-audits/2026-08-12-evolv-frictitious-board-packages.md`
- Create: `Hangboards/evolv-kilter-basic-long/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/frictitious-doormount-pro-7/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/frictitious-megalith/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: official Evolv and Frictitious source sets.
- Produces: only complete packages for `evolv.kilter-basic-long`, `frictitious.doormount-pro-7`, and `frictitious.megalith`.

- [ ] **Step 1: Capture the three complete official source sets in the audit.**

  Record product, straight-on, oblique where needed, and official numbered/measurement sources with their checked date, then write evidence-key rows for every package field and retained asset.

- [ ] **Step 2: Enforce source readiness before package work.**

  Add a source-gap section for each candidate missing official evidence for any hold count, depth/size, capacity, or classification. Leave blocked candidates exactly primary-only and unregistered.

- [ ] **Step 3: Author and evidence-map every ready package.**

  Build the four JSON sidecars using only official facts; use normalized vector geometry traced as reviewed-human-authored normalization of official imagery; map every physical/artwork hold ID exactly; and map only manufacturer-supported routine semantics.

- [ ] **Step 4: Register and verify ready packages.**

  Add ready IDs in deterministic catalog order, extend the package fixtures/assertions for their expected hold-ID sets, and run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q` followed by `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 5: Commit and push.**

  ```sh
  git add Hangboards/evolv-kilter-basic-long Hangboards/frictitious-doormount-pro-7 Hangboards/frictitious-megalith Hangboards/catalog.json docs/source-audits/2026-08-12-evolv-frictitious-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author Evolv and Frictitious board packages"
  git push origin HEAD
  ```

### Task 6: Audit and author the single-board documentation batch

**Files:**
- Create: `docs/source-audits/2026-08-12-single-board-documentation-packages.md`
- Create: `Hangboards/lattice-triple-rung/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/moon-armstrong/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/nature-stoak-board-iii/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/target10a-linebreaker-base/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: the independent official source sets for Lattice, Moon, Nature, and Target10a.
- Produces: zero to four complete packages for the four stable IDs in the batch table.

- [ ] **Step 1: Record the four independent official audits.**

  In one audit document, use a separate source/evidence table and date for each manufacturer. Capture only official product, front, oblique as required, and hold-guide/measurement documents; identify every required package evidence key before writing any JSON.

- [ ] **Step 2: Record blockers or author full packages.**

  For each candidate, either write the exact missing official hold evidence and leave it unregistered, or create all four sidecars with source-backed board fields, holds, semantic mappings, artwork, and evidence maps. Never create a partial package.

- [ ] **Step 3: Catalog/test/validate the accepted set.**

  Add only successful package IDs to `catalog.json`, assert their exact physical/artwork hold-ID equality in `test_approved_board_packages.py`, and run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q` plus `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 4: Commit and push.**

  ```sh
  git add Hangboards/lattice-triple-rung Hangboards/moon-armstrong Hangboards/nature-stoak-board-iii Hangboards/target10a-linebreaker-base Hangboards/catalog.json docs/source-audits/2026-08-12-single-board-documentation-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author documented single-board packages"
  git push origin HEAD
  ```

### Task 7: Audit and author the Metolius batch

**Files:**
- Create: `docs/source-audits/2026-08-12-metolius-board-packages.md`
- Create: `Hangboards/metolius-climbers-edge/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/metolius-contact/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/metolius-project/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/metolius-simulator-3d/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: official Metolius product pages, images, hold-depth diagrams, and manuals; the existing Compact II audit is a source-format reference only, not evidence for another product.
- Produces: only source-complete Metolius packages for the four listed IDs.

- [ ] **Step 1: Build the Metolius evidence audit.**

  Record dedicated official sources for each model. Do not apply Compact II dimensions or numbered depths to another board; list an exact official source ID for each model's product facts, per-hold facts, geometry, semantics, primary PNG, and any retained manufacturer photo.

- [ ] **Step 2: Gate each model on its own complete hold documentation.**

  Add an exact blocker row for a model whose documents do not support all hold facts. A shared manufacturer product page alone does not make a model ready.

- [ ] **Step 3: Author full sidecars for every ready model.**

  Create each ready package with exact cross-document board IDs, complete unique physical holds, normalized artwork containing exactly those hold IDs, source-backed semantic groups, `presentation.assetPath = "assets/primary.png"`, and exact evidence maps.

- [ ] **Step 4: Register, test, and validate the accepted models.**

  Update the flat registry in ID order; add exact hold-ID assertions; run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q`; then run `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 5: Commit and push.**

  ```sh
  git add Hangboards/metolius-climbers-edge Hangboards/metolius-contact Hangboards/metolius-project Hangboards/metolius-simulator-3d Hangboards/catalog.json docs/source-audits/2026-08-12-metolius-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author Metolius board packages"
  git push origin HEAD
  ```

### Task 8: Audit and author the So iLL and Tension batches

**Files:**
- Create: `docs/source-audits/2026-08-12-soill-tension-board-packages.md`
- Create: `Hangboards/soill-iron-palm-2/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/soill-split-palm/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/soill-training-tiles/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/tension-grindstone/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/tension-honestone/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/tension-whetstone/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: official So iLL and Tension material for six independent models.
- Produces: only full packages with `soill.*` and `tension.*` IDs listed above.

- [ ] **Step 1: Audit all six products separately.**

  Record individual official source sets and exact evidence-key tables. Do not use one model's hold diagram to support another model's capacity, depth, grip, or geometry.

- [ ] **Step 2: Split supported and blocked models without changing package state.**

  For every missing official hold field, write the exact blocker paragraph and leave the directory unregistered/primary-only. For every fully supported model, proceed directly to complete package authoring.

- [ ] **Step 3: Create sidecars and evidence for supported models.**

  Create all four documents at once, include only one generated primary image, use declared official source IDs for every evidence key, and ensure semantic IDs name only supported physical-hold groups.

- [ ] **Step 4: Update registry/test inventory and validate.**

  Add ready IDs, assert each package's physical/artwork hold equality, run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q`, and run `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 5: Commit and push.**

  ```sh
  git add Hangboards/soill-iron-palm-2 Hangboards/soill-split-palm Hangboards/soill-training-tiles Hangboards/tension-grindstone Hangboards/tension-honestone Hangboards/tension-whetstone Hangboards/catalog.json docs/source-audits/2026-08-12-soill-tension-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author So iLL and Tension board packages"
  git push origin HEAD
  ```

### Task 9: Audit and author the Trango batch

**Files:**
- Create: `docs/source-audits/2026-08-12-trango-board-packages.md`
- Create: `Hangboards/trango-rock-prodigy-forge/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/trango-rock-prodigy-natural/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/trango-rock-prodigy-pivot/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: official Trango sources for Forge, Natural, and Pivot. The existing Training Center package is not cross-model evidence.
- Produces: source-complete `trango.rock-prodigy-forge`, `trango.rock-prodigy-natural`, and `trango.rock-prodigy-pivot` packages where supported.

- [ ] **Step 1: Create the product-specific Trango audit.**

  Capture official product pages, product imagery, manuals/depth guides, and checked date for each of Forge, Natural, and Pivot. Associate each candidate's exact facts and artwork/asset evidence keys with its own source IDs.

- [ ] **Step 2: Reject unsupported cross-model extrapolation.**

  If a Training Center source is the only proof of a Forge, Natural, or Pivot hold fact, write that exact source gap and keep that candidate unregistered; shared brand naming does not establish a hold map.

- [ ] **Step 3: Author complete ready packages.**

  Create all four canonical JSON documents per ready board, with declared source-backed dimensions, hold inventory, semantic mapping, and normalized vector artwork. Keep the existing generated PNG only as `assets/primary.png` and evidence-map it as an adaptation.

- [ ] **Step 4: Register and verify.**

  Add only accepted IDs to `catalog.json`, add exact hold-set assertions, and run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q` plus `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 5: Commit and push.**

  ```sh
  git add Hangboards/trango-rock-prodigy-forge Hangboards/trango-rock-prodigy-natural Hangboards/trango-rock-prodigy-pivot Hangboards/catalog.json docs/source-audits/2026-08-12-trango-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author Trango board packages"
  git push origin HEAD
  ```

### Task 10: Audit and author the YY Vertical batch

**Files:**
- Create: `docs/source-audits/2026-08-12-yy-vertical-board-packages.md`
- Create: `Hangboards/yy-verticalboard-evo/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/yy-verticalboard-first/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/yy-verticalboard-light/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/yy-verticalboard-one/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: official YY Vertical documentation for four distinct models.
- Produces: only complete `yy.verticalboard-*` packages.

- [ ] **Step 1: Record four separate official source sets.**

  In the YY audit, list the official product, front/oblique, and hold guide/measurement material independently for Evo, First, Light, and One. Write exact evidence-key coverage rows before authoring package data.

- [ ] **Step 2: Enforce the readiness decision per model.**

  Write exact source blockers for unsupported fields and make no partial package. Treat visual similarity among YY products as no evidence at all.

- [ ] **Step 3: Create complete packages for ready models.**

  Build source-backed holds, semantics, and artwork, preserve only `primary.png` as generated art, and make evidence map keys exactly equal validator-required fields/elements/assets.

- [ ] **Step 4: Catalog and validate.**

  Add ready IDs in deterministic order; extend exact hold-ID tests; run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q`; then run `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 5: Commit and push.**

  ```sh
  git add Hangboards/yy-verticalboard-evo Hangboards/yy-verticalboard-first Hangboards/yy-verticalboard-light Hangboards/yy-verticalboard-one Hangboards/catalog.json docs/source-audits/2026-08-12-yy-vertical-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author YY Vertical board packages"
  git push origin HEAD
  ```

### Task 11: Audit and author the Zlagboard batch

**Files:**
- Create: `docs/source-audits/2026-08-12-zlagboard-board-packages.md`
- Create: `Hangboards/zlagboard-evo/{board,evidence,semantics,artwork}.json`
- Create: `Hangboards/zlagboard-pro/{board,evidence,semantics,artwork}.json`
- Modify: `Hangboards/catalog.json`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`

**Interfaces:**
- Consumes: official Zlagboard material for Evo and Pro.
- Produces: complete `zlagboard.evo` and `zlagboard.pro` packages when their separate official source sets are complete.

- [ ] **Step 1: Audit official Evo and Pro sources separately.**

  Record each product's official URL, front imagery, oblique imagery where required, manufacturer hold guide/measurements, checked date, and exact map of required evidence keys.

- [ ] **Step 2: Produce blockers or full sidecars.**

  Do not derive missing fields from either model's generated image. For a ready model create all four sidecars in one change; for a blocked model record exact missing fields and retain only its primary image.

- [ ] **Step 3: Register/test/validate ready models.**

  Update the flat catalog only for ready models, assert physical and artwork IDs match, run `python3 -m pytest Tools/HangboardPipeline/tests/test_approved_board_packages.py Tools/HangboardPipeline/tests/test_board_catalog.py -q`, and run `scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json`.

- [ ] **Step 4: Commit and push.**

  ```sh
  git add Hangboards/zlagboard-evo Hangboards/zlagboard-pro Hangboards/catalog.json docs/source-audits/2026-08-12-zlagboard-board-packages.md Tools/HangboardPipeline/tests/test_approved_board_packages.py
  git commit -m "feat: author Zlagboard board packages"
  git push origin HEAD
  ```

### Task 12: Update the iOS catalog boundary and prove direct package delivery

**Files:**
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `Tools/HangboardPipeline/tests/test_board_package_staging.py`

**Interfaces:**
- Consumes: every accepted catalog entry and `BoardPackageStore.init(bundle: Bundle = .main)`.
- Produces: an application boundary test that permits only catalog-declared package data and bundle tests proving JSON/`primary.png` delivery for every accepted board.

- [ ] **Step 1: Write the failing all-catalog runtime boundary test.**

  Replace the hard-coded two-board expectation with an exact expected sorted ID list computed from the completed catalog fixture. Add an XCTest assertion that every loaded board has a non-nil presentation URL whose last path component is `primary.png` and lies below `Hangboards/` plus that catalog entry's `path` plus `assets/`.

  ```swift
  let expectedIDs = ["metolius.wood-grips-compact-ii", "trango.rock-prodigy-training-center"]
  XCTAssertEqual(BoardCatalog.all.map(\.id).sorted(), expectedIDs)
  for board in BoardCatalog.all {
      XCTAssertEqual(BoardCatalog.packageStore.presentationImageURL(for: board)?.lastPathComponent, "primary.png")
  }
  ```

- [ ] **Step 2: Run the focused XCTest target and confirm RED.**

  Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardSourceBoundaryTests -only-testing:HangTenTests/BoardPackageStoreTests`

  Expected: RED until the expected fixture list/staged-package assertions are updated for accepted authoring batches.

- [ ] **Step 3: Update runtime/staging expectations without adding board-specific app code.**

  Update the exact test ID list to match `catalog.json` after all accepted batches. In `test_board_package_staging.py`, assert the staged tree contains each catalog directory and its `assets/primary.png`, has no unregistered candidate, and byte-matches every source sidecar/asset. Do not change `BoardPackageStore.swift` unless a validated package exposes a real decoder defect; it remains generic.

- [ ] **Step 4: Run iOS/package staging GREEN.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests/test_board_package_staging.py -q
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardSourceBoundaryTests -only-testing:HangTenTests/BoardPackageStoreTests
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  ```

  Expected: the app reads package resources directly and no alternate generated board asset is bundled.

- [ ] **Step 5: Commit and push delivery verification.**

  ```sh
  git add HangTenTests/BoardSourceBoundaryTests.swift HangTenTests/BoardPackageStoreTests.swift Tools/HangboardPipeline/tests/test_board_package_staging.py
  git commit -m "test: verify direct source-backed board delivery"
  git push origin HEAD
  ```

### Task 13: Perform the final inventory, visual, and CI gates

**Files:**
- Modify: `Tools/HangboardPipeline/tests/test_generated_catalog_import.py`
- Modify: `Tools/HangboardPipeline/tests/test_approved_board_packages.py`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`
- Modify: `Hangboards/catalog.json`

**Interfaces:**
- Consumes: the 31-candidate table, accepted package sidecars, source audits, and staged application bundle.
- Produces: a final inventory that is either 33 complete catalog packages or complete explicit evidence-blocker records for every unregistered candidate; no review-state data enters the app.

- [ ] **Step 1: Write the final candidate partition test.**

  Define the 31 slugs as a literal expected set in `test_generated_catalog_import.py`. Assert their union with existing packages is 33 directories, every directory has `assets/primary.png`, every registered package validates, and every unregistered directory has exactly that primary asset and a matching blocker heading in the committed batch audit.

  ```python
  candidate_slugs = {
      "beastmaker-1000", "beastmaker-2000", "dewoodstok-woodbord", "escape-beta",
      "escape-unlimited", "evolv-kilter-basic-long", "frictitious-doormount-pro-7",
      "frictitious-megalith", "lattice-triple-rung", "metolius-climbers-edge",
      "metolius-contact", "metolius-project", "metolius-simulator-3d", "moon-armstrong",
      "nature-stoak-board-iii", "soill-iron-palm-2", "soill-split-palm",
      "soill-training-tiles", "target10a-linebreaker-base", "tension-grindstone",
      "tension-honestone", "tension-whetstone", "trango-rock-prodigy-forge",
      "trango-rock-prodigy-natural", "trango-rock-prodigy-pivot", "yy-verticalboard-evo",
      "yy-verticalboard-first", "yy-verticalboard-light", "yy-verticalboard-one",
      "zlagboard-evo", "zlagboard-pro",
  }
  assert candidate_slugs <= {path.name for path in (REPO_ROOT / "Hangboards").iterdir() if path.is_dir()}
  assert unregistered == blockers_documented_in_source_audits
  ```

- [ ] **Step 2: Run the final inventory test to establish RED.**

  Run: `python3 -m pytest Tools/HangboardPipeline/tests/test_generated_catalog_import.py -q`

  Expected: RED until its expected candidate set and blocker/registration partition match the audited source work.

- [ ] **Step 3: Reconcile the source-audit and runtime inventories.**

  Update the literal 31-slug test set, each catalog-derived expected ID list, and each audit's accepted/blocker sections. A candidate may be in exactly one of the registered validated set or the exact blocker set. Remove no primary image unless replacing it with the same package's canonical `assets/primary.png`; remove any discovered README, review directory, outline, or alternate generated image.

- [ ] **Step 4: Run full automated verification.**

  Run:

  ```sh
  python3 -m pytest Tools/HangboardPipeline/tests -q
  scripts/hangboard-tools.sh catalog validate --catalog Hangboards/catalog.json
  scripts/hangboard-tools.sh catalog status --catalog Hangboards/catalog.json
  xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
  xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
  ```

  Expected: all tests pass, catalog validation succeeds, and catalog status contains only IDs and paths.

- [ ] **Step 5: Visually validate each newly registered board on the owned simulator.**

  Follow `validate-hang-ten-ios` on a simulator named with the current `CONDUCTOR_WORKSPACE_NAME`. Inspect each package board's normal and active hold rendering in portrait and landscape; verify its presentation is `primary.png`, highlighted shapes match the same `artwork.json` hold pieces, and no screw holes, alternate previews, generated variants, or review-state labels render. Shut down and delete the exact owned simulator afterward.

- [ ] **Step 6: Commit and push the final inventory.**

  ```sh
  git add Hangboards/catalog.json Hangboards Tools/HangboardPipeline/tests/test_generated_catalog_import.py Tools/HangboardPipeline/tests/test_approved_board_packages.py HangTenTests/BoardSourceBoundaryTests.swift docs/source-audits
  git commit -m "feat: complete source-backed hangboard catalog"
  git push origin HEAD
  ```

## Self-review

- Spec coverage: Tasks 1–2 enforce the state-free/primary-only canonical shape; Tasks 3–11 apply the mandatory official-source readiness gate to all 31 named candidates; Task 12 proves direct iOS package consumption; Task 13 verifies the complete catalog-or-explicit-blocker result, CI, and visual rendering.
- No-invention coverage: every batch requires official product/front/oblique/hold source material before package JSON, records an exact blocker otherwise, and forbids generated images or existing runtime data as factual evidence.
- Type/interface consistency: all tasks use the existing `load_board_package` and `validate_catalog` interfaces and the existing `BoardPackageStore` package bundle interface; no new runtime model or lifecycle field is introduced.
- Placeholder scan: package paths, candidate slugs, catalog IDs, audit paths, test files, commands, and commit messages are all concrete. Source facts intentionally are not prefilled: doing so before manufacturer verification would violate the goal.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-12-full-source-backed-board-authoring.md`.

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task with review between tasks.
2. **Inline Execution** — execute tasks in this session with checkpoints.
