# All-board metadata and physical-hold audit implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task with fresh implementers and review checkpoints.

**Goal:** Reconcile every `Hangboards/*/board.json` with current online evidence so app content contains no unsupported product facts, missing physical holds, duplicated logical holds, or invented hold regions.

**Architecture:** Keep `Hangboards/` as the 34-product source library. A package with a complete, source-backed `board.json` remains directly discoverable; a product whose current physical inventory cannot be mapped without inventing facts is demoted to the repository's supported `assets/primary.png`-only draft shape. Preserve every product image. Record one durable 34-row source audit and use the existing discovery boundary to prove only defensible packages ship.

**Tech stack:** JSON, Markdown, Python/pytest, Swift/XCTest, repository hangboard tools.

## Global constraints

- Follow `docs/ADDING_A_BOARD.md`: required hold fields are `id`, `name`, `kind`, and nonempty normalized `geometry`; omit optional measurements, capacities, grip types, and features when evidence does not establish them.
- Treat one physical contact region as one hold. Multiple geometry pieces may form one hold, but an arbitrary left/right split through one continuous cavity is not two physical holds.
- Do not hand-author replacement coordinates, masks, product-specific geometry code, or per-board visual tuning. The scalable-pipeline rule makes an image-only draft safer than an invented reconstruction.
- Do not delete `assets/primary.png`. A retired package must contain exactly `assets/primary.png` under `assets/`.
- This is a configuration/content audit. Per the repository exception, do not add source-text regression tests; update existing exact expectations and validate with existing parsers, renderers, and tests.
- Do not modify training-plan instructions or invent routine semantics.

## Final active inventory

The source audit should justify exactly these seven finished packages:

- `beastmaker-1000`
- `beastmaker-2000`
- `dewoodstok-woodbord`
- `escape-beta-22`
- `evolv-kilter-basic-long`
- `lattice-triple-rung`
- `metolius-wood-grips-compact-ii`

All other current package directories remain present as primary-image-only drafts until a source-backed, scalable reauthoring can establish their complete physical inventory.

## Task 1: Publish the 34-product source audit

**Files:**

- Create: `docs/source-audits/2026-08-19-all-board-metadata-hold-audit.md`

- [ ] Create a single audit covering all 34 package slugs, checked 2026-08-19.
- [ ] For every board record its authoritative/current product sources, current JSON hold count, source-backed expected physical count or explicit unknown, verified identity/dimensions/material facts, exact discrepancy, and final action (`keep`, `correct`, or `primary-only draft`).
- [ ] Include `### \`slug\`` headings for every demoted package so the existing blocker-heading parser can recognize all 27 drafts.
- [ ] Explain that the 2026-08-19 audit supersedes earlier readiness conclusions where the single-file schema made optional metadata omissible.
- [ ] Verify all links and the 7/27 decision against the research brief; do not broaden secondary evidence into unsupported facts.

## Task 2: Restore the evidence-gated discovery boundary

**Files:**

- Delete: `Hangboards/<slug>/board.json` for every current package except the seven in **Final active inventory**.
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`
- Modify: `Tools/HangboardPipeline/tests/test_generated_catalog_import.py`

- [ ] Remove only the 27 unsupported `board.json` files; retain each exact product directory and `assets/primary.png`.
- [ ] Change the Swift catalog expectation to the seven retained board IDs. Remember the Metolius folder's document ID is `metolius.wood-grips-compact-ii`.
- [ ] Add the new source audit filename to `SOURCE_AUDITS` so the existing image-only draft contract recognizes the consolidated blocker headings.
- [ ] Run `rtk scripts/hangboard-tools.sh packages validate --root Hangboards` and the focused generated-catalog/Swift boundary tests. Do not use `--final-inventory`, because 27 deliberate drafts must remain.

## Task 3: Correct the seven active packages

**Files:**

- Modify: `Hangboards/beastmaker-1000/board.json`
- Modify: `Hangboards/beastmaker-2000/board.json`
- Modify: `Hangboards/dewoodstok-woodbord/board.json`
- Modify: `Hangboards/escape-beta-22/board.json`
- Modify: `Hangboards/evolv-kilter-basic-long/board.json`
- Modify: `Hangboards/lattice-triple-rung/board.json`
- Modify only if needed for canonical URL cleanup: `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Modify existing exact-value package tests as required; do not create new tests.

- [ ] Beastmaker 1000: use the canonical manufacturer page and `580 × 150 × 58 mm`; preserve the 22 visible regions; remove unsourced per-pocket millimeter values and derived optional semantics; retain only facts established by Beastmaker's enumerated inventory and official imagery.
- [ ] Beastmaker 2000: preserve the 25 visible regions and `580 × 150 × 58 mm`; remove image-inferred millimeter values and derived optional semantics except a clearly mapped official fact. Keep labels conservative when the product page supplies only grouped inventory.
- [ ] deWoodstok Woodbord: preserve 17 regions and `590 × 148 × 40 mm`; replace the unsupported `FSC-certified` subtitle with source-backed solid/certified bamboo wording. Preserve capacities only where the official 12 four-finger plus 4 two-finger inventory and visible layout establish the mapping.
- [ ] Escape Beta Board: model 19 physical cavities, not 22 logical halves. Keep mirrored left/right holds for families 1–8; combine the existing two geometry pieces for each continuous central family 9–11 into one `*-center` hold. Preserve sourced names/kinds/depths, remove derived grip/capacity/feature fields, and update the existing package test to assert 19 holds / 22 pieces and symmetry only for families 1–8.
- [ ] Evolv Basic Training Board (Long): set manufacturer/name/URL/dimensions/material wording from Evolv; keep four rows, reclassify the top row as the rounded jug, and map the remaining rows to the official 20/15/10 mm rounded edges in visible top-to-bottom order. Remove unsupported optional semantics.
- [ ] Lattice Triple Rung: preserve the three official 45/10/20 mm continuous edges and dimensions; remove invented fixed finger capacity and other derived optional tags because the manufacturer explicitly allows arbitrary hand width/finger selection on continuous edges.
- [ ] Metolius Compact II: keep the 19 visibly distinct regions and current sourced depth/capacity mapping; use the canonical live product URL. Do not merge visually separate side rails with neighboring pockets.
- [ ] Run focused package tests and the package validator.

## Task 4: Repository and simulator verification

- [ ] Run `rtk scripts/hangboard-tools.sh packages validate --root Hangboards`.
- [ ] Run the full existing Python hangboard pipeline/workbench suite through `uv` with `pytest`.
- [ ] Run `rtk scripts/export-plan-library.sh --check`.
- [ ] Build and test the iOS target on an isolated simulator according to `validate-hang-ten-ios`.
- [ ] Inspect at least one retained-board selector and active highlight, including Escape's merged center geometry and Evolv's four rows; save only useful visual evidence under `.context` or the documented audit asset path.
- [ ] Clean up every exact temporary download and owned simulator resource before completion.

