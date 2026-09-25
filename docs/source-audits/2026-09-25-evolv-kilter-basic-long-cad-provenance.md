# Evolv Kilter Basic Board (Long) — native CAD provenance

2026-09-25. This board gained a native FreeCAD source
(`Hangboards/evolv-kilter-basic-long/evolv-kilter-basic-long.FCStd`) authored as
a **display simplification**. It replaces the previous committed runtime asset;
`board.json` is now generated from the FCStd's `HangTenBoardManifest` at build
time and is no longer committed.

## Sources (reused; re-verified)

Product identity, overall dimensions, material, and the four labelled holds are
from Evolv's product page and manufacturer imagery, as already audited in
`docs/source-audits/2026-08-12-evolv-frictitious-board-packages.md` and
re-confirmed in its 2026-08-25 section:

- Product page: <https://www.evolvsports.com/en-us/basic-training-board-_long_-66-0000082105>
- Straight-on official image: <https://oberalp.imgix.net/ef857c73-13f1-4205-ac47-706cd101e1bb.jpg?auto=format&cs=srgb&fit=clip&type=still&w=628>

Published facts used: overall 79 × 16 × 6 cm; holds `jug-rounded` (rounded jug),
`edge-20`, `edge-15`, `edge-10` (20 / 15 / 10 mm rounded edges). No depth is
published for the jug.

## What is source-bound vs authored

- **Source-bound:** product identity, overall dimensions, hold inventory, and the
  three grip depths (20 / 15 / 10 mm).
- **Authored (display simplification):** the board's cross-section. It is
  **measured from the approved committed display mesh** at revision
  `91ab368f9` (`Hangboards/evolv-kilter-basic-long/assets/primary.usdz`, sha256
  `82a20c9772978184369799408c716232a96cbaa3e05781c5cb54f40de8430b41`) — an
  ordered boundary loop of the projected body + contact triangles, simplified to
  0.05 mm and authored as a fully constrained Sketcher profile — not recovered
  manufacturing geometry. The sculpted reference surface is simplified to a
  prismatic comb.

## Method

`Tools/HangboardCAD` starter scripts (`.context`, not committed): the vector
profile is extracted from `assets/primary.usdz` and authored as a
`lattice-triple-rung`-style sketch + pad, with one contiguous run of the
profile's own sketch edges extruded per hold, capped at that hold's published
grip depth. Contact regions are bound to sketch edges resolved by position, never
to pad faces.

## Verification

- `compile_board`: feature tree recomputes cleanly; published-depth gate passes
  (`edge-20` 20.000, `edge-15` 14.999, `edge-10` 9.985 mm); descriptor
  `modelBounds` 0.790 × 0.15994 × 0.06 m matches the published envelope.
- `verify_reproducible`: the committed asset rebuilds byte-identically
  (`5727cb40d8f4f19f…`).
- Package validation passes (`scripts/hangboard-packages.sh validate`).

## Preview evidence

`docs/source-audits/2026-09-25-evolv-kilter-basic-long-cad-preview.png` renders
the migrated board (left) beside the superseded reference at revision `91ab368f9`
(right) for front, side, and top (`Tools/HangboardCAD/preview.py`; CPU geometry
renders, not native SceneKit).

## Caveats

- The board is a **display simplification**, not product-accurate and not
  manufacturing-ready.
- No in-app (native SceneKit) verification was performed for this change; review
  evidence is the CPU preview renders (front/side/top) against the superseded
  committed asset.
- `HangTenSourceKind` is `native-parametric-measured-profile`: the profile is
  measured from the approved mesh, so the measured label is accurate.
