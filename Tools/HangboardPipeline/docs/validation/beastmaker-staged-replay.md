# Beastmaker 1000 staged replay — V14 promotion

The packaged Beastmaker geometry is the accepted V14 contract. It preserves
the canonical 22-region topology: 17 pockets, 3 slopers, 2 jugs, and exactly
one continuous `sloper-center`.

## Reviewed source of truth

The untracked review artifacts remain immutable under `work/real-beastmaker/`:

- `replay/v14-mixed-corner-semantics-candidate-v14/`: regions 01–05.
  The jugs keep their organic board-following outlines and deliberate hard
  transitions; the outer slopers keep their flat/vertical and sharp geometry;
  the center sloper remains one double-width region.
- `replay/v14-controlled-top-middle-v11-bottom-v12-candidate-v13/`: regions
  06–22. The upper/middle V11 geometry and contracted V12 lower row are the
  accepted visual reference.

The package records these paths in
`hangboard_vectorizer.beastmaker_v14_paths`. The path-contract SHA-256 is
`7e09b264c10f66d99290f888d525da459bcf59d4bf5844533b130a0b5f8bc367`.
Dense review polylines are promoted as cubic Bezier pocket contours within a
visually negligible tolerance; pockets are never stored as jagged vectors.

## Pinned production inputs

- Source decoded RGB SHA-256:
  `e1429eefc16670169b032545fe1093272ca0fb9b5fdb67d7a85b1289b9f19dd3`
- Packaged raster SHA-256 (unchanged):
  `4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627`
- V14 production Stage 3 SVG SHA-256:
  `8346788e3b7e8d8f7b034d19e647a07eaac3e567854a8b66ca013a2413b508ba`

The production constructor rejects any path, hash, region inventory, or
center-sloper drift before Stage 3–5 artifacts are written. The smooth board
outline also contains the four outer jug/sloper paths.

## Regression coverage

The replay tests lock the exact package path map/hash, topology and order,
mirrored pairs, approved row centerlines, outward middle pockets, genuine
Bezier pocket curves, scoped hard-edge semantics for 01–05, board containment,
and exact Stage 4 selection-mask coverage. Stage 3 embeds the one packaged
raster before the 22 overlay paths; Stage 4 regenerates all standard highlight
variants from those paths and verifies their immutable V14 evidence hashes;
Stage 5 records a fresh real-suite JUnit result. The tracked evidence fixture
also preserves the approved dense candidate map and validates each promoted
compact path by raster IoU, area delta, and centroid delta.

Run a production replay only into a new directory:

```bash
rtk env PYTHONPATH=src python -c '
from pathlib import Path
from hangboard_vectorizer.beastmaker_replay import run_replay_final

root = Path("../../work/real-beastmaker")
run_replay_final(root / "source.jpg", root / "replay" / "v18")
'
```

The replay refuses existing directories and requires a clean Git worktree.

## Superseded partial replay

`replay/v15` and `replay/v16` are retained as partial evidence: each contains
Stage 3/4 artifacts and the JUnit result, but no Stage 5 summary because a
template-invariant gate failed. `replay/v17` is the completed pre-fixture
replay. This independent-evidence update writes its completed replay to fresh
`replay/v18`; no prior replay directory is overwritten.

## Stage 4 selectable illustration replay

The accepted Stage 4 artifact is
`work/real-beastmaker/stage4-onboarding-v1/`. It is composed from only the
accepted Stage 1 V3 RGBA bytes and Stage 3 V1 vector document: the SVG embeds
the original PNG byte-for-byte and its 22 selectable paths retain the exact
Stage 3 IDs, piece assignment, type, ordering, and display paths. Its review
sheet is `stage-4-review.png`; candidate hashes are recorded in
`stage-4-candidate-hashes.json` and the comparison decision in
`stage-4-acceptance.json`. This is evidence-preserving composition rather than
procedural product redrawing.

- `stage-4-product.svg`:
  `8f4de7a71c32c2d4bce541258a3cd1cd666f8c38c534bb3c5739002d12c625c7`
- `stage-4-manifest.json`:
  `bb71cc4433875231f4a45f5c20f636e21424a1c12f778f5c00ca9015f1aeb9b5`
- `stage-4-normal.png`:
  `4afa493bb51144fef9278ee2d305acc8517beffd8cc5602ee1bf7f19d8a19d9c`
- `stage-4-highlights.json`:
  `4cd1821289300472a7939a6e9906e32d9177a854ce235c94d6fe3ea41c0cd976`
