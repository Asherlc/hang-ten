# metolius-wood-grips-deluxe-ii CAD authoring provenance

Date: 2026-09-24

`Hangboards/metolius-wood-grips-deluxe-ii/metolius-wood-grips-deluxe-ii.FCStd` was
authored by a throwaway script under `.context/`, which was not committed (see
`docs/freecad-authoring-migration.md`). The committed FCStd stands alone. Its
embedded `HangTenBoardManifest` is the previously hand-authored `board.json`.
The regenerated file is token-identical to it, except that the front
presentation `aspectRatio` changed from `2.8347345959048824` to
`2.8240740604423875`. That value is the new descriptor's `modelBounds` x/y
ratio (610 × 216 mm); the old one was the ratio of the voxel mesh bounds
(608.76 × 214.75 mm). The top-level `aspectRatio` `2.0` is unchanged.

This record keeps the trail from the published product facts and the
pre-migration generator to the authored document.

## Dimension source

The approved pre-migration asset was generated from explicit numbers, not
traced from images. Its generator is a signed-distance model in
`geometry.py`, and its numbers are in `geometry-config.json`. That generator
voxelised the model at 0.8 mm, meshed it with marching cubes, and decimated it
to 65k triangles. Both files are readable from Git:

```sh
P=.context/migration/source/hangboards-batch-01/models/metolius-wood-grips-ii-deluxe
git show 7120457fe3^:$P/source/geometry-config.json
git show 7120457fe3^:$P/source/geometry.py
git show 7120457fe3^:$P/sources.md
```

Its coordinates are millimetres, X right, Y rear with the front at -Y, Z up, and
its origin is rear-bottom-centre. That is already the native FreeCAD frame, so
every number below was carried over without transformation. The reference USDZ
(`reference.py` commit `6b828e15`, SHA-256
`cfdf112a2f4ebecb69ebeca2a2102af3e64bcb72a08ba90cb555e60fa50e16e6`) was used
only as a comparison. The mounting bores in the config were deleted in
e89ad9957, and they stay omitted under the repository's screw-hole/hardware
omission policy.

## Sourced versus approximated fields

