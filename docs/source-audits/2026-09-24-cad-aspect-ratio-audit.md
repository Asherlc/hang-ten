# CAD board `aspectRatio` audit (2026-09-24)

Scope: the FreeCAD-backed packages whose `board.json` is generated from the
`HangTenBoardManifest` property of `Hangboards/<slug>/<slug>.FCStd`: the five
audited first, and `metolius-prime-rib`, added when its source was merged with
the build-time generation (see the addendum below). The question was whether each
manifest `aspectRatio` (top level and the single model presentation, which are
equal on all six) is correct, should be corrected, or should be derived from the
CAD geometry at build time.

Result: **all six values are kept unchanged. No FCStd geometry, descriptor or
generator change was made for this audit.**

## What `aspectRatio` means for model media

* Raster presentations: the package validator
  (`board_catalog.py`, `_ASPECT_RATIO_RELATIVE_TOLERANCE`) and
  `BoardPackageStore.validatePresentationAspectRatio` require it to match the PNG
  width/height within 0.1%. No such rule exists for model media; both only
  require a positive finite number.
* iOS model rendering: `BoardMapView` sizes the viewport box with
  `.aspectRatio(presentation.aspectRatio, contentMode: .fit)`. Inside that box the
  camera is fitted from geometry, not from the stored value:
  `BoardModelScene.framing` projects `modelBounds` (or, for reusable instances,
  the union of every instance's transformed bounds plus suspension cord points)
  and `frame(in:)` sets
  `orthographicScale = max(height, width / viewportAspect) * fitPadding / 2`.
  A stored value that differs from the projected geometry therefore only adds
  letterbox margin; it never crops or distorts the model.
  `BoardPresentation.aspectRatio(for:)` replaces the stored value with the
  geometry framing when the media has `orientation` metadata.
* Android: `BoardCanvas` uses the top-level `aspectRatio` for its canvas box.
* Catalog convention (measured over all 46 model presentations, the five CAD
  boards included): 19 store the descriptor x-span / y-span bit-exactly, 14 store
  a rounded or exact-rational value within 1.2e-7 relative (for example
  `1.7142857` = 12/7 on `captain-fingerfood-dual`), and 13 store a deliberate
  display/layout value that is not the single-unit front ratio (for example
  `trango-rock-prodigy-pivot` 2.0, `yy-penta-evo` 1.5, `tension-flash-board`
  1.5). Only `test_fixed_front_model_presentation_ratios_match_descriptor_bounds`
  pins bounds equality, and only for six named non-CAD packages.

## Per-board findings

"Descriptor ratio" is `(max.x - min.x) / (max.y - min.y)` of
`assets/primary.model.json` `modelBounds` (runtime metres, front view is +Z).

| Board | Stored (kept) | Descriptor ratio | Relative diff | Decision |
| --- | --- | --- | --- | --- |
| `captain-fingerfood-pocket` | `1.6666667` | `1.6666666666666665` (0.110 / 0.066) | 2.0e-8 | (a) keep |
| `lattice-mxedge-lift-large` | `1.7142857142857142` | `1.714285728862974` (0.167999998 / 0.097999998) | 8.5e-9 | (a) keep |
| `lattice-mxedge-lift-small` | `1.7142857142857142` | `1.714285728862974` (same brick) | 8.5e-9 | (a) keep |
| `lattice-triple-rung` | `4.2307694857988265` | `4.2307694857988265` | 0 | (a) keep |
| `metolius-rock-rings-3d` | `1.5` | `0.79347825` (0.146 / 0.184, one ring) | n/a (pair layout) | (a) keep |
| `metolius-prime-rib` | `4.7619050011605735` | `4.7619050011605735` (0.508000016 / 0.106679998) | 0 | (a) keep |

### captain-fingerfood-pocket — keep `1.6666667`

* Evidence: manufacturer dimensions `110 × 66 × 29 mm`
  (productURL <https://en.captainfingerfood.rocks/products/lines-hangboard>),
  front face 110 × 66 mm = 5/3. The measured CAD envelope is the same
  110 × 29 × 66 mm (native x × depth × height; see
  `2026-09-24-captain-fingerfood-pocket-cad-provenance.md`) and the descriptor
  bounds are ±0.055 / ±0.033 m.
* The stored value is 5/3 rounded to 7 decimals; the 2e-8 difference is below
  one device pixel on any viewport and has been unchanged since before the
  shallow-history root (`b5aa7c2`, 2026-09-15).

### lattice-mxedge-lift-large and lattice-mxedge-lift-small — keep `1.7142857142857142`

* Evidence (measured geometry, not a published fact): both provenance docs
  record a mesh envelope of 168 × 34 × 98 mm, measured from the Git-resolved
  reference USDZ; the front face is 168 × 98 mm = 12/7 exactly, which is what the
  stored double is. The descriptor's 0.167999998 / 0.097999998 is float32 export
  noise on the same envelope.
* The published catalogue string `20 × 11 × 5 cm`
  (<https://latticetraining.com/app/uploads/2026/01/Lattice_Catalogue_25_Web_161225.pdf>)
  is a rounded shared string (20/11 = 1.818) and is not a basis for the ratio;
  the provenance docs already document that the geometry follows the mesh.
* Unchanged since `b5aa7c2`.

### lattice-triple-rung — keep `4.2307694857988265`

* Bit-identical to the descriptor ratio (0.550000012 / 0.129999995). Published
  size `55 × 13 × 5 cm`
  (<https://latticetraining.com/product/triple-rung-wooden-hangboard/>) gives
  550/130 = 4.2307692; the stored value is that ratio as carried through the
  float32 bounds. Unchanged since `b5aa7c2`.

### metolius-rock-rings-3d — keep `1.5`

* This is a schema-v2 reusable-instance presentation: two ring instances
  (`left-ring`, `right-ring`) with identity base transforms that are placed side
  by side by their suspension `canonicalPoses` (translation x = −0.105 / +0.105 m,
  itself labelled `authored-display-estimate`). The descriptor `modelBounds`
  describe **one** ring (146 × 184 mm, published `184 × 146 × 57 mm` on
  <https://www.metoliusclimbing.com/collections/training-equipment/products/rock-rings-3d>),
  so 0.793 is the ratio of a single unit and would be the wrong viewport shape
  for the pair.
* Origin of `1.5`: before the 3D migration (`8fe0662`, 2026-09-20) the package
  had a raster `front-pair` presentation whose `assets/primary.png` was
  1536 × 1024 px (read from commit `b5aa7c2`), i.e. exactly 1.5, and the raster
  validator enforced that match. The PNG followed the official straight-on
  paired product photograph cited in
  `2026-08-20-complete-hangboard-catalog.md`
  (<https://www.metoliusclimbing.com/cdn/shop/files/Rock-Rings-black-white.jpg?v=1759460123>).
  The migration kept the value as the paired viewport shape.
* The pair's projected geometry depends on display estimates: measured with
  the presentation camera (`viewDirection [0, -0.1, -1]`), the two ring boxes
  alone project to 0.356 × 0.189 m (≈ 1.89), and adding the two invisible
  overhead anchors (`offsetFromBoardBounds` y = 0.19 m) gives 0.356 × 0.375 m
  (≈ 0.95). Neither is a sourced fact, and the renderer fits whichever it
  computes into the 1.5 box, so there is no correctness defect to fix and no
  source that would justify a different number.

### metolius-prime-rib — keep `4.7619050011605735`

* Bit-identical to the descriptor ratio (0.508000016 / 0.106679998 m). Published
  size `20" x 4.2" x 1.5"` (<https://www.metoliusclimbing.com/products/prime-rib>,
  "Specs & Details"; manifest `dimensions` "20 × 4.2 × 1.5 in") gives
  20 / 4.2 = 4.7619047619; the stored value is that ratio carried through the
  float32 bounds (5.0e-8 relative). The native source's envelope is authored to
  the published 508 × 106.68 mm (`BoardThickness`/`BoardHeight` and the pad
  length in `2026-09-24-metolius-prime-rib-cad-provenance.md`), so the
  recompiled descriptor keeps the same `modelBounds`. Unchanged since `b5aa7c2`.

## Why not derive `aspectRatio` at build time

* It is not safe for all six: for `metolius-rock-rings-3d` the single-unit
  `modelBounds` ratio (0.793) is wrong for the paired layout, and a pair-aware
  derivation would depend on display-estimate spacing and cord/anchor geometry.
* For the other five it would only replace exact or sourced ratios
  (5/3, 12/7) with float32-noise ratios, a change of ≤ 2e-8 with no visible
  effect, while altering generated `board.json` bytes and the FCStd-locked
  delivery inventory for no benefit.
* Therefore `aspectRatio` stays an authored manifest field, as documented in
  `Tools/HangboardCAD/README.md`. Note that the README's reason ("not reproducible
  from the descriptor's `modelBounds` for most boards") is accurate for the
  whole model catalog but, among the six CAD boards, the only non-reproducible
  one is the paired `metolius-rock-rings-3d`; the other five reproduce within
  2e-8 (`metolius-prime-rib` bit-exactly).

## App rendering and tests

No value changed, so camera fit, snapshots and fixtures are unaffected. Tests
that read these values: `HangTenTests/BoardModelTests.swift` sizes test
viewports from `defaultPresentation.aspectRatio`; no Swift, Kotlin or Python
test pins any of the first five CAD boards' ratios.
`test_prime_rib_package_freezes_the_official_three_edge_inventory`
(`Tools/HangboardPackages/tests/test_approved_board_packages.py`) pins
`metolius-prime-rib`'s `4.7619050011605735`, as it did before the migration.

## Verification (2026-09-24)

* `Tools/HangboardPackages`: `python -m pytest tests -q` → 718 passed.
* `python scripts/verify-model-delivery.py` → exit 0.
* `python -m pytest Tools/HangboardModels/tests/test_model_delivery_alignment.py -q` → 8 passed.
* `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` →
  exit 0, 64 boards, 0 drafts.
* `scripts/stage-board-packages.py --target android` into a scratch
  `Hangboards` directory → exit 0; staged `board.json` for the five boards
  carries the values in the table above (top level and presentation).

### Addendum: metolius-prime-rib (2026-09-24)

* `scripts/stage-board-packages.py` (Xcode layout and `--target android`) into
  scratch directories → exit 0; the staged `metolius-prime-rib/board.json` is
  byte-identical to `board_manifest.py --all --output-dir` output and to the
  `board.json` last committed at `657a303`, carrying `4.7619050011605735` (top
  level and presentation).
* `scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` →
  exit 0; `python scripts/verify-model-delivery.py` → exit 0 with six
  source-backed packages.
