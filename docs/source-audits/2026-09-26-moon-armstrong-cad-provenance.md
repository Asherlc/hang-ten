# Moon Armstrong native CAD migration

Date: 2026-09-26. Package `moon-armstrong`, revision `2026-09-contact-first`
(unchanged). The committed FCStd is the only source of the board geometry and
metadata. The one-off authoring script is workspace scratch at
`.context/eatable-racoon/author_moon_armstrong.py`. Rebuilding the package uses
only `Tools/HangboardCAD/compile_board.py`.

This is a display model re-authored from manufacturer evidence, in the manner
of `trango-rock-prodigy-pivot`. It is not recovered manufacturing geometry. It
makes no product-accuracy or load-bearing claim.

## Why the reference was not traced

The approved asset (prior USDZ SHA-256
`26e916d54b39f1f6afcf78b53bdc883a584dae0ff6e78d67fb8823ee1daf8e6a`) was a
marching-cubes display estimate. Its generator config is retained at
`2dd5182b4:.context/migration/source/hangboards-batch-01/models/moon-armstrong-ash/source/geometry-config.json`.
Checked against Moon's photographs (lessons §19), it was wrong about the
product:

- The centre 22 mm and 18 mm holds were open shelves cut into the board. The
  photos show proud rails.
- The edge slot floors were not at the published depths (the "8 mm" slot's
  floor was 22 mm deep).
- It had no tier steps; all slots were in one front plane.

The block layout (4-edge block, jug block, centre, 4-edge block, jug block) and
the 21 contact identities were right, and are kept.

## Evidence

