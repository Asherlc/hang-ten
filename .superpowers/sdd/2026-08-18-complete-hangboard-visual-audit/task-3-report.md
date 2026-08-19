# Task 3 report — Complete source, metadata, and geometry audit

Status: **DONE_WITH_CONCERNS**

Commit: `Audit and refine complete hangboard catalog` (this report is included
in that commit).

The complete 34-board source/metadata/geometry audit is implemented. All
authoritative high-confidence scalar corrections and supported removals from
the reviewed matrix were applied. The catalog-generic presentation crop was
materialized for 27 packages. No derived hold contour passed the complete
authoritative inventory, topology, symmetry/multi-piece, and coordinate-free
mapping contract, so geometry materialization correctly failed closed for all
boards.

## Retained BEFORE evidence and exact manifest

- Contact sheet (3150×13008):
  `docs/source-audits/assets/2026-08-18-complete-hangboard-visual-audit/before-contact-sheet.png`
- Per-board directory:
  `docs/source-audits/assets/2026-08-18-complete-hangboard-visual-audit/before/`
- Count: 34 full-resolution PNGs, one for each completed package and exactly
  equal to package discovery IDs.
- Capture manifest used for the equality assertion:
  `.context/all-board-audit/task-3-before/manifest.json` (workspace evidence,
  intentionally ignored by git).

Exact per-board screenshot manifest:

1. `before/beastmaker-1000--4fee18798954.png`
2. `before/beastmaker-2000--305c473cc719.png`
3. `before/dewoodstok-woodbord--e40376735372.png`
4. `before/escape-beta--dd6fe9b3a8dc.png`
5. `before/escape-beta-22--245680ffb240.png`
6. `before/escape-unlimited--19831f6dfe62.png`
7. `before/evolv-kilter-basic-long--ac4049aa3a2d.png`
8. `before/frictitious-doormount-pro-7--8a23c5cc8dca.png`
9. `before/frictitious-megalith--33de4ccadb0c.png`
10. `before/lattice-triple-rung--98ec533951a6.png`
11. `before/metolius-climbers-edge--1e84e2649b1d.png`
12. `before/metolius-contact--ec276e428883.png`
13. `before/metolius-project--5007e676de90.png`
14. `before/metolius-simulator-3d--ad3f6e0bbb16.png`
15. `before/metolius.wood-grips-compact-ii--ecd2a502a9db.png`
16. `before/moon-armstrong--3e59a2c3ad25.png`
17. `before/nature-stoak-board-iii--23853bedbe8d.png`
18. `before/soill-iron-palm-2--eb1bcad6f0bc.png`
19. `before/soill-split-palm--cc07b6832b7c.png`
20. `before/soill-training-tiles--073b9c42fd16.png`
21. `before/target10a-linebreaker-base--83a10cb8e4e0.png`
22. `before/tension-grindstone--4c704daf13a7.png`
23. `before/tension-honestone--223e0ec49199.png`
24. `before/tension-whetstone--c085c83b3df1.png`
25. `before/trango-rock-prodigy-forge--3524ced1ecba.png`
26. `before/trango-rock-prodigy-natural--7f4ed5768d6a.png`
27. `before/trango-rock-prodigy-pivot--7cf9f33e474c.png`
28. `before/trango.rock-prodigy-training-center--54f0d57dd133.png`
29. `before/yy-verticalboard-evo--52da4a0e33ab.png`
30. `before/yy-verticalboard-first--8a369008547e.png`
31. `before/yy-verticalboard-light--8f078a49c3e1.png`
32. `before/yy-verticalboard-one--53c8899c8937.png`
33. `before/zlagboard-evo--e51ac1a87bfb.png`
34. `before/zlagboard-pro--af6b10e747d3.png`

Every per-board capture and the contact sheet were visually inspected. No SVG
canvas clips an expected manifest region. Seven audited packages visually
retain strong path alignment; the other 27 expose coarse, omitted, or
misgrouped topology and remain explicit geometry blockers.

## Per-board disposition summary

The full audit row, primary manufacturer URL(s), exact baseline inventory
hash, and H/P/point counts for every board are in
`docs/source-audits/2026-08-18-complete-hangboard-visual-audit.md`.

