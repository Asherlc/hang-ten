# j-bryant-ftg-32 CAD authoring provenance

Date: 2026-09-25. Package `Hangboards/j-bryant-ftg-32`, board ID
`j-bryant.ftg-32`, revision `amazon-b0fzgy19t9-ftg-32-2026-09` (unchanged).

This record preserves the provenance of the one-off throwaway authoring script
`.context/needy-octopus-j-bryant-ftg-32-cad/author_j_bryant_ftg_32.py`
(workspace scratch, not committed). The saved
`Hangboards/j-bryant-ftg-32/j-bryant-ftg-32.FCStd` stands alone: the shared
compiler never runs that script, and nothing in it is required to rebuild the
published runtime asset. Its embedded `HangTenBoardManifest` is now the source
of `board.json` (`Tools/HangboardCAD/board_manifest.py`); the hand-authored
`board.json` was deleted and its path added to `.gitignore`, following
`Tools/HangboardCAD/README.md` ("Authoring a new CAD board").

Evidence gate: no new visual sources were retained. Geometry reuses the exact
human-approved 2026-09-20 evidence set from
`docs/source-audits/2026-09-20-j-bryant-ftg-32-3d.md` (7 retained user
attachments + 4 fetched ASIN records, design conversation of 2026-09-20), plus
the approved compiled reference below, which is a byte-identical product of
that evidence. The operator approved proceeding on that set before authoring.
The live ASIN listing (`https://www.amazon.com/dp/B0FZGY19T9`) was re-read
during this task and corroborates the two published depths in its own copy
("shallow 0.63 in" / "deep 0.98 in"), the Beech material, and the FTG-32 part
number; the listing is mutable and its pinned bytes remain the retained
evidence.

## Reference bytes (superseded delivery)

| Artifact | SHA-256 |
| --- | --- |
| `assets/primary.usdz` (Blender-authored, retired) | `5b9c6eac0f5e2381d8d28833bdf0c723a4e512e94d034b000817f5230ac3bc3d` |
| `assets/primary.model.json` (retired) | `7b45d01a7bd46f71da3c0c1159afb89853a62d18b8d49bb002ed3fb0aaa4fbfa` |
| `board.json` (hand-authored, deleted; generated form is parsed-identical) | `8552236ab7da3458a1153a12b958611ec4a7593621eef652efb7ca33102616e8` |

## New delivery

| Artifact | SHA-256 |
| --- | --- |
| `j-bryant-ftg-32.FCStd` (native source, Git LFS) | `f531709ec16f51dd91e12c0e9c8205f3a8a92bbfbd99b3ee93b941d08204dce1` |
| `assets/primary.usdz` (compiled) | `9d2b92359e981afe15dfad90ec8d93081779def62691615f7d0c20c6d97caa8a` |
| `assets/primary.model.json` (descriptor, `modelSHA256` equals the USDZ) | `a6c786f16ff05355b8e1c2e0c5b8a22e4fb3018da8e8d604e7e8eaaa5bb0954a` |

Document properties: `HangTenBoardID=j-bryant.ftg-32`,
`HangTenPresentationID=primary`, `HangTenSchemaVersion=1`,
`HangTenSourceKind=native-parametric-measured-profile`,
`HangTenCoordinateFrame=freecad-mm-z-up-front-negative-y`,
`HangTenTessellationDeflection=0.08`. Bound nodes keep the shipped identities
`Cube_001` (body), `edge_16_mesh_001` (`edge-16`), `edge_25_mesh_001`
(`edge-25`), so suspension bindings, cord routes, cameras, and all native
tests are untouched. Descriptor bounds are identical to the retired reference:
minimum `[-0.052499998, -0.0385, -0.0185]`, maximum
`[0.052499998, 0.0385, 0.0185]` m.

## Number provenance

PUBLISHED (board manifest, ASIN listing, approved 2026-09-20 gallery):
overall 105 x 77 x 37 mm; grip depths 16 / 25 mm; beech material.

MEASURED from the reference USDZ world meshes (host OpenUSD, exact):
body spans `[0.105, 0.077, 0.037]` m; contact quads 71 mm wide at native
`z = +/-22.45` with depth spans exactly 16 / 25 mm from the front
(`Y = -18.5`); recess opening 83 x 45 with 6 mm corner radii centered at
`X/Z = 0`; upper back at native `Y = -2.5`; lower back at `Y = +6.5`;
back transition slope from `(Y=-2.5, Z=-4)` to `(Y=+6.5, Z=-8)`;
lower side walls at `X = +/-41.5` down to `Z = -16.5` with r6 corner coves
below (floor 71 wide), matching the upper corners; bores r3 at `(X,Z) =
(+/-25, 0)` through the block.

DISPLAY ESTIMATES (authored, documented here, not product facts): exterior
rounding 5.5 mm; sharp recess rim (reference lip rounding 0 mm); contact
regions as flat horizontal faces recessed 0.05 mm off each ledge, on plain
`Part::Feature` holders; analytic beech material (`0.62,0.43,0.265`, roughness
0.52) with the reference texture embedded
(`textures/nervous_frog_analytic_beech.png`, SHA-256
`fb36762f79d541032e6357c9e27181434c6a0c1ddc2c31bdb5645fbd66d470ee`).