Manufacturer text, identical on the [Beech](https://moonclimbing.com/moon-armstrong-fingerboard-beech.html),
[Ash](https://moonclimbing.com/moon-armstrong-fingerboard-ash.html) and
[Sycamore](https://moonclimbing.com/moon-armstrong-fingerboard-sycamore.html)
pages (accessed 2026-09-26): 65 cm × 16.5 cm × 5.5 cm, 2 × 35 degree slopers,
2 × 25/20/15/10/8 mm slots, 2 × 22 mm two-fingered pockets, 2 × 22 mm
one-fingered pockets, a central jug and central 22 mm and 18 mm edges.

Photographs (bytes not retained in the repository; SHA-256 of the downloaded
files):

| Image | SHA-256 | Used for |
| --- | --- | --- |
| [Moon blog, 20230927-DSC01046.jpg](https://moonclimbing.com/media/magefan_blog/20230927-DSC01046.jpg) (8775 × 5850, wall-mounted, near-orthographic) | `9e4193e26a1ef644b6b61e4ba19ce9ebbc4f3f4590daff09c3e22357d96826b5` | Every front-view coordinate |
| [Beech product photo 01](https://moonclimbing.com/media/catalog/product/6/0/60-112-bec_moon_armstrong_fingerboard_bec_01.jpg) | `21a4434780ca543b9d10b331e79f4e2882e2bfa53d807f2eb7cbb96af8a1f01c` | Aspect-ratio cross-check; sloped tops of the 4-edge blocks |
| [Ash product photo 01](https://moonclimbing.com/media/catalog/product/6/0/60-112-ash_moon_armstrong_fingerboard_ash_01.jpg) | `1ef01eb6fd7a5ac45e017d1146d8b3e37cad2ba68a4db7fd760c7f8a12ac59bc` | Layout cross-check |
| [Beech 02](https://moonclimbing.com/media/catalog/product/6/0/60-112-bec_moon_armstrong_fingerboard_bec_02.jpg), [Sycamore 02](https://moonclimbing.com/media/catalog/product/6/0/60-112-syc_moon_armstrong_fingerboard_syc_02.jpg) | `fc06c58f845627b633a4a85b8df9ba5bfef29f1ac1d691379123820ad0252cff`, `4334cc4c36357ec8e069f9580822915a27d62d519f7644724dfe7bb3c27557e8` | Proud centre bar with an arched notch through it; proud 22 mm rail |
| [Beech 04](https://moonclimbing.com/media/catalog/product/6/0/60-112-bec_moon_armstrong_fingerboard_bec_04.jpg) | `b3d0e96d893021f9e9639debd110db1b84a3ad163ab3da881663d99c47c58f40` | Mono is a through bore (pulley cord threaded through it) |
| Gripped Magazine, [DSC_1957](https://gripped.com/wp-content/uploads/2021/12/DSC_1957.jpg) and [DSC_1970](https://gripped.com/wp-content/uploads/2021/12/DSC_1970.jpg) (secondary; earlier plywood edition) | `b1c36cf512bb71497f7bb6b7c08533ae68d3219654eba299b4e86694d4b9cc02`, `f3ed965fdbe94e7fc7da8eef738478d13e4078db46e12c34360273624e396d39` | Tier fronts step back going down (ply laminations) |
| Owner-supplied plywood-edition views (end-on view of the far-left block; board lying face up), supplied in the task conversation | not retained | Tier depths; sloper on the 4-edge block tops; blocks proud of a thinner centre plate |

No first-party side view or dimensioned drawing exists (the two Moon YouTube
videos, `_eqSOtXyJNk` and `qGWWUzBYMQo`, are front views too). Depth-direction
values are therefore labelled estimates below.

## Scale and frame

Native frame: millimetres, +X right, +Z up, front −Y, back plane y = 0.

The front view was read by eye off 1 mm-gridded crops of the blog photo
(`Tools/HangboardCAD/photo_grid.py crop`, scale 12.91 px/mm, origin px
(4402, 3700) = bottom centre). The scale anchor is the published 650 mm width
over the front outline (px 207 to 8598).

**Conflict: height.** At 650 mm wide, the front outline measures about 153 mm
tall in both the blog photo and Beech photo 01 (width/height 4.24 and 4.29).
The photo is not foreshortened: the engraved logo disc images as a circle
(491 px wide, about 490 px tall). Moon publishes 16.5 cm. The operator chose
the width anchor on 2026-09-26. The model reaches 165 mm only at the back of
the two sloper blocks, which the photos' low camera cannot see. That is a
consistent reading of both facts, but it is not confirmed.

**Adaptation: perspective.** Each left-side block reads about 9 mm narrower
than its right-side twin (4-edge 99 vs 109 mm, jug 120.7 vs 128.6 mm), and the
centre features read 4.9 mm left of the midpoint. This is consistent with a
camera right of centre. The blocks are authored as repeated designs: widths are
the mean of each pair (4-edge 104, jug 124.7, gaps 16.5 mm). That gives a
159.6 mm centre section against 159.8 mm read directly. In-block positions are
averaged in normalized coordinates, with the far-right block's bottom tier
mirrored (mono and two-finger pocket swap sides, as photographed). The centre
is authored symmetric about x = 0.

## Authored geometry

Published: overall width 650, depth 55, sloper-block back height 165, slot
depths 25/20/15/10/8, pocket depths 22, centre edges 22/18, sloper angle 35°.

Read from the blog photo (± about 1 mm, then averaged as above):

- Block x-extents: B1 −325…−221, B2 −204.5…−79.8, B4 79.8…183.8,
  B5 200.3…325.
- 4-edge tiers (z): 25 mm 105.5…top, 20 mm 63.5…105.5, 10 mm 30.6…63.5,
  8 mm 0…30.6. Slot mouths (block-local x, z): 25 mm 7…96.4, 115…141;
  20 mm 7…96.4, 71…95; 10 mm 7…96.4, 36.7…54.3; 8 mm 10…93.5, 6.2…23.6.
  The front-top edge (sloper foot) is z 154.2.
- Jug tiers (z): jug 88.3…156 (flat top), 15 mm 40.5…88.3, low 0…40.5. Jug
  mouth 13.3…111.6, 110…141.5; 15 mm slot 18.2…111.5, 54…75; two-finger
  pocket 21.4…68.6, 10.6…30.4; mono Ø21 at (99.1, 20.5).
- Centre: bar x ±60, z 123.3…151 (corner r5); arched notch as a vertical
  stadium x ±19.1, z 89.5…137.5; 22 mm rail x ±48.4, z 62.5…88.8; 18 mm rail
  x ±46.9, z 1…26 (rail corners r8); field steps at z 57 and 110.5; exposed
  plate top z 135.5 between blocks.

Estimates (no dimensioned source; labelled):

- Tier front depths from the ply-lamination widths in the owner's end-on view:
  4-edge 55 / 43 / 35 / 31 mm; jug block 55 / 45 / 38 mm.
- Base plate 25 mm, centre field fronts 30 mm (middle) and 35 mm (upper), bar
  20 mm proud of the upper field, notch floor 33 mm.
- Jug pocket depth 35 mm (unpublished).
- 35° sloper plane from the 4-edge front-top edge (z 154.2) rising back to
  z 165, then flat. The operator's photos place the slopers on the 4-edge
  blocks, not the jug blocks.
- Round-overs: 3 mm on tile, rail and bar front edges and on hold mouths;
  6 mm tile corners. These are approximated by four ruled stations of a
  quarter circle.

Adaptation — mono depth: the monos are through bores, but the manifest gives
them a 22 mm depth. Each mono contact is the front 22 mm of its bore (the bore
loft has a station there, so the body face is split exactly), and the rest of
the bore stays body. Moon's "22mm one-fingered pocket" may describe the
opening size rather than the depth. The manifest is left unchanged.

Omitted: the logo engraving, "train hard / climb harder" text, screws, and
the pulley cord holes (hardware omission policy). Suspension metadata is
unchanged.

## Construction

Part workbench: static `Part::Feature` primitives (a box plate, and ruled
`Part.makeLoft` solids of rounded-rectangle sections for every tier, rail, bar
and hold cutter), combined by `Part::MultiFuse` (additions) and
`Part::MultiFuse` (cutters) into one `Part::Cut`, all with `Refine = False`.
Each tier is one loft from the back plane to its front with the round-over
stations. Each hold cutter is one loft from 1 mm in front of the face, through
the mouth round-over, to its floor.

Every contact region is a compound of copies of the compiled body's own faces.
A face is selected when its sample points lie on the hold's cutter, rail or bar
surface (pocket faces are also bounded to front…front + depth), or, for a
sloper, when it lies on the 35° plane within the block. Regions therefore
coincide exactly with the body surface they partition, and their Y extents
equal the published depths. The document sets `HangTenCurvedRegionPartition`
(conical mouth flares) and `HangTenSurfaceNormals`. The deflection is 0.1 mm.
The FCStd is 649 KB and tracked with Git LFS.

## Metadata

The hand-authored `board.json` is embedded as `HangTenBoardManifest`. The
generated file keeps the deleted one's values, key order and number
spellings, with one change. The model presentation's `aspectRatio` is now the
new descriptor `modelBounds` x/y ratio, `3.9393936268136036`. It was
`3.9573770458016795`, taken from the superseded mesh's bounds, and
`test_fixed_front_model_presentation_ratios_match_descriptor_bounds` requires
the two to agree. The top-level `aspectRatio` (1.4141666666666666) and every
sourced field are unchanged. Apart from that, only the `×` escape differs. All 21 contact IDs and all 22 node IDs of the previous descriptor are
kept.

## Verification

- `compile_board.py` check and publish: 21 contacts bound, published-depth
  gate exact on every declared depth, 62,674 triangles, USDZ 1.9 MB (was
  4.3 MB).
- `verify_reproducible.py --package moon-armstrong`: byte-identical rebuild on
  the pinned macOS toolchain (FreeCAD 1.1.3, OCCT 7.8.1, OpenUSD 26.08).
- Package validation with `--final-inventory` and
  `scripts/verify-model-delivery.py` pass. The delivery lock was refreshed.
- Front, side and top previews next to the previous asset, the
  model-over-manufacturer-photo overlay, and the app captures are in
  `docs/pr-screenshots/moon-armstrong/`. The overlay aligns block outlines,
  every mouth, both rails and the notched bar with the photo. The one
  exception is the sloper backs rising to 165 mm, which the photo does not
  show.
- iOS Simulator (iPhone 17 Pro, iOS 26.5, Debug, board-detail route):
  `sloper-left` (default), `jug-left`, `sloper-right`, `center-jug`,
  `mono-right`, `edge-8-left` and `center-edge-18` were each opened by deep
  link. Each was confirmed via `boardDetail.selectedHold.<contactID>`, and the
  highlight landed on the right region. The simulator device was created and
  deleted by the review script's exit trap.
- `compare_exports.py` was not used as evidence, because the reference
  contradicts the manufacturer photos (see above).

## Open questions for review

- Is the true height 165 mm at the front, or only at the sloper backs?
- Tier depths, plate thickness and jug depth are photo-read estimates from
  the plywood edition; the hardwood edition may differ.