| board | metadata disposition | geometry/presentation disposition |
| --- | --- | --- |
| beastmaker-1000 | 580 × 150 mm face dimensions retained; thickness withheld after final review | retain audited paths; no crop; numbered mapping absent |
| beastmaker-2000 | unchanged | retain audited paths; no crop; numbered mapping absent |
| dewoodstok-woodbord | unchanged | retain audited paths; no crop; depth-to-ID map absent |
| escape-beta | legacy facts withheld | no materialization; generic crop |
| escape-beta-22 | unchanged | retain audited paths; no crop; 11/22 grouping unresolved |
| escape-unlimited | dimensions and required subtitle corrected | no materialization; generic crop |
| evolv-kilter-basic-long | dimensions corrected | no materialization; generic crop |
| frictitious-doormount-pro-7 | dimensions corrected; unsupported optional semantics removed | no materialization; generic crop; 7/8 record mismatch blocked |
| frictitious-megalith | dimensions corrected | no materialization; generic crop |
| lattice-triple-rung | unchanged | retain audited paths; no crop |
| metolius-climbers-edge | current-version facts withheld | no materialization; generic crop |
| metolius-contact | dimensions corrected; unsupported optional semantics removed | no materialization; generic crop |
| metolius-project | dimensions corrected | no materialization; generic crop |
| metolius-simulator-3d | dimensions corrected; unsupported optional semantics removed | no materialization; generic crop |
| metolius.wood-grips-compact-ii | unchanged | retain audited paths; no crop |
| moon-armstrong | dimensions corrected | no materialization; generic crop; likely model mismatch |
| nature-stoak-board-iii | dimensions corrected | no materialization; generic crop; adjustable state unresolved |
| soill-iron-palm-2 | canonical URL repaired | no materialization; generic crop |
| soill-split-palm | canonical URL repaired | no materialization; generic crop |
| soill-training-tiles | canonical URL repaired | no materialization; generic crop |
| target10a-linebreaker-base | unsupported secondary facts withheld | no materialization; generic crop |
| tension-grindstone | dimensions corrected | no materialization; generic crop |
| tension-honestone | contradicted end-pocket capacity removed | no materialization; generic crop |
| tension-whetstone | dimensions corrected; contradicted 4F semantics removed | no materialization; generic crop |
| trango-rock-prodigy-forge | unchanged | no materialization; generic crop |
| trango-rock-prodigy-natural | dimensions corrected | no materialization; generic crop |
| trango-rock-prodigy-pivot | unsupported facts withheld | no materialization; generic crop; orientation contract absent |
| trango.rock-prodigy-training-center | unchanged | retain audited multi-piece paths; no crop |
| yy-verticalboard-evo | dimensions corrected; contradicted 3F semantics removed | no materialization; generic crop |
| yy-verticalboard-first | dimensions corrected; unsupported 3F semantics removed | no materialization; generic crop |
| yy-verticalboard-light | dimensions corrected | no materialization; generic crop |
| yy-verticalboard-one | dimensions corrected; contradicted 3F semantics removed | no materialization; generic crop |
| zlagboard-evo | unsupported generation-specific facts withheld | no materialization; generic crop |
| zlagboard-pro | unsupported generation-specific facts withheld | no materialization; generic crop |

## Source field mappings

Authoritative scalar corrections:

- 16 dimensions: Escape Unlimited; Evolv Basic Long; Frictitious Pro 7 and
  Megalith; Metolius Contact, Project, and Simulator 3-D; Moon Armstrong;
  Nature Stoak III; Tension Grindstone and Whetstone; Trango Natural; YY Evo,
  First, Light, and One. Final review supersedes the earlier Beastmaker 1000
  thickness correction: its 580 × 150 mm face dimensions remain unchanged and
  thickness is withheld because 58 mm is documented only for a separate Beech
  variant.
- Three canonical product URLs: So iLL Iron Palm 2.0, Split Palm, and Training
  Tiles.
- Escape Unlimited schema-required subtitle replaced with the sourced four
  descending finger-pad depth-level description.

Supported optional-semantic removals:

- Pro 7, Contact, and Simulator: unsupported `gripType`, `fingerCapacity`, and
  `features` mappings removed from retained schema-required records.
- YY Evo, First, and One: unsupported/contradicted 3F grip and capacity removed
  from the affected two pocket records per package.
- Tension Whetstone: contradicted 4F grip and capacity removed.
- Tension Honestone: contradicted capacity 4 removed. Its retained 4F grip type
  is called out below as a concern rather than silently replaced.

No schema-required hold, kind, or geometry was deleted and no replacement
per-hold semantic was inferred.

## Geometry materialization, point gates, and blockers

The complete image-only derivation over 34 boards produced seven unlabeled
candidates across four boards (Beastmaker 1000: 2; deWoodstok: 1;
Frictitious Megalith: 1; Training Center: 3), 4,704 rejections, zero verified
symmetry pairs, zero drafts, and zero command errors. Report SHA-256:
`5316c10ae7cab909b044ceeab3649a5e5c4777bbeb519cd7a727cbe8f206d393`.

No candidate set had all of authoritative inventory, complete candidate
topology, verified symmetry/multi-piece policy, and a complete hash-bound
coordinate-free mapping. Materializations: **0**. No coordinates, masks,
per-board templates, or product-specific tuning were authored.

The generic simplifier examined all 34 packages under its normal write gate:
zero eligible changes and 240 unsupported rounded rectangles. Editable points
remain exactly **1,890 → 1,890**. Because no simplification was accepted,
accepted native-pixel maximum deviation and symmetric-difference totals are
both 0.0. The post-write dry run reports zero changes.

