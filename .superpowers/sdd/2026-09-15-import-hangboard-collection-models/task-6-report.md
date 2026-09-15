# Task 6 — Trango Rock Prodigy Training Center model migration

Completed 2026-09-15.

## Delivered package

- Replaced the raster presentation with the sole hash-bound model pair:
  `assets/primary.usdz` (`bdb9c3867d6adefe2f356612d49597b8e9c528f556f1f5b9bc12c97fc05aba1d`)
  and `assets/primary.model.json` (`026573be4eb702f64d8a807e7a2685356949e381ddab73ff3e49aa486d90bda6`).
- Removed `assets/primary.png`, all raster contact geometry, canonical paths,
  cached frames, and fallback media. The package inventory is exactly
  `board.json`, `assets/primary.usdz`, and `assets/primary.model.json`.
- Preserved the exact existing Training Center revision identity and all 24
  ordered catalog contact IDs and facts. A preexisting-facts comparison (with
  presentation removed) differs only by the final newline.

## Revision isolation and mapping decision

The source audit retains the official Training Center front image and use
instructions, plus the supplied GLB. The review uses no Forge, Natural, or
Pivot facts. The supplied GLB SHA-256 is
`59bb4bc1d1930b2fa14266d5f17e67859815912e2decab15dd1861c07f452c57`.

It has two body meshes and 20 named contact meshes. Its two
`pinch-combination-*` meshes each represent two existing overlapping pinch
selection identities. The only source correction is therefore contract-only:
two linked source nodes per side bind the existing medium/wide pinch IDs while
sharing the untouched supplied mesh data. The corrected transport source SHA
is `44f578442c2b80e05e4c790d81b99790defdf147ea7e5a1b3ab13f7faedf5ac5`.
Every other supplied contact mesh maps explicitly and one-to-one to its
existing ID; both body meshes remain nonselectable.

## Exact shipped verification

`Tools/HangboardModels/verify_trango_rock_prodigy_training_center.py` checks
the exact shipped file hash, imports the USDZ into an empty Blender scene,
rebuilds the descriptor from the actual imported triangles, and requires its
24-contact keyset and distinct left/right medium/wide pinch node bindings. The
retained result reports 26 nodes (two body and 24 contact), and descriptor
equality with the imported USDZ. Its Blender-free companion test locks the
ordered 24 IDs and four independent pinch bindings.

All generated source, mapping, evidence, and verification artifacts are under
the workspace-owned ignored `.context/lumpy-liger-hangboard-collection/trango-rock-prodigy-training-center/` directory. No HTTP server or external runtime
resource was created.

## Reviewer follow-up — model-only package regression

The prior board-package test still read the removed raster
`media.contactGeometry` and failed with `KeyError` after this migration. It
now verifies the model-only package boundary, descriptor schema/frame, exact
USDZ SHA-256 binding, complete 24-contact inventory, two body nodes, and all
four separate bilateral pinch bindings. Focused command:
`Tools/HangboardPackages/.venv/bin/python -m pytest tests/test_trango_rock_prodigy_training_center_board_package.py -q` — `1 passed`.