| Field | Status | Evidence |
| --- | --- | --- |
| Face 610 × 216 mm (24 × 8.5 in); `board.json` `dimensions` `24 × 8.5 in` | Published | <https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards>: "24" x 8.5" (610 mm x 216 mm)"; re-fetched 2026-09-24 |
| 26-contact inventory (#1 jugs, #2 flat slopers, #3/#6/#9 edges, #4/#7/#10 three-finger, #5/#8/#11 two-finger, #12 round sloper, #13/#14/#15 four-finger) | Published | Metolius numbered Deluxe diagram (M-DIAGRAM-V2, hosted at <https://www.backcountry.com/images/items/1200/MET/MET007G/ONECOL_D3.jpg>), as recorded in the pre-migration `sources.md` |
| Depths 31/32/38, 25/25/28, and 19 mm (the compiler's published-depth gate) | Published | same diagram; the authored pocket `Length` equals each value, and each region's Y extent measures exactly that depth |
| 70 mm projection | Retained estimate | retailer rounded "60 × 22 × 7 cm" (<https://8a.pl/chwytotablica-metolius-wood-grips-ii-deluxe>); Metolius publishes no projection. A 2026-09-24 web search found no other projection figure. |
| Stepped three-tier side profile (`profileYZ`, 16 vertices) and front outline (`outlineXZ`, 16 vertices) | Retained estimate | pre-migration config, which labels them "authored photo-derived estimates" |
| Pocket centres, widths (48 / 78 / 110 mm), height 25 mm, radius 12.5 mm, and floor positions (`floorY`) | Retained estimate, except depth | pre-migration config |
| 1.2 mm floor and 2 mm mouth blends | Retained estimate, **represented as chamfers** | config `floorFillet` 1.2 and `lipRound` 2 were smooth blends. They are authored as chamfers of the same size, because toroidal fillets on these arcs tessellate to about 300k triangles (see lessons §15). This is a stated display choice. |
| 3 mm end rounds and 2.5 mm outline rounds | **Omitted** | config `endRoundMm`, `outlineRoundMm`; the body edges are sharp. This is the main source of the `compare_exports` deviation below. |
| Top-region boundaries at x = ±238 and ±81 mm | Authored from outline vertices | the config selectors used ±240/±238 and ±80/±79; the boundaries were moved onto the outline vertices so each top hold owns whole faces |
| Material: `neutral_product_material`, base colour 0.73, 0.58, 0.39, roughness 0.75, metallic 0 | Carried | colour from the config `color`; roughness from the reference `UsdPreviewSurface`. The reference `dummy_texture.png` is a 1 × 1 black pixel and is not embedded. |
| Node IDs (`body_001`, `hold_NN_…_001`) | Carried | reference descriptor |

## Document structure

Document properties: `HangTenSchemaVersion` 1, `HangTenSourceKind`
`native-parametric-measured-profile`, `HangTenCoordinateFrame`
`freecad-mm-z-up-front-negative-y`, `HangTenTessellationDeflection` 0.05, and
`HangTenCurvedRegionPartition` true. The last opts into the curved-region
partition, which is needed because the hold walls are cylinders and the
chamfers are cones.

- `Body` (`PartDesign::Body`, node `body_001`):
  - `ProfileSketch0`–`4` (lines only) and `ProfilePad0`–`4`: the side profile
    padded over x = [-310, -238, -81, 81, 238, 310] with `Refine = False`, so the
    top-region boundaries are real edges.
  - `OutlineSketch` and `OutlineTrim`: a through-all pocket that removes
    everything outside the front outline. This also sets the board ends at
    x = ±305.
  - `Sketch_<hold>` and `Pocket_<hold>` (21 of each): a capsule of two lines and
    two arcs, on its tier front plane (y = -70, -55, or -43), with pocket
    `Length` equal to the published depth.
  - `FloorChamfers` (1.2 mm, 78 edges) and `MouthChamfers` (2 mm, 102 edges).
    The six floor edges that lie on the board end faces are excluded.
- 26 `Contact_*` `Part::Feature` objects: each is a copy of the body faces its
  hold owns, carrying `NodeID`, `ContactID`, and `HangTenHoldOutline`.
  - A pocket or edge owns every face that lies behind its tier front plane, no
    deeper than its floor, and inside the capsule grown by the 2 mm mouth.
  - A top hold owns the up-facing faces above z = 185 mm within its x span.

  The outline is the mouth capsule, clipped at x = ±305 for side-open edges.
  For jugs and slopers it is the region's bounding rectangle. Because these are
  static copies, editing a pocket `Length` moves the body but not its contact
  object; the published-depth gate catches that mismatch. The sketch-and-pad
  edit-propagation suite is not claimed.

## Evidence

- Compile: 23,260 triangles (body 2,572). The compiled asset has no unpaired
  open edges. Every published-depth gate is exact
  (31/32/38, 25/25/28, and 19 mm). `modelBounds` is 610 × 216 × 70 mm, and the
  build is byte-reproducible (`verify_reproducible.py`).
- `compare_exports`: worst two-way sampled deviation 1.94 mm (limit 0.5 mm;
  18,082 reference and 23,260 candidate triangles). **Accepted deviation:** the
  reference is a voxelised and decimated rendering of the same config. The
  difference comes from the omitted end and outline rounds, and from
  chamfered versus rounded pocket mouths.
- Descriptor `facePlaneAABB` against the reference, in mm:
  - Pockets and edges: 0.4–2.0, except `edge-3-31-left` at 4.9 and
    `pocket-5-38-two-left` at 11.1. At those two holds the reference is
    asymmetric against its own config: its left two-finger node is 62 mm wide
    against the 52 mm authored mouth.
  - Top regions: 15–43. The reference's decimated triangles spilled outside
    its selection boxes; for example, its jug node reaches down to z = 143 mm.
- In app: iPhone 17 Pro simulator (iOS 26.5), Debug board-detail review route.
  Wood colour renders, and three holds were each selected and confirmed via
  `boardDetail.selectedHold.<id>`:
  - `jug-1-left`, the default selection;
  - `pocket-5-38-two-left`, which highlights as one capsule, walls included,
    with depth 38 mm;
  - `edge-3-31-left`, a side-open edge that runs out through the board end.
- Not verified: suspension, accessibility, and performance.