The generic presentation normalizer accepted exact pixel-subset crops for 27
packages and reprojected their existing geometry frames to the same native
pixels. Seven packages were already normalized. Its post-write dry run reports
zero changes.

Before and after remain exactly 34 boards, 359 ordered logical holds, 363
geometry pieces, and 1,890 editable points. All coordinate-free inventory
hashes are unchanged except the eight documented optional-semantic removals;
the exact before/after hash pairs are recorded in the audit document.

## Red-green evidence

1. Added focused complete-catalog source/data assertions first.
2. Initial run: two expected failures for authoritative facts and optional
   semantics.
3. Applied the minimum package changes; focused run: 2 passed.
4. First presentation write failed closed because removing Escape Unlimited's
   subtitle violated a schema requirement.
5. Added the required-subtitle assertion and observed the focused red failure.
6. Wrote the source-backed four-level subtitle; focused run: 2 passed.

## Validation and idempotence

```sh
rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  Tools/HangboardPipeline/tests/test_complete_catalog_source_audit.py -q
# 2 passed

# From Tools/HangboardPipeline
rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=../../.context/task-2-pythonpath python3 -m pytest \
  tests/test_board_presentation.py tests/test_board_path_simplification.py \
  tests/test_approved_board_packages.py \
  tests/test_complete_catalog_source_audit.py -q
# 41 passed

# From Tools/HangboardWorkbench
rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  tests/test_board_geometry.py tests/test_board_package.py -q
# 72 passed

rtk scripts/hangboard-tools.sh packages validate --root Hangboards
# 34 completed packages; zero drafts; exit 0

rtk scripts/hangboard-tools.sh packages simplify-hold-paths --root Hangboards
# 34 boards; 0 changed; 1,890 points retained

rtk scripts/hangboard-tools.sh packages normalize-presentations --root Hangboards
# 34 boards; 0 changed after write

rtk git diff --check
# clean
```

## Concerns

- Twenty-seven packages still have unresolved authoritative hold-boundary or
  grouping contracts. They were intentionally left geometrically unchanged
  apart from exact crop/reprojection; the board table states each blocker.
- Tension Honestone's manufacturer inventory contradicts the retained
  `fourFingerPocket` grip type, but the approved matrix only supports removing
  capacity 4 and does not provide a complete per-ID replacement map. The grip
  type remains rather than inventing mono placement.
- Escape Beta's accessible manufacturer page describes the current Beta Board;
  the package's legacy identity and facts remain unverified.
- Zlagboard generation identity and Trango Pivot orientation semantics remain
  unresolved, so generation/orientation-specific metadata was withheld.

## Fix round 1 — authoritative product identities

Status: **DONE_WITH_CONCERNS**. This follow-up corrects two omitted identity
fields without changing any hold, piece, geometry, or screenshot asset.

The reviewed Frictitious package audit identifies the exact current model URL
as `https://frictitiousclimbing.com/en-ca/products/doormount-pro`; that literal
replaces the stale `frictitious.com/products/doormount-pro-7` value. The current
So iLL product page identifies the model as `Iron Palm 2.0`; the package name
now matches it exactly. The canonical audit's opening policy now says only
selected matrix-approved optional semantics were removed and explicitly names
Tension Honestone's retained blocked `fourFingerPocket` semantic.

Red/green evidence:

```sh
rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  Tools/HangboardPipeline/tests/test_complete_catalog_source_audit.py -q
# RED: 2 failed, 2 passed
# - stale Frictitious URL was https://frictitious.com/products/doormount-pro-7
# - stale So iLL name was Iron Palm 2

rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  Tools/HangboardPipeline/tests/test_complete_catalog_source_audit.py -q
# GREEN: 4 passed
```

Cross-suite/package validation:

```sh
# From Tools/HangboardPipeline
rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=../../.context/task-2-pythonpath python3 -m pytest \
  tests/test_board_presentation.py tests/test_board_path_simplification.py \
  tests/test_approved_board_packages.py \
  tests/test_complete_catalog_source_audit.py -q
# 43 passed

# From Tools/HangboardWorkbench
rtk env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  tests/test_board_geometry.py tests/test_board_package.py -q
# 72 passed

rtk scripts/hangboard-tools.sh packages validate --root Hangboards
# 34 completed packages; zero drafts; exit 0
```

The package inventory assertion remains exactly 359 ordered logical holds and
363 geometry pieces. The retained baseline remains 35 PNG files (34 per-board
BEFORE captures plus the contact sheet), with deterministic path-and-content
tree SHA-256
`34d0d8f85c4bedd9704c630fcfede9d27971567c56dbbde243185fd1b3aaeb26`.
`git diff` against the original Task 3 commit reports no changed baseline
asset path. `git diff --check` is clean.
