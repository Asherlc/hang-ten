# Task 6 — Trango Rock Prodigy Training Center model migration

Completed 2026-09-15.

## Delivered package

- Replaced the raster presentation with the sole hash-bound model pair:
  `assets/primary.usdz` (`f56c6da3e001f445810dfeaa3afd69e658d3c19780664952980a28ac4b5992c1`)
  and `assets/primary.model.json` (`45b51d0390a71c0f21540dd6e682e5aa2afa15bc6e234c67edc2ffdd7c931073`).
  These are the final corrected model bytes (matching the Git LFS object OID)
  and descriptor bytes, not the LFS pointer text.
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

It has two body meshes and 22 named contact meshes. Final review rejected the
initial duplicate-node pinch export because coincident triangles cannot be
picked independently. The corrected source partitions each original
`pinch-combination-*` mesh into 3,613 lower and 5,087 upper triangles, with no
duplicates or geometry changes. The lower/medium and upper/wide assignment is
an authored display binding estimate, not a manufacturer positional fact.
The corrected native source SHA is
`a07855a4d81dd05e9dd849b7001e12c6b059acbac3e93320b7b3e24679c2055e`.
Every other supplied contact mesh maps explicitly and one-to-one to its
existing ID; both body meshes remain nonselectable.

## Exact shipped verification

`Tools/HangboardModels/verify_trango_rock_prodigy_training_center.py` checks
the exact shipped file hash, imports the USDZ into an empty Blender scene,
rebuilds the descriptor from the actual imported triangles, and requires its
24-contact keyset, distinct left/right medium/wide pinch node bindings, and
disjoint pinch triangles. The
retained result reports 26 nodes (two body and 24 contact), and descriptor
equality with the imported USDZ. Its Blender-free companion test locks the
ordered 24 IDs and every source-node-to-contact mapping individually. The final
native tests prove a reachable nearest triangle and projected screen hit for
each contact mesh, and four simulator coordinate taps selected the separate
pinch regions; see the source audit's final review evidence.

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