## Construction (native mm, +X right, +Z up, front -Y)

`Part.makeBox` block at `(-52.5, -18.5, -38.5)`, then
`Part.makeFillet(5.5, shape.Edges)` over all 12 edges. The `Part::Fillet`
document object is unusable in this FreeCAD build: its `Edges` property raises
`TypeError: int() argument must be ... not 'PrimitivePy'` for both edge
objects and 1-based indices, so the primitive shape is filleted directly and
held on a plain `Part::Feature`. Then a chain of single-tool `Part::Cut`s
(each asserted by a volume trace, every step removing >100 mm^3): rounded-rect
prism (83 x 45, r6) to `Y = -2.5`; lower-center box (71 wide, to `Z = -8`) and
two lower-side boxes (`X = +/-35.5..41.5`, `Z = -16.5..-8`) to `Y = +6.5`;
sketched right-triangle prism for the below-slope band (vertices
`(Y,Z) = (-2.5,-4), (-2.5,-8), (6.5,-8)`, shape locked by coincident +
horizontal/vertical + two scalar lengths, extruded `X = +/-41.5`); two r3 bore
cylinders. Bottom corner cylinders run the full lower depth so the floor coves
survive; a full-width lower box would swallow them (measured 4 mm deviation
when tried). Contact faces are horizontal planes at native `z = +/-22.45`.

Tooling lessons, kept for the next migration: a fused recess tool
(`Part::MultiFuse`, and a rotated-box knife bounded by `Part::Common`)
produces a valid shape with correct volume whose downstream body cut silently
no-ops; `Part::Refine` does not heal it. Sequential primitive/sweep-tool cuts
behave exactly. `Part::Plane` is rejected by the archive preflight;
`Sketcher::SketchObject` + `Part::Extrusion` is accepted. `Part::Extrusion`
with `Symmetric` splits `LengthFwd` into total (83 wide needs `LengthFwd = 83`,
not 41.5). Sketcher `Distance` on an edge is a safe scalar length; no
axis-distance constraint was used anywhere, so the pinned `DistanceX`/`DistanceY`
negation quirk cannot bite. `Part::Box` `Placement` is the minimum corner, not
the centre.

## Compiler changes required by this migration

Two shared-compiler defects blocked the migration and are fixed here:

1. `compile_board.py` treated only `HangTenSchemaVersion == 2` as the
   slot-keyed schema, so the committed `schemaVersion: 3` packages fell through
   with an empty slot list and failed `contract.validate_bindings`. The check is
   now `version >= 2`.
2. `usdz_writer.py` wrote already-rotated **board-frame** points with an
   identity `/root` xform. Every approved Blender-sourced reference instead
   writes native Z-up points with a `(x, y, z) -> (x, z, -y)` `/root`
   rotation. The world meshes are identical either way, but the app authors its
   canonical camera directions in the mesh-local frame and rotates them with
   the board, so the board-frame CAD asset occluded the 16 mm/25 mm
   ceiling/floor contact ledges. The writer now matches the reference structure
   (`runtime_point` identity + `xformOp:rotateXYZ(-90, 0, 0)` on `/root`), and
   `read_usdz` rotates normals with the same local-to-world transform it
   already applied to positions. This does not change any board's world mesh.

## Verification

* Author asserts: pad bbox `(-52.5,-18.5,-38.5)-(52.5,18.5,38.5)` within 0.05;
  volume 221042 mm^3; contact `YLength` 16.000/25.000; slope void/solid probes,
  including two that discriminate the slope normal orientation; per-cut volume
  trace monotonic.
* Compiler: depths 16.0/25.0 exact; nodes `Cube_001`, `edge_16_mesh_001`
  (2 tris), `edge_25_mesh_001` (2 tris); source unchanged by reopen.
* `compare_exports.py` vs the retired reference: 0.0377 mm worst sampled
  deviation, both directions (limit 0.5 mm). Descriptor bounds identical.
* `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`
  exits 0 (64 complete, no drafts); manifest round-trips parsed-identical to
  the deleted `board.json`.
* `scripts/verify-model-delivery.py` passes after refreshing the lock's
  `sha256Manifest`; the lock still pins each committed file exactly.
* Python: `Tools/HangboardCAD/tests` + `Tools/HangboardPackages/tests`
  `778 passed, 9 skipped`.
* Native iOS (isolated Simulator, iPhone 16 Pro, iOS 26.5, signing enabled):
  the seven focused FTG-32 tests pass, and the full affected classes pass —
  `BoardModelTests` 75, `BoardSourceBoundaryTests` 18,
  `SuspendedBoardPresentationTests` 59 (152 passed, 0 failures). The
  `testJBryantFTG32CanonicalSelectedEdgesAreUnoccluded` regression now resolves
  every selected-contact triangle to its contact in both poses.

## Native app validation

PASSED. The exact build/test command, simulator identity, and the runs are
recorded in the task conversation. The retired reference is the sole
comparison target; the app-side fix was the `/root` structure above, not any
board-data change.
